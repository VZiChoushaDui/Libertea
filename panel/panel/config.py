import os
import re
import socket
import requests
from datetime import timedelta

print("Initializing...")

# Force ipv4 for requests
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

LIBERTEA_VERSION = 1020
VERSION_ENDPOINT = "https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/version.txt"

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


SERVER_MAIN_IP = requests.get('https://api.ipify.org', timeout=5).content.decode('utf8')

if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', SERVER_MAIN_IP):
    raise Exception("couldn't fetch SERVER_MAIN_IP")

# print("SERVER_MAIN_IP: " + SERVER_MAIN_IP)

def get_mongodb_password():
    return os.environ.get('PANEL_MONGODB_PASSWORD')

def get_panel_secret_key():
    return os.environ.get('PANEL_SECRET_KEY')

def get_admin_uuid():
    return os.environ.get('PANEL_ADMIN_UUID')

def get_proxy_connect_uuid():
    return os.environ.get('PANEL_PROXY_CONNECT_UUID')

def get_panel_domain():
    return os.environ.get('PANEL_DOMAIN')

def get_mongodb_connection_string():
    connstr = "mongodb://" + MONGODB_USER + ":" + get_mongodb_password() + "@" + MONGODB_HOST
    # print("connstr:", connstr)
    return connstr

def get_hostcontroller_api_key():
    return os.environ.get('HOSTCONTROLLER_API_KEY')

def get_bootstrap_script_url():
    return "https://raw.githubusercontent.com/VZiChoushaDui/Libertea/master/bootstrap.sh"
