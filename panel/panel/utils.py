import uuid
import socket
import pymongo
import requests
from . import config
from . import sysops
from . import settings
from datetime import datetime
from pymongo import MongoClient

online_routes = {}

def create_user(note, referrer=None, max_ips=None):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
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

    if sysops.haproxy_update_users_list():
        return panel_id, connect_url

    raise Exception("Failed to update HAProxy users list")

def update_user(panel_id, note=None, max_ips=None, referrer=None):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
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
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    user = users.find_one({"note": note})
    if user is None:
        return None
    return user["_id"]

def delete_user(panel_id):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    if users.find_one({"_id": panel_id}) is None:
        return False

    users.delete_one({"_id": panel_id})

    return sysops.haproxy_update_users_list()

def get_users():
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    all_users = [{
        "panel_id": user["_id"],
        "connect_url": user["connect_url"],
        "note": user["note"],
    } for user in users.find()]
    return all_users

def remove_domain(domain):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    if domains.find_one({"_id": domain}) is None:
        return False

    domains.delete_one({"_id": domain})
    sysops.haproxy_update_domains_list()
    return True

def add_domain(domain, dns_domain=None, sni=None):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
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

def get_domains():
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains

    all_domains = [domain["_id"] for domain in domains.find()]
    return all_domains

def get_domain_dns_domain(domain):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is None:
        return None
    if not "dns_domain" in domain_entry:
        return None
    return domain_entry["dns_domain"]

def get_domain_sni(domain):
    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    domains = db.domains
    domain_entry = domains.find_one({"_id": domain})
    if domain_entry is None:
        return None
    if not "sni" in domain_entry:
        return None
    return domain_entry["sni"]

def get_active_domains():
    return [x for x in get_domains() if check_domain_set_properly(x) == 'active']

def get_user_max_ips(panel_id=None, conn_url=None):
    if panel_id is None and conn_url is None:
        return 0

    if panel_id is not None and conn_url is not None:
        raise Exception("Both panel_id and conn_url are not None")

    client = pymongo.MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    if panel_id is not None:
        user = users.find_one({"_id": panel_id})
    else:
        user = users.find_one({"connect_url": conn_url})

    if user is None:
        return 0

    default_max_ips = settings.get_default_max_ips()
    max_ips = user.get("max_ips", default_max_ips)

    if max_ips is None or max_ips <= 0:
        return default_max_ips

    return max_ips


def online_route_ping(ip):
    online_routes[ip] = datetime.now()

def online_route_get_last_seen(ip):
    return online_routes.get(ip, None)

def online_route_get_all(max_age_secs=300):
    # get all online routes (max last seen 5 minutes ago)
    now = datetime.now()
    # return [ip for ip, last_seen in online_routes.items() if (now - last_seen).total_seconds() < max_age_secs]
    ips = []
    for ip, last_seen in online_routes.items():
        if (now - last_seen).total_seconds() < max_age_secs:
            ips.append(ip)
            print("online_route_get_all: ip", ip, "last seen", last_seen, "now", now, "diff", (now - last_seen).total_seconds())
    return ips

check_domain_set_properly_cache = {}
check_domain_set_properly_cache_max_time = 60
def check_domain_set_properly(domain, force_check=False):
    if not force_check:
        if domain in check_domain_set_properly_cache:
            timestamp = check_domain_set_properly_cache[domain][0]
            if (datetime.utcnow() - timestamp).total_seconds() < check_domain_set_properly_cache_max_time:
                return check_domain_set_properly_cache[domain][1]

    # send a request to https://[domain]/[get_admin_uuid]/. It should return 401 unauthorized
    try:
        r = requests.get("https://{}/{}/".format(domain, config.get_admin_uuid()), verify=False, timeout=1)
        if r.status_code == 401:

            # make sure domain does not resolve to config.SERVER_MAIN_IP
            try:
                ip = socket.gethostbyname(domain)
                if ip == config.SERVER_MAIN_IP:
                    check_domain_set_properly_cache[domain] = (datetime.utcnow(), 'cdn-disabled')
                    return 'cdn-disabled'
            except:
                check_domain_set_properly_cache[domain] = (datetime.utcnow(), 'unknown')
                return 'unknown'

            check_domain_set_properly_cache[domain] = (datetime.utcnow(), 'active')
            return 'active'
    except Exception as e:
        print(e)
        check_domain_set_properly_cache[domain] = (datetime.utcnow(), 'inactive')
        return 'inactive'

    check_domain_set_properly_cache[domain] = (datetime.utcnow(), 'inactive')
    return 'inactive'

def check_domain_cdn_provider(domain):
    # send a request to https://[domain]/[get_admin_uuid]/ and check headers
    try:
        r = requests.get("https://{}/{}/".format(domain, config.get_admin_uuid()), verify=False, timeout=1)
        if r.status_code == 401:
            header_server = r.headers.get('server', '').lower()
            if header_server == 'cloudflare':
                return 'Cloudflare'
    except Exception as e:
        print(e)
    return 'Unknown'


def has_active_endpoints():
    if len(online_route_get_all()) > 0:
        return True

    client = MongoClient(config.get_mongodb_connection_string())
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

    