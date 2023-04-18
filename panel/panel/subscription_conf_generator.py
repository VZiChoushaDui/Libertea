import os
import re
import json
import base64
from . import utils
from . import config
from . import settings
from . import clash_conf_generator
from pymongo import MongoClient
from flask import render_template
from datetime import datetime, timedelta

def fix_path_for_grpc_clients(path):
    path = path.replace('/', '___')
    if path.startswith('___'):
        path = '/' + path[3:]
    return path

def generate_conf(user_id, connect_url, vless=True, trojan=True, shadowsocks=True, enabled_tiers=None):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    provider_urls = []
    providers = clash_conf_generator.get_providers(connect_url, db)
    if enabled_tiers is not None:
        providers = [p for p in providers if p['tier'] in enabled_tiers]
    try:
        providers = sorted(providers, key=lambda k: int(k['tier']))
    except:
        pass

    for provider in providers:
        # generate url for each provider
        if provider['type'] == 'trojan-ws' and trojan:
            provider_urls.append('trojan://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?sni=' + provider['sni'] + '&type=ws&host=' + provider['host'] + '&path=' + provider['path'] + 
                                 '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + '&fp=chrome' +
                                 '#' + config.get_panel_domain() + ' ' + provider['name'])
        elif provider['type'] == 'vless-ws' and vless:
            provider_urls.append('vless://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?sni=' + provider['sni'] + '&type=ws&host=' + provider['host'] + '&path=' + provider['path'] + 
                                 '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + '&security=tls&encryption=none&fp=chrome'
                                 '#' + config.get_panel_domain() + ' ' + provider['name'])
        elif provider['type'] == 'ss-v2ray' and shadowsocks:
            # add xray plugin to url
            provider_urls.append('ss://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?plugin=v2ray-plugin%3Btls%3Bhost%3D' + provider['host'] + '%3Bpath%3D' + provider['path'] + '%3Bmux%3D4' + 
                                 '#' + config.get_panel_domain() + ' ' + provider['name'])
        elif provider['type'] == 'vless-grpc':
            provider_urls.append('vless://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) +
                                    '?sni=' + provider['sni'] + '&type=grpc&host=' + provider['host'] +
                                    '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + '&serviceName=' + fix_path_for_grpc_clients(provider['path'])[1:] +
                                    '&security=tls&encryption=none&fp=chrome#' + config.get_panel_domain() + ' ' + provider['name'])
        elif provider['type'] == 'trojan-grpc':
            provider_urls.append('trojan://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) +
                                    '?sni=' + provider['sni'] + '&type=grpc&host=' + provider['host'] + '&path=' +
                                    '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + '&serviceName=' + fix_path_for_grpc_clients(provider['path'])[1:] +
                                    '&fp=chrome#' + config.get_panel_domain() + ' ' + provider['name'])
        elif provider['type'] == 'vmess-ws':
            # vmess is a base64 encoded json
            vmess_json = {
                'v': '2',
                'ps': provider['name'],
                'add': provider['host'],
                'port': str(provider['port']),
                'id': provider['password'],
                'aid': '2',
                'net': 'ws',
                'type': 'none',
                'host': provider['host'],
                'path': provider['path'],
                'tls': 'tls',
                'sni': provider['sni'],
                'allowInsecure': provider['skip_cert_verify'],
            }
            provider_urls.append('vmess://' + base64.b64encode(json.dumps(vmess_json).encode('utf-8')).decode('utf-8'))
        elif provider['type'] == 'vmess-grpc':
            vmess_json = {
                'v': '2',
                'ps': provider['name'],
                'add': provider['host'],
                'port': str(provider['port']),
                'id': provider['password'],
                'aid': '2',
                'net': 'grpc',
                'type': 'none',
                'host': provider['host'],
                'path': fix_path_for_grpc_clients(provider['path']),
                'tls': 'tls',
                'sni': provider['sni'],
                'allowInsecure': provider['skip_cert_verify'],
                'serviceName': fix_path_for_grpc_clients(provider['path'])[1:],
            }
            provider_urls.append('vmess://' + base64.b64encode(json.dumps(vmess_json).encode('utf-8')).decode('utf-8'))


    return provider_urls



def generate_conf_json(user_id, connect_url, enabled_tiers=None):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    providers = clash_conf_generator.get_providers(connect_url, db)
    provider_confs = []    
    if enabled_tiers is not None:
        providers = [p for p in providers if p['tier'] in enabled_tiers]
    try:
        providers = sorted(providers, key=lambda k: int(k['tier']))
    except:
        pass

    for provider in providers:
        if provider['type'] == 'ss-v2ray':
            ss_json_v2ray = {
                "server": provider['server'],
                "server_port": provider['port'],
                "password": provider['password'],
                "method": "chacha20-ietf-poly1305",
                "plugin": "v2ray-plugin",
                "plugin_opts": "tls;host=" + provider['host'] + ";path=" + fix_path_for_grpc_clients(provider['path']) + ";mux=4",
                "remarks": config.get_panel_domain() + ' ' + provider['name'],
            }
            provider_confs.append(ss_json_v2ray)

    return provider_confs
