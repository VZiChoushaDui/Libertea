import json
from . import utils
from . import config
from datetime import datetime
from pymongo import MongoClient

def ___get_total_gigabytes(file_name, conn_url):
    try:
        with open(file_name, 'r') as f:
            data = json.load(f)

        for user in data['users']:
            entry_name = list(user.keys())[0]
            if entry_name == conn_url:
                gigabytes = user[entry_name]['megabytes'] / 1024
                gigabytes = round(gigabytes * 1000) / 1000
                gigabytes = str(gigabytes) + ' GB'
                return gigabytes

        return '0 GB'
    except:
        return '-'

def ___get_total_ips(file_name, conn_url):
    try:
        with open(file_name, 'r') as f:
            data = json.load(f)

        for user in data['users']:
            entry_name = list(user.keys())[0]
            if entry_name == conn_url:
                connections = user[entry_name]['ips']
                connections = str(connections)
                return connections

        return '0'
    except:
        return '-'

def get_gigabytes_today(user_id, db=None):
    if db is None:
        client = MongoClient(config.get_mongodb_connection_string())
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_gigabytes(file_name, conn_url)

def get_gigabytes_this_month(user_id, db=None):
    if db is None:
        client = MongoClient(config.get_mongodb_connection_string())
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_gigabytes(file_name, conn_url)

def get_ips_today(user_id, db=None):
    if db is None:
        client = MongoClient(config.get_mongodb_connection_string())
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_ips(file_name, conn_url)

def get_ips_this_month(user_id, db=None):
    if db is None:
        client = MongoClient(config.get_mongodb_connection_string())
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_ips(file_name, conn_url)

def get_gigabytes_today_all():
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_gigabytes(file_name, '[total]')

def get_gigabytes_this_month_all():
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_gigabytes(file_name, '[total]')

def get_ips_today_all():
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_ips(file_name, '[total]')

def get_ips_this_month_all():
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_ips(file_name, '[total]')
    