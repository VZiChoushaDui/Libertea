import os
import re
import binascii
from . import utils
from . import config
from . import settings
from pymongo import MongoClient
from flask import render_template
from datetime import datetime, timedelta

def init_provider_info(type, name, group_name, host, port, password, path, meta_only, entry_type, server=None, sni=None, tier=None, use_camouflage=True):
    if server is None:
        server = host
    if sni is None:
        sni = host

    # if server is an ip address, sni and host are google.com, else sni and host are server
    skip_cert_verify = "false"
    if utils.validate_ip(host):
        if use_camouflage:
            camouflage_domain = settings.get_camouflage_domain_without_protocol()
            if camouflage_domain is None:
                camouflage_domain = 'example.com'
            sni = camouflage_domain
            host = camouflage_domain
            skip_cert_verify = "true"
        else:
            sni = 'google.com'
            host = 'google.com'

    return {
        'type': type,
        'name': name,
        'group_name': group_name,
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

def get_all_servers(db):
    servers = []
    ports = settings.get_secondary_proxy_ports(db=db)
    try:
        ports = [int(x) for x in ports.replace('and', ',').split(',')]
    except:
        ports = [443]

    secondary_proxy_domains_all = set()
    for secondary_route in utils.online_route_get_all(db=db):
        server_entry_type = utils.get_route_entry_type(secondary_route, db=db)
        tier = utils.get_domain_or_online_route_tier(secondary_route, db=db)
        if tier is None:
            tier = utils.get_default_tier(server_entry_type)
        for port in ports:
            secondary_proxy_domain = utils.get_domain_for_ip(secondary_route, db=db)
            if secondary_proxy_domain is not None:
                servers.append((secondary_proxy_domain, port, tier, server_entry_type))
                secondary_proxy_domains_all.add(secondary_proxy_domain)
            else:
                servers.append((secondary_route, port, tier, server_entry_type))

    for server in utils.get_domains(db=db):
        if server in secondary_proxy_domains_all:
            continue
        if settings.get_add_domains_even_if_inactive(db=db) or utils.check_domain_set_properly(server, db=db) in ['active', 'cdn-disabled']:
            server_entry_type = utils.get_route_entry_type(server, db=db)
            tier = utils.get_domain_or_online_route_tier(server, db=db)
            if tier is None:
                tier = utils.get_default_tier(server_entry_type)

            servers.append((server, 443, tier, server_entry_type))

    return servers

def get_providers(connect_url, db, is_for_subscription=False, enabled_tiers=None):
    servers = get_all_servers(db=db)
    
    # # DEBUG ONLY
    # servers.append((config.SERVER_MAIN_IP, 443))

    providers = []
    idx = 0
    for server, port, tier, server_entry_type in servers:
        if enabled_tiers is not None and str(tier) not in enabled_tiers:
            continue            

        server_ips_str = utils.get_domain_dns_domain(server, db=db)
        server_ips = [server_ips_str]
        if server_ips_str is not None and ',' in server_ips_str:
            server_ips = server_ips_str.split(',')
        for s in server_ips:
            group_name = str(idx) + "-" + server
            providers.append({
                'type': 'servergroup',
                'tier': tier,
                'name': group_name,
                'group_name': group_name,
                'meta_only': False,
            })
            trW = None
            vlW = None
            trG = None
            vlG = None
            vmG = None
            ssW = None
            if settings.get_provider_enabled('trojanws', db=db):
                trW = init_provider_info(
                    type='trojan-ws',
                    name='TrW-' + str(idx) + "-" + server,
                    group_name=group_name,
                    port=port,
                    password=os.environ.get('CONN_TROJAN_WS_AUTH_PASSWORD'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_TROJAN_WS_URL'),
                    meta_only=False,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=tier,
                )
            if settings.get_provider_enabled('vlessws', db=db):
                vlW = init_provider_info(
                    type='vless-ws',
                    name='VlW-' + str(idx) + "-" + server,
                    group_name=group_name,
                    port=port,
                    password=os.environ.get('CONN_VLESS_WS_AUTH_UUID'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_VLESS_WS_URL'),
                    meta_only=True,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=tier,
                )
            if settings.get_provider_enabled('trojangrpc', db=db):
                trG = init_provider_info(
                    type='trojan-grpc',
                    name='TrG-' + str(idx) + "-" + server,
                    group_name=group_name,
                    port=port,
                    password=os.environ.get('CONN_TROJAN_GRPC_AUTH_PASSWORD'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_TROJAN_GRPC_URL'),
                    meta_only=False,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=tier,
                )
            if settings.get_provider_enabled('vlessgrpc', db=db):
                if server_entry_type != 'SecondaryProxy' or is_for_subscription:
                    # SecondaryProxy does not support vless-grpc in clash
                    vlG = init_provider_info(
                        type='vless-grpc',
                        name='VlG-' + str(idx) + "-" + server,
                        group_name=group_name,
                        port=port,
                        password=os.environ.get('CONN_VLESS_GRPC_AUTH_UUID'),
                        path='/' + connect_url + '/' + os.environ.get('CONN_VLESS_GRPC_URL'),
                        meta_only=True,
                        entry_type=server_entry_type,
                        sni=utils.get_domain_sni(server, db=db),
                        host=server,
                        server=s,
                        tier=tier,
                    )
            if settings.get_provider_enabled('vmessgrpc', db=db):
                vmG = init_provider_info(
                    type='vmess-grpc',
                    name='VmG-' + str(idx) + "-" + server,
                    group_name=group_name,
                    port=port,
                    password=os.environ.get('CONN_VMESS_GRPC_AUTH_UUID'),
                    path='/' + connect_url + '/' + os.environ.get('CONN_VMESS_GRPC_URL'),
                    meta_only=True,
                    entry_type=server_entry_type,
                    sni=utils.get_domain_sni(server, db=db),
                    host=server,
                    server=s,
                    tier=tier,
                )
            if settings.get_provider_enabled('ssv2ray', db=db):
                if not is_for_subscription or server_entry_type != 'SecondaryProxy':
                    # subscription does not support secondary proxy (invalid cert)
                    ssW = init_provider_info(
                        type='ss-v2ray',
                        name='ssW-' + str(idx) + "-" + server,
                        group_name=group_name,
                        port=port,
                        password=os.environ.get('CONN_SHADOWSOCKS_V2RAY_AUTH_PASSWORD'),
                        path='/' + connect_url + '/' + os.environ.get('CONN_SHADOWSOCKS_V2RAY_URL'),
                        meta_only=False,
                        entry_type=server_entry_type,
                        sni=utils.get_domain_sni(server, db=db),
                        host=server,
                        server=s,
                        tier=tier,
                    )

            if server_entry_type == 'SecondaryProxy':
                if trG is not None:
                    providers.append(trG)
                if vlG is not None:
                    providers.append(vlG)
                if vmG is not None:
                    providers.append(vmG)
                if trW is not None:
                    providers.append(trW)
                if vlW is not None:
                    providers.append(vlW)
                if ssW is not None:
                    providers.append(ssW)
            else:
                if trW is not None:
                    providers.append(trW)
                if vlW is not None:
                    providers.append(vlW)
                if trG is not None:
                    providers.append(trG)
                if vlG is not None:
                    providers.append(vlG)
                if vmG is not None:
                    providers.append(vmG)
                if ssW is not None:
                    providers.append(ssW)
                    
                
            
            idx += 1

    return providers

def generate_conf_singlefile(user_id, connect_url, meta=False, premium=False, enabled_tiers=None, custom_info_entries=None):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    providers = get_providers(connect_url, db, enabled_tiers=enabled_tiers)
    
    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id, db=db):
            ips_direct_countries.append(country_id)
    domain_direct_suffixes = config.get_regional_domain_suffixes(ips_direct_countries)

    if custom_info_entries is not None and isinstance(custom_info_entries, list):
        current_time = datetime.now()
        if len(ips_direct_countries) == 1:
            current_time = config.current_time_in_timezone(ips_direct_countries[0])
        custom_info_entries = [f"Updated @ {current_time.strftime('%Y-%m-%d %H:%M')}"] + custom_info_entries
    
    udp_exists = settings.get_provider_enabled('trojanws', db=db)

    tiers = []
    for i in range(4):
        tiers.append({
            'index': str(i+1),
            'exists': len([x for x in providers if x['tier'] == str(i+1)]) > 0,
            'type': settings.get_tier_proxygroup_type(i+1, db=db),
        })

    group_names = set()
    for p in providers:
        group_names.add(p['group_name'])
    group_names = list(group_names)
    groups = []
    for g in group_names:
        first_provider = [x for x in providers if x['group_name'] == g and x['type'] != 'servergroup'][0]
        groups.append({
            'index': len(groups),
            'name': g,
            'server': first_provider['server'],
            'host': first_provider['host'],
            'sni': first_provider['sni'],
            'entry_type': first_provider['entry_type'],
        })

    health_check_group = ''
    try:
        for p in sorted(providers, key=lambda x: x['host'] + x['server']):
            health_check_group += p['host'] + p['server']
        health_check_group = str(hex(binascii.crc32(health_check_group.encode('utf-8')) & 0xffffffff))[2:]
    except:
        pass

    result = render_template('main-singlefile.yaml', 
        providers=providers,
        health_check_group=health_check_group,
        meta=meta,
        premium=premium,
        ips_direct_countries=ips_direct_countries,
        user_id=user_id,
        panel_domain=config.get_panel_domain(),
        udp_exists=udp_exists,
        health_check=settings.get_periodic_health_check(),
        tiers=tiers,
        groups=groups,
        manual_tier_select_clash=settings.get_manual_tier_select_clash(),
        domain_direct_suffixes=domain_direct_suffixes,
        custom_info_entries=custom_info_entries if custom_info_entries is not None else [],
    )

    return result

def generate_conf(file_name, user_id, connect_url, meta=False, premium=False, enabled_tiers=None):
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
    
    providers = get_providers(connect_url, db=db, enabled_tiers=enabled_tiers)

    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id, db=db):
            ips_direct_countries.append(country_id)
    domain_direct_suffixes = config.get_regional_domain_suffixes(ips_direct_countries)

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
            domain_direct_suffixes=domain_direct_suffixes,
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
        manual_tier_select_clash=settings.get_manual_tier_select_clash(),
    )
