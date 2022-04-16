import os
import time
import socket
import requests
from datetime import datetime

# Force ipv4 for requests
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo


SERVER_MAIN_IP = requests.get('https://api.ipify.org').content.decode('utf8')

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
            data="ip=" + SERVER_MAIN_IP)
        # print status code and response text
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result.status_code, result.text)
    except Exception as e:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e)

    time.sleep(30)
