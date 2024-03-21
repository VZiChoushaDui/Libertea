import os
import time
import random
from . import sysops
from . import config
from datetime import datetime, timedelta

def save_cert(domain, reload_haproxy=True):
    fullchain_file = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
    privkey_file = '/etc/letsencrypt/live/' + domain + '/privkey.pem'
    cert_file = '/etc/ssl/ha-certs/' + domain + '.pem'

    prev_file_hash = None
    if os.path.isfile(cert_file):
        with open(cert_file, 'r') as f:
            prev_file_hash = hash(f.read())
            
    with open(cert_file, 'w') as f:
        f.write(open(fullchain_file).read())
        f.write(open(privkey_file).read())

    new_file_hash = None
    with open(cert_file, 'r') as f:
        new_file_hash = hash(f.read())

    if prev_file_hash == new_file_hash:
        print('  - Certificate file unchanged')
        return False

    if reload_haproxy:
        print('  - Reloading HAProxy')
        sysops.haproxy_reload()
    return True

def cert_exists(domain):
    cert_file = '/etc/ssl/ha-certs/' + domain + '.pem'
    return os.path.isfile(cert_file)

def generate_certificate(domain, retry=True, reload_haproxy=True):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domain_certificates = db.domain_certificates
    domain_entry = domain_certificates.find_one({'_id': domain})
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
        except Exception as e:
            pass
    
    # generate certificate
    email_address = 'info@' + domain 
    print('*** Generating certificate for ' + domain)

    result = sysops.run_command('certbot certonly --standalone -d ' + domain + ' --agree-tos --email ' +
                                email_address + ' --non-interactive' + ' --http-01-port 9999')
    if result == 256 and retry:
        # try again after 10 seconds
        print('  - Certificate generation failed (256). Retrying in 10 seconds.')
        time.sleep(10)
        result = sysops.run_command('certbot certonly --standalone -d ' + domain + ' --agree-tos --email ' +
                                    email_address + ' --non-interactive' + ' --http-01-port 9999')

    if result == 0:
        print('  - Certificate generated successfully')
        result = save_cert(domain, reload_haproxy=reload_haproxy)

        print('  - Finalizing')
        domain_certificates.update_one({'_id': domain}, {'$set': {
            '_id': domain, 
            'updated_at': datetime.now(),
            'failure_count': 0,
            'skip_until': datetime.now()
        }}, upsert=True)

        if result:
            return 'success'
        return 'unchanged'
    else:
        print('  - Certificate generation for ' + domain + ' failed: ' + str(result))

        fullchain_file = '/etc/letsencrypt/live/' + domain + '/fullchain.pem'
        privkey_file = '/etc/letsencrypt/live/' + domain + '/privkey.pem'

        result = False
        try:
            if os.path.isfile(fullchain_file) and os.path.isfile(privkey_file):
                print('  - Saving certificate')
                result = save_cert(domain, reload_haproxy=False)
        except Exception as e:
            print(e)

        domain_certificates.update_one({'_id': domain}, {'$set': {
            '_id': domain,
            'failure_count': domain_entry['failure_count'] + 1 if domain_entry is not None else 1,
            'updated_at': datetime.now() - timedelta(days=100),
            'skip_until': datetime.now() + timedelta(hours=3) if domain_entry is not None and domain_entry['failure_count'] > 5 else datetime.now() + timedelta(minutes=5),
        }}, upsert=True)
        
        if result:
            return 'failed_but_changed'
        return 'failed'
    
