import os
import re
import json
import time
import random
import socket
import requests
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

FAKE_TRAFFIC_AVERAGE_GIGABYTES_PER_DAY = 10
FAKE_TRAFFIC_AVERAGE_DELAY_BETWEEN_REQUESTS = 0.25
FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS = 0.01
LOG_LEVEL = 3

FAKE_TRAFFIC_COUNTRIES_LIST = ["CN", "CU", "TH", "TM", "IR", "SY", "SA", "TR"]

def get_fake_traffic_average_bytes_per_second():
    return FAKE_TRAFFIC_AVERAGE_GIGABYTES_PER_DAY * 1024 * 1024 * 1024 / (24 * 60 * 60)

def get_fake_traffic_average_bytes_per_request():
    return get_fake_traffic_average_bytes_per_second() * FAKE_TRAFFIC_AVERAGE_DELAY_BETWEEN_REQUESTS


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
        'https://ifconfig.io/country_code',
        'https://ipinfo.io/country',
        'https://ipapi.co/country_code',
        'https://ifconfig.co/country-iso',
        'https://api.myip.com',
        'https://api.ipregistry.co/?key=tryout'
    ])

def get_country_code():
    try:
        url = get_ip_api_url()
        result = requests.get(url, timeout=20).content.decode('utf8').strip()
        if url == 'https://api.myip.com':
            result = json.loads(result)['cc']
        elif url == 'https://api.ipregistry.co/?key=tryout':
            result = json.loads(result)['location']['country']['code']
        return result
    except Exception as e:
        print(e)
        return ''

while True:
    SERVER_COUNTRY = get_country_code()
    if not len(SERVER_COUNTRY) == 2:
        raise Exception("couldn't fetch SERVER_MAIN_COUNTRY. Result was: " + str(SERVER_COUNTRY))
    if not SERVER_COUNTRY in FAKE_TRAFFIC_COUNTRIES_LIST:
        print("SERVER_COUNTRY", SERVER_COUNTRY, "not in countries list. Will not send fake traffic.")
        time.sleep(3 * 3600)
    else:
        break

FAKE_TRAFFIC_ENDPOINT = os.environ.get('PROXY_REGISTER_ENDPOINT') + '/fake-traffic'
FAKE_TRAFFIC_ENDPOINT = FAKE_TRAFFIC_ENDPOINT.replace(os.environ.get('CONN_PROXY_IP'), '127.0.0.1')

def get_fake_traffic_random_data_size_bytes():
    # generate expovariate random data size, with a bias towards smaller sizes, with min size of 1 byte and average size of get_average_bytes_per_request()
    return max(1, int(random.expovariate(1 / get_fake_traffic_average_bytes_per_request()))) 

def get_fake_traffic_sleep_time_secs():
    return FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS + random.random() * (FAKE_TRAFFIC_AVERAGE_DELAY_BETWEEN_REQUESTS * 2 - FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS)

def get_fake_traffic_random_data():
    return os.urandom(get_fake_traffic_random_data_size_bytes())

def fake_traffic_random_sleep(request_time_elapsed_secs):
    sleep_time_secs = get_fake_traffic_sleep_time_secs() - request_time_elapsed_secs
    if sleep_time_secs < FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS:
        sleep_time_secs = FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS

    if LOG_LEVEL >= 3:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Sleeping for", sleep_time_secs, "seconds")
    time.sleep(sleep_time_secs)

start_time = datetime.now()
total_len = 0
while True:
    req_time_start = datetime.now()

    try:
        # generate random data 
        data = get_fake_traffic_random_data()

        if LOG_LEVEL >= 2:
            total_len += len(data)

        if LOG_LEVEL >= 3:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Sending", len(data), "bytes to", FAKE_TRAFFIC_ENDPOINT)
        result = requests.post(FAKE_TRAFFIC_ENDPOINT,
            verify=False, timeout=5,
            data=data,
            headers={
                'Content-Type': 'application/octet-stream',
            },
        )

    except Exception as e:
        if LOG_LEVEL >= 1:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e)

    req_time_end = datetime.now()

    fake_traffic_random_sleep((req_time_end - req_time_start).total_seconds())

    if LOG_LEVEL >= 2:
        avg_per_second = total_len / (datetime.now() - start_time).total_seconds()
        avg_gb_per_day = avg_per_second * 60 * 60 * 24 / (1024 * 1024 * 1024)
        avg_per_second = int(avg_per_second)
        avg_gb_per_day = round(avg_gb_per_day, 2)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Total sent:", total_len, "bytes in ", (datetime.now() - start_time).total_seconds(), "seconds")
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Average:", avg_per_second, "bytes per second, or", avg_gb_per_day, "GB per day")

