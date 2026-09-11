import base64
import math
import random
import re
import subprocess
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

import requests

RELAYS_URL = 'https://api.mullvad.net/www/relays/wireguard/'
AUTH_URL = 'https://api.mullvad.net/auth/v1/token'
DEVICES_URL = 'https://api.mullvad.net/accounts/v1/devices'
WG_PORT = 51820
WG_MTU = '1280'
RELAY_CACHE_TTL = 6 * 3600
RELAY_ERROR_TTL = 60
RELAY_TIMEOUT = 12
TOKEN_CACHE_TTL = 30 * 60
HTTP_ROTATE_COOLDOWN = timedelta(minutes=5)
TICK_INTERVAL = 60
REQUEST_TIMEOUT = 30
DEFAULT_ROTATE_DAYS = 1
DEFAULT_ROTATE_HOUR = 0
# Fixed choices shown in the UI — a free-form day count invites off-by-one
# schedules (e.g. "every 4 days") that are hard to reason about at a glance.
ROTATE_DAY_CHOICES = [1, 2, 3, 5, 7, 10, 14, 20, 30]
# Rotation slots are phase-locked to this instant, so the chosen hour keeps its
# meaning instead of drifting with whenever the last rotation happened.
_SCHEDULE_EPOCH = datetime(2000, 1, 1)

_relay_lock = threading.Lock()
_relay_cache = {'at': 0.0, 'relays': None, 'error_at': 0.0, 'error': ''}
_token_lock = threading.Lock()
_token_cache = {}  # account -> (token, expiry_epoch)
_tick_lock = threading.Lock()
_agent_started = False


class MullvadError(ValueError):
    """User-facing Mullvad API or configuration error."""


class MullvadDeviceLimitError(MullvadError):
    """The account already holds the maximum number of devices."""


def normalize_account(value):
    """Mullvad account numbers are digits only, so spacing and dashes are noise."""
    return re.sub(r'[^0-9]', '', str(value or ''))


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hex_block_after(text, label):
    lines = text.splitlines()
    collecting = False
    parts = []
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if not collecting:
            if lower.startswith(label.lower()):
                collecting = True
                rest = stripped[len(label):].strip()
                if rest:
                    parts.append(rest)
            continue
        if lower.startswith('pub:') or lower.startswith('priv:') or lower.startswith('-----'):
            break
        if re.fullmatch(r'[0-9a-fA-F: \t]+', stripped):
            parts.append(stripped)
            continue
        break
    return re.sub(r'[^0-9a-fA-F]', '', ''.join(parts))


def generate_wireguard_keypair():
    """Return (private_key, public_key) as WireGuard base64 strings."""
    try:
        priv = subprocess.run(
            ['wg', 'genkey'], capture_output=True, text=True, timeout=10, check=True,
        ).stdout.strip()
        pub = subprocess.run(
            ['wg', 'pubkey'], input=priv + '\n', capture_output=True, text=True,
            timeout=10, check=True,
        ).stdout.strip()
        if priv and pub:
            return priv, pub
    except (OSError, subprocess.SubprocessError):
        pass

    pem = subprocess.run(
        ['openssl', 'genpkey', '-algorithm', 'X25519'],
        capture_output=True, timeout=15,
    )
    if pem.returncode != 0:
        raise MullvadError('Could not generate a WireGuard keypair.')
    text = subprocess.run(
        ['openssl', 'pkey', '-text', '-noout'],
        input=pem.stdout, capture_output=True, timeout=15,
    )
    if text.returncode != 0:
        raise MullvadError('Could not generate a WireGuard keypair.')
    raw = text.stdout.decode('utf-8', errors='replace')
    priv_hex = _hex_block_after(raw, 'priv:')
    pub_hex = _hex_block_after(raw, 'pub:')
    try:
        priv_bytes = bytes.fromhex(priv_hex)
        pub_bytes = bytes.fromhex(pub_hex)
    except ValueError:
        raise MullvadError('Could not generate a WireGuard keypair.')
    if len(priv_bytes) != 32 or len(pub_bytes) != 32:
        raise MullvadError('Could not generate a WireGuard keypair.')
    return (
        base64.b64encode(priv_bytes).decode('ascii'),
        base64.b64encode(pub_bytes).decode('ascii'),
    )


def fetch_relays(force=False):
    now = time.time()
    with _relay_lock:
        cached = _relay_cache['relays']
        if not force and cached is not None and now - _relay_cache['at'] < RELAY_CACHE_TTL:
            return cached
        # Networks that block api.mullvad.net would otherwise pay the full
        # timeout again on every retry.
        if cached is None and now - _relay_cache['error_at'] < RELAY_ERROR_TTL:
            raise MullvadError(_relay_cache['error'])
    try:
        response = requests.get(RELAYS_URL, timeout=RELAY_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        if cached is not None:
            return cached
        message = 'Could not load Mullvad server list: ' + str(e)
        with _relay_lock:
            _relay_cache['error_at'] = now
            _relay_cache['error'] = message
        raise MullvadError(message)
    if not isinstance(data, list):
        raise MullvadError('Mullvad server list was not a list.')
    relays = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if item.get('active') is False:
            continue
        hostname = str(item.get('hostname') or '').strip()
        pubkey = str(item.get('pubkey') or '').strip()
        ipv4 = str(item.get('ipv4_addr_in') or '').strip()
        if not hostname or not pubkey or not ipv4:
            continue
        relays.append({
            'hostname': hostname,
            'fqdn': str(item.get('fqdn') or hostname).strip(),
            'country_code': str(item.get('country_code') or '').strip().lower(),
            'country_name': str(item.get('country_name') or '').strip(),
            'city_code': str(item.get('city_code') or '').strip().lower(),
            'city_name': str(item.get('city_name') or '').strip(),
            'ipv4': ipv4,
            'ipv6': str(item.get('ipv6_addr_in') or '').strip(),
            'pubkey': pubkey,
        })
    with _relay_lock:
        _relay_cache['at'] = now
        _relay_cache['relays'] = relays
        _relay_cache['error_at'] = 0.0
        _relay_cache['error'] = ''
    return relays


def city_key(relay):
    return '%s/%s' % (relay.get('country_code', ''), relay.get('city_code', ''))


def relay_tree(relays=None):
    if relays is None:
        relays = fetch_relays()
    countries = {}
    for relay in relays:
        cc = relay['country_code']
        if not cc:
            continue
        country = countries.setdefault(cc, {
            'code': cc,
            'name': relay['country_name'] or cc.upper(),
            'cities': {},
        })
        ck = city_key(relay)
        city = country['cities'].setdefault(ck, {
            'code': relay['city_code'],
            'key': ck,
            'name': relay['city_name'] or relay['city_code'],
            'servers': [],
        })
        city['servers'].append({'hostname': relay['hostname']})
    out = []
    for country in sorted(countries.values(), key=lambda c: c['name'].lower()):
        cities = []
        for city in sorted(country['cities'].values(), key=lambda c: c['name'].lower()):
            city['servers'] = sorted(city['servers'], key=lambda s: s['hostname'])
            cities.append(city)
        out.append({
            'code': country['code'],
            'name': country['name'],
            'cities': cities,
        })
    return {'countries': out}


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def filter_relays(relays, countries=None, cities=None, servers=None):
    """Narrow the pool using the hierarchical multi-select rules.

    - 2+ countries: every server in those countries (city/server picks ignored).
    - 1 country, 2+ cities: servers in those cities.
    - 1 country, 1 city, 1+ servers: those hostnames (that still belong to the city).
    - Empty city/server lists mean "all at that level".
    """
    countries = [c.lower() for c in _as_list(countries)]
    cities = _as_list(cities)
    servers = _as_list(servers)
    pool = list(relays)
    if countries:
        allowed = set(countries)
        pool = [r for r in pool if r.get('country_code') in allowed]
    if len(countries) == 1:
        if cities:
            allowed_cities = set(cities)
            pool = [r for r in pool if city_key(r) in allowed_cities]
        if len(cities) == 1 and servers:
            allowed_hosts = set(servers)
            pool = [r for r in pool if r.get('hostname') in allowed_hosts]
    return pool


def pick_relay(pool, current_hostname=None):
    if not pool:
        raise MullvadError('No Mullvad servers match the selected location.')
    others = [r for r in pool if r.get('hostname') != current_hostname]
    return random.choice(others or pool)


def _as_dt(value):
    """Return value as a naive UTC datetime, which is how Mongo hands them back."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _api_error_message(response):
    text = (response.text or '').strip()
    try:
        payload = response.json()
        if isinstance(payload, dict):
            # 'code' is a machine token like INVALID_ACCOUNT, so prefer prose.
            for key in ('detail', 'error', 'message', 'code'):
                if payload.get(key):
                    return str(payload[key])
    except Exception:
        pass
    return text[:300] if text else 'HTTP %s' % response.status_code


def _get_access_token(account, force_refresh=False):
    now = time.time()
    with _token_lock:
        if force_refresh:
            _token_cache.pop(account, None)
        cached = _token_cache.get(account)
        if cached and cached[1] > now + 30:
            return cached[0]
    try:
        response = requests.post(
            AUTH_URL,
            json={'account_number': account},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as e:
        raise MullvadError('Could not sign in to Mullvad: ' + str(e))
    if response.status_code >= 400:
        raise MullvadError('Mullvad account was rejected: ' + _api_error_message(response))
    try:
        payload = response.json()
    except Exception:
        raise MullvadError('Mullvad login returned an unexpected response.')
    token = payload.get('access_token') or payload.get('token')
    if not token:
        raise MullvadError('Mullvad login did not return an access token.')
    expiry = now + TOKEN_CACHE_TTL
    exp = payload.get('expiry') or payload.get('expires_at')
    exp_dt = _as_dt(exp)
    if exp_dt:
        expiry = min(expiry, exp_dt.timestamp())
    with _token_lock:
        _token_cache[account] = (token, expiry)
    return token


def _device_request(method, url, account, **kwargs):
    """Call a device endpoint, retrying once with a fresh access token."""
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)
    base_headers = dict(kwargs.pop('headers', None) or {})
    response = None
    for refresh in (False, True):
        headers = dict(base_headers)
        headers['Authorization'] = 'Bearer ' + _get_access_token(account, force_refresh=refresh)
        headers.setdefault('Content-Type', 'application/json')
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
        except Exception as e:
            raise MullvadError('Mullvad API request failed: ' + str(e))
        if response.status_code not in (401, 403):
            return response
    return response


def _addresses_from_device(payload):
    v4 = str(payload.get('ipv4_address') or payload.get('ipv4') or '').strip()
    v6 = str(payload.get('ipv6_address') or payload.get('ipv6') or '').strip()
    addresses = []
    if v4:
        addresses.append(v4 if '/' in v4 else v4 + '/32')
    if v6:
        addresses.append(v6 if '/' in v6 else v6 + '/128')
    if not addresses:
        raise MullvadError('Mullvad did not assign tunnel addresses to this device.')
    return ', '.join(addresses)


def delete_device(account, device_id):
    if not account or not device_id:
        return False
    try:
        response = _device_request('DELETE', DEVICES_URL.rstrip('/') + '/' + str(device_id), account)
        return response.status_code < 400 or response.status_code == 404
    except Exception:
        return False


def _is_device_limit(response):
    if response.status_code not in (400, 409):
        return False
    blob = (response.text or '').lower() + ' ' + _api_error_message(response).lower()
    return (
        ('max' in blob and 'device' in blob)
        or 'too many devices' in blob
        or 'max_devices' in blob
        or 'device limit' in blob
    )


def create_device(account, pubkey):
    body = {'pubkey': pubkey, 'hijack_dns': False}
    response = _device_request('POST', DEVICES_URL, account, json=body)
    if response.status_code >= 400:
        detail = _api_error_message(response)
        if _is_device_limit(response):
            raise MullvadDeviceLimitError(
                'This Mullvad account has no free device slots: ' + detail)
        raise MullvadError('Could not register a Mullvad device: ' + detail)
    try:
        payload = response.json()
    except Exception:
        raise MullvadError('Mullvad device registration returned an unexpected response.')
    device_id = payload.get('id') or payload.get('device_id')
    if not device_id:
        raise MullvadError('Mullvad device registration did not return a device id.')
    return {
        'mullvad_device_id': str(device_id),
        'wg_local_address': _addresses_from_device(payload),
    }


def replace_device_key(account, device_id, pubkey):
    url = DEVICES_URL.rstrip('/') + '/' + str(device_id) + '/pubkey'
    response = _device_request('PUT', url, account, json={'pubkey': pubkey})
    if response.status_code >= 400:
        raise MullvadError('Could not rotate the Mullvad WireGuard key: ' + _api_error_message(response))
    try:
        payload = response.json()
    except Exception:
        raise MullvadError('Mullvad key rotation returned an unexpected response.')
    return {'wg_local_address': _addresses_from_device(payload)}


def _register_or_rotate_keys(account, current):
    """Return fresh WireGuard keys bound to a Mullvad device on this account.

    A device that gets replaced is reported as mullvad_stale_device rather than
    deleted, so the outbound keeps a working identity until the new config is
    proven good. Callers settle it with commit_device_swap/rollback_device_swap.
    """
    priv, pub = generate_wireguard_keypair()
    old_account = normalize_account((current or {}).get('mullvad_account'))
    old_device = (current or {}).get('mullvad_device_id')
    same_account = bool(current and old_account == account)

    if same_account and old_device:
        try:
            info = replace_device_key(account, old_device, pub)
            info['wg_private_key'] = priv
            info['mullvad_device_id'] = old_device
            return info
        except MullvadError:
            pass

    reclaimed = False
    try:
        info = create_device(account, pub)
    except MullvadDeviceLimitError:
        # Freeing a slot only helps when the full account is the one we own a
        # device on, so a different account must simply report the limit.
        if not (same_account and old_device) or not delete_device(account, old_device):
            raise
        reclaimed = True
        info = create_device(account, pub)

    result: dict = dict(info)
    result['wg_private_key'] = priv
    if old_device and not reclaimed:
        result['mullvad_stale_device'] = {'account': old_account or account,
                                          'device_id': old_device}
    return result


def commit_device_swap(pending):
    """Drop the replaced device now that its successor carries traffic."""
    stale = (pending or {}).get('mullvad_stale_device') or {}
    if stale.get('device_id'):
        delete_device(stale.get('account'), stale['device_id'])
    return {'mullvad_stale_device': None}


def rollback_device_swap(pending, restored):
    """Undo provisioning for a save that never reached service.

    Returns fields to merge into the restored document.
    """
    new_device = (pending or {}).get('mullvad_device_id')
    old_device = (restored or {}).get('mullvad_device_id')
    if not new_device or new_device == old_device:
        return {}
    stale = (pending or {}).get('mullvad_stale_device') or {}
    if stale.get('device_id') == old_device:
        delete_device(normalize_account(pending.get('mullvad_account')), new_device)
        return {}
    # The old device's slot was reclaimed, so the restored server keeps the
    # identity we just made rather than one Mullvad no longer knows.
    return {
        'mullvad_account': pending.get('mullvad_account'),
        'mullvad_device_id': new_device,
        'wg_private_key': pending.get('wg_private_key'),
        'wg_local_address': pending.get('wg_local_address'),
        'mullvad_stale_device': None,
    }


def _wg_fields_from_relay(relay, key_info, keep_keys=None):
    fields = {
        'server': relay['ipv4'],
        'server_port': WG_PORT,
        'wg_peer_public_key': relay['pubkey'],
        'wg_pre_shared_key': '',
        'wg_mtu': WG_MTU,
        'wg_reserved': '',
        'mullvad_hostname': relay['hostname'],
        'mullvad_country_name': relay.get('country_name', ''),
        'mullvad_city_name': relay.get('city_name', ''),
        'mullvad_last_rotated_at': _utcnow(),
    }
    if key_info:
        fields.update(key_info)
    elif keep_keys:
        for key in ('wg_private_key', 'wg_local_address', 'mullvad_device_id'):
            if keep_keys.get(key):
                fields[key] = keep_keys[key]
    return fields


def rotate(data, current=None, rotate_keys=None):
    """Pick a server (and optionally new keys) and return WG/runtime fields."""
    account = normalize_account(data.get('mullvad_account') or (current or {}).get('mullvad_account'))
    if not account:
        raise MullvadError('Mullvad account number is required.')
    countries = data.get('mullvad_countries')
    cities = data.get('mullvad_cities')
    servers = data.get('mullvad_servers')
    if countries is None and current:
        countries = current.get('mullvad_countries')
        cities = current.get('mullvad_cities')
        servers = current.get('mullvad_servers')
    pool = filter_relays(fetch_relays(), countries, cities, servers)
    relay = pick_relay(pool, (current or {}).get('mullvad_hostname'))
    if rotate_keys is None:
        rotate_keys = bool(data.get('mullvad_rotate_keys', True))
    need_keys = rotate_keys or not (current and current.get('wg_private_key') and current.get('wg_local_address'))
    key_info = None
    keep_keys = current
    if need_keys:
        key_info = _register_or_rotate_keys(account, current)
    fields = _wg_fields_from_relay(relay, key_info, keep_keys=keep_keys)
    fields['mullvad_account'] = account
    return fields


# Fields that describe the live tunnel. The outbound form never posts them, so
# on edit they are carried over from the stored document.
_TUNNEL_KEYS = (
    'server', 'server_port', 'wg_private_key', 'wg_peer_public_key',
    'wg_pre_shared_key', 'wg_local_address', 'wg_mtu', 'wg_reserved',
    'mullvad_hostname', 'mullvad_device_id', 'mullvad_last_rotated_at',
    'mullvad_country_name', 'mullvad_city_name',
    'mullvad_last_http_check_at', 'mullvad_last_http_status',
)


def _same_selection(a, b):
    return sorted(_as_list(a)) == sorted(_as_list(b))


def apply_form(data, current=None):
    """Fill Mullvad runtime/WG fields for create or update."""
    account = normalize_account(data.get('mullvad_account'))
    if not account:
        raise MullvadError('Mullvad account number is required.')
    data['mullvad_account'] = account
    data['mullvad_countries'] = _as_list(data.get('mullvad_countries'))
    data['mullvad_cities'] = _as_list(data.get('mullvad_cities'))
    data['mullvad_servers'] = _as_list(data.get('mullvad_servers'))
    data['type'] = 'mullvad'
    if not data.get('name'):
        data['name'] = 'Mullvad VPN'

    if current and current.get('type') == 'mullvad':
        for key in _TUNNEL_KEYS:
            if current.get(key) not in (None, ''):
                data[key] = current[key]

        # The picker is empty when the relay list could not be loaded, which
        # must not silently wipe a working location on an unrelated edit.
        if not data['mullvad_countries']:
            data['mullvad_countries'] = _as_list(current.get('mullvad_countries'))
            data['mullvad_cities'] = _as_list(current.get('mullvad_cities'))
            data['mullvad_servers'] = _as_list(current.get('mullvad_servers'))
        if not data['mullvad_countries']:
            raise MullvadError('Select at least one Mullvad country.')

        same_account = normalize_account(current.get('mullvad_account')) == account
        has_tunnel = bool(
            current.get('wg_private_key') and current.get('wg_local_address')
            and current.get('mullvad_device_id') and current.get('mullvad_hostname')
        )
        location_changed = not (
            _same_selection(data['mullvad_countries'], current.get('mullvad_countries'))
            and _same_selection(data['mullvad_cities'], current.get('mullvad_cities'))
            and _same_selection(data['mullvad_servers'], current.get('mullvad_servers'))
        )
        if same_account and has_tunnel and not location_changed:
            return data

        if same_account and has_tunnel:
            pool = filter_relays(
                fetch_relays(),
                data['mullvad_countries'],
                data['mullvad_cities'],
                data['mullvad_servers'],
            )
            if any(r['hostname'] == current['mullvad_hostname'] for r in pool):
                return data

        data.update(rotate(
            data, current,
            rotate_keys=not (same_account and current.get('wg_private_key')),
        ))
        return data

    if not data['mullvad_countries']:
        raise MullvadError('Select at least one Mullvad country.')
    data.update(rotate(data, None, rotate_keys=True))
    return data


def socks_port_for(ob, all_obs):
    from . import outbounds as ob_module
    if not ob.get('enabled', True):
        return None
    if ob.get('backup'):
        ranks = ob_module.backup_ranks(all_obs)
        if ob.get('index') not in ranks:
            return None
        return ob_module.backup_socks_port(ranks[ob['index']])
    return ob_module.BASE_PORT + ob['index']


def _http_check(ob, socks_port):
    url = str(ob.get('mullvad_http_url') or '').strip()
    if not url:
        return None
    method = str(ob.get('mullvad_http_method') or 'GET').upper()
    if method not in ('GET', 'POST', 'HEAD'):
        method = 'GET'
    proxies = {
        'http': 'socks5h://127.0.0.1:%s' % socks_port,
        'https': 'socks5h://127.0.0.1:%s' % socks_port,
    }
    try:
        response = requests.request(
            method, url, proxies=proxies, timeout=20, allow_redirects=False,
        )
        return response.status_code
    except Exception:
        return None


def rotate_interval_days(ob):
    """Snap a stored day count to the nearest option the UI actually offers."""
    try:
        days = int(ob.get('mullvad_rotate_days') or DEFAULT_ROTATE_DAYS)
    except (TypeError, ValueError):
        days = DEFAULT_ROTATE_DAYS
    return min(ROTATE_DAY_CHOICES, key=lambda choice: abs(choice - days))


def rotate_hour(ob):
    try:
        hour = int(ob.get('mullvad_rotate_hour', DEFAULT_ROTATE_HOUR))
    except (TypeError, ValueError):
        hour = DEFAULT_ROTATE_HOUR
    return hour if 0 <= hour <= 23 else DEFAULT_ROTATE_HOUR


def describe_rotate_schedule(ob):
    days = rotate_interval_days(ob)
    label = 'daily' if days == 1 else 'every %d days' % days
    return '%s @ %02d:00 UTC' % (label, rotate_hour(ob))


def _scheduled_slot(ob, now):
    """The most recent rotation slot at or before now, in UTC."""
    interval = timedelta(days=rotate_interval_days(ob))
    anchor = _SCHEDULE_EPOCH.replace(hour=rotate_hour(ob))
    return anchor + interval * math.floor((now - anchor) / interval)


def next_rotation_at(ob, now=None):
    """Next due rotation in UTC, or None when rotation is off.

    A slot in the past means it is due on the next tick.
    """
    if not ob.get('mullvad_rotate'):
        return None
    now = now or _utcnow()
    slot = _scheduled_slot(ob, now)
    last = _as_dt(ob.get('mullvad_last_rotated_at'))
    if last is None or last < slot:
        return slot
    return slot + timedelta(days=rotate_interval_days(ob))


def _due_for_time_rotate(ob, now):
    if not ob.get('mullvad_rotate'):
        return False
    last = _as_dt(ob.get('mullvad_last_rotated_at'))
    return last is None or last < _scheduled_slot(ob, now)


def _due_for_http_check(ob, now):
    if not ob.get('mullvad_http_check'):
        return False
    url = str(ob.get('mullvad_http_url') or '').strip()
    if not url:
        return False
    try:
        minutes = int(ob.get('mullvad_http_interval_minutes') or 10)
    except (TypeError, ValueError):
        minutes = 10
    minutes = max(1, min(1440, minutes))
    last = _as_dt(ob.get('mullvad_last_http_check_at'))
    rotated = _as_dt(ob.get('mullvad_last_rotated_at'))
    if rotated and now - rotated < HTTP_ROTATE_COOLDOWN:
        return False
    if last is None:
        return True
    return now - last >= timedelta(minutes=minutes)


def _http_should_rotate(ob, status):
    try:
        expected = int(ob.get('mullvad_http_code'))
    except (TypeError, ValueError):
        return False
    return status is not None and status == expected


def _save_rotate(outbound_id, fields):
    from . import outbounds as ob_module
    ob_module.update(outbound_id, fields)


def tick():
    """Rotate due Mullvad outbounds. Returns how many were rotated."""
    if not _tick_lock.acquire(blocking=False):
        return 0
    try:
        from . import outbounds as ob_module
        from . import sysops

        now = _utcnow()
        all_obs = ob_module.get_all()
        rotated = 0
        for ob in all_obs:
            if ob.get('type') != 'mullvad' or not ob.get('enabled', True):
                continue
            outbound_id = str(ob['_id'])
            # Anything still recorded here was swapped at least a tick ago, so
            # the document in hand is the only identity still referenced.
            if (ob.get('mullvad_stale_device') or {}).get('device_id'):
                _save_rotate(outbound_id, commit_device_swap(ob))
                ob['mullvad_stale_device'] = None
            do_rotate = _due_for_time_rotate(ob, now)
            http_status = None
            if _due_for_http_check(ob, now):
                port = socks_port_for(ob, all_obs)
                if port is not None:
                    http_status = _http_check(ob, port)
                patch = {
                    'mullvad_last_http_check_at': now,
                    'mullvad_last_http_status': http_status,
                }
                _save_rotate(outbound_id, patch)
                ob.update(patch)
                if _http_should_rotate(ob, http_status):
                    do_rotate = True
            if not do_rotate:
                continue
            try:
                fields = rotate(ob, ob, rotate_keys=bool(ob.get('mullvad_rotate_keys', True)))
                fields['mullvad_last_http_check_at'] = now
                _save_rotate(outbound_id, fields)
                ob_module.reset_health(ob['index'])
                rotated += 1
            except Exception:
                traceback.print_exc()
        if rotated:
            success, error = sysops.apply_outbound_config()
            if not success:
                print('Mullvad rotation could not apply the new config: ' + str(error))
        return rotated
    finally:
        _tick_lock.release()


def _agent_loop():
    while True:
        time.sleep(TICK_INTERVAL)
        try:
            tick()
        except Exception:
            traceback.print_exc()


_agent_lock_fd = None

def start_agent():
    """Start the Mullvad rotate loop in one process. Safe to call many times."""
    global _agent_started, _agent_lock_fd
    if _agent_started:
        return
    import fcntl
    try:
        _agent_lock_fd = open('/tmp/libertea-mullvad-rotate.lock', 'w')
        fcntl.flock(_agent_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if _agent_lock_fd is not None:
            try:
                _agent_lock_fd.close()
            except Exception:
                pass
            _agent_lock_fd = None
        return
    _agent_started = True
    thread = threading.Thread(target=_agent_loop, name='mullvad-rotate', daemon=True)
    thread.start()
