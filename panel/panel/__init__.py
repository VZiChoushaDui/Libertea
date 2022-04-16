from . import utils
from . import config
from . import sysops
from flask import Flask

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
