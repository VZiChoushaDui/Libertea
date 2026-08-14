import os
import json
import time
import glob
import ipaddress as _ipaddress
from datetime import datetime
from bson import ObjectId
from . import config

_ROOT = config.get_root_dir()
OUTBOUND_JSON_PATH          = _ROOT + 'data/outbound.json'
SINGBOX_HOSTS_PATH          = _ROOT + 'data/singbox-hosts.txt'
SINGBOX_DIRECT_PATH         = _ROOT + 'data/singbox-direct.txt'
SINGBOX_BLOCK_PATH          = _ROOT + 'data/singbox-block.txt'
CLASH_CUSTOM_RULES_PATH     = _ROOT + 'data/clash-custom-rules.txt'
MAX_OUTBOUNDS = 20
BASE_PORT        = 13000   # normal SOCKS ports:  13000-13019
BACKUP_BASE_PORT = 13100   # backup SOCKS ports:  13100-13119

OPENVPN_CONF_DIR = '/etc/openvpn'
OPENVPN_TUN_PREFIX = 'tun-lb-'
OPENVPN_UNIT_NAME = 'libertea-ovpn@'
OPENVPN_UNIT_PATH = f'/etc/systemd/system/{OPENVPN_UNIT_NAME}.service'
OPENVPN_UNIT_CONTENT = """\
[Unit]
Description=Libertea OpenVPN tunnel %i
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/sbin/openvpn --config /etc/openvpn/%i.conf
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

SS_METHODS = [
    'chacha20-ietf-poly1305',
    'aes-128-gcm',
    'aes-256-gcm',
    '2022-blake3-aes-128-gcm',
    '2022-blake3-aes-256-gcm',
    '2022-blake3-chacha20-poly1305',
]

def _db():
    client = config.get_mongo_client()
    return client[config.MONGODB_DB_NAME]

def get_all():
    return list(_db().outbounds.find().sort('index', 1))

def get_one(outbound_id):
    return _db().outbounds.find_one({'_id': ObjectId(outbound_id)})

def create(data):
    db = _db()
    used = {o['index'] for o in db.outbounds.find({}, {'index': 1})}
    index = next((i for i in range(MAX_OUTBOUNDS) if i not in used), None)
    if index is None:
        raise ValueError(f'Maximum number of outbounds reached ({MAX_OUTBOUNDS})')
    data['index'] = index
    data['created_at'] = datetime.now()
    data['updated_at'] = datetime.now()
    return str(db.outbounds.insert_one(data).inserted_id)

def update(outbound_id, data):
    data['updated_at'] = datetime.now()
    _db().outbounds.update_one({'_id': ObjectId(outbound_id)}, {'$set': data})

def delete(outbound_id):
    _db().outbounds.delete_one({'_id': ObjectId(outbound_id)})


# ---------------------------------------------------------------------------
# Routing list helpers  (plain-text, one entry per line)
# ---------------------------------------------------------------------------

def _read_text(path):
    """Return the raw contents of a list file, or '' if it doesn't exist."""
    if not os.path.exists(path):
        return ''
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ''

def _write_text(path, text):
    """Atomically write text to path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, path)

def get_hosts_list():
    return _read_text(SINGBOX_HOSTS_PATH)

def set_hosts_list(text):
    _write_text(SINGBOX_HOSTS_PATH, text)

def get_direct_list():
    return _read_text(SINGBOX_DIRECT_PATH)

def set_direct_list(text):
    _write_text(SINGBOX_DIRECT_PATH, text)

def get_block_list():
    return _read_text(SINGBOX_BLOCK_PATH)

def set_block_list(text):
    _write_text(SINGBOX_BLOCK_PATH, text)

def get_clash_custom_rules():
    return _read_text(CLASH_CUSTOM_RULES_PATH)

def set_clash_custom_rules(text):
    _write_text(CLASH_CUSTOM_RULES_PATH, text)


def parse_list(text):
    """Parse a list file (or textarea) into (domains, ips).

    Blank lines and lines starting with '#' are skipped.
    Each remaining entry is classified as an IP/CIDR if it parses as a valid
    network address (plain IPs are normalised to CIDR, e.g. '1.2.3.4/32'),
    otherwise it is treated as a domain suffix.
    """
    domains, ips = [], []
    for raw in text.splitlines():
        entry = raw.strip()
        if not entry or entry.startswith('#'):
            continue
        try:
            network = _ipaddress.ip_network(entry, strict=False)
            ips.append(str(network))
        except ValueError:
            domains.append(entry)
    return domains, ips

def parse_hosts(text):
    """Parse a hosts list file (or textarea) into a dict.

    Each non-blank, non-comment line must be: domain ip
    """
    result = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            result[parts[0]] = parts[1]
    return result


# ---------------------------------------------------------------------------
# sing-box config generation
# ---------------------------------------------------------------------------

def _build_wg_endpoint(ob, tag):
    """Build a sing-box 1.11+ WireGuard endpoint entry (goes in config['endpoints']).
    Schema: https://sing-box.sagernet.org/configuration/endpoint/wireguard/
    """
    peer = {
        'address':     ob.get('server', ''),
        'port':        int(ob.get('server_port', 51820)),
        'public_key':  ob.get('wg_peer_public_key', ''),
        'allowed_ips': ['0.0.0.0/0', '::/0'],
    }
    if ob.get('wg_pre_shared_key'):
        peer['pre_shared_key'] = ob['wg_pre_shared_key']
    if ob.get('wg_reserved'):
        try:
            parts = [int(x.strip()) for x in ob['wg_reserved'].split(',') if x.strip()]
            if len(parts) == 3:
                peer['reserved'] = parts
        except ValueError:
            pass

    result = {
        'type':        'wireguard',
        'tag':         tag,
        'address':     [a.strip() for a in ob.get('wg_local_address', '').split(',') if a.strip()],
        'private_key': ob.get('wg_private_key', ''),
        'peers':       [peer],
    }
    mtu = 1408  # 1500 (Ethernet) - 60 (WireGuard overhead) = 1440, rounded down to 1408
    if ob.get('wg_mtu'):
        try:
            mtu = int(ob['wg_mtu'])
        except ValueError:
            pass
    result['mtu'] = mtu
    return result


def _compute_ovpn_indices(outbounds):
    """Assign sequential indices (0, 1, 2, ...) to enabled OpenVPN outbounds.
    Returns a dict mapping outbound['index'] -> ovpn_index."""
    mapping = {}
    slot = 0
    for ob in outbounds:
        if ob.get('type') == 'openvpn' and ob.get('enabled', True):
            mapping[ob['index']] = slot
            slot += 1
    return mapping


def _build_proxy_outbound(ob, tag, ovpn_indices=None):
    ob_type = ob.get('type', 'vless')

    # Direct outbound bound to a specific network interface
    if ob_type == 'direct':
        result = {'tag': tag, 'type': 'direct'}
        if ob.get('bind_interface'):
            result['bind_interface'] = ob['bind_interface']
        return result

    # OpenVPN — sing-box routes through the tun interface that openvpn creates
    if ob_type == 'openvpn':
        ovpn_idx = (ovpn_indices or {}).get(ob['index'], 0)
        return {
            'tag': tag,
            'type': 'direct',
            'bind_interface': f'{OPENVPN_TUN_PREFIX}{ovpn_idx}',
        }

    # Proxy-based outbounds (vless, vmess, shadowsocks, trojan)
    server    = ob.get('server', '')
    port      = int(ob.get('server_port', 443))
    transport = ob.get('transport', 'tcp')

    result = {'tag': tag, 'type': ob_type, 'server': server, 'server_port': port}

    # Auth fields
    if ob_type in ('vless', 'vmess'):
        result['uuid'] = ob.get('uuid', '')
        if ob_type == 'vmess':
            result['security'] = 'auto'
    elif ob_type == 'shadowsocks':
        result['method']   = ob.get('method', 'chacha20-ietf-poly1305')
        result['password'] = ob.get('password', '')
    elif ob_type == 'trojan':
        result['password'] = ob.get('password', '')
    elif ob_type == 'socks':
        result['version'] = ob.get('socks_version', '5') or '5'
        if ob.get('socks_username'):
            result['username'] = ob['socks_username']
            result['password'] = ob.get('socks_password', '')
        return result  # SOCKS has no transport or TLS

    # Transport
    if transport == 'ws':
        t = {'type': 'ws'}
        if ob.get('transport_path'):
            t['path'] = ob['transport_path']
        if ob.get('transport_host'):
            t['headers'] = {'Host': ob['transport_host']}
        result['transport'] = t
    elif transport == 'grpc':
        t = {'type': 'grpc'}
        if ob.get('transport_service_name'):
            t['service_name'] = ob['transport_service_name']
        result['transport'] = t
    elif transport == 'http':
        t = {'type': 'http'}
        if ob.get('transport_path'):
            t['path'] = ob['transport_path']
        if ob.get('transport_host'):
            t['host'] = [ob['transport_host']]
        result['transport'] = t
    # tcp: no transport field needed

    # VLESS flow (xtls-rprx-vision requires TCP + REALITY)
    if ob_type == 'vless' and ob.get('vless_flow'):
        result['flow'] = ob['vless_flow']

    # TLS / REALITY
    if ob.get('tls') or ob.get('tls_reality'):
        tls = {'enabled': True}
        if ob.get('tls_sni'):
            tls['server_name'] = ob['tls_sni']
        if ob.get('tls_reality'):
            tls['reality'] = {
                'enabled':    True,
                'public_key': ob.get('tls_reality_public_key', ''),
                'short_id':   ob.get('tls_reality_short_id', ''),
            }
        else:
            if ob.get('tls_insecure'):
                tls['insecure'] = True
        if ob.get('tls_fingerprint'):
            tls['utls'] = {
                'enabled':     True,
                'fingerprint': ob['tls_fingerprint'],
            }
        result['tls'] = tls

    return result


def generate_config(outbounds, relay_config=None):
    """Return the full sing-box config dict for data/outbound.json.

    relay_config is read from the global settings if not supplied.  When
    enabled it wraps every proxy outbound with a hysteria2 hop so that
    websites see the relay server's IP rather than this machine's IP.
    WireGuard endpoints and direct-interface outbounds are left unwrapped.
    """
    if relay_config is None:
        from . import settings as _settings
        relay_config = _settings.get_relay_config()

    relay_active = (
        relay_config.get('enabled')
        and relay_config.get('server', '').strip()
    )
    relay_protocol_default = relay_config.get('protocol', 'hysteria2')

    ovpn_indices  = _compute_ovpn_indices(outbounds)
    inbounds      = []
    outbound_cfgs = []
    endpoints     = []
    route_rules   = []
    dns_servers   = []   # per-slot DNS servers built during the loop
    dns_rules     = []   # per-slot DNS rules built during the loop

    for ob in outbounds:
        if not ob.get('enabled', True):
            continue

        i         = ob['index']
        socks_tag = f'socks-in-{i}'
        proxy_tag = f'proxy-{i}'
        is_backup = ob.get('backup', False)
        out_port  = BACKUP_BASE_PORT + i if is_backup else BASE_PORT + i

        inbounds.append({
            'type': 'socks',
            'listen': '127.0.0.1',
            'listen_port': out_port,
            'tag': socks_tag,
        })

        ob_type = ob.get('type', 'vless')

        if ob_type == 'wireguard':
            endpoints.append(_build_wg_endpoint(ob, proxy_tag))
        else:
            outbound_cfgs.append(_build_proxy_outbound(ob, proxy_tag, ovpn_indices))

        if relay_active and not ob.get('relay_disabled'):
            relay_tag = f'relay-{i}'
            relay_protocol = ob.get('relay_protocol_override') or relay_protocol_default

            if relay_protocol == 'shadowsocks':
                relay_ob = {
                    'type':        'shadowsocks',
                    'tag':         relay_tag,
                    'server':      relay_config['server'].strip(),
                    'server_port': int(relay_config.get('port', 8080)),
                    'method':      '2022-blake3-chacha20-poly1305',
                    'password':    relay_config.get('password', ''),
                }
            else:  # hysteria2 (default)
                relay_ob = {
                    'type':        'hysteria2',
                    'tag':         relay_tag,
                    'server':      relay_config['server'].strip(),
                    'server_port': int(relay_config.get('port', 8080)),
                    'password':    relay_config.get('password', ''),
                    'tls':         {'enabled': True, 'insecure': True},
                }

            if ob_type in ('direct', 'openvpn'):
                # Local-interface outbounds: relay connects through the interface
                built = _build_proxy_outbound(ob, proxy_tag, ovpn_indices)
                iface = built.get('bind_interface')
                if iface:
                    relay_ob['bind_interface'] = iface
            else:
                # Remote outbounds (proxy / wireguard): relay chains via detour
                relay_ob['detour'] = proxy_tag
            outbound_cfgs.append(relay_ob)
            final_tag = relay_tag
        else:
            final_tag = proxy_tag

        route_rules.append({'inbound': [socks_tag], 'outbound': final_tag})

        # DNS for this slot: direct queries stay local, everything else goes
        # through the same outbound so the DNS exit IP matches the VPN exit IP.
        if ob_type not in ('direct', 'openvpn'):
            dns_tag = f'dns-vpn-{i}'
            dns_servers.append({
                'type':   'udp',
                'tag':    dns_tag,
                'server': '8.8.8.8',
                'detour': final_tag,
            })
            dns_rules.append({
                'inbound':     [socks_tag],
                'action':      'route',
                'server':      dns_tag,
                'rewrite_ttl': 10800,
            })

    if not any(ob.get('enabled', True) for ob in outbounds):
        # No enabled outbounds — expose a single direct SOCKS on 13000 so
        # HAProxy has something to connect to, but don't add a hidden 2998
        # escape hatch that could leak when outbounds are present.
        inbounds.append({
            'type': 'socks',
            'listen': '127.0.0.1',
            'listen_port': BASE_PORT,
            'tag': 'socks-direct',
        })
        outbound_cfgs.append({'type': 'direct', 'tag': 'direct'})
        route_rules.append({'inbound': ['socks-direct'], 'outbound': 'direct'})
    else:
        # Outbounds exist — add a bare 'direct' outbound only so sing-box's
        # route 'final' rule has a valid tag; no inbound is exposed for it.
        outbound_cfgs.append({'type': 'direct', 'tag': 'direct'})

    # Always include a block outbound so block rules can reference it
    outbound_cfgs.append({'type': 'block', 'tag': 'block'})

    # Load and parse optional static hosts overrides
    hosts         = parse_hosts(_read_text(SINGBOX_HOSTS_PATH))
    hosts_domains = list(hosts.keys()) if hosts else []

    # Load and parse optional direct-bypass and block lists
    direct_domains, direct_ips = parse_list(_read_text(SINGBOX_DIRECT_PATH))
    block_domains,  block_ips  = parse_list(_read_text(SINGBOX_BLOCK_PATH))

    # Build DNS block rules (returned before anything else so blocked domains/IPs
    # never get a real answer, regardless of which inbound the query comes from)
    dns_block_rules = []
    if block_domains:
        dns_block_rules.append({'domain_suffix': block_domains, 'action': 'reject', 'method': 'default'})
    if block_ips:
        dns_block_rules.append({'ip_cidr': block_ips, 'action': 'reject', 'method': 'default'})

    dns = {
        'servers': [
            {
                "type": "hosts",
                "tag": "hosts",
                "predefined": hosts if hosts else {}
            },
            {
                'type': 'udp',
                'tag': 'dns-direct',
                'server': '8.8.8.8',
            },
            # Fallback VPN DNS used when no outbounds are active
            {
                'type': 'udp',
                'tag': 'dns-vpn',
                'server': '8.8.8.8',
            },
            {
                "type": "fakeip",
                "tag": "fakeip",
                "inet4_range": "198.18.0.0/15",
                "inet6_range": "fc00::/18"
            },
            *dns_servers,
        ],
        'rules': [
            # Block rules come first — blocked domains/IPs always return NXDOMAIN
            *dns_block_rules,
            *([{
                'domain': hosts_domains,
                'action': 'route',
                'server': 'hosts',
            }] if hosts_domains else []),
            # .ir and any user-configured direct domains always resolve locally
            {
                'domain_suffix': ['.ir', *direct_domains],
                'action': 'route',
                'server': 'dns-direct',
                'rewrite_ttl': 10800,
            },
            # Per-slot rules: non-direct queries from a VPN inbound go through that slot's DNS
            *dns_rules,
            {
                'query_type': ['A', 'AAAA'],
                'action': 'route',
                'server': 'fakeip',
                'rewrite_ttl': 10800,
            },
        ],
        'final': 'dns-vpn',
        'strategy': 'prefer_ipv4',
        'disable_cache': False,
        'disable_expire': False,
        'cache_capacity': 100000,
    }

    # Block route rules — must come before direct-bypass and VPN rules so
    # blocked traffic is dropped even if a direct or VPN rule would match too.
    block_route_rules = []
    if block_domains:
        block_route_rules.append({'domain_suffix': block_domains, 'outbound': 'block'})
    if block_ips:
        block_route_rules.append({'ip_cidr': block_ips, 'outbound': 'block'})
    if block_route_rules:
        route_rules = block_route_rules + route_rules

    # Direct-bypass route rules must come before per-slot VPN rules
    bypass_rule = {}
    if direct_domains:
        bypass_rule['domain_suffix'] = direct_domains
    if direct_ips:
        bypass_rule['ip_cidr'] = direct_ips
    if bypass_rule:
        bypass_rule['outbound'] = 'direct'
        route_rules = [bypass_rule] + route_rules

    cfg = {
        'log': {'level': 'warn'},
        'dns': dns,
        'inbounds': inbounds,
        'outbounds': outbound_cfgs,
        'route': {
            'rules': route_rules,
            'final': 'direct',
            'default_domain_resolver': 'dns-direct',
        },
    }
    if endpoints:
        cfg['endpoints'] = endpoints

    return cfg


def _ovpn_service_name(index):
    return f'{OPENVPN_UNIT_NAME}libertea-out-{index}'

def _ovpn_conf_path(index):
    return os.path.join(OPENVPN_CONF_DIR, f'libertea-out-{index}.conf')

def _ovpn_auth_path(index):
    return os.path.join(OPENVPN_CONF_DIR, f'libertea-out-{index}.auth')

def apply_openvpn(outbounds):
    """Write .ovpn configs, (re)start or stop systemd units.
    Uses its own index space (0, 1, 2, …) independent of outbound indices.
    Returns (success: bool, error_msg: str|None).
    """
    ovpn_indices = _compute_ovpn_indices(outbounds)
    wanted_ovpn_indices = set(ovpn_indices.values())

    os.makedirs(OPENVPN_CONF_DIR, exist_ok=True)

    # Ensure our systemd template unit exists
    if not os.path.exists(OPENVPN_UNIT_PATH):
        with open(OPENVPN_UNIT_PATH, 'w') as f:
            f.write(OPENVPN_UNIT_CONTENT)
        os.system('systemctl daemon-reload')

    for ob in outbounds:
        if ob.get('type') != 'openvpn' or not ob.get('enabled', True):
            continue
        oidx = ovpn_indices[ob['index']]
        tun_name = f'{OPENVPN_TUN_PREFIX}{oidx}'

        ovpn_body = (ob.get('ovpn_config') or '').rstrip('\n')
        # Strip directives that would hijack the default route
        ovpn_body = '\n'.join(
            line for line in ovpn_body.splitlines()
            if not line.strip().startswith('redirect-gateway')
        )
        injected = [
            f'dev {tun_name}',
            'dev-type tun',
            'route-nopull',
            'route-noexec',
            'script-security 2',
        ]

        if ob.get('ovpn_username') and ob.get('ovpn_password'):
            auth_path = _ovpn_auth_path(oidx)
            with open(auth_path, 'w') as f:
                f.write(ob['ovpn_username'] + '\n')
                f.write(ob['ovpn_password'] + '\n')
            os.chmod(auth_path, 0o600)
            injected.append(f'auth-user-pass {auth_path}')

        conf = ovpn_body + '\n' + '\n'.join(injected) + '\n'
        conf_path = _ovpn_conf_path(oidx)
        with open(conf_path, 'w') as f:
            f.write(conf)
        os.chmod(conf_path, 0o600)

        svc = _ovpn_service_name(oidx)
        os.system(f'systemctl restart {svc}')

    # Give services a moment to crash on bad config, then check
    if wanted_ovpn_indices:
        time.sleep(3)
        failed = []
        for ob in outbounds:
            if ob.get('type') != 'openvpn' or not ob.get('enabled', True):
                continue
            oidx = ovpn_indices[ob['index']]
            svc = _ovpn_service_name(oidx)
            if os.system(f'systemctl is-active --quiet {svc}') != 0:
                name = ob.get('name') or f'OpenVPN #{oidx}'
                failed.append(name)
        if failed:
            return False, f'OpenVPN failed to start (bad config?): {", ".join(failed)}'

    # Stop services for OpenVPN indices no longer wanted
    for path in glob.glob(os.path.join(OPENVPN_CONF_DIR, 'libertea-out-*.conf')):
        fname = os.path.basename(path)
        try:
            oidx = int(fname.replace('libertea-out-', '').replace('.conf', ''))
        except ValueError:
            continue
        if oidx not in wanted_ovpn_indices:
            svc = _ovpn_service_name(oidx)
            os.system(f'systemctl stop {svc}')
            os.remove(path)
            auth = _ovpn_auth_path(oidx)
            if os.path.exists(auth):
                os.remove(auth)

    return True, None


def write_config(outbounds=None):
    if outbounds is None:
        outbounds = get_all()
    cfg = generate_config(outbounds)

    # Sanity-check: cfg must have exactly the inbounds we built.
    # When outbounds exist: one inbound per enabled outbound.
    # When no outbounds: one direct inbound on BASE_PORT.
    enabled_obs = [o for o in outbounds if o.get('enabled', True)]
    expected_inbounds = len(enabled_obs) if enabled_obs else 1
    if len(cfg.get('inbounds', [])) < expected_inbounds:
        raise RuntimeError(
            f'Generated config has fewer inbounds than expected '
            f'({len(cfg.get("inbounds", []))} < {expected_inbounds}); refusing to write.'
        )

    # Write to a sibling temp file then rename — rename(2) is atomic on the
    # same filesystem, so sing-box can never read a half-written file even if
    # it restarts mid-write.
    tmp_path = OUTBOUND_JSON_PATH + '.tmp'
    os.makedirs(os.path.dirname(OUTBOUND_JSON_PATH), exist_ok=True)
    with open(tmp_path, 'w') as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp_path, OUTBOUND_JSON_PATH)
    return cfg


# ---------------------------------------------------------------------------
# Remote relay setup helper
# ---------------------------------------------------------------------------

def build_relay_setup_command_template() -> str:
    """Return the relay setup script with __RELAY_PORT__ and __RELAY_PASSWORD__
    as placeholders.  Substitution is done client-side in JavaScript so the
    panel updates instantly without a round-trip on every keystroke.

    The relay server runs two inbounds on the SAME port:
      • Shadowsocks 2022-blake3-chacha20-poly1305 on TCP
      • Hysteria2 on UDP  (QUIC — self-signed TLS)
    Both share the same password.  The client chooses which protocol to use
    per-outbound; the server happily accepts either.
    """
    cfg_json = """\
{
  "log": { "level": "warn" },
  "dns": {
    "servers": [
      { "type": "udp", "tag": "google", "server": "8.8.8.8" }
    ],
    "final": "google",
    "strategy": "prefer_ipv4"
  },
  "inbounds": [
    {
      "type": "shadowsocks",
      "tag": "ss-in",
      "listen": "0.0.0.0",
      "listen_port": __RELAY_PORT__,
      "network": "tcp",
      "method": "2022-blake3-chacha20-poly1305",
      "password": "__RELAY_PASSWORD__"
    },
    {
      "type": "hysteria2",
      "tag": "hy2-in",
      "listen": "0.0.0.0",
      "listen_port": __RELAY_PORT__,
      "users": [
        { "password": "__RELAY_PASSWORD__" }
      ],
      "tls": {
        "enabled": true,
        "certificate_path": "/etc/libertea-relay/cert.pem",
        "key_path": "/etc/libertea-relay/key.pem"
      }
    }
  ],
  "outbounds": [
    { "type": "direct", "tag": "direct" },
    { "type": "block",  "tag": "block"  }
  ],
  "route": {
    "final": "direct",
    "auto_detect_interface": true
  }
}"""
    # Single-quotes around the heredoc delimiter mean bash won't expand
    # anything inside — safe even if the password contains special chars.
    script = """\
#!/usr/bin/env bash
set -euo pipefail

### ── Libertea Remote Relay Setup ──────────────────────────────────────────
### Run this once on your relay server. It installs sing-box, generates a
### self-signed TLS cert, writes the config, and starts a systemd service.
### Both Shadowsocks (TCP) and Hysteria2 (UDP) listen on the same port so
### each outbound can independently pick which protocol to use.
### ────────────────────────────────────────────────────────────────────────

INSTALL_DIR="/etc/libertea-relay"
SERVICE="libertea-relay"

echo "[1/5] Detecting system..."
if command -v apt-get &>/dev/null; then
    PKG=apt-get
elif command -v yum &>/dev/null; then
    PKG=yum
else
    echo "Unsupported package manager. Install sing-box manually."; exit 1
fi

echo "[2/5] Installing dependencies (curl, openssl)..."
$PKG install -y curl openssl >/dev/null 2>&1

echo "[3/5] Installing sing-box 1.13.1..."
SB_VER="1.13.1"
case "$(uname -m)" in
    x86_64|amd64) SB_ARCH=amd64 ;;
    aarch64|arm64) SB_ARCH=arm64 ;;
    *) echo "Unsupported architecture: $(uname -m) (need x86_64 or aarch64)"; exit 1 ;;
esac
SB_TMP="$(mktemp -d)"
curl -fsSL "https://github.com/SagerNet/sing-box/releases/download/v${SB_VER}/sing-box-${SB_VER}-linux-${SB_ARCH}.tar.gz" -o "$SB_TMP/sing-box.tar.gz"
tar -xzf "$SB_TMP/sing-box.tar.gz" -C "$SB_TMP"
install -m 755 "$SB_TMP/sing-box-${SB_VER}-linux-${SB_ARCH}/sing-box" /usr/local/bin/sing-box
rm -rf "$SB_TMP"

echo "[4/5] Writing config and TLS cert..."
mkdir -p "$INSTALL_DIR"

# Self-signed cert (12 months) — used by Hysteria2 (TLS/QUIC)
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 \\
    -keyout "$INSTALL_DIR/key.pem" -out "$INSTALL_DIR/cert.pem" \\
    -days 365 -nodes -subj "/CN=example.com" 2>/dev/null

cat > "$INSTALL_DIR/config.json" << 'SINGBOX_CONFIG_EOF'
""" + cfg_json + """
SINGBOX_CONFIG_EOF

echo "[5/5] Installing and starting systemd service..."
cat > /etc/systemd/system/${SERVICE}.service << 'UNIT_EOF'
[Unit]
Description=Libertea Remote Relay (sing-box)
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/local/bin/sing-box run -c /etc/libertea-relay/config.json
Restart=on-failure
RestartSec=5
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
UNIT_EOF

systemctl daemon-reload
systemctl enable ${SERVICE}
systemctl restart ${SERVICE}

echo ""
echo "✓ Libertea relay is running on port __RELAY_PORT__ (Shadowsocks/TCP + Hysteria2/UDP)"
"""
    return script


# ---------------------------------------------------------------------------
# HAProxy agent health checks
# ---------------------------------------------------------------------------
# For each outbound slot N, a tiny TCP server listens on AGENT_BASE_PORT+N.
# HAProxy connects periodically (agent-check) and reads "up\n" or "down\n".
# A background thread probes each SOCKS proxy by making a real HTTP request
# through it.

AGENT_BASE_PORT = 13900
CTRL_BASE_PORT  = 13800   # control port per slot: panel sends RESET, health worker clears state
HEALTH_CHECK_URL = 'http://cp.cloudflare.com/generate_204'
HEALTH_CHECK_INTERVAL = 10      # seconds between probes
HEALTH_CHECK_TIMEOUT  = 10      # seconds per probe request
HEALTH_FAIL_THRESHOLD = 3       # consecutive failures before marking down
HEALTH_MIN_SAMPLES_UI = 3       # need this many history samples before showing Healthy/Down in panel
OVPN_RESTART_THRESHOLD = 15    # consecutive failures before restarting OpenVPN
HEALTH_HISTORY_SIZE = 50        # ring buffer size for response times

import socket
import socketserver
import threading
import statistics
import requests as _requests
from collections import deque

# _health_status:  {slot: bool}              — current up/down for HAProxy
# _health_fails:   {slot: int}               — consecutive failure counter
# _health_history: {slot: deque of float}    — last N response times in ms, -1 for failure
# _health_weight:  {slot: int}               — user-configured weight 1-100 (default 100)
_health_status  = {}
_health_fails   = {}
_health_history = {}
_health_weight  = {}
_health_lock    = threading.Lock()
_reset_event    = threading.Event()   # wakes the probe loop after a reset

def _clear_slot(slot):
    """Clear in-memory health state for one slot. Weight is preserved across resets."""
    with _health_lock:
        _health_status.pop(slot, None)
        _health_fails.pop(slot, None)
        _health_history.pop(slot, None)

def set_weight(slot, weight):
    """Set the HAProxy weight for a slot (1-100). Communicated via agent response."""
    with _health_lock:
        _health_weight[slot] = max(1, min(100, int(weight or 100)))

def reset_health(slot):
    """Tell the health worker process to reset state for this slot via TCP,
    then immediately re-probe it.  Falls back gracefully if not yet started."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(('127.0.0.1', CTRL_BASE_PORT + slot))
        s.sendall(b'RESET\n')
        s.close()
    except Exception:
        # Worker not running yet (e.g. during first startup) — clear locally.
        _clear_slot(slot)
    _reset_event.set()

def _get_health(slot):
    with _health_lock:
        return _health_status.get(slot, False)

def _get_stats(slot):
    """Return (median_ms or None, loss_pct or None, sample_count).
    loss_pct is None until the window is full."""
    with _health_lock:
        buf = _health_history.get(slot)
        if not buf:
            return None, None, 0
    samples = list(buf)
    total = len(samples)
    if total == 0:
        return None, None, 0
    good = [s for s in samples if s >= 0]
    median_ms = round(statistics.median(good)) if good else None
    loss_pct = round(samples.count(-1) / total * 100, 1) if total >= 4 else None
    return median_ms, loss_pct, total

def get_all_health():
    """Query ctrl ports for stats. Works across uWSGI workers.
    Returns {slot: {'up': bool, 'ping': int|None, 'loss': float|None,
                    'samples': int, 'display_status': 'checking'|'up'|'down'}}."""
    result = {}
    for slot in range(MAX_OUTBOUNDS):
        port = CTRL_BASE_PORT + slot
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            s.connect(('127.0.0.1', port))
            s.sendall(b'STATS\n')
            data = s.recv(128).decode().strip()
            s.close()
            parts = data.split('|')
            up = parts[0] == 'up'
            ping = int(parts[1]) if len(parts) > 1 and parts[1] != '?' else None
            loss = float(parts[2]) if len(parts) > 2 and parts[2] != '?' else None
            samples = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
            weight = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 100

            if samples == 0:
                display_status = 'checking'
            elif samples < HEALTH_MIN_SAMPLES_UI:
                display_status = 'up' if up else 'checking'
            else:
                display_status = 'up' if up else 'down'

            result[slot] = {
                'up': up,
                'ping': ping,
                'loss': loss,
                'samples': samples,
                'weight': weight,
                'display_status': display_status,
            }
        except Exception:
            pass
    return result

def _record_probe(slot, ms):
    """Record a probe result. ms >= 0 means success, ms == -1 means failure."""
    with _health_lock:
        if slot not in _health_history:
            _health_history[slot] = deque(maxlen=HEALTH_HISTORY_SIZE)
        _health_history[slot].append(ms)

        if ms >= 0:
            _health_fails[slot] = 0
            _health_status[slot] = True
        else:
            _health_fails[slot] = _health_fails.get(slot, 0) + 1
            if _health_fails[slot] >= HEALTH_FAIL_THRESHOLD:
                _health_status[slot] = False


class _CtrlHandler(socketserver.BaseRequestHandler):
    """Handle commands from other worker processes on the control port.

    RESET  → clear in-memory state for this slot and wake the probe loop.
    STATS  → return 'up|ping|loss|samples\\n' for the panel to read.
    """
    def handle(self):
        try:
            cmd = self.request.recv(16).decode().strip()
        except OSError:
            return
        if cmd == 'RESET':
            _clear_slot(self.server.slot_index)
            _reset_event.set()
        elif cmd == 'STATS':
            slot = self.server.slot_index
            up = _get_health(slot)
            status = 'up' if up else 'down'
            median_ms, loss_pct, sample_count = _get_stats(slot)
            with _health_lock:
                weight = _health_weight.get(slot, 100)
            ping_str = str(median_ms) if median_ms is not None else '?'
            loss_str = str(loss_pct) if loss_pct is not None else '?'
            try:
                self.request.sendall(
                    f'{status}|{ping_str}|{loss_str}|{sample_count}|{weight}\n'.encode()
                )
            except OSError:
                pass


class _CtrlServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, slot):
        self.slot_index = slot
        super().__init__(('127.0.0.1', CTRL_BASE_PORT + slot), _CtrlHandler)


class _AgentHandler(socketserver.BaseRequestHandler):
    """Respond to HAProxy agent-check.
    Format: 'up <weight>%\\n' when healthy, 'down\\n' when not.
    HAProxy parses space-separated tokens — 'up' sets state, '<n>%' sets weight."""
    def handle(self):
        slot = self.server.slot_index
        up = _get_health(slot)
        try:
            if up:
                with _health_lock:
                    weight = _health_weight.get(slot, 100)
                self.request.sendall(f'up {weight}%\n'.encode())
            else:
                self.request.sendall(b'down\n')
        except OSError:
            pass


class _AgentServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, slot):
        self.slot_index = slot
        port = AGENT_BASE_PORT + slot
        super().__init__(('127.0.0.1', port), _AgentHandler)


def _probe_slot(slot, is_backup=False):
    """Try an HTTP request through the SOCKS proxy for this slot.
    Uses BACKUP_BASE_PORT for backup outbounds, BASE_PORT otherwise.
    Returns response time in ms on success, -1 on failure."""
    socks_port = BACKUP_BASE_PORT + slot if is_backup else BASE_PORT + slot
    proxies = {
        'http':  f'socks5h://127.0.0.1:{socks_port}',
        'https': f'socks5h://127.0.0.1:{socks_port}',
    }
    try:
        r = _requests.get(HEALTH_CHECK_URL, proxies=proxies,
                          timeout=HEALTH_CHECK_TIMEOUT)
        if r.status_code == 204:
            return r.elapsed.total_seconds() * 1000
        return -1
    except Exception:
        return -1


def _health_check_loop():
    """Periodically probe all configured outbound slots."""
    while True:
        # Wait for the normal interval, but wake early if reset_health() fires.
        woken_by_reset = _reset_event.wait(timeout=HEALTH_CHECK_INTERVAL)
        _reset_event.clear()
        if woken_by_reset:
            # Brief pause so the DB write from the edit/delete has committed
            # before we read outbounds back.
            time.sleep(1)
        try:
            all_obs = get_all()
            ovpn_indices = _compute_ovpn_indices(all_obs)
            active_slots = set()
            for ob in all_obs:
                slot = ob['index']
                active_slots.add(slot)
                # Sync weight from DB into memory on every cycle
                set_weight(slot, ob.get('weight', 100))
                if not ob.get('enabled', True):
                    _record_probe(slot, -1)
                    continue
                ms = _probe_slot(slot, is_backup=ob.get('backup', False))
                _record_probe(slot, ms)

                # Auto-restart OpenVPN if persistently failing
                if ms < 0 and ob.get('type') == 'openvpn' and slot in ovpn_indices:
                    with _health_lock:
                        fails = _health_fails.get(slot, 0)
                    if fails >= OVPN_RESTART_THRESHOLD and fails % OVPN_RESTART_THRESHOLD == 0:
                        oidx = ovpn_indices[slot]
                        svc = _ovpn_service_name(oidx)
                        print(f"Health check: restarting {svc} after {fails} consecutive failures")
                        os.system(f'systemctl restart {svc}')

            # Mark unconfigured slots as down
            with _health_lock:
                for slot in list(_health_status.keys()):
                    if slot not in active_slots:
                        _health_status[slot] = False
        except Exception:
            pass


_started = False

def start_health_agents():
    """Start agent TCP servers and the probe loop. Safe to call multiple times."""
    global _started
    if _started:
        return
    _started = True

    for slot in range(MAX_OUTBOUNDS):
        srv = _AgentServer(slot)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()

        ctrl = _CtrlServer(slot)
        t2 = threading.Thread(target=ctrl.serve_forever, daemon=True)
        t2.start()

    t = threading.Thread(target=_health_check_loop, daemon=True)
    t.start()
    print(f"Outbound health agents started on ports {AGENT_BASE_PORT}-{AGENT_BASE_PORT + MAX_OUTBOUNDS - 1}")
