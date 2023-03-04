import os
import time
import random
import socket
import requests
from datetime import datetime

LIBERTEA_PROXY_VERSION = 1001

# Force ipv4 for requests
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

def get_ip_api_url():
    return random.choice([
        'https://api.ipify.org',
        'https://ifconfig.io/ip',
        'http://ifconfig.io/ip',
        'https://ipecho.net/plain',
        'http://ipecho.net/plain'
    ])
SERVER_MAIN_IP = requests.get(get_ip_api_url(), timeout=3).content.decode('utf8').strip()

REGISTER_ENDPOINT = os.environ.get('PROXY_REGISTER_ENDPOINT')
API_KEY = os.environ.get('PANEL_SECRET_KEY')

while True:
    try:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Sending request to register proxy at", REGISTER_ENDPOINT)
        result = requests.post(REGISTER_ENDPOINT,
            verify=False, timeout=5,
            headers={
                "X-API-KEY": API_KEY,
                "Content-Type": "application/x-www-form-urlencoded"
            }, 
            data="ip=" + SERVER_MAIN_IP + "&version=" + str(LIBERTEA_PROXY_VERSION))
        # print status code and response text
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result.status_code, result.text)
    except Exception as e:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e)

    time.sleep(30)
