import time
import uuid
import socket
import pymongo
import requests
import threading
from . import config
from . import sysops
from datetime import datetime

def get_default_max_ips(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "default_max_ips"})
    if setting is None:
        return 5
    return setting["value"]

def set_default_max_ips(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "default_max_ips"}, {"$set": {"value": val}}, upsert=True)

def get_secondary_proxy_use_80_instead_of_443(db=None):
    ### DEPRECATED ###
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "secondary_proxy_use_80_instead_of_443"})
    if setting is None:
        return True
    return setting["value"]

def set_secondary_proxy_use_80_instead_of_443(val, db=None):
    ### DEPRECATED ###
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "secondary_proxy_use_80_instead_of_443"}, {"$set": {"value": val}}, upsert=True)

def get_secondary_proxy_ports(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "secondary_proxy_ports"})
    if setting is None:
        return "80,443"
    return setting["value"]

def set_secondary_proxy_ports(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "secondary_proxy_ports"}, {"$set": {"value": val}}, upsert=True)

def get_route_direct_country_enabled(country, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "route_direct_country_enabled_" + country})
    if setting is None:
        return False
    return setting["value"]

def set_route_direct_country_enabled(country, val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "route_direct_country_enabled_" + country}, {"$set": {"value": val}}, upsert=True)

def get_provider_enabled(provider_name, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "provider_enabled_" + provider_name})
    if setting is None:
        return True
    return setting["value"]

def set_provider_enabled(provider_name, val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "provider_enabled_" + provider_name}, {"$set": {"value": val}}, upsert=True)

def get_single_clash_file_configuration(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "single_clash_file_configuration"})
    if setting is None:
        return True
    return setting["value"]

def set_single_clash_file_configuration(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "single_clash_file_configuration"}, {"$set": {"value": val}}, upsert=True)

def get_providers_from_all_endpoints(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "providers_from_all_endpoints"})
    if setting is None:
        return False
    return setting["value"]

def set_providers_from_all_endpoints(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "providers_from_all_endpoints"}, {"$set": {"value": val}}, upsert=True)

def get_add_domains_even_if_inactive(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "add_domains_even_if_inactive"})
    if setting is None:
        return False
    return setting["value"]

def set_add_domains_even_if_inactive(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "add_domains_even_if_inactive"}, {"$set": {"value": val}}, upsert=True)

def get_camouflage_domain(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "camouflage_domain"})
    if setting is None:
        return ""
    return setting["value"]

def set_camouflage_domain(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]

    if get_camouflage_domain(db=db) == val:
        print("camouflage domain is already set to " + val)
        return

    db.settings.update_one({"_id": "camouflage_domain"}, {"$set": {"value": val}}, upsert=True)
    sysops.haproxy_update_camouflage_list() 

def get_periodic_health_check(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "periodic_health_check"})
    if setting is None:
        return False
    return setting["value"]

def set_periodic_health_check(val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    db.settings.update_one({"_id": "periodic_health_check"}, {"$set": {"value": val}}, upsert=True)
    
def get_tier_proxygroup_type(tier_index, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    setting = db.settings.find_one({"_id": "tier_proxygroup_type_" + str(tier_index)})
    if setting is None:
        return "urltest"
    return setting["value"]

def set_tier_proxygroup_type(tier_index, val, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]

    if val not in ['urltest', 'loadbalance', 'fallback']:
        return False
    
    db.settings.update_one({"_id": "tier_proxygroup_type_" + str(tier_index)}, {"$set": {"value": val}}, upsert=True)
    return True
