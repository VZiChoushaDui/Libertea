import json
import psutil
import requests
from . import utils
from . import config
from pymongo import MongoClient
from datetime import datetime, timedelta

def ___get_total_gigabytes(file_name, conn_url, return_as_string=True, domain=None):
    try:
        with open(file_name, 'r') as f:
            data = json.load(f)

        for user in data['users']:
            entry_name = list(user.keys())[0]
            if entry_name == conn_url:
                gigabytes = 0
                if domain is None:
                    gigabytes = user[entry_name]['megabytes'] / 1024
                else:
                    if domain in user[entry_name]['domains']:
                        gigabytes = user[entry_name]['domains'][domain]['megabytes'] / 1024
                    else:
                        gigabytes = 0

                if return_as_string:
                    gigabytes = round(gigabytes * 1000) / 1000
                    gigabytes = str(gigabytes) + ' GB'
                return gigabytes
                
        if return_as_string:
            return '0 GB'
        return 0
    except:
        if return_as_string:
            return '-'
        return None

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
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_gigabytes(file_name, conn_url)

def get_gigabytes_this_month(user_id, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_gigabytes(file_name, conn_url)

def get_ips_today(user_id, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_ips(file_name, conn_url)

def get_ips_this_month(user_id, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_ips(file_name, conn_url)

def get_gigabytes_today_all():
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_gigabytes(file_name, '[total]')

def get_traffic_per_day(user_id, days=7, domain=None, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']

    xs = []
    ys = []
    for i in range(days - 1, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        file_name = './data/usages/day/{}.json'.format(date)
        xs.append(date)
        try:
            traffic = ___get_total_gigabytes(file_name, conn_url, return_as_string=False, domain=domain)
            if traffic is None:
                traffic = 0
            ys.append(traffic)
        except:
            ys.append(None)

    return xs, ys

def get_traffic_per_day_all(days=7, domain=None, include_extra_data_for_online_route=False):
    xs = []
    ys = []

    client = config.get_mongo_client()
    db = client[config.MONGODB_DB_NAME]

    for i in range(days - 1, -1, -1):
        date_obj = datetime.now() - timedelta(days=i)
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        file_name = './data/usages/day/{}.json'.format(date)
        xs.append(date)
        try:
            traffic = ___get_total_gigabytes(file_name, '[total]', return_as_string=False, domain=domain)
            if traffic is None:
                traffic = 0

            if include_extra_data_for_online_route:
                extra_traffic = utils.online_route_get_traffic(domain, date_obj.year, date_obj.month, date_obj.day)
                print("extra_traffic @", date, ":", extra_traffic)
                if extra_traffic is not None:
                    if '443' in extra_traffic:
                        print(extra_traffic['443'])
                        traffic += extra_traffic['443']['received_bytes'] + extra_traffic['443']['sent_bytes']
            ys.append(traffic)
        except:
            ys.append(None)

    return xs, ys

def get_gigabytes_this_month_all():
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_gigabytes(file_name, '[total]')

def get_ips_today_all():
    file_name = './data/usages/day/{}.json'.format(datetime.now().strftime('%Y-%m-%d'))
    return ___get_total_ips(file_name, '[total]')

def get_ips_this_month_all():
    file_name = './data/usages/month/{}.json'.format(datetime.now().strftime('%Y-%m'))
    return ___get_total_ips(file_name, '[total]')
    
def get_connected_ips_right_now(user_id, long=False, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    user = users.find_one({"_id": user_id})
    conn_url = user['connect_url']
    
    try:
        req = requests.get(f'https://localhost/{ conn_url }/connected-ips-count' + ('-long' if long else ''), verify=False, timeout=0.1)
        if req.status_code == 200:
            return req.text
    except:
        pass

    return None

def get_total_connected_ips_right_now(long=False):
    try:
        req = requests.get(f'https://localhost/{ config.get_admin_uuid() }/total-connected-ips-count' + ('-long' if long else ''), verify=False, timeout=0.1)
        if req.status_code == 200:
            return int(req.text)
    except:
        pass

    return None

def save_connected_ips_count(db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
    users = db.users
    connected_ips_log = db.connected_ips_log

    cur_hour_min = datetime.now().strftime('%H:%M')
    total_connected_ips = 0
    total_connected_users = 0
    user_ids = list(users.find({}, {'_id': 1}))
    connected_user_ids = []
    for user_id in user_ids:
        user_id = user_id['_id']
        connected_ips = get_connected_ips_right_now(user_id, long=True, db=db)
        if connected_ips is not None:
            if connected_ips.isdigit():
                connected_ips = int(connected_ips)
                if connected_ips > 0:
                    total_connected_users += 1
                    connected_user_ids.append(user_id)
                entry_key = str(user_id) + '--' + str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day)
                connected_ips_log.update_one(
                    {'_id': entry_key},
                    {'$set': {
                        cur_hour_min: connected_ips,
                    }},
                    upsert=True
                )
                total_connected_ips += connected_ips
    entry_key = 'ALL--' + str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day)
    connected_ips_log.update_one(
        {'_id': entry_key},
        {
            '$setOnInsert': {
                'connected_users': [],
            }
        },
        upsert=True
    )

    connected_ips_log.update_one(
        {'_id': entry_key},
        {
            '$set': {
                cur_hour_min: total_connected_ips,
            },
            '$addToSet': {
                'connected_users': {
                    '$each': connected_user_ids
                }
            }
        },
        upsert=True
    )

    connected_ips_log.update_one(
        {'_id': "ALL--Recent"},
        {
            '$set': {
                "total_connected_ips": total_connected_ips,
                "total_connected_users": total_connected_users,
            }
        },
        upsert=True
    )
    

def get_connected_ips_over_time(user_id, year, month, day, db=None):
    if db is None:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]

    connected_ips_log = db.connected_ips_log
    entry_key = str(user_id) + '--' + str(year) + '-' + str(month) + '-' + str(day)

    try:
        return dict(connected_ips_log.find_one({'_id': entry_key}))
    except Exception as e:
        return {}

def get_all_connected_ips_over_time(year, month, day, db=None):
    return get_connected_ips_over_time('ALL', year, month, day, db)

def get_connected_users_now(long=False):
    try:
        req = requests.get(f'https://localhost/{ config.get_admin_uuid() }/total-connected-users-count' + ('-long' if long else ''), verify=False, timeout=0.1)
        if req.status_code == 200:
            return int(req.text)
    except:
        pass

    return None

def get_connected_users_today(db=None):
    try:
        if db is None:
            client = config.get_mongo_client()
            db = client[config.MONGODB_DB_NAME]

        connected_ips_log = db.connected_ips_log
        entry_key = 'ALL--' + str(datetime.now().year) + '-' + str(datetime.now().month) + '-' + str(datetime.now().day)
        res = connected_ips_log.find_one({'_id': entry_key})
        return len(list(res['connected_users']))
    except Exception as e:
        return '-'


def get_system_stats_cpu():
    try:
        return str(int(psutil.cpu_percent())) + '%'
    except:
        pass
    return '-'

def get_system_stats_ram():
    try:
        return str(int(psutil.virtual_memory()[2])) + '%'
    except:
        pass
    
    return '-'
