import uuid
import socket
import pymongo
import requests
from . import stats
from . import config
from . import sysops
from . import settings
from datetime import datetime
from pymongo import MongoClient

___max_ips = {}
___max_ips_updated_at = None
___default_max_ips = None

def ___update_max_ips_cache(db=None):
    global ___max_ips
    global ___max_ips_updated_at
    global ___default_max_ips

    if ___max_ips_updated_at is None or (datetime.utcnow() - ___max_ips_updated_at).total_seconds() > 60:
        print("Updating max_ips cache")

        if db is None:
            client = config.get_mongo_client()
            db = client[config.MONGODB_DB_NAME]

        ___max_ips = {}
        default_max_ips = int(settings.get_default_max_ips(db))
        for user in db.users.find():
            ___max_ips[user["_id"]] = int(user.get("max_ips", default_max_ips))
            ___max_ips[user["connect_url"]] = int(user.get("max_ips", default_max_ips))
        ___max_ips_updated_at = datetime.utcnow()

        ___default_max_ips = settings.get_default_max_ips(db)

    return ___max_ips

def ___get_max_ips(panel_id_or_connect_url, db=None):
    global ___max_ips

    ___update_max_ips_cache(db)
    user_max_ips = ___max_ips.get(panel_id_or_connect_url, ___default_max_ips)
    if user_max_ips <= 0:
        return ___default_max_ips
    return user_max_ips

def create_user(note, referrer=None, max_ips=None):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    # check if note is already in use
    if users.find_one({"note": note}) is not None:
        return None, None
    
    panel_id = str(uuid.uuid4())
    connect_url = str(uuid.uuid4())

    new_user = {
        "_id": panel_id,
        "connect_url": connect_url,
        "note": note,
        "referrer": referrer,
        "created_at": datetime.utcnow(),
    }

    if max_ips is not None:
        new_user["max_ips"] = max_ips

    users.insert_one(new_user)

    users.create_index('connect_url')

    if sysops.haproxy_update_users_list():
        return panel_id, connect_url

    raise Exception("Failed to update HAProxy users list")

def update_user(panel_id, note=None, max_ips=None, referrer=None):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    if note is not None:
        users.update_one({"_id": panel_id}, {"$set": {"note": note}})
    if max_ips is not None:
        users.update_one({"_id": panel_id}, {"$set": {"max_ips": int(max_ips)}})
    if referrer is not None:
        users.update_one({"_id": panel_id}, {"$set": {"referrer": referrer}})

    return sysops.haproxy_update_users_list()

def get_panel_id_from_note(note):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    user = users.find_one({"note": note})
    if user is None:
        return None
    return user["_id"]

def delete_user(panel_id):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    if users.find_one({"_id": panel_id}) is None:
        return False

    users.delete_one({"_id": panel_id})

    return sysops.haproxy_update_users_list()

def get_users():
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    all_users = [{
        "panel_id": user["_id"],
        "connect_url": user["connect_url"],
        "note": user["note"],
    } for user in users.find()]
    return all_users

def remove_domain(domain):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    if domains.find_one({"_id": domain}) is None:
        return False

    domains.delete_one({"_id": domain})
    sysops.haproxy_update_domains_list()
    return True

def add_domain(domain, dns_domain=None, sni=None):
    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    # check if domain is already in use
    if domains.find_one({"_id": domain}) is not None:
        return 409
    
    new_domain = {
        '_id': domain,
    }
    if dns_domain is not None:
        new_domain["dns_domain"] = dns_domain
    if sni is not None:
        new_domain["sni"] = sni

    domains.insert_one(new_domain)
    if not sysops.haproxy_update_domains_list():
        remove_domain(domain)
        return 500

    # if not sysops.haproxy_renew_certs():
    #     remove_domain(domain)
    #     return 501

    return 200

def get_domains(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    all_domains = [domain["_id"] for domain in domains.find()]
    return all_domains

def get_domain_dns_domain(domain, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is None:
        return None
    if not "dns_domain" in domain_entry:
        return None
    return domain_entry["dns_domain"]

def get_domain_sni(domain, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is None:
        return None
    if not "sni" in domain_entry:
        return None
    return domain_entry["sni"]

def update_domain(domain, dns_domain=None, sni=None, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    if domains.find_one({"_id": domain}) is None:
        return False

    if dns_domain is not None:
        domains.update_one({"_id": domain}, {"$set": {"dns_domain": dns_domain}})

    if sni is not None:
        domains.update_one({"_id": domain}, {"$set": {"sni": sni}})

    return True

def get_active_domains(db=None):
    return [x for x in get_domains(db=db) if check_domain_set_properly(x, db=db) == 'active']

def get_user_max_ips(panel_id=None, conn_url=None, db=None):
    if panel_id is None and conn_url is None:
        return 0

    if panel_id is not None and conn_url is not None:
        raise Exception("Both panel_id and conn_url are not None")

    if panel_id is not None:
        return ___get_max_ips(panel_id, db=db)
    else:
        return ___get_max_ips(conn_url, db=db)


def online_route_ping(ip, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    online_routes = db.online_routes
    online_routes.update_one({"_id": ip}, {"$set": {"last_seen": datetime.now()}}, upsert=True)


def online_route_get_last_seen(ip, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    online_routes = db.online_routes
    online_route = online_routes.find_one({"_id": ip})
    if online_route is None:
        return None

    return online_route["last_seen"]

def online_route_get_all(max_age_secs=300, db=None):
    # get all online routes (max last seen 5 minutes ago)
    now = datetime.now()
    
    ips = []
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    online_routes = db.online_routes
    for online_route in online_routes.find():
        ip = online_route["_id"]
        last_seen = online_route["last_seen"]
        if (now - last_seen).total_seconds() < max_age_secs:
            ips.append(ip)
            # print("online_route_get_all: ip", ip, "last seen", last_seen, "now", now, "diff", (now - last_seen).total_seconds())

    return ips

check_domain_set_properly_cache_max_time = 60

def domain_cache_update_db(domain, status=None, cdn=None, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    if status is not None:
        domains.update_one({"_id": domain}, {"$set": {"__cache_domain_timestamp": datetime.utcnow(), "__cache_domain_status": status}}, upsert=False)
    if cdn is not None:
        domains.update_one({"_id": domain}, {"$set": {"__cache_domain_cdn": cdn}}, upsert=False)


def update_domain_cache(domain, try_count=3, db=None):
    # send a request to https://[domain]/[get_admin_uuid]/. It should return 401 unauthorized
    try:
        r = requests.get("https://{}/{}/".format(domain, config.get_admin_uuid()), verify=False, timeout=3)
        if r.status_code == 401:
            header_server = r.headers.get('server', '').lower()
            if header_server == 'cloudflare':
                domain_cache_update_db(domain, cdn='Cloudflare', db=db)
            else:
                domain_cache_update_db(domain, cdn='Unknown', db=db)

            # make sure domain does not resolve to config.SERVER_MAIN_IP
            try:
                ip = socket.gethostbyname(domain)
                if ip == config.SERVER_MAIN_IP:
                    domain_cache_update_db(domain, status='cdn-disabled', db=db)
                    return
            except:
                domain_cache_update_db(domain, status='unknown', db=db)
                return

            domain_cache_update_db(domain, status='active', db=db)
            return
    except Exception as e:
        print("update_domain_cache error", e)

        if try_count > 1:
            update_domain_cache(domain, try_count=try_count-1, db=db)
            return

        domain_cache_update_db(domain, status='inactive', db=db)

    domain_cache_update_db(domain, status='inactive', db=db)

def check_domain_set_properly(domain, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is not None:
        if "__cache_domain_status" in domain_entry:
            return domain_entry["__cache_domain_status"]
    return '-'

def check_domain_cdn_provider(domain, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is not None:
        if "__cache_domain_cdn" in domain_entry:
            return domain_entry["__cache_domain_cdn"]
    return '-'

def update_user_stats_cache(user_id, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    if user is None:
        return

    traffic_today = stats.get_gigabytes_today(user['_id'], db=db)
    traffic_this_month = stats.get_gigabytes_this_month(user['_id'], db=db)
    ips_today = stats.get_ips_today(user['_id'], db=db)

    users.update_one({"_id": user_id}, {"$set": {
        "__cache_traffic_today": traffic_today, 
        "__cache_traffic_this_month": traffic_this_month, 
        "__cache_ips_today": ips_today}}, 
    upsert=False)

def has_active_endpoints(db=None):
    if len(online_route_get_all()) > 0:
        return True

    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    all_domains = [{
        "id": domain["_id"],
        "status": check_domain_set_properly(domain["_id"]),
    } for domain in domains.find()]

    for domain in all_domains:
        if domain['status'] == 'active':
            return True

    return False

def top_level_domain_equivalent(domain1, domain2):
    domain1 = domain1.lower()
    domain2 = domain2.lower()

    domain1 = '.'.join(domain1.split('.')[-2:])
    domain2 = '.'.join(domain2.split('.')[-2:])
    return domain1 == domain2

    