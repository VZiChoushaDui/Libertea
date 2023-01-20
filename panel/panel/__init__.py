from . import utils
from . import config
from . import sysops
from flask import Flask
from pymongo import MongoClient
import uwsgidecorators

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



def create_app():
    app = Flask(__name__)

    print("Updating HAProxy lists")
    sysops.haproxy_update_users_list()
    sysops.haproxy_update_domains_list()

    from .admin import blueprint as admin_blueprint
    app.register_blueprint(admin_blueprint)
    
    from .user import blueprint as user_blueprint
    app.register_blueprint(user_blueprint)

    from .api import blueprint as api_blueprint
    app.register_blueprint(api_blueprint)

    return app
