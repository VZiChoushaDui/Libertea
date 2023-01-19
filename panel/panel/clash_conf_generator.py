import os
import re
from . import utils
from . import config
from . import settings
from flask import render_template

def init_provider_info(type, name, host, port, password, path, meta_only, entry_type, server=None, sni=None):
    if server is None:
        server = host
    if sni is None:
        sni = host

    # if server is an ip address, sni and host are google.com, else sni and host are server
    skip_cert_verify = "false"
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', server):
        sni = 'google.com'
        host = 'google.com'
        skip_cert_verify = "true"

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
    }

def get_providers(connect_url):
    servers = []
    for server in utils.get_domains():
        if utils.check_domain_set_properly(server) == 'active':
            servers.append((server, 443, 'CDNProxy'))
    for secondary_route in utils.online_route_get_all():
        if settings.get_secondary_proxy_use_80_instead_of_443():
            servers.append((secondary_route, 80, 'SecondaryProxy'))
        else:
            servers.append((secondary_route, 443, 'SecondaryProxy'))
    
    # # DEBUG ONLY
    # servers.append((config.SERVER_MAIN_IP, 443))

    providers = []
    idx = 0
    for server, port, server_type in servers:      
        server_type_ex = server_type
        if server_type == 'CDNProxy':
            if utils.check_domain_cdn_provider(server) == 'Cloudflare':
                server_type_ex += '-Cloudflare'
            else:
                server_type_ex += '-Other'

        if settings.get_provider_enabled('trojanws'):
            providers.append(init_provider_info(
                type='trojan-ws',
                name='TrW-' + str(idx) + "-" + server,
                port=port,
                password=os.environ.get('CONN_TROJAN_WS_AUTH_PASSWORD'),
                path='/' + connect_url + '/' + os.environ.get('CONN_TROJAN_WS_URL'),
                meta_only=False,
                entry_type=server_type_ex,
                sni=utils.get_domain_sni(server),
                host=server,
                server=utils.get_domain_dns_domain(server),
            ))
        if settings.get_provider_enabled('vlessws'):
            providers.append(init_provider_info(
                type='vless-ws',
                name='VlW-' + str(idx) + "-" + server,
                port=port,
                password=os.environ.get('CONN_VLESS_WS_AUTH_UUID'),
                path='/' + connect_url + '/' + os.environ.get('CONN_VLESS_WS_URL'),
                meta_only=True,
                entry_type=server_type_ex,
                sni=utils.get_domain_sni(server),
                host=server,
                server=utils.get_domain_dns_domain(server),
            ))
        if settings.get_provider_enabled('ssv2ray'):
            providers.append(init_provider_info(
                type='ss-v2ray',
                name='ssV-' + str(idx) + "-" + server,
                port=port,
                password=os.environ.get('CONN_SHADOWSOCKS_V2RAY_AUTH_PASSWORD'),
                path='/' + connect_url + '/' + os.environ.get('CONN_SHADOWSOCKS_V2RAY_URL'),
                meta_only=False,
                entry_type=server_type_ex,
                sni=utils.get_domain_sni(server),
                host=server,
                server=utils.get_domain_dns_domain(server),
            ))
        idx += 1

    return providers

def generate_conf_singlefile(connect_url, meta=False):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    providers = get_providers(connect_url)

    cloudflare_exists = False
    direct_exists = False
    cdn_other_exists = False
    for provider in providers:
        if provider['entry_type'] == 'CDNProxy-Cloudflare':
            cloudflare_exists = True
        elif provider['entry_type'] == 'CDNProxy-Other':
            cdn_other_exists = True
        elif provider['entry_type'] == 'SecondaryProxy':
            direct_exists = True

    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id):
            ips_direct_countries.append(country_id)

    return render_template('main-singlefile.yaml', 
        providers=providers,
        meta=meta,
        ips_direct_countries=ips_direct_countries,
        cloudflare_exists=cloudflare_exists,
        direct_exists=direct_exists,
        cdn_other_exists=cdn_other_exists,
    )

def generate_conf(file_name, user_id, connect_url, meta=False):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    if file_name not in ['main.yaml', 'cloudflare.yaml', 'cdn-other.yaml', 'direct.yaml', 'rules.yaml']:
        return ""

    providers = get_providers(connect_url)

    cloudflare_exists = False
    direct_exists = False
    cdn_other_exists = False
    for provider in providers:
        if provider['entry_type'] == 'CDNProxy-Cloudflare':
            cloudflare_exists = True
        elif provider['entry_type'] == 'CDNProxy-Other':
            cdn_other_exists = True
        elif provider['entry_type'] == 'SecondaryProxy':
            direct_exists = True

    ips_direct_countries = []
    for country in config.ROUTE_IP_LISTS:
        country_id = country['id']
        if settings.get_route_direct_country_enabled(country_id):
            ips_direct_countries.append(country_id)

    domains = set([config.get_panel_domain()])
    if settings.get_providers_from_all_endpoints():
        domains = set(utils.get_active_domains())
        domains.add(config.get_panel_domain())
    
    return render_template(file_name, 
        providers=providers,
        meta=meta,
        cloudflare_exists=cloudflare_exists,
        direct_exists=direct_exists,
        cdn_other_exists=cdn_other_exists,
        ips_direct_countries=ips_direct_countries,
        user_id=user_id,
        domains=list(domains),
    )
