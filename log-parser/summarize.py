import os
import re
import sys
import json
from datetime import datetime, timedelta


# read days length from arguments
window_days = 1
if len(sys.argv) > 1:
    window_days = int(sys.argv[1])
    
parsed_path = '/data/parsed-logs/'
output_root_path = '/data/usages/'

users = {}
try:
    users_path = '/root/vless/clash-conf/users.csv'
    with open(users_path, 'r') as f:
        for line in f:
            parts = line.split(',')
            users[parts[1]] = parts[2].strip()
            if len(parts) > 3 and parts[3].strip() != '':
                users[parts[1]] += ' (' + parts[3].strip() + ')'
except:
    pass

def get_user(url):
    if not url in users:
        return url
    return users[url]

def generate_summary(start_date, end_date, output_folder, file_name):
    print('Generating summary for ' + output_folder + '/' + file_name)

    output_path = output_root_path + output_folder + '/'

    # make sure output path exists
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    files = os.listdir(parsed_path)
    files_to_parse = []
    for file in files:
        # we need to parse all files that are within the window
        # file name format is one of these two:
        #   endpoints-event.json-yyyymmdd.json 
        #   endpoints-event.json-yyyymmdd-hh.json
        # we need to support both formats
        
        if not file.startswith('endpoints-event.json-'):
            continue
        
        file_parts = file.split('-')
        if len(file_parts) == 3:
            file_date = datetime.strptime(file_parts[2].split('.')[0], '%Y%m%d')
        elif len(file_parts) == 4:
            file_date = datetime.strptime(file_parts[2] + file_parts[3].split('.')[0], '%Y%m%d%H')
        else:
            continue
            
        if file_date >= start_date and file_date < end_date:
            files_to_parse.append(file)

    endpoints = {}
    for file in files_to_parse:
        # print('   Loading file: ' + file)
        
        with open(parsed_path + '/' + file, 'r', encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            for endpoint in data:
                for ip in data[endpoint]:
                    if not endpoint in endpoints:
                        endpoints[endpoint] = {}
                        
                    if not ip in endpoints[endpoint]:
                        endpoints[endpoint][ip] = {
                            'megabytes': 0,
                            'time': 0,
                            'connections': 0,
                        }
                        
                    endpoints[endpoint][ip]['megabytes'] += data[endpoint][ip]['megabytes']
                    endpoints[endpoint][ip]['time'] += data[endpoint][ip]['time']
                    endpoints[endpoint][ip]['connections'] += data[endpoint][ip]['connections']


    # print("   Generating summary")
    summary = {}
    summary['[total]'] = {
        'ips': set(),
        'megabytes': 0,
        'time': 0,
        'connections': 0,
    }
    for endpoint in endpoints:
        summary[endpoint] = {
            'ips': set(),
            'megabytes': 0,
            'time': 0,
            'connections': 0,
        }

        for ip in endpoints[endpoint]:
            summary[endpoint]['ips'].add(ip)
            summary[endpoint]['megabytes'] += endpoints[endpoint][ip]['megabytes']
            summary[endpoint]['time'] += endpoints[endpoint][ip]['time']
            summary[endpoint]['connections'] += endpoints[endpoint][ip]['connections']

            summary['[total]']['ips'].add(ip)
            summary['[total]']['megabytes'] += endpoints[endpoint][ip]['megabytes']
            summary['[total]']['time'] += endpoints[endpoint][ip]['time']
            summary['[total]']['connections'] += endpoints[endpoint][ip]['connections']

    for ep in summary:
        summary[ep]['ips'] = len(summary[ep]['ips'])

    summary_endpoints_list = [{key: value} for key, value in summary.items()]
    summary_endpoints_list.sort(key=lambda x: list(x.values())[0]['megabytes'], reverse=True)



    summary_users = {}
    summary_users['[total]'] = {
        'ips': set(),
        'megabytes': 0,
        # 'time': 0,
        # 'connections': 0,
        'domains': {},
    }
    for endpoint in endpoints:
        endpoint_parts = endpoint.split('/')
        domain = '',
        user = ''

        if len(endpoint_parts) < 2:
            continue

        domain = endpoint_parts[0]
        user = endpoint_parts[1]
        
        user = get_user(user)

        if not user in summary_users:
            summary_users[user] = {
                'ips': set(),
                'megabytes': 0,
                # 'time': 0,
                # 'connections': 0,
                'domains': {},
            }
            
        if not domain in summary_users[user]['domains']:
            summary_users[user]['domains'][domain] = {
                'ips': set(),
                'megabytes': 0,
                # 'time': 0,
                # 'connections': 0,
            }
        if not domain in summary_users['[total]']['domains']:
            summary_users['[total]']['domains'][domain] = {
                'ips': set(),
                'megabytes': 0,
                # 'time': 0,
                # 'connections': 0,
            }

        for ip in endpoints[endpoint]:
            summary_users[user]['ips'].add(ip)
            summary_users[user]['megabytes'] += endpoints[endpoint][ip]['megabytes']
            # summary_users[user]['time'] += endpoints[endpoint][ip]['time']
            # summary_users[user]['connections'] += endpoints[endpoint][ip]['connections']
            
            summary_users[user]['domains'][domain]['ips'].add(ip)
            summary_users[user]['domains'][domain]['megabytes'] += endpoints[endpoint][ip]['megabytes']
            # summary_users[user]['domains'][domain]['time'] += endpoints[endpoint][ip]['time']
            # summary_users[user]['domains'][domain]['connections'] += endpoints[endpoint][ip]['connections']

            summary_users['[total]']['ips'].add(ip)
            summary_users['[total]']['megabytes'] += endpoints[endpoint][ip]['megabytes']
            # summary_users['[total]']['time'] += endpoints[endpoint][ip]['time']
            # summary_users['[total]']['connections'] += endpoints[endpoint][ip]['connections']
            
            summary_users['[total]']['domains'][domain]['ips'].add(ip)
            summary_users['[total]']['domains'][domain]['megabytes'] += endpoints[endpoint][ip]['megabytes']
            # summary_users['[total]']['domains'][domain]['time'] += endpoints[endpoint][ip]['time']
            # summary_users['[total]']['domains'][domain]['connections'] += endpoints[endpoint][ip]['connections']

    for ep in summary_users:
        summary_users[ep]['ips'] = len(summary_users[ep]['ips'])
        if 'domains' in summary_users[ep]:
            for domain in summary_users[ep]['domains']:
                summary_users[ep]['domains'][domain]['ips'] = len(summary_users[ep]['domains'][domain]['ips'])

    summary_users_list = [{key: value} for key, value in summary_users.items() if value['megabytes'] > 1]
    summary_users_list.sort(key=lambda x: list(x.values())[0]['ips'], reverse=True)

    summary_reverse = {
        'users': summary_users_list,
        'endpoints': summary_endpoints_list,
        'ips': [],
        'megabytes': [],
        # 'time': [],
        # 'connections': [],
    }

    for endpoint in summary:
        summary_reverse['ips'].append({
            'endpoint': endpoint,
            'value': summary[endpoint]['ips'],
        })
        summary_reverse['megabytes'].append({
            'endpoint': endpoint,
            'value': summary[endpoint]['megabytes'],
        })
        # summary_reverse['time'].append({
        #     'endpoint': endpoint,
        #     'value': summary[endpoint]['time'],
        # })
        # summary_reverse['connections'].append({
        #     'endpoint': endpoint,
        #     'value': summary[endpoint]['connections'],
        # })

    # sort by value
    summary_reverse['ips'].sort(key=lambda x: x['value'], reverse=True)
    summary_reverse['megabytes'].sort(key=lambda x: x['value'], reverse=True)
    # summary_reverse['time'].sort(key=lambda x: x['value'], reverse=True)
    # summary_reverse['connections'].sort(key=lambda x: x['value'], reverse=True)


    with open(output_path + file_name, 'w') as f:
        json.dump(summary_reverse, f, indent=4)


for i in [0]: #range(30, 0, -1):
    last_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    last_day -= timedelta(days=i)
    
    end_date = last_day + timedelta(days=1)

    last_day_name = last_day.strftime('%Y-%m-%d')
    generate_summary(last_day, end_date, 'day', last_day_name + '.json')


    # from beginning of the week
    last_week = last_day - timedelta(days=last_day.weekday())
    last_week_name = last_week.strftime('%Y-%m-%d')
    generate_summary(last_week, end_date, 'week', last_week_name + '.json')


    # from beginning of the month
    last_month = last_day.replace(day=1)
    last_month_name = last_month.strftime('%Y-%m')
    generate_summary(last_month, end_date, 'month', last_month_name + '.json')
