import os
import pymongo
from . import config
from . import settings

def get_root_dir():
    # get current directory
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return current_dir + '/../../'

def run_command(command):
    # go to root directory
    os.chdir(get_root_dir())
    # run the command, and return the exit code
    result = os.system(command)

    print("Ran command '" + command + "' and got exit code " + str(result))
    return result

def haproxy_reload():
    print("**** Reloading haproxy container ****")
    if run_command('docker kill -s HUP ' + config.HAPROXY_CONTAINER_NAME) == 0:
        return True
    
    return False

def haproxy_renew_certs():
    if run_command('./haproxy/certbot.sh') == 0:
        return True
    
    return False

def haproxy_ensure_folder():
    folder = get_root_dir() + 'data/haproxy-lists'
    if not os.path.exists(folder):
        os.makedirs(folder)

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
