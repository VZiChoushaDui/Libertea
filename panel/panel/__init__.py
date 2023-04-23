import requests
from . import stats
from . import utils
from . import config
from . import certbot
from . import health_check
from . import sysops
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

@uwsgidecorators.timer(5 * 60)
def periodic_update_users_stats(signal):
    print("CRON: Updating users stats cache")
    users = utils.get_users()
    for user in users:
        utils.update_user_stats_cache(user['panel_id'])
    print("CRON: done")

@uwsgidecorators.timer(15 * 60)
def periodic_health_check_parse(signal):
    print("CRON: Health check parse")
    health_check.parse()
    print("CRON: done")

@uwsgidecorators.cron(-10, -1, -1, -1, -1)
def save_connected_ips(signal):
    print("CRON: Saving connected IPs")
    stats.save_connected_ips_count()
    print("CRON: done")

@uwsgidecorators.cron(-5, -1, -1, -1, -1)
def update_certificates(signal):
    print("CRON: Updating certificates")
    domains = utils.get_domains()
    domains.append(config.get_panel_domain())
    for domain in domains:
        certbot.generate_certificate(domain)
    print("CRON: done")


def create_app():
    app = Flask(__name__)

    print("Updating HAProxy lists")
    sysops.haproxy_update_users_list()
    sysops.haproxy_update_domains_list()
    sysops.haproxy_update_camouflage_list()

    try:
        update_certificates(None)
    except:
        pass

    app.register_blueprint(admin.blueprint)
    app.register_blueprint(user.blueprint)
    app.register_blueprint(api.blueprint)

    return app
