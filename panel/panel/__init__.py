import requests
import threading
from . import stats
from . import utils
from . import config
from . import certbot
from . import health_check
from . import settings
from . import sysops
from . import welcome
from . import admin
from . import user
from . import api
import uwsgidecorators
from flask import Flask
from pymongo import MongoClient
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

@uwsgidecorators.timer(30)
def periodic_update_domains(signal):
    print("CRON: Updating domains cache")
    domains = utils.get_domains()
    for domain in domains:
        utils.update_domain_cache(domain)
    print("CRON: done updating domains cache")

@uwsgidecorators.timer(10 * 60)
def periodic_update_users_stats(signal):
    print("CRON: Updating users stats cache")
    stats.cleanup_json_cache(force=True)
    users = utils.get_users()
    for user in users:
        utils.update_user_stats_cache(user['panel_id'])
    stats.cleanup_json_cache(force=True)
    print("CRON: done updating users stats cache")

@uwsgidecorators.timer(33 * 60)
def periodic_health_check_parse(signal):
    print("CRON: Health check parse")
    health_check.parse()
    print("CRON: done health check parse")

@uwsgidecorators.cron(-10, -1, -1, -1, -1)
def save_connected_ips(signal):
    print("CRON: Saving connected IPs")
    stats.save_connected_ips_count()
    print("CRON: done saving connected IPs")

@uwsgidecorators.cron(-5, -1, -1, -1, -1)
def update_certificates(signal):
    print("CRON: Updating certificates")
    domains = utils.get_domains()
    domains.append(config.get_panel_domain())
    for domain in domains:
        certbot.generate_certificate(domain)
    print("CRON: done updating certificates")


def create_app():
    app = Flask(__name__)

    print("Updating HAProxy lists")
    sysops.haproxy_update_users_list()
    sysops.haproxy_update_domains_list()
    sysops.haproxy_update_camouflage_list()

    if settings.get_migration_counter() <= 1:
        for domain in utils.get_domains():
            settings.all_domains_ever_push(domain)
        settings.set_migration_counter(2)
    
    if settings.get_migration_counter() <= 2:
        if sysops.regenerate_camouflage_cert():
            settings.set_migration_counter(3)
            

    domains_count = len(utils.get_domains())
    users_count = len(utils.get_users())
    if users_count == 0:
        print("No users, will create the first one")
        # No users, create the first one
        utils.create_user('Libertea user')

    if domains_count == 0:
        print("No domains, will create the first one")
        domain = config.get_panel_domain()
        utils.add_domain(domain)
        threading.Thread(target=utils.update_domain_cache, args=(domain, 2)).start()

    try:
        update_certificates(None)
    except:
        pass

    app.register_blueprint(admin.blueprint)
    app.register_blueprint(user.blueprint)
    app.register_blueprint(api.blueprint)
    app.register_blueprint(welcome.blueprint)

    return app
