import urllib
import requests
from . import utils
from . import stats
from . import config
from . import settings
from datetime import datetime
from pymongo import MongoClient
from flask import Blueprint, render_template, redirect, url_for, flash, request

blueprint = Blueprint('admin', __name__)

root_url = '/' + config.get_admin_uuid() + '/'

@blueprint.route(root_url)
def dashboard():
    update_available = False
    try:
        latest_version = requests.get(config.VERSION_ENDPOINT, timeout=1).text
        latest_version = int(latest_version)
        if config.LIBERTEA_VERSION < latest_version:
            update_available = True
    except:
        pass

    return render_template('admin/dashboard.jinja', 
        page='dashboard',
        users_count=len(utils.get_users()),
        admin_uuid=config.get_admin_uuid(),
        active_domains_count=len(utils.get_active_domains()),
        proxies_count=len(utils.online_route_get_all()),
        no_domain_warning=not utils.has_active_endpoints(),
        no_camouflage_warning=settings.get_camouflage_domain() == None or settings.get_camouflage_domain() == '',
        traffic_today=stats.get_gigabytes_today_all(),
        traffic_this_month=stats.get_gigabytes_this_month_all(),
        ips_today=stats.get_ips_today_all(),
        panel_domain=config.get_panel_domain(),
        month_name=datetime.now().strftime("%B"),
        update_available=update_available,
        cur_version=config.LIBERTEA_VERSION,
    )


@blueprint.route(root_url + 'users/')
def users():
    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    month_short_name = datetime.now().strftime("%b")
    
    all_users = [{
        "id": user["_id"],
        "note": user["note"],
        "created_at_timestamp": user["created_at"].timestamp(),
        "traffic_this_month": user["__cache_traffic_this_month"].replace(' GB', '') if "__cache_traffic_this_month" in user else "0",
        "ips_today": user["__cache_ips_today"] if "__cache_ips_today" in user else 0,
    } for user in users.find()]

    return render_template('admin/users.jinja', 
        page='users',
        no_domain_warning=not utils.has_active_endpoints(),
        month_name=month_short_name,
        admin_uuid=config.get_admin_uuid(),
        users=all_users)

@blueprint.route(root_url + 'users/<user>/', methods=['GET'])
def user(user):
    if user == 'new':
        return render_template('admin/new_user.jinja',
            back_to='users',
            admin_uuid=config.get_admin_uuid(),
            max_ips=settings.get_default_max_ips()
        )

    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    user = users.find_one({"_id": user})
    if user is None:
        return '', 404

    max_ips_default = False
    if 'max_ips' not in user or user['max_ips'] is None or user['max_ips'] == 0:
        max_ips_default = True
        user['max_ips'] = settings.get_default_max_ips()

    user['panel_url'] = "https://" + config.get_panel_domain() + "/" + user['_id'] + "/"

    return render_template('admin/user.jinja',
        back_to='users',
        no_domain_warning=not utils.has_active_endpoints(),
        traffic_today=user['__cache_traffic_today'] if '__cache_traffic_today' in user else '-',
        traffic_this_month=user['__cache_traffic_this_month'] if '__cache_traffic_this_month' in user else '-',
        ips_today=user['__cache_ips_today'] if '__cache_ips_today' in user else '-',
        month_name=datetime.now().strftime("%B"),
        admin_uuid=config.get_admin_uuid(),
        max_ips_default=max_ips_default,
        default_max_ips_count=settings.get_default_max_ips(),
        user=user)


@blueprint.route(root_url + 'users/<user>/', methods=['POST'])
def user_save(user):
    max_ips_default = request.form.get('max_ips_default', None)
    max_ips = int(request.form.get('max_ips', 0))
    note = request.form.get('note', None)

    if max_ips < 0:
        max_ips = 0

    if max_ips_default == 'on':
        max_ips = 0

    if user == 'new':
        uid, _ = utils.create_user(note=note, max_ips=max_ips)
        if note.strip() == '':
            utils.update_user(uid, note=uid)
        return redirect(url_for('admin.user', user=uid))
        
    if note.strip() == '':
        note = user
    utils.update_user(user, max_ips=max_ips, note=note)
    return redirect(url_for('admin.users', user=user))

@blueprint.route(root_url + 'users/<user>/', methods=['DELETE'])
def user_delete(user):
    utils.delete_user(user)
    return '', 200


@blueprint.route(root_url + 'domains/')
def domains():
    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    all_domains = [{
        "id": domain["_id"],
        "status": utils.check_domain_set_properly(domain["_id"]),
        "warning": utils.top_level_domain_equivalent(domain["_id"], config.get_panel_domain()),
    } for domain in domains.find()]

    return render_template('admin/domains.jinja', 
        page='domains',
        admin_uuid=config.get_admin_uuid(),
        domains=all_domains)


@blueprint.route(root_url + 'domains/<domain>/', methods=['GET'])
def domain(domain):
    if domain == 'new':
        return render_template('admin/new_domain.jinja',
            back_to='domains',
            server_ip=config.SERVER_MAIN_IP,
            admin_uuid=config.get_admin_uuid(),
        )

    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domain_entry = db.domains.find_one({"_id": domain})

    if domain_entry is None:
        return '', 404

    utils.update_domain_cache(domain_entry['_id'], try_count=1)

    return render_template('admin/domain.jinja', 
        back_to='domains',
        admin_uuid=config.get_admin_uuid(),
        server_ip=config.SERVER_MAIN_IP,
        ip_override=utils.get_domain_dns_domain(domain_entry['_id']),
        domain=domain_entry['_id'],
        same_domain_as_panel_warning=utils.top_level_domain_equivalent(domain_entry["_id"], config.get_panel_domain()),
        status=utils.check_domain_set_properly(domain_entry['_id']),
        cdn_provider=utils.check_domain_cdn_provider(domain_entry['_id']))

@blueprint.route(root_url + 'domains/<domain>/', methods=['POST'])
def domain_save(domain):
    if domain == 'new':
        domain = request.form.get('domain', None)
        if domain is not None:
            domain = domain.strip()
            if domain.startswith('http://'):
                domain = domain[7:]
            if domain.startswith('https://'):
                domain = domain[8:]
            if domain.startswith('www.'):
                domain = domain[4:]
            utils.add_domain(domain)

        if request.form.get('next', None) == 'dashboard':
            return redirect(url_for('admin.dashboard'))
        
        return redirect(url_for('admin.domain', domain=domain))

    ip_override = request.form.get('ip_override', None)
    if ip_override is not None:
        ip_override = ip_override.strip()
        if ip_override == '':
            ip_override = None

        utils.update_domain(domain, dns_domain=ip_override)
    return redirect(url_for('admin.domains'))

@blueprint.route(root_url + 'domains/<domain>/', methods=['DELETE'])
def domain_delete(domain):
    utils.remove_domain(domain)
    return '', 200

@blueprint.route(root_url + 'proxies/')
def proxies():
    proxy_ips = utils.online_route_get_all()
    print(proxy_ips)
    proxies = [{
        'ip': x
    } for x in proxy_ips]

    return render_template('admin/proxies.jinja',
        page='proxies',
        proxies=proxies,
        bootstrap_script_url=config.get_bootstrap_script_url(),
        server_ip=config.SERVER_MAIN_IP,
        panel_secret_key=config.get_panel_secret_key(),
        proxy_register_endpoint=f"https://{config.SERVER_MAIN_IP}/{config.get_proxy_connect_uuid()}/route",
        admin_uuid=config.get_admin_uuid())

def check_camouflage_domain(camouflage_domain):
    try:
        r = requests.get(camouflage_domain, timeout=5, allow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36',
            })
        if r.status_code == 200:
            if not r.url.startswith('https://'):
                # return redirect(root_url + 'settings/?camouflage_error=camouflage_domain_not_https&camouflage_domain=' + urllib.parse.quote(camouflage_domain))
                return "camouflage_domain_not_https", camouflage_domain

            camouflage_domain = 'https://' + r.url.split('/')[2]
        else:
            settings.set_camouflage_domain("")
            print("Error while checking camouflage domain: Got response " + str(r.status_code) + " from " + camouflage_domain)
            # return redirect(root_url + 'settings/?camouflage_error=camouflage_domain_not_reachable&camouflage_domain=' + urllib.parse.quote(camouflage_domain))
            return "camouflage_domain_not_reachable", camouflage_domain
    except Exception as e:
        settings.set_camouflage_domain("")
        print("Error while checking camouflage domain " + camouflage_domain + ": " + str(e))
        # return redirect(root_url + 'settings/?camouflage_error=camouflage_domain_not_reachable&camouflage_domain=' + urllib.parse.quote(camouflage_domain))
        return "camouflage_domain_not_reachable", camouflage_domain

    return "", camouflage_domain


@blueprint.route(root_url + 'settings/', methods=['GET'])
def app_settings():
    camouflage_error = request.args.get('camouflage_error', None)
    camouflage_domain = request.args.get('camouflage_domain', None)

    if camouflage_domain is None:
        saved_camouflage_domain = settings.get_camouflage_domain()
        if saved_camouflage_domain is None or saved_camouflage_domain == "":
            camouflage_domain = "https://"
        else:
            camouflage_domain = saved_camouflage_domain
            camouflage_domain_status, camouflage_domain = check_camouflage_domain(camouflage_domain)
            if camouflage_domain_status != "":
                camouflage_error = camouflage_domain_status
        
    
    return render_template('admin/settings.jinja',
        page='settings',
        admin_uuid=config.get_admin_uuid(),
        max_ips=settings.get_default_max_ips(),
        proxy_use_80=settings.get_secondary_proxy_use_80_instead_of_443(),
        single_file_clash=settings.get_single_clash_file_configuration(),
        providers_from_all_endpoints=settings.get_providers_from_all_endpoints(),
        add_domains_even_if_inactive=settings.get_add_domains_even_if_inactive(),
        camouflage_domain=camouflage_domain,
        camouflage_error=camouflage_error,
        route_direct_countries=config.ROUTE_IP_LISTS,
        route_direct_country_enabled={x['id']: settings.get_route_direct_country_enabled(x['id']) for x in config.ROUTE_IP_LISTS},
        provider_enabled={x: settings.get_provider_enabled(x) for x in ['vlessws', 'vmessws', 'trojanws', 'ssv2ray']},
    )

@blueprint.route(root_url + 'settings/', methods=['POST'])
def app_settings_save():
    max_ips = request.form.get('max_ips', None)
    proxy_use_80 = request.form.get('proxy_use_80', None)
    single_file_clash = request.form.get('single_file_clash', None)
    providers_from_all_endpoints = request.form.get('providers_from_all_endpoints', None)
    route_direct = {x['id']: request.form.get('route_direct_' + x['id'], None) for x in config.ROUTE_IP_LISTS}
    provider_enabled = {x: request.form.get('provider_' + x, None) for x in ['vlessws', 'vmessws', 'trojanws', 'ssv2ray']}
    add_domains_even_if_inactive = request.form.get('add_domains_even_if_inactive', None)
    camouflage_domain = request.form.get('camouflage_domain', None)

    if max_ips is not None:
        settings.set_default_max_ips(max_ips)
    if add_domains_even_if_inactive is not None:
        settings.set_add_domains_even_if_inactive(add_domains_even_if_inactive == 'on')
    settings.set_secondary_proxy_use_80_instead_of_443(proxy_use_80 == 'on')
    settings.set_single_clash_file_configuration(single_file_clash == 'on')
    settings.set_providers_from_all_endpoints(providers_from_all_endpoints == 'on')
    for x in config.ROUTE_IP_LISTS:
        settings.set_route_direct_country_enabled(x['id'], route_direct[x['id']] == 'on')
    for x in ['vlessws', 'vmessws', 'trojanws', 'ssv2ray']:
        settings.set_provider_enabled(x, provider_enabled[x] == 'on')

    # if none of trojanws and ssv2ray is enabled, enable trojanws
    if not settings.get_provider_enabled('trojanws') and not settings.get_provider_enabled('ssv2ray'):
        settings.set_provider_enabled('trojanws', True)

    if camouflage_domain is not None:
        if camouflage_domain == '' or camouflage_domain == 'https://':
            settings.set_camouflage_domain("")
        else:
            if not camouflage_domain.startswith('http'):
                camouflage_domain = 'https://' + camouflage_domain

            # check if domain is reachable
            camouflage_domain_status, camouflage_domain = check_camouflage_domain(camouflage_domain)
            if camouflage_domain_status == "":
                settings.set_camouflage_domain(camouflage_domain)
            else:
                return redirect(root_url + 'settings/?camouflage_error=' + camouflage_domain_status + '&camouflage_domain=' + urllib.parse.quote(camouflage_domain))

    return redirect(url_for('admin.app_settings'))

