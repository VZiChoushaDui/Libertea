import os
import re
import random
import socket
import requests
from pytz import timezone
from datetime import datetime, timedelta
from pymongo import MongoClient

print("Initializing...")

# Force ipv4 for requests
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

def get_libertea_branch():
    return os.environ.get('LIBERTEA_BRANCH_NAME')

LIBERTEA_VERSION = 1043
LIBERTEA_PROXY_VERSION = 1007
VERSION_ENDPOINT = "https://raw.githubusercontent.com/VZiChoushaDui/Libertea/" + get_libertea_branch() + "/version.txt"

HAPROXY_CONTAINER_NAME = 'libertea-haproxy'

# MONGODB_HOST = "libertea-mongodb:27017"
MONGODB_HOST = "localhost:27017"
MONGODB_USER = "root"
MONGODB_DB_NAME = "panel"

JWT_VALID_TIME = timedelta(hours=24)

ROUTE_IP_LISTS = [
    {
        "id": "cn",
        "name": "China",
    },
    {
        "id": "ru",
        "name": "Russia",
    },
    {
        "id": "cu",
        "name": "Cuba",
    },
    {
        "id": "th",
        "name": "Thailand",
    },
    {
        "id": "tm",
        "name": "Turkmenistan",
    },
    {
        "id": "ir",
        "name": "Iran",
    },
    {
        "id": "sy",
        "name": "Syria",
    },
    {
        "id": "sa",
        "name": "Saudi Arabia",
    },
    {
        "id": "tr",
        "name": "Turkey",
    }
]
ROUTE_IP_LISTS = sorted(ROUTE_IP_LISTS, key=lambda k: k['name'])

def get_ip_api_url():
    return random.choice([
        'https://api.ipify.org',
        'https://ifconfig.io/ip',
        'https://icanhazip.com',
        'https://ident.me',
        'https://ipecho.net/plain',
        'https://myexternalip.com/raw',
        'https://wtfismyip.com/text',
        'https://checkip.amazonaws.com',
    ])

SERVER_MAIN_IP = None
for i in range(5):
    try:
        ip = requests.get(get_ip_api_url(), timeout=3).content.decode('utf8').strip()
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            print("Failed to get server ip. Result was: " + str(ip))
            continue

        SERVER_MAIN_IP = ip
        break
    except Exception as e:
        print("Failed to get server ip: " + str(e))

if SERVER_MAIN_IP is None:
    raise Exception("couldn't fetch SERVER_MAIN_IP")

if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', SERVER_MAIN_IP):
    raise Exception("couldn't fetch SERVER_MAIN_IP. Result was: " + str(SERVER_MAIN_IP))

# print("SERVER_MAIN_IP: " + SERVER_MAIN_IP)

def get_mongodb_password():
    return os.environ.get('PANEL_MONGODB_PASSWORD')

def get_panel_secret_key():
    return os.environ.get('PANEL_SECRET_KEY')

def get_admin_uuid():
    return os.environ.get('PANEL_ADMIN_UUID')

def get_proxy_connect_uuid():
    return os.environ.get('PANEL_PROXY_CONNECT_UUID')

def get_proxy_configuration_uuid():
    return os.environ.get('PANEL_PROXY_CONFIGURATION_UUID')

def get_panel_domain():
    return os.environ.get('PANEL_DOMAIN')

def get_mongodb_connection_string():
    connstr = "mongodb://" + MONGODB_USER + ":" + get_mongodb_password() + "@" + MONGODB_HOST
    # print("connstr:", connstr)
    return connstr

___mongoClient = None
___mongoClientPid = None

def get_mongo_client():
    global ___mongoClient
    global ___mongoClientPid

    my_pid = os.getpid()
    if ___mongoClient is None or ___mongoClientPid != my_pid:
        print(f" -- creating mongo client on pid {my_pid}")
        ___mongoClient = MongoClient(get_mongodb_connection_string(), serverSelectionTimeoutMS=5000)
        ___mongoClientPid = my_pid

    try:
        ___mongoClient.server_info()
    except Exception as e:
        print(f" -- reconnecting mongo client on pid {my_pid}")
        ___mongoClient = MongoClient(get_mongodb_connection_string(), serverSelectionTimeoutMS=5000)
        ___mongoClientPid = my_pid

    return ___mongoClient

def get_hostcontroller_api_key():
    return os.environ.get('HOSTCONTROLLER_API_KEY')

def get_bootstrap_script_url():
    return "https://raw.githubusercontent.com/VZiChoushaDui/Libertea/" + get_libertea_branch() + "/bootstrap.sh"

def get_root_dir():
    env_root_dir = os.environ.get('LIBERTEA_ROOT_DIR')
    if env_root_dir is not None and env_root_dir != "":
        path = env_root_dir
        if path[-1] != '/':
            path += '/'
        return path
    return "/root/libertea/"


def get_regional_domain_suffixes(countries):
    suffixes = ['local', 'lan']
    if 'cn' in countries: # china
        suffixes.append('cn')
    elif 'cu' in countries: # cuba
        suffixes.append('cu')
    elif 'ir' in countries: # iran
        suffixes.append('ir')
    elif 'ru' in countries: # russia
        suffixes.append('ru')
    elif 'sa' in countries: # saudi arabia
        suffixes.append('sa')
    elif 'sy' in countries: # syria
        suffixes.append('sy')
    elif 'th' in countries: # thailand
        suffixes.append('th')
    elif 'tm' in countries: # turkmenistan
        suffixes.append('tm')
    elif 'tr' in countries:
        suffixes.append('tr')
    return suffixes

def get_timezone(country):
    if country == 'cn':
        return 'Asia/Shanghai'
    elif country == 'ru':
        return 'Europe/Moscow'
    elif country == 'cu':
        return 'America/Havana'
    elif country == 'th':
        return 'Asia/Bangkok'
    elif country == 'tm':
        return 'Asia/Ashgabat'
    elif country == 'ir':
        return 'Asia/Tehran'
    elif country == 'sy':
        return 'Asia/Damascus'
    elif country == 'sa':
        return 'Asia/Riyadh'
    elif country == 'tr':
        return 'Europe/Istanbul'
    return 'UTC'

def current_time_in_timezone(country):
    return datetime.now(timezone(get_timezone(country)))

SIGNAL_INVALIDATE_CACHE = 18