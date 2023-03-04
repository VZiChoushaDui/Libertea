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

def generate_conf(user_id, connect_url, vless=True, trojan=True, shadowsocks=True):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    providers = clash_conf_generator.get_providers(connect_url, db)
    provider_urls = []

    for provider in providers:
        # generate url for each provider
        if provider['type'] == 'trojan-ws' and trojan:
            provider_urls.append('trojan://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?sni=' + provider['sni'] + '&type=ws&host=' + provider['host'] + '&path=' + provider['path'] + 
                                 '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + 
                                 '#' + provider['name'])
        elif provider['type'] == 'vless-ws' and vless:
            provider_urls.append('vless://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?sni=' + provider['sni'] + '&type=ws&host=' + provider['host'] + '&path=' + provider['path'] + 
                                 '&alpn=http/1.1&allowInsecure=' + (provider['skip_cert_verify']) + '&security=tls&encryption=none'
                                 '#' + provider['name'])
        elif provider['type'] == 'ss-v2ray' and shadowsocks:
            # add xray plugin to url
            provider_urls.append('ss://' + provider['password'] + '@' + provider['server'] + ':' + str(provider['port']) + provider['path'] + 
                                 '?plugin=v2ray-plugin%3Btls%3Bhost%3D' + provider['host'] + '%3Bpath%3D' + provider['path'] + '%3Bmux%3D4' + 
                                 '#' + provider['name'])
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
        
    return provider_urls



def generate_conf_json(user_id, connect_url):
    if not utils.has_active_endpoints():
        raise Exception('No active domains found')

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    providers = clash_conf_generator.get_providers(connect_url, db)
    provider_confs = []

    for provider in providers:
        if provider['type'] == 'ss-v2ray':
            ss_json_xray = {
                "server": provider['server'],
                "server_port": provider['port'],
                "password": provider['password'],
                "method": "chacha20-ietf-poly1305",
                "plugin": "xray-plugin",
                "plugin_opts": "tls;host=" + provider['host'] + ";path=" + provider['path'] + ";mux=8",
                "remarks": provider['name'],
            }
            ss_json_v2ray = {
                "server": provider['server'],
                "server_port": provider['port'],
                "password": provider['password'],
                "method": "chacha20-ietf-poly1305",
                "plugin": "v2ray-plugin",
                "plugin_opts": "tls;host=" + provider['host'] + ";path=" + provider['path'] + ";mux=8",
                "remarks": provider['name'],
            }
            provider_confs.append(ss_json_xray)
            provider_confs.append(ss_json_v2ray)

    return provider_confs
