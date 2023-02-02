import urllib.parse
from . import config
from . import settings
from pymongo import MongoClient
from . import clash_conf_generator
from flask import Blueprint, render_template, redirect, url_for, flash, request

blueprint = Blueprint('user', __name__)

def get_user(id):
    client = MongoClient(config.get_mongodb_connection_string())
    db = client[config.MONGODB_DB_NAME]
    users = db.users

    user = list(users.find({'_id': id}))
    if len(user) == 0:
        return None
    return user[0]
    

@blueprint.route('/<id>/')
def user_dashboard(id):
    user = get_user(id)
    if user is None:
        return "", 404

    try:
        ua = request.headers.get('User-Agent')
        if 'Clash' in ua or 'Stash' in ua:
            return redirect('/{}/config.yaml'.format(id))
    except:
        pass

    conf_url = request.url_root.replace('http://', 'https://') + str(id) + '/config.yaml'
    name = config.get_panel_domain() + "-" + user['_id'][0:8]

    manual_conf_url = request.url_root.replace('http://', 'https://') + str(id) + '/mconfig.yaml'

    clash_conf_url = "clash://install-config?url=" + urllib.parse.quote_plus(conf_url) + "&name=" + urllib.parse.quote(name)
    return render_template('user.jinja', 
        user=user, 
        clash_conf_url=clash_conf_url,
        clash_manual_conf_url=manual_conf_url
    )

@blueprint.route('/<id>/<file_name>.yaml')
def user_config(id, file_name):
    user = get_user(id)
    if user is None:
        return "", 404

    ua = request.headers.get('User-Agent')
    is_meta = 'Clash' in ua and ('Meta' in ua or 'Stash' in ua)

    if file_name == 'mconfig':
        conf = clash_conf_generator.generate_conf_singlefile(user['connect_url'], 
            meta=is_meta)

        # don't show in browser, use a header to force download
        return conf, 200, {
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Disposition': 'attachment; filename="' + config.get_panel_domain() + "-" + str(id) + '.yaml"',
        }

    if settings.get_single_clash_file_configuration() and file_name == 'config':
        conf = clash_conf_generator.generate_conf_singlefile(user['connect_url'], 
            meta=is_meta)
    else:
        if file_name == 'config':
            file_name = 'main'

        conf = clash_conf_generator.generate_conf(file_name + '.yaml', user['_id'], user['connect_url'], 
            meta=is_meta)
        
        if conf == "":
            return "", 404

    return conf, 200, {
        'Content-Type': 'text/plain; charset=utf-8',
        'Content-Disposition': 'inline; filename="' + config.get_panel_domain() + "-" + str(id) + '.yaml"',
    }
