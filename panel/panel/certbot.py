import os
import time
import tempfile
from . import sysops
from . import config
from datetime import datetime, timedelta

HA_CERTS_DIR = '/etc/ssl/ha-certs/'
LE_LIVE_DIR = '/etc/letsencrypt/live/'


def _user_certs_dir():
    return config.get_root_dir() + 'certs'


def _ha_cert_path(domain):
    return HA_CERTS_DIR + domain + '.pem'


def _user_cert_path(domain):
    return os.path.join(_user_certs_dir(), domain + '.pem')


def _le_fullchain_path(domain):
    return LE_LIVE_DIR + domain + '/fullchain.pem'


def _le_privkey_path(domain):
    return LE_LIVE_DIR + domain + '/privkey.pem'


def _looks_like_combined_pem(text):
    """HAProxy needs a certificate and a private key in the same file."""
    if not text or not text.strip():
        return False
    has_cert = '-----BEGIN CERTIFICATE-----' in text
    has_key = (
        '-----BEGIN PRIVATE KEY-----' in text
        or '-----BEGIN RSA PRIVATE KEY-----' in text
        or '-----BEGIN EC PRIVATE KEY-----' in text
        or '-----BEGIN ENCRYPTED PRIVATE KEY-----' in text
    )
    return has_cert and has_key


def _read_valid_pem(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r') as f:
            text = f.read()
    except OSError:
        return None
    if not _looks_like_combined_pem(text):
        return None
    return text


def _atomic_write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix='.pem-', suffix='.tmp', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _install_pem(domain, content, reload_haproxy=True):
    cert_file = _ha_cert_path(domain)
    if not _looks_like_combined_pem(content):
        print('  - Refusing to install empty or incomplete certificate for ' + domain)
        return False

    prev = _read_valid_pem(cert_file)
    if prev is not None and hash(prev) == hash(content):
        print('  - Certificate file unchanged')
        return False

    _atomic_write(cert_file, content)

    if reload_haproxy:
        print('  - Reloading HAProxy')
        sysops.haproxy_reload()
    return True


def save_cert(domain, reload_haproxy=True):
    """Install a Let's Encrypt fullchain+privkey into HAProxy's cert dir.

    Sources are read and validated before the live HAProxy PEM is touched, so a
    failed or empty certbot run cannot truncate a working certificate.
    """
    fullchain_file = _le_fullchain_path(domain)
    privkey_file = _le_privkey_path(domain)

    try:
        with open(fullchain_file, 'r') as f:
            fullchain = f.read()
        with open(privkey_file, 'r') as f:
            privkey = f.read()
    except OSError as e:
        print('  - Let\'s Encrypt files missing or unreadable, not writing HAProxy cert: ' + str(e))
        return False

    content = fullchain + privkey
    if not _looks_like_combined_pem(content):
        print('  - Let\'s Encrypt files empty or incomplete, not writing HAProxy cert')
        return False

    return _install_pem(domain, content, reload_haproxy=reload_haproxy)


def save_user_cert(domain, reload_haproxy=True):
    """Install a user-provided combined PEM into HAProxy's cert dir."""
    content = _read_valid_pem(_user_cert_path(domain))
    if content is None:
        print('  - User-provided certificate missing or invalid for ' + domain)
        return False
    return _install_pem(domain, content, reload_haproxy=reload_haproxy)


def cert_exists(domain):
    return _read_valid_pem(_ha_cert_path(domain)) is not None


def user_cert_exists(domain):
    return _read_valid_pem(_user_cert_path(domain)) is not None


def cleanup_invalid_certs():
    """Remove empty or incomplete PEMs from HAProxy's cert dir.

    HAProxy loads every *.pem under /etc/ssl/ha-certs/. An empty leftover from a
    failed certbot write makes it refuse to start. selfsigned.pem is left alone.
    Returns True if any file was removed.
    """
    if not os.path.isdir(HA_CERTS_DIR):
        return False

    removed = False
    for name in os.listdir(HA_CERTS_DIR):
        if not name.endswith('.pem') or name == 'selfsigned.pem':
            continue
        path = os.path.join(HA_CERTS_DIR, name)
        if _read_valid_pem(path) is not None:
            continue
        print('  - Removing invalid/empty HAProxy cert ' + path)
        try:
            os.remove(path)
            removed = True
        except OSError as e:
            print('  - Failed to remove ' + path + ': ' + str(e))
    return removed


def generate_certificate(domain, retry=True, reload_haproxy=True):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domain_certificates = db.domain_certificates
    domain_entry = domain_certificates.find_one({'_id': domain})

    # Drop a leftover empty PEM for this domain so HAProxy can load the rest.
    ha_path = _ha_cert_path(domain)
    if os.path.isfile(ha_path) and _read_valid_pem(ha_path) is None:
        print('  - Removing invalid/empty HAProxy cert for ' + domain)
        try:
            os.remove(ha_path)
        except OSError:
            pass

    # Manual override / fallback: a combined PEM at {root}/certs/<domain>.pem
    # wins so the panel works with no Let's Encrypt access.
    if user_cert_exists(domain):
        print('  - Using user-provided certificate for ' + domain)
        try:
            changed = save_user_cert(domain, reload_haproxy=reload_haproxy)
            if changed:
                return 'success'
            return 'unchanged'
        except Exception as e:
            print('  - Error installing user-provided certificate for ' + domain + ': ' + str(e))
            # Fall through to certbot if the manual file could not be installed.

    if domain_entry is not None:
        try:
            if domain_entry['updated_at'] > datetime.now() - timedelta(days=1):
                if not cert_exists(domain):
                    print('Certificate for ' + domain + ' does not exist. Regenerating.')
                else:
                    print('Certificate for ' + domain + ' is still valid. Skipping.')
                    return 'skipped'
            if domain_entry['skip_until'] > datetime.now():
                print('Certificate for ' + domain + ' is skipped due to multiple failures. Skipping.')
                return 'skipped_multiple_failures'
        except Exception:
            pass

    email_address = 'info@' + domain
    print('*** Generating certificate for ' + domain)

    result = sysops.run_command('certbot certonly --standalone -d ' + domain + ' --agree-tos --email ' +
                                email_address + ' --non-interactive' + ' --http-01-port 9999')
    if result == 256 and retry:
        print('  - Certificate generation failed (256). Retrying in 10 seconds.')
        time.sleep(10)
        result = sysops.run_command('certbot certonly --standalone -d ' + domain + ' --agree-tos --email ' +
                                    email_address + ' --non-interactive' + ' --http-01-port 9999')

    if result == 0:
        print('  - Certificate generated successfully')
        saved = save_cert(domain, reload_haproxy=reload_haproxy)

        print('  - Finalizing')
        domain_certificates.update_one({'_id': domain}, {'$set': {
            '_id': domain,
            'updated_at': datetime.now(),
            'failure_count': 0,
            'skip_until': datetime.now()
        }}, upsert=True)

        if saved:
            return 'success'
        return 'unchanged'

    print('  - Certificate generation for ' + domain + ' failed: ' + str(result))

    # Do not copy leftover LE files unless they form a valid combined PEM.
    saved = False
    try:
        if os.path.isfile(_le_fullchain_path(domain)) and os.path.isfile(_le_privkey_path(domain)):
            print('  - Checking leftover Let\'s Encrypt files')
            saved = save_cert(domain, reload_haproxy=False)
    except Exception as e:
        print('  - Error saving certificate:', e)

    if not saved and user_cert_exists(domain):
        print('  - Falling back to user-provided certificate for ' + domain)
        try:
            saved = save_user_cert(domain, reload_haproxy=reload_haproxy)
            if saved:
                return 'failed_but_changed'
        except Exception as e:
            print('  - Error installing user-provided certificate:', e)

    domain_certificates.update_one({'_id': domain}, {'$set': {
        '_id': domain,
        'failure_count': domain_entry['failure_count'] + 1 if domain_entry is not None else 1,
        'updated_at': datetime.now() - timedelta(days=100),
        'skip_until': datetime.now() + timedelta(hours=3) if domain_entry is not None and domain_entry['failure_count'] > 5 else datetime.now() + timedelta(minutes=5),
    }}, upsert=True)

    if saved:
        return 'failed_but_changed'
    return 'failed'
