from . import utils
from . import config
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

@blueprint.route('/' + config.get_proxy_connect_uuid() + '/route', methods=['POST'])
def add_route():
    if not validate_user_panel_secret():
        return "", 404

    ip = request.form.get('ip')
    if ip == None or ip == "":
        return "", 404

    utils.online_route_ping(ip)
    return "", 200
    