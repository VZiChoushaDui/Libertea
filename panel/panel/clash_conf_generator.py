import os
import re
from . import utils
from . import config
from . import settings
from pymongo import MongoClient
from flask import render_template
from datetime import datetime, timedelta

def init_provider_info(type, name, host, port, password, path, meta_only, entry_type, server=None, sni=None, tier=None):
    if server is None:
        server = host
    if sni is None:
        sni = host

    # if server is an ip address, sni and host are google.com, else sni and host are server
    skip_cert_verify = "false"
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host):
        sni = 'google.com'
        host = 'google.com'
        skip_cert_verify = "true"

    if tier is None:
        tier = utils.get_default_tier(entry_type)

    return {
        'type': type,
        'name': name,
        'server': server,
        'port': port,
        'password': password,
        'sni': sni,
        'path': path,
        'host': host,
        'skip_cert_verify': skip_cert_verify,
        'meta_only': meta_only,
        'entry_type': entry_type,
        'tier': tier,
    }

def get_providers(connect_url, db):
    servers = []

    ports = settings.get_secondary_proxy_ports(db=db)
    try:
        ports = [int(x) for x in ports.split(',')]
    except:
        ports = [443]

    for secondary_route in utils.online_route_get_all(db=db):
        for port in ports:
            servers.append((secondary_route, port))
    for server in utils.get_domains(db=db):
        if settings.get_add_domains_even_if_inactive(db=db) or utils.check_domain_set_properly(server, db=db) == 'active':
            servers.append((server, 443))
    
    # # DEBUG ONLY
    # servers.append((config.SERVER_MAIN_IP, 443))

    providers = []
    idx = 0
    for server, port in servers:      
        server_entry_type = utils.get_route_entry_type(server, db=db)
        server_ips_str = utils.get_domain_dns_domain(server, db=db)
        server_ips = [server_ips_str]
        if server_ips_str is not None and ',' in server_ips_str:
            server_ips = server_ips_str.split(',')
        for s in server_ips:
            if settings.get_provider_enabled('trojangrpc', db=db):
                providers.append(init_provider_info(
                    type='trojan-grpc',
                    name='TrG-' + str(idx) + "-" + server,
                    port=port,
                    password=os.environ.get('CONN_TROJAN_GRPC_AUTH_PASSWORD'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_TROJAN_GRPC_URL'),
                    meta_only=False,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=utils.get_domain_or_online_route_tier(server, db=db),
                ))
            if settings.get_provider_enabled('trojanws', db=db):
                providers.append(init_provider_info(
                    type='trojan-ws',
                    name='TrW-' + str(idx) + "-" + server,
                    port=port,
                    password=os.environ.get('CONN_TROJAN_WS_AUTH_PASSWORD'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_TROJAN_WS_URL'),
                    meta_only=False,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=utils.get_domain_or_online_route_tier(server, db=db),
                ))
            if settings.get_provider_enabled('vlessws', db=db):
                providers.append(init_provider_info(
                    type='vless-ws',
                    name='VlW-' + str(idx) + "-" + server,
                    port=port,
                    password=os.environ.get('CONN_VLESS_WS_AUTH_UUID'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_VLESS_WS_URL'),
                    meta_only=True,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=utils.get_domain_or_online_route_tier(server, db=db),
                ))
            if settings.get_provider_enabled('ssv2ray', db=db):
                providers.append(init_provider_info(
                    type='ss-v2ray',
                    name='ssV-' + str(idx) + "-" + server,
                    port=port,
                    password=os.environ.get('CONN_SHADOWSOCKS_V2RAY_AUTH_PASSWORD'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_SHADOWSOCKS_V2RAY_URL'),
                    meta_only=False,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=utils.get_domain_or_online_route_tier(server, db=db),
                ))
            idx += 1

    return providers

def generate_conf_singlefile(user_id, connect_url, meta=False, premium=False):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    providers = get_providers(connect_url, db)
    
    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id, db=db):
            ips_direct_countries.append(country_id)
    
    udp_exists = settings.get_provider_enabled('trojanws', db=db)

    tiers = []
    for i in range(4):
        tiers.append({
            'index': str(i+1),
            'exists': len([x for x in providers if x['tier'] == str(i+1)]) > 0,
            'type': settings.get_tier_proxygroup_type(i+1, db=db),
        })

    result = render_template('main-singlefile.yaml', 
        providers=providers,
        meta=meta,
        premium=premium,
        ips_direct_countries=ips_direct_countries,
        user_id=user_id,
        panel_domain=config.get_panel_domain(),
        udp_exists=udp_exists,
        health_check=settings.get_periodic_health_check(),
        tiers=tiers,
    )

    return result

def generate_conf(file_name, user_id, connect_url, meta=False, premium=False):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    if file_name not in ['main.yaml', 'tier1.yaml', 'tier2.yaml', 'tier3.yaml', 
                            'tier1-udp.yaml', 'tier2-udp.yaml', 'tier3-udp.yaml', 
                            'rules.yaml', 'cloudflare.yaml', 'cdn-other.yaml', 
                            'direct.yaml', 'cloudflare-udp.yaml', 'cdn-other-udp.yaml', 
                            'direct-udp.yaml', 'rules.yaml', 'health-check-providers.yaml']:
        return ""

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    
    providers = get_providers(connect_url, db=db)

    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id, db=db):
            ips_direct_countries.append(country_id)

    domains = set([config.get_panel_domain()])
    if settings.get_providers_from_all_endpoints(db=db):
        domains = set(utils.get_active_domains(db=db))
        domains.add(config.get_panel_domain())
    
    udp_exists = settings.get_provider_enabled('trojanws', db=db)
    
    if file_name.startswith('tier') and file_name.endswith('.yaml'):
        tier = int(file_name[4])
        if file_name.endswith('udp.yaml'):
            file_name = 'tier-udp.yaml'
        else:
            file_name = 'tier.yaml'

        return render_template(file_name, 
            providers=[x for x in providers if x['tier'] == str(tier)],
            meta=meta,
            premium=premium,
            ips_direct_countries=ips_direct_countries,
            user_id=user_id,
            panel_domain=config.get_panel_domain(),
            domains=list(domains),
            udp_exists=udp_exists,
        )


    tiers = []
    for i in range(4):
        tiers.append({
            'index': str(i+1),
            'exists': len([x for x in providers if x['tier'] == str(i+1)]) > 0,
            'type': settings.get_tier_proxygroup_type(i+1, db=db),
        })

    return render_template(file_name, 
        providers=providers,
        meta=meta,
        premium=premium,
        ips_direct_countries=ips_direct_countries,
        user_id=user_id,
        panel_domain=config.get_panel_domain(),
        domains=list(domains),
        udp_exists=udp_exists,
        tiers=tiers,
    )
