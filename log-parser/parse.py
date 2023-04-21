import os
import re
import sys
import json

logs_path = '/data/logs/'
output_path = '/data/parsed-logs/'

pattern = re.compile(r"(?P<log_date>[0-9\-T\:\+]+) (?P<server_addr>[a-zA-Z0-9\.\-]*) haproxy\[[0-9\-]+\]\: (?P<remote_conn_addr>[0-9\.\:]+) \[(?P<request_date>[^\]]*)\] (?P<frontend_name>[^\s]*) (?P<backend_name>[^\s\/]*)\/(?P<server_name>[^\s\/]*) (?P<ms_wait>[0-9\-]+)\/(?P<ms_queue>[0-9\-]+)\/(?P<ms_backend_connect_wait>[0-9\-]+)\/(?P<ms_backend_wait>[0-9\-]+)\/(?P<ms_active>[0-9\-]+) (?P<http_status_code>[0-9\-]+) (?P<bytes_server_to_client>[0-9\-]+) [^\s]* [^\s]* [^\s]* [^\s]*\/[^\s]*\/[^\s]*\/[^\s]*\/[^\s]* [^\s]*\/[^\s]* \{((?P<cdn_server_type>[0-9a-zA-Z\.\-]+)\|)?(?P<remote_fwd_ip>[0-9.]*)(\|(?P<domain_name>[0-9a-zA-Z\.\-]+))?(\:)?\} \"(?P<http_req_type>[A-Z]*) (?P<endpoint>[a-zA-Z0-9\-\.\/\:]*) [a-zA-Z0-9\.\/]*\" (?P<bytes_client_to_server>[0-9\-]+)")

#### EXAMPLE:
#### log_date : 2022-10-19T16:17:22+00:00
#### server_addr : static.141.61.21.65.clients.your-server.de
#### remote_conn_addr : 89.45.48.75:54656
#### request_date : 19/Oct/2022:16:17:01.523
#### frontend_name : main~
#### backend_name : snapp
#### server_name : sp
#### ms_wait : 0
#### ms_queue : 0
#### ms_backend_connect_wait : 1
#### ms_backend_wait : 1
#### ms_active : 21211
#### http_status_code : 101
#### bytes_server_to_client : 9989
#### remote_fwd_ip : 5.210.196.222
#### domain_name (optional): mydomain.com
#### http_req_type : GET
#### endpoint : /llama
#### bytes_client_to_server : 3310

# find files that end with '.log' in logs_path
for file in os.listdir(logs_path):
    if file.endswith('.log'):
        print('Parsing file: ' + file)

        endpoints = {}

        with open(logs_path + '/' + file, 'r', encoding='utf-8', errors='ignore') as f:
            counter = 0
            for line in f:
                counter += 1
                if counter % 10_000 == 0:
                    print(counter, "lines parsed", end='\r')
                
                if 'NOSRV' in line:
                    continue

                # match line with regex
                match = re.search(pattern, line)
                if match:
                    items = dict(match.groupdict())

                    item_key = items['endpoint']
                    if items['domain_name'] is not None:
                        if items['domain_name'] == 'google.com':
                            # this is a Libertea secondary proxy, will use remote_conn_addr (without port) instead of google.com
                            item_key = items['remote_conn_addr'].split(':')[0] + item_key
                        else:
                            item_key = items['domain_name'] + item_key

                    if not item_key in endpoints:
                        endpoints[item_key] = {}

                    ip = items['remote_fwd_ip']
                    if not ip in endpoints[item_key]:
                        endpoints[item_key][ip] = {
                            'megabytes': 0,
                            'time': 0,
                            'connections': 0,
                        }

                    endpoints[item_key][ip]['megabytes'] += (int(items['bytes_server_to_client']) + int(items['bytes_client_to_server'])) / 1000000
                    endpoints[item_key][ip]['time'] += (int(items['ms_active'])) / 1000
                    endpoints[item_key][ip]['connections'] += 1


                # else:
                #     print("no match for", line)

        # save endpoints and summary to file
        with open(output_path + 'endpoints-' + file.replace('.log', '.json'), 'w') as f:
            json.dump(endpoints, f, indent=4)
