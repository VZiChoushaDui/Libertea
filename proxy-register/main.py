import os
import re
import json
import time
import random
import psutil
import socket
import requests
import threading
import socketserver
import urllib.parse
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

LIBERTEA_PROXY_VERSION = 1004

FAKE_TRAFFIC_AVERAGE_GIGABYTES_PER_DAY = 10
FAKE_TRAFFIC_AVERAGE_DELAY_BETWEEN_REQUESTS = 0.25
FAKE_TRAFFIC_MIN_DELAY_BETWEEN_REQUESTS = 0.01
LOG_LEVEL = 0

FAKE_TRAFFIC_ENDPOINT = os.environ.get('PROXY_REGISTER_ENDPOINT') + '/fake-traffic'
FAKE_TRAFFIC_ENDPOINT = FAKE_TRAFFIC_ENDPOINT.replace(os.environ.get('CONN_PROXY_IP'), '127.0.0.1')

FAKE_TRAFFIC_COUNTRIES_LIST = ["CN", "CU", "TH", "TM", "IR", "SY", "SA", "TR"]

# Force ipv4 for requests
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [response
            for response in responses
            if response[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

def get_fake_traffic_average_bytes_per_second():
    return FAKE_TRAFFIC_AVERAGE_GIGABYTES_PER_DAY * 1024 * 1024 * 1024 / (24 * 60 * 60)

def get_fake_traffic_average_bytes_per_request():
    return get_fake_traffic_average_bytes_per_second() * FAKE_TRAFFIC_AVERAGE_DELAY_BETWEEN_REQUESTS

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


def get_ip_api_url():
    return random.choice([
        'https://api.ipify.org',
        'http://api.ipify.org',
        'https://ifconfig.io/ip',
        'http://ifconfig.io/ip',
        'https://icanhazip.com',
        'http://icanhazip.com',
        'https://ident.me',
        'http://ident.me',
        'https://ipecho.net/plain',
        'http://ipecho.net/plain',
        'https://myexternalip.com/raw',
        'http://myexternalip.com/raw',
        'https://wtfismyip.com/text',
        'http://wtfismyip.com/text',
        'https://checkip.amazonaws.com',
        'http://checkip.amazonaws.com',
    ])
SERVER_MAIN_IP = requests.get(get_ip_api_url(), timeout=3).content.decode('utf8').strip()

if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', SERVER_MAIN_IP):
    raise Exception("couldn't fetch SERVER_MAIN_IP. Result was: " + str(SERVER_MAIN_IP))

REGISTER_ENDPOINT = os.environ.get('PROXY_REGISTER_ENDPOINT')
API_KEY = os.environ.get('PANEL_SECRET_KEY')
PROXY_TYPE = os.environ.get('PROXY_TYPE')

SSH_PUBLIC_KEY_PATH = '/root/.ssh/id_rsa.pub'
with open(SSH_PUBLIC_KEY_PATH, 'r') as f:
    SSH_PUBLIC_KEY = f.read().strip()

last_bytes_received = {}
last_bytes_sent = {}

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

def register_periodically():
    global last_bytes_received
    global last_bytes_sent

    while True:
        try:
            
            bytes_data = {}
            for listenport in last_bytes_received:
                if not listenport in bytes_data:
                    bytes_data[listenport] = {}
                bytes_data[listenport]['received'] = last_bytes_received[listenport]
            last_bytes_received.clear()
            for listenport in last_bytes_sent:
                if not listenport in bytes_data:
                    bytes_data[listenport] = {}
                bytes_data[listenport]['sent'] = last_bytes_sent[listenport]
            last_bytes_sent.clear()

            bytes_data = json.dumps(bytes_data)

            data = "ip=" + SERVER_MAIN_IP + "&version=" + str(LIBERTEA_PROXY_VERSION) + \
                "&proxyType=" + urllib.parse.quote(PROXY_TYPE) + \
                "&cpuUsage=" + urllib.parse.quote(get_system_stats_cpu()) + \
                "&ramUsage=" + urllib.parse.quote(get_system_stats_ram()) + \
                "&sshKey=" + urllib.parse.quote(SSH_PUBLIC_KEY) + \
                "&trafficData=" + urllib.parse.quote(bytes_data)
            
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Sending request to register proxy at", REGISTER_ENDPOINT, "with data ", data)

            result = requests.post(REGISTER_ENDPOINT,
                verify=False, timeout=5,
                headers={
                    "X-API-KEY": API_KEY,
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data=data
            )
            # print status code and response text
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), result.status_code, result.text)
            time.sleep(random.randint(15, 45))
        except Exception as e:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e)
            time.sleep(30)


def fake_traffic():
    global last_bytes_received
    global last_bytes_sent

    start_time = datetime.now()
    total_len = 0
    while True:
        req_time_start = datetime.now()

        try:
            # generate random data 
            data = get_fake_traffic_random_data()

            if 'FAKE' not in last_bytes_sent:
                last_bytes_sent['FAKE'] = 0
            last_bytes_sent['FAKE'] += len(data)

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




class SyslogUDPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        global last_bytes_received
        global last_bytes_sent

        try:
            data = bytes.decode(self.request[0].strip())
            data = str(data)

            # format: LIBERTEA_PROXY:%listenport %ci:%cp [%t] recv=%B sent=%U %Tw/%Tc/%Tt
            if 'LIBERTEA_PROXY:' not in data:
                return

            # remove syslog header
            data = data[data.index('LIBERTEA_PROXY:'):]

            # parse data with regex
            match = re.match(r'LIBERTEA_PROXY:(\d+) (\d+\.\d+\.\d+\.\d+):(\d+) \[(.*)\] recv=(\d+) sent=(\d+) (\d+)/(\d+)/(\d+)', data)
            if not match:
                print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Invalid data format received from haproxy: " + data)
                return

            listenport = match.group(1)

            # client_ip = match.group(2)
            # client_port = match.group(3)

            # timestamp = match.group(4)

            bytes_received = match.group(5)
            bytes_sent = match.group(6)

            # session_duration = match.group(7)
            # connect_duration = match.group(8)
            # total_duration = match.group(9)

            if listenport not in last_bytes_received:
                last_bytes_received[listenport] = 0
            if listenport not in last_bytes_sent:
                last_bytes_sent[listenport] = 0

            last_bytes_received[listenport] += int(bytes_received)
            last_bytes_sent[listenport] += int(bytes_sent)

        except Exception as e:
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Error while parsing data:", e)
           


if __name__ == "__main__":
    # create a new thread for periodic proxy registration
    threading.Thread(target=register_periodically).start()

    # create a new thread for fake traffic
    threading.Thread(target=fake_traffic).start()

    try:
        server = socketserver.UDPServer(("127.0.0.1", 10514), SyslogUDPHandler)
        server.serve_forever(poll_interval=0.5)
    except (IOError, SystemExit):
        raise
    except KeyboardInterrupt:
        print("Server Terminated")
        exit(0)
