import re
import json
from . import utils
from . import config
from . import sysops
from pymongo import MongoClient
from flask import Blueprint, render_template, redirect, url_for, flash, request

blueprint = Blueprint('api', __name__)

def validate_user():
    api_key = request.headers.get('X-API-KEY')
    if api_key != config.get_hostcontroller_api_key():
        return False
    return True

def validate_user_panel_secret():
    api_key = request.headers.get('X-API-KEY')
    if api_key != config.get_panel_secret_key():
        return False
    return True

@blueprint.route('/api/maxIps', methods=['GET'])
def can_accept_new_user():
    if not validate_user():
        return "", 404

    conn_url = request.args.get('connId')
    max_ips = utils.get_user_max_ips(conn_url=conn_url)

    return str(max_ips), 200


@blueprint.route('/api/createUser', methods=['POST'])
def create_user():
    if not validate_user():
        return "", 404

    note = request.form.get('note')
    referrer = request.form.get('referrer')

    panel_id, connect_url = utils.create_user(note, referrer)

    if panel_id == None:
        return {
            "panelId": "",
            "note": note,
            "duplicate": "true"
        }

    return {
        "panelId": panel_id,
        "connectUrl": connect_url,
        "note": note,
        "referrer": referrer,
    }

@blueprint.route('/api/updateUser', methods=['POST'])
def update_user():
    if not validate_user():
        return "", 404

    panel_id = request.form.get('panelId')
    note = request.form.get('note')
    referrer = request.form.get('referrer')

    utils.update_user(panel_id, note, referrer)

    return "", 200

@blueprint.route('/api/removeUser', methods=['POST'])
def remove_user():
    if not validate_user():
        return "", 404

    panel_id = request.form.get('panelId')

    if (panel_id == None):
        note = request.form.get('note')
        panel_id = utils.get_panel_id_from_note(note)
        if (panel_id == None):
            return "", 404

    if utils.delete_user(panel_id):
        return "", 200

    return "", 404

@blueprint.route('/api/getUsers', methods=['GET'])
def get_users():
    if not validate_user():
        return "", 404

    users = utils.get_users()
    return users


@blueprint.route('/api/addDomain', methods=['POST'])
def add_domain():
    if not validate_user():
        return "", 404

    domain = request.form.get('domain')
    if domain == None or domain == "":
        return "", 400

    dns_domain = None
    sni = None
    args = request.form.get('args')
    try:
        if args != None and args != '':
            args_list = args.strip().split(',')
            for arg in args_list:
                if arg.startswith('dns_domain='):
                    dns_domain = arg[11:]
                    print("DNS Domain: " + dns_domain)
                if arg.startswith('sni='):
                    sni = arg[4:]
                    print("SNI: " + sni)
    except:
        pass


    result = utils.add_domain(domain, dns_domain=dns_domain, sni=sni)
    return "", result
    
@blueprint.route('/api/removeDomain', methods=['POST'])
def remove_domain():
    if not validate_user():
        return "", 404

    domain = request.form.get('domain')
    if utils.remove_domain(domain):
        return "", 200

    return "", 404

@blueprint.route('/api/getDomains', methods=['GET'])
def get_domains():
    if not validate_user():
        return "", 404

    domains = utils.get_domains()
    return domains

@blueprint.route('/' + config.get_proxy_configuration_uuid() + '/<config_id>', methods=['GET'])
def get_configuration(config_id):
    if config_id == 'main-ip':
        return config.SERVER_MAIN_IP, 200
    elif config_id == 'panel-secret-key':
        return config.get_panel_secret_key(), 200
    elif config_id == 'proxy-connect-uuid':
        return config.get_proxy_connect_uuid(), 200
    elif config_id == 'panel-domain':
        return config.get_panel_domain(), 200
    
    return "", 404
    

@blueprint.route('/' + config.get_proxy_connect_uuid() + '/route', methods=['POST'])
def add_route():
    if not validate_user_panel_secret():
        return "", 404

    ip = request.form.get('ip')
    if ip == None or ip == "":
        return "", 404

    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        return "", 404

    version = request.form.get('version')
    if version == None or version == "":
        version = "1000"
    if not version.isdigit():
        version = "1000"
    version = int(version)

    proxy_type = request.form.get('proxyType', 'https')
    cpu_usage = request.form.get('cpuUsage', 'Unknown')
    ram_usage = request.form.get('ramUsage', 'Unknown')
    fake_traffic_enabled = request.form.get('fakeTrafficEnabled', 'False')
    fake_traffic_avg_gb_per_day = request.form.get('fakeTrafficAvgGbPerDay', '0')

    try:
        fake_traffic_enabled = fake_traffic_enabled.lower() == 'true'
        fake_traffic_avg_gb_per_day = float(fake_traffic_avg_gb_per_day)
    except:
        fake_traffic_enabled = False
        fake_traffic_avg_gb_per_day = 0

    utils.online_route_ping(ip, version, proxy_type, cpu_usage, ram_usage, fake_traffic_enabled, fake_traffic_avg_gb_per_day)
    
    ssh_key = request.form.get('sshKey')
    # add the public key to authorized_keys file of user "libertea"
    if ssh_key != None and ssh_key != "":
        sysops.add_ssh_key(ssh_key)

    traffic_data = request.form.get('trafficData')
    try:
        traffic_data = json.loads(traffic_data)
        if traffic_data != None:
            utils.online_route_update_traffic(ip, traffic_data)
    except:
        print("Error parsing bytes data:", traffic_data)
        pass
    
    return "", 200
    