import re
import json
import urllib
import socket
import requests
import threading
from . import utils
from . import stats
from . import config
from . import sysops
from . import settings
from . import health_check
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request

blueprint = Blueprint('admin', __name__)

root_url = '/' + config.get_admin_uuid() + '/'

@blueprint.route(root_url)
def rootpage():
    users_count = len(utils.get_users())
    if users_count <= 1:
        # if not settings.get_has_dashboard_opened():
        #     return redirect(url_for('welcome.welcome'))
        return redirect(url_for('welcome.welcome'))

    return redirect(url_for('admin.dashboard'))

def get_health_warnings():
    update_available = False
    try:
        latest_version = requests.get(config.VERSION_ENDPOINT, timeout=1).text
        latest_version = int(latest_version)
        if config.LIBERTEA_VERSION < latest_version:
            update_available = True
    except:
        pass

    route_direct_country_enabled = {x['id']: settings.get_route_direct_country_enabled(x['id']) for x in config.ROUTE_IP_LISTS}
    
    return {
        'no_camouflage': {
            'status': settings.get_camouflage_domain() == None or settings.get_camouflage_domain() == '',
            'score_penalty': 0.4,
            'severity': 2,
        },
        'update_available': {
            'status': update_available,
            'score_penalty': 0.1,
            'severity': 1,
        },
        'proxy_update_available': {
            'status': utils.online_route_any_update_available(),
            'score_penalty': 0.1,
            'severity': 1,
        },
        'no_direct_country': {
            'status': not any(route_direct_country_enabled.values()),
            'score_penalty': 0.1,
            'severity': 1,
        },
        'same_domain_for_panel_and_vpn': {
            'status': config.get_panel_domain() in utils.get_domains(),
            'score_penalty': 0.1,
            'severity': 1,
        },
        'no_secondary_route': {
            'status': len(utils.online_route_get_all()) == 0,
            'score_penalty': 0.1,
            'severity': 1,
        },
        'secondary_route_without_domain': {
            'status': any([x for x in utils.online_route_get_all() if utils.get_domain_for_ip(x) is None]),
            'score_penalty': 0.1,
            'severity': 1,
        }
    }

@blueprint.route(root_url + "security/")
def security():
    health_warnings = get_health_warnings()

    no_warnings = True
    for warning in health_warnings:
        if health_warnings[warning]['status']:
            no_warnings = False
            break

    return render_template('admin/security.jinja',
        page='security',
        libertea_version=config.LIBERTEA_VERSION,
        back_to='dashboard',
        admin_uuid=config.get_admin_uuid(),
        health_warnings=health_warnings,
        no_warnings=no_warnings,
        panel_domain=config.get_panel_domain(),
    )

@blueprint.route(root_url + "dashboard/")
def dashboard():
    settings.set_has_dashboard_opened(True)

    health_warnings = get_health_warnings()
    warning_level = 0
    security_score = 1
    for warning in health_warnings:
        if health_warnings[warning]['status']:
            warning_level = max(warning_level, health_warnings[warning]['severity'])
            security_score -= health_warnings[warning]['score_penalty']
            
    flavour = config.get_libertea_branch()
    if flavour is None or flavour == "" or flavour == "master":
        flavour = "release"

    return render_template('admin/dashboard.jinja', 
        page='dashboard',
        libertea_version=config.LIBERTEA_VERSION,
        libertea_flavour=flavour,
        admin_uuid=config.get_admin_uuid(),
        users_count=len(utils.get_users()),
        domains_count=len(utils.get_domains()),
        active_domains_count=len(utils.get_active_domains()),
        proxies_count=len(utils.online_route_get_all()),
        no_domain_warning=not utils.has_active_endpoints(),
        panel_domain=config.get_panel_domain(),
        month_name=datetime.now().strftime("%B"),
        proxy_update_available=utils.online_route_any_update_available(),
        warning_level=warning_level,
        security_score=security_score,
    )


@blueprint.route(root_url + "health/<domain>", methods=['GET'])
def health_domain(domain):
    if domain == 'cache':
        return health_check.get_health_cache()

    hours = int(str(request.args.get('hours', '24')))
    return health_check.get_health_data(domain, hours=hours)

def get_bootstrap_env():
    if config.get_libertea_branch() == "master":
        return ""
    return "export LIBERTEA_BRANCH=" + config.get_libertea_branch() + " && "

@blueprint.route(root_url + "stats/user", methods=['GET'])
def user_stats():
    ips_now = stats.get_total_connected_ips_right_now()
    ips_now_long = stats.get_total_connected_ips_right_now(long=True)
    users_now = stats.get_connected_users_now()
    users_now_long = stats.get_connected_users_now(long=True)
    traffic_today = stats.get_gigabytes_today_all()
    traffic_this_month = stats.get_gigabytes_this_month_all()
    traffic_past_30_days = stats.get_gigabytes_past_30_days_all()
    ips_today = stats.get_ips_today_all()
    users_today = stats.get_connected_users_today()

    try:
        traffic_today = str(round(traffic_today, 2)) + " GB"
        traffic_this_month = str(round(traffic_this_month, 2)) + " GB"
        traffic_past_30_days = str(round(traffic_past_30_days, 2)) + " GB"
    except:
        pass
    try:
        if int(users_now) > int(users_today):
            users_today = users_now
    except:
        pass
    try:
        if int(ips_now) > int(ips_today):
            ips_today = ips_now
    except:
        pass

    return {
        'ips_now': ips_now,
        'ips_now_long': ips_now_long,
        'users_now': users_now,
        'users_now_long': users_now_long,
        'traffic_today': traffic_today,
        'traffic_this_month': traffic_this_month,
        'traffic_past_30_days': traffic_past_30_days,
        'ips_today': ips_today,
        'users_today': users_today,
    }

@blueprint.route(root_url + "stats/system", methods=['GET'])
def system_stats():
    return {
        'cpu': stats.get_system_stats_cpu(),
        'ram': stats.get_system_stats_ram(),
    }

@blueprint.route(root_url + "stats/system/<ip>", methods=['GET'])
def system_stats_ip(ip):
    metadata = utils.online_route_get_metadata(ip)

    return {
        'cpu': metadata['latest_cpu_usage'] if 'latest_cpu_usage' in metadata else 'N/A',
        'ram': metadata['latest_ram_usage'] if 'latest_ram_usage' in metadata else 'N/A',
        'proxy_type': metadata['proxy_type'] if 'proxy_type' in metadata else 'HTTPS',
        'fake_traffic_enabled': metadata['fake_traffic_enabled'] if 'fake_traffic_enabled' in metadata else False,
        'fake_traffic_avg_gb_per_day': metadata['fake_traffic_avg_gb_per_day'] if 'fake_traffic_avg_gb_per_day' in metadata else 0,
    }

@blueprint.route(root_url + "stats/connections", methods=['GET'])
def connection_stats():
    connected_ips_over_time_xs = []
    connected_ips_over_time_ys = []

    days = str(request.args.get('days', '7'))
    if not days.isdigit():
        days = '7'
    days = int(days)

    connected_ips_over_time_format = re.compile('[0-9][0-9]\:[0-9][0-9]')
    cur_date = datetime.now() - timedelta(days=days, seconds=1)
    while cur_date <= datetime.now():
        connected_ips_over_time_raw = stats.get_all_connected_ips_over_time(cur_date.year, cur_date.month, cur_date.day)
        day_str = cur_date.strftime("%m-%d")
        for key in connected_ips_over_time_raw:
            if connected_ips_over_time_format.match(key) and str(connected_ips_over_time_raw[key]).isdigit():
                connected_ips_over_time_xs.append(day_str + " " + key)
                connected_ips_over_time_ys.append(int(connected_ips_over_time_raw[key]))
        cur_date += timedelta(days=1)

    return {
        "x": connected_ips_over_time_xs,
        "y": connected_ips_over_time_ys,
    }

@blueprint.route(root_url + "stats/connections/<user_id>", methods=['GET'])
def connection_stats_user(user_id):
    connected_ips_over_time_xs = []
    connected_ips_over_time_ys = []
    
    days = str(request.args.get('days', '7'))
    if not days.isdigit():
        days = '7'
    days = int(days)

    connected_ips_over_time_format = re.compile('[0-9][0-9]\:[0-9][0-9]')
    cur_date = datetime.now() - timedelta(days=7, seconds=1)
    while cur_date <= datetime.now():
        connected_ips_over_time_raw = stats.get_connected_ips_over_time(user_id, cur_date.year, cur_date.month, cur_date.day)
        day_str = cur_date.strftime("%m-%d")
        for key in connected_ips_over_time_raw:
            if connected_ips_over_time_format.match(key) and str(connected_ips_over_time_raw[key]).isdigit():
                connected_ips_over_time_xs.append(day_str + " " + key)
                connected_ips_over_time_ys.append(int(connected_ips_over_time_raw[key]))
        cur_date += timedelta(days=1)

    return {
        "x": connected_ips_over_time_xs,
        "y": connected_ips_over_time_ys,
    }

@blueprint.route(root_url + "stats/traffic", methods=['GET'])
def traffic_stats():
    days = str(request.args.get('days', '7'))
    if not days.isdigit():
        days = '7'
    days = int(days)

    traffic_over_time_xs, traffic_over_time_ys = stats.get_traffic_per_day_all(days=days)
    traffic_over_time_xs = [x[5:] for x in traffic_over_time_xs]

    return {
        "x": traffic_over_time_xs,
        "y": traffic_over_time_ys,
    }

@blueprint.route(root_url + "stats/traffic/user/<user_id>", methods=['GET'])
def traffic_stats_user(user_id):
    days = str(request.args.get('days', '7'))
    if not days.isdigit():
        days = '7'
    days = int(days)

    traffic_over_time_xs, traffic_over_time_ys = stats.get_traffic_per_day(user_id, days=days)
    traffic_over_time_xs = [x[5:] for x in traffic_over_time_xs]

    return {
        "x": traffic_over_time_xs,
        "y": traffic_over_time_ys,
    }
    
@blueprint.route(root_url + "stats/traffic/domain/<domain>", methods=['GET'])
def traffic_stats_domain(domain):
    days = str(request.args.get('days', '7'))
    if not days.isdigit():
        days = '7'
    days = int(days)

    traffic_over_time_xs, traffic_over_time_ys = stats.get_traffic_per_day_all(days=days, domain=domain)
    traffic_over_time_xs = [x[5:] for x in traffic_over_time_xs]

    return {
        "x": traffic_over_time_xs,
        "y": traffic_over_time_ys,
    }

@blueprint.route(root_url + 'users/')
def users():
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    month_short_name = datetime.now().strftime("%b")
    
    all_users = [{
        "id": user["_id"],
        "note": user["note"],
        "created_at_timestamp": user["created_at"].timestamp(),
        "traffic_today": str(user["__cache_traffic_today"]) if "__cache_traffic_today" in user else "0",
        "traffic_this_month": str(user["__cache_traffic_this_month"]) if "__cache_traffic_this_month" in user else "0",
        "traffic_past_30_days": str(user["__cache_traffic_past_30_days"]) if "__cache_traffic_past_30_days" in user else "0",
        "ips_today": user["__cache_ips_today"] if "__cache_ips_today" in user else 0,
    } for user in users.find()]

    return render_template('admin/users.jinja', 
        page='users',
        libertea_version=config.LIBERTEA_VERSION,
        no_domain_warning=not utils.has_active_endpoints(),
        month_name=month_short_name,
        month_long_name=datetime.now().strftime("%B"),
        admin_uuid=config.get_admin_uuid(),
        users=all_users)

@blueprint.route(root_url + 'users/<user>/', methods=['GET'])
def user(user):
    if user == 'new':
        return render_template('admin/new_user.jinja',
            back_to='users',
            libertea_version=config.LIBERTEA_VERSION,
            admin_uuid=config.get_admin_uuid(),
            max_ips=settings.get_default_max_ips()
        )

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    user = users.find_one({"_id": user})
    if user is None:
        return '', 404

    max_ips_default = False
    if 'max_ips' not in user or user['max_ips'] is None or user['max_ips'] == 0:
        max_ips_default = True
        user['max_ips'] = settings.get_default_max_ips()

    if 'monthly_traffic' not in user or user['monthly_traffic'] is None:
        user['monthly_traffic'] = -1
    
    user_expired = False
    if 'user_active_until' not in user or user['user_active_until'] is None:
        user['user_active_until'] = ''
    try:
        if user['user_active_until'] != '':
            active_until_date = datetime.strptime(user['user_active_until'], '%Y-%m-%d %H:%M')
            if active_until_date < datetime.now():
                user_expired = True
    except:
        user['user_active_until'] = ''

    user['panel_url'] = "https://" + config.get_panel_domain() + "/" + user['_id'] + "/"
    user['tier_enabled_for_subscription'] = utils.get_user_tiers_enabled_for_subscription(user['_id'])

    return render_template('admin/user.jinja',
        back_to='users',
        libertea_version=config.LIBERTEA_VERSION,
        no_domain_warning=not utils.has_active_endpoints(),
        traffic_today=round(stats.get_gigabytes_today(user['_id'], db=db), 2),
        traffic_this_month=round(stats.get_gigabytes_this_month(user['_id'], db=db), 2),
        traffic_past_30_days=round(stats.get_gigabytes_past_30_days(user['_id'], db=db), 2),
        ips_today=user['__cache_ips_today'] if '__cache_ips_today' in user else '-',
        month_name=datetime.now().strftime("%B"),
        admin_uuid=config.get_admin_uuid(),
        max_ips_default=max_ips_default,
        default_max_ips_count=settings.get_default_max_ips(),
        user_expired=user_expired,
        user=user)

@blueprint.route(root_url + 'users/<user>/', methods=['POST'])
def user_save(user):
    max_ips_default = request.form.get('max_ips_default', None)
    max_ips = int(request.form.get('max_ips', 0))
    note = request.form.get('note', None)
    tier_enabled_for_subscription = {str(i): request.form.get(f'tier_enabled_for_subscription_{i}', None) for i in [1,2,3,4, 'default']}

    if max_ips < 0:
        max_ips = 0

    if max_ips_default == 'on':
        max_ips = 0

    monthly_traffic = -1
    try:
        monthly_traffic_unlimited = request.form.get('monthly_traffic_unlimited', None)
        if monthly_traffic_unlimited == 'on':
            monthly_traffic = -1
        else:
            monthly_traffic = int(request.form.get('monthly_traffic', -1))
            if monthly_traffic <= 0:
                monthly_traffic = -1
    except:
        pass

    user_active_until = request.form.get('user_active_until', '')
    user_active_until_unlimited = request.form.get('user_active_until_unlimited', None)
    if user_active_until_unlimited == 'on':
        user_active_until = ''

    if user == 'new':
        uid, _ = utils.create_user(note=note, max_ips=max_ips)
        if note.strip() == '':
            utils.update_user(uid, note=uid)
        tier_enabled_for_subscription['default'] = True
        utils.update_user(uid, max_ips=max_ips, tier_enabled_for_subscription=tier_enabled_for_subscription, 
            monthly_traffic=monthly_traffic, user_active_until=user_active_until)
        return redirect(url_for('admin.user', user=uid))
        
    if note.strip() == '':
        note = user
    utils.update_user(user, max_ips=max_ips, note=note, tier_enabled_for_subscription=tier_enabled_for_subscription, 
        monthly_traffic=monthly_traffic, user_active_until=user_active_until)  
    return redirect(url_for('admin.user', user=user))

@blueprint.route(root_url + 'users/<user>/', methods=['DELETE'])
def user_delete(user):
    utils.delete_user(user)
    return '', 200

@blueprint.route(root_url + 'domains/')
def domains():
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    all_domains = [{
        "id": domain["_id"],
        "ip": utils.get_domain_ip(domain["_id"]),
        "status": utils.check_domain_set_properly(domain["_id"], db=db),
        "warning": utils.top_level_domain_equivalent(domain["_id"], config.get_panel_domain()),
        "tier": utils.get_domain_or_online_route_tier(domain["_id"], db=db, return_default_if_none=True),
    } for domain in domains.find()]

    proxy_ips = utils.secondary_route_get_all(db)
    proxies = [{
        "ip": x['ip'],
        "tier": x['tier'],
        "update_available": x['update_available'],
        "online": x['online'],
        "domains": [utils.get_domain_for_ip(x['ip'])] if utils.get_domain_for_ip(x['ip']) is not None else [],
    } for x in proxy_ips]

    proxy_domains = []
    for proxy in proxies:
        proxy_domains += proxy['domains']
    all_domains = [x for x in all_domains if x['id'] not in proxy_domains]

    all_domains = sorted([x for x in all_domains if x['status'] in ['active', 'cdn-disabled']], key=lambda k: int(k['tier'])) + \
        sorted([x for x in all_domains if x['status'] not in ['active', 'cdn-disabled']], key=lambda k: int(k['tier']))
    
    proxies = sorted([x for x in proxies if x['online']], key=lambda k: int(k['tier'])) + \
        sorted([x for x in proxies if not x['online']], key=lambda k: int(k['tier']))

    return render_template('admin/domains.jinja', 
        page='domains',
        libertea_version=config.LIBERTEA_VERSION,
        panel_domain=config.get_panel_domain(),
        admin_uuid=config.get_admin_uuid(),
        domains=all_domains,
        proxies=proxies,
        server_ip=config.SERVER_MAIN_IP,
        health_check=settings.get_periodic_health_check(db=db),
    )

@blueprint.route(root_url + 'proxies/new/', methods=['GET'])
def new_proxy():
    return render_template('admin/new_secondary_proxy.jinja',
        back_to='domains',
        libertea_version=config.LIBERTEA_VERSION,
        server_ip=config.SERVER_MAIN_IP,
        proxy_configuration_uuid=config.get_proxy_configuration_uuid(),
        panel_domain=config.get_panel_domain(),
        admin_uuid=config.get_admin_uuid(),
        bootstrap_script_url=config.get_bootstrap_script_url(),
        bootstrap_env=get_bootstrap_env(),
        panel_secret_key=config.get_panel_secret_key(),
        proxy_register_endpoint=f"https://{config.SERVER_MAIN_IP}/{config.get_proxy_connect_uuid()}/route",
    )

@blueprint.route(root_url + 'domains/<id>/', methods=['GET'])
def domain(id):
    if id == 'new':
        return render_template('admin/new_domain.jinja',
            back_to='domains',
            libertea_version=config.LIBERTEA_VERSION,
            server_ip=config.SERVER_MAIN_IP,
            admin_uuid=config.get_admin_uuid(),
        )

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domain_entry = db.domains.find_one({"_id": id})

    tier = utils.get_domain_or_online_route_tier(id)
    if tier is None:
        tier = utils.get_default_tier_for_route(id)
    tier = str(tier)

    if domain_entry is None:
        proxy_ips = utils.secondary_route_get_all()
        entry = [x for x in proxy_ips if x['ip'] == id]
        if len(entry) == 0:
            return '', 404

        entry = entry[0]
        return render_template('admin/domain.jinja', 
            back_to='domains',
            libertea_version=config.LIBERTEA_VERSION,
            status='active' if entry['online'] else 'inactive',
            admin_uuid=config.get_admin_uuid(),
            server_ip=config.SERVER_MAIN_IP,
            domain=id,
            secondary_proxy=True,
            proxy_domain=request.args.get('proxy_domain', utils.get_domain_for_ip(id)),
            proxy_domain_error=request.args.get('proxy_domain_error', None),
            secondary_proxy_update_available=utils.online_route_update_available(id),
            bootstrap_script_url=config.get_bootstrap_script_url(),
            bootstrap_env=get_bootstrap_env(),
            panel_secret_key=config.get_panel_secret_key(),
            proxy_configuration_uuid=config.get_proxy_configuration_uuid(),
            panel_domain=config.get_panel_domain(),
            proxy_register_endpoint=f"https://{config.SERVER_MAIN_IP}/{config.get_proxy_connect_uuid()}/route",
            health_check=settings.get_periodic_health_check(),
            tier=tier,
        )

    utils.update_domain_cache(domain_entry['_id'], try_count=1)

    return render_template('admin/domain.jinja', 
        back_to='domains',
        libertea_version=config.LIBERTEA_VERSION,
        admin_uuid=config.get_admin_uuid(),
        server_ip=config.SERVER_MAIN_IP,
        ip_override=utils.get_domain_dns_domain(domain_entry['_id']),
        domain=domain_entry['_id'],
        same_domain_as_panel_warning=utils.top_level_domain_equivalent(domain_entry["_id"], config.get_panel_domain()),
        status=utils.check_domain_set_properly(domain_entry['_id']),
        cdn_provider=utils.check_domain_cdn_provider(domain_entry['_id']),
        secondary_proxy=False,
        health_check=settings.get_periodic_health_check(),
        tier=tier,
    )

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

            if len(domain) == 0:
                return redirect(url_for('admin.dashboard'))
            
            utils.add_domain(domain)
            utils.update_domain_cache(domain, 1)
            threading.Thread(target=utils.update_domain_cache, args=(domain, 3)).start()

        if request.form.get('next', None) == 'dashboard':
            return redirect(url_for('admin.dashboard'))
        
        return redirect(url_for('admin.domain', id=domain))

    ip_override = request.form.get('ip_override', None)
    if ip_override is not None:
        ip_override = ip_override.strip()
        if ip_override == '':
            ip_override = domain

        utils.update_domain(domain, dns_domain=ip_override)

    priority = request.form.get('priority', None)
    if priority is not None:
        priority = int(priority)
        utils.set_domain_or_online_route_tier(domain, priority)
    
    return redirect(url_for('admin.domain', id=domain))

@blueprint.route(root_url + 'domains/<id>/proxydomain', methods=['POST'])
def proxydomain_save(id):
    proxy_domain = request.form.get('proxy_domain', None)
    if proxy_domain is not None:
        proxy_domain = proxy_domain.strip()
        if proxy_domain == '':
            proxy_domain = None

        if proxy_domain is not None:
            proxy_domain_ip = socket.gethostbyname(proxy_domain)
            print(id, ":", "domain", proxy_domain, "points to ip", proxy_domain_ip)
            if proxy_domain_ip != id:
                return redirect(root_url + 'domains/' + id + '/?proxy_domain_error=domain_does_not_point_to_ip&proxy_domain=' + urllib.parse.quote(proxy_domain))

            prev_proxy_domain = utils.get_domain_for_ip(id)
            if prev_proxy_domain is not None and prev_proxy_domain != proxy_domain:
                utils.remove_domain(prev_proxy_domain)

            utils.add_domain(proxy_domain)
            utils.update_domain_cache(proxy_domain, 1)
            threading.Thread(target=utils.update_domain_cache, args=(proxy_domain, 3)).start()

            return redirect(root_url + 'domains/' + id + '/?proxy_domain=' + urllib.parse.quote(proxy_domain))

    return redirect(root_url + 'domains/' + id + '/')

@blueprint.route(root_url + 'domains/<domain>/', methods=['DELETE'])
def domain_delete(domain):
    if not utils.remove_domain(domain):
        utils.mark_route_as_deleted(domain)
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
        libertea_version=config.LIBERTEA_VERSION,
        proxies=proxies,
        bootstrap_script_url=config.get_bootstrap_script_url(),
        bootstrap_env=get_bootstrap_env(),
        server_ip=config.SERVER_MAIN_IP,
        panel_secret_key=config.get_panel_secret_key(),
        proxy_register_endpoint=f"https://{config.SERVER_MAIN_IP}/{config.get_proxy_connect_uuid()}/route",
        admin_uuid=config.get_admin_uuid())

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
            camouflage_domain_status, camouflage_domain = utils.check_camouflage_domain(camouflage_domain)
            if camouflage_domain_status != "":
                camouflage_error = camouflage_domain_status
        
    tier_enabled_for_subscription = {}
    proxygroup_type_selected = {}
    for i in [1,2,3,4]:
        proxygroup_type_selected[str(i)] = settings.get_tier_proxygroup_type(i)
        tier_enabled_for_subscription[str(i)] = settings.get_tier_enabled_for_subscription(i)
    print(tier_enabled_for_subscription)

    return render_template('admin/settings.jinja',
        page='settings',
        libertea_version=config.LIBERTEA_VERSION,
        main_domain=config.get_panel_domain(),
        server_ip=config.SERVER_MAIN_IP,
        admin_uuid=config.get_admin_uuid(),
        max_ips=settings.get_default_max_ips(),
        proxy_port=settings.get_secondary_proxy_ports(),
        single_file_clash=settings.get_single_clash_file_configuration(),
        providers_from_all_endpoints=settings.get_providers_from_all_endpoints(),
        add_domains_even_if_inactive=settings.get_add_domains_even_if_inactive(),
        health_check=settings.get_periodic_health_check(),
        manual_tier_select_clash=settings.get_manual_tier_select_clash(),
        camouflage_domain=camouflage_domain,
        camouflage_error=camouflage_error,
        route_direct_countries=config.ROUTE_IP_LISTS,
        route_direct_country_enabled={x['id']: settings.get_route_direct_country_enabled(x['id']) for x in config.ROUTE_IP_LISTS},
        provider_enabled={x: settings.get_provider_enabled(x) for x in ['vlessws', 'trojanws', 'trojangrpc', 'vlessgrpc', 'vmessgrpc', 'ssv2ray', 'ssgrpc']},
        proxygroup_type_selected=proxygroup_type_selected,
        tier_enabled_for_subscription=tier_enabled_for_subscription,
        use_warp=settings.get_use_warp(),
    )

@blueprint.route(root_url + 'settings/', methods=['POST'])
def app_settings_save():
    max_ips = request.form.get('max_ips', None)
    proxy_port = request.form.get('proxy_port', None)
    single_file_clash = request.form.get('single_file_clash', None)
    providers_from_all_endpoints = request.form.get('providers_from_all_endpoints', None)
    route_direct = {x['id']: request.form.get('route_direct_' + x['id'], None) for x in config.ROUTE_IP_LISTS}
    provider_enabled = {x: request.form.get('provider_' + x, None) for x in ['vlessws', 'trojanws', 'trojangrpc', 'vlessgrpc', 'vmessgrpc', 'ssv2ray', 'ssgrpc']}
    add_domains_even_if_inactive = request.form.get('add_domains_even_if_inactive', None)
    camouflage_domain = request.form.get('camouflage_domain', None)
    health_check = request.form.get('health_check', None)
    manual_tier_select_clash = request.form.get('manual_tier_select_clash', None)
    use_warp = request.form.get('use_warp', None)

    tier_enabled_for_subscription = {i: request.form.get(f'tier_enabled_for_subscription_{i}', None) for i in [1,2,3,4]}
    tiers_proxygroup_type = {i: request.form.get(f'tier_{i}_proxygroup_type', None) for i in [1,2,3,4]}
    for i in tiers_proxygroup_type.keys():
        settings.set_tier_proxygroup_type(i, tiers_proxygroup_type[i])
        settings.set_tier_enabled_for_subscription(i, tier_enabled_for_subscription[i] == 'on')

    if max_ips is not None:
        settings.set_default_max_ips(max_ips)
    if proxy_port is not None:
        settings.set_secondary_proxy_ports(proxy_port)

    settings.set_add_domains_even_if_inactive(add_domains_even_if_inactive == 'on')
    settings.set_single_clash_file_configuration(single_file_clash == 'on')
    settings.set_providers_from_all_endpoints(providers_from_all_endpoints == 'on')
    settings.set_periodic_health_check(health_check == 'on')
    settings.set_manual_tier_select_clash(manual_tier_select_clash == 'on')
    settings.set_use_warp(use_warp == 'on')
    for x in config.ROUTE_IP_LISTS:
        settings.set_route_direct_country_enabled(x['id'], route_direct[x['id']] == 'on')
    for x in ['vlessws', 'trojanws', 'ssv2ray', 'trojangrpc', 'vlessgrpc', 'vmessgrpc', 'ssgrpc']:
        settings.set_provider_enabled(x, provider_enabled[x] == 'on')

    # if none of trojanws, ssv2ray and trojangrpc is enabled, enable trojangrpc
    if not settings.get_provider_enabled('trojanws') and not settings.get_provider_enabled('ssv2ray') and not settings.get_provider_enabled('trojangrpc') and not settings.get_provider_enabled('ssgrpc'):
        settings.set_provider_enabled('trojangrpc', True)

    if camouflage_domain is not None:
        if camouflage_domain == '' or camouflage_domain == 'https://':
            settings.set_camouflage_domain("")
        else:
            # check if domain is reachable
            camouflage_domain_status, camouflage_domain = utils.check_camouflage_domain(camouflage_domain)
            if camouflage_domain_status == "":
                prev_camouflage_domain = settings.get_camouflage_domain()
                if prev_camouflage_domain != camouflage_domain:
                    settings.set_camouflage_domain(camouflage_domain)
                    sysops.regenerate_camouflage_cert()
            else:
                return redirect(root_url + 'settings/?camouflage_error=' + camouflage_domain_status + '&camouflage_domain=' + urllib.parse.quote(camouflage_domain))

    return redirect(url_for('admin.app_settings'))

@blueprint.route(root_url + 'settings/reset_tiers/', methods=['POST'])
def app_settings_reset_tiers():
    utils.reset_all_user_tiers_enabled_for_subscription()
    return "ok", 200

@blueprint.route(root_url + 'api/proxies/online', methods=['GET'])
def get_proxies_json():
    proxy_ips = utils.secondary_route_get_all()
    proxies = [{
        "ip": x['ip'],
        "tier": x['tier'],
        "update_available": x['update_available'],
    } for x in proxy_ips if x['online']]

    return json.dumps(proxies)
