import os
import time
import pymongo
import threading
from . import config
from . import settings

def get_root_dir():
    return "/root/libertea/"

def run_command(command):
    # go to root directory
    os.chdir(get_root_dir())
    # run the command, and return the exit code
    result = os.system(command)

    print("Ran command '" + command + "' and got exit code " + str(result))
    return result

def ___haproxy_reload_internal(sleep_secs):
    print("**** Reloading haproxy container ****")
    if run_command('sleep ' + str(sleep_secs) + ' && docker kill -s HUP ' + config.HAPROXY_CONTAINER_NAME) == 0:
        return True
    
    return False

def haproxy_reload():
    th = threading.Thread(target=___haproxy_reload_internal, args=(2,))
    th.start()
    return True
    

def haproxy_renew_certs():
    if run_command('./haproxy/certbot.sh') == 0:
        return True
    
    return False

def haproxy_ensure_folder():
    folder = get_root_dir() + 'data/haproxy-lists'
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except:
            pass

def haproxy_update_users_list():
    count = 0
    haproxy_ensure_folder()
    with open(get_root_dir() + 'data/haproxy-lists/valid-user-endpoints.lst', 'w') as f:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
        users = db.users
        for user in users.find():
            # write each user to file
            f.write('/' + user['connect_url'] + '/' + '\n')
            f.write('/' + user['connect_url'] + '___' + '\n')
            count += 1

    print("Wrote " + str(count) + " users to haproxy-lists/valid-user-endpoints.lst")

    count = 0
    with open(get_root_dir() + 'data/haproxy-lists/valid-panel-endpoints.lst', 'w') as f:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
        users = db.users
        for user in users.find():
            # write each user to file
            f.write('/' + user['_id'] + '/' + '\n')
            count += 1
        f.write('/' + config.get_proxy_connect_uuid() + '/' + '\n')
        count += 1

    print("Wrote " + str(count) + " users to haproxy-lists/valid-panel-endpoints.lst")
    return haproxy_reload()

def haproxy_update_domains_list():
    count = 0
    haproxy_ensure_folder()
    with open(get_root_dir() + 'data/haproxy-lists/domains.lst', 'w') as f:
        client = config.get_mongo_client()
        db = client[config.MONGODB_DB_NAME]
        domains = db.domains
        for domain in domains.find():
            # write each domain to file
            f.write(domain['_id'] + '\n')
            count += 1

    print("Wrote " + str(count) + " domains to haproxy-lists/domains.lst")
    return haproxy_reload()

def haproxy_update_camouflage_list():
    count = 0
    haproxy_ensure_folder()
    with open(get_root_dir() + 'data/haproxy-lists/camouflage-hosts.lst', 'w') as f:
        camouflage_domain = settings.get_camouflage_domain()
        if camouflage_domain and camouflage_domain.startswith('https://'):
            camouflage_domain = camouflage_domain[8:]
        f.write(camouflage_domain + '\n')
        count += 1

    print("Wrote " + str(count) + " domains to haproxy-lists/camouflage-hosts.lst")
    return haproxy_reload()

def add_ssh_key(ssh_key):
    ssh_keys_dir = '/home/libertea/.ssh'
    ssh_key_file = ssh_keys_dir + '/authorized_keys'

    if not os.path.exists(ssh_keys_dir):
        os.makedirs(ssh_keys_dir)

    if not os.path.exists(ssh_key_file):
        with open(ssh_key_file, 'w') as f:
            f.write(ssh_key + '\n')
        return True

    # check if the key already exists
    with open(ssh_key_file, 'r') as f:
        for line in f.readlines():
            if ssh_key in line:
                return True
            
    # append the key to the file
    with open(ssh_key_file, 'a') as f:
        f.write(ssh_key + '\n')

    return True
