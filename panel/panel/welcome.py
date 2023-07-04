import re
import json
import urllib
import requests
import threading
from . import utils
from . import stats
from . import config
from . import settings
from . import health_check
from . import admin
from pymongo import MongoClient
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request

blueprint = Blueprint('welcome', __name__)

root_url = '/' + config.get_admin_uuid() + '/'

@blueprint.route(root_url + 'welcome/')
def welcome():
    first_user = utils.get_users()[0]
    setup_finished = settings.get_camouflage_domain() != ""

    return render_template('admin/welcome/welcome.jinja',
        admin_uuid=config.get_admin_uuid(),
        first_user_url = first_user['panel_id'],
        setup_finished = setup_finished,
    )

@blueprint.route(root_url + 'welcome/routes/')
def routes():
    return render_template('admin/welcome/routes.jinja',
        admin_uuid=config.get_admin_uuid(),
        panel_domain=config.get_panel_domain(),
    )

@blueprint.route(root_url + 'welcome/routes/custom/', methods=['GET'])
def routes_custom():
    return render_template('admin/welcome/routes-custom.jinja',
        admin_uuid=config.get_admin_uuid(),
        server_ip=config.SERVER_MAIN_IP,
    )

@blueprint.route(root_url + 'welcome/routes/custom/', methods=['POST'])
def routes_custom_post():
    domain = request.form.get('domain', None)
    if domain is None:
        return redirect(url_for('welcome.routes_custom'))

    domain = domain.strip()
    if domain.startswith('http://'):
        domain = domain[7:]
    if domain.startswith('https://'):
        domain = domain[8:]
    if domain.startswith('www.'):
        domain = domain[4:]

    if len(domain) == 0:
        return redirect(url_for('welcome.routes_custom'))
    
    utils.add_domain(domain)
    threading.Thread(target=utils.update_domain_cache, args=(domain, 2)).start()

    return redirect(url_for('welcome.routes2'))

@blueprint.route(root_url + 'welcome/routes/default/')
def routes_default():
    domain = config.get_panel_domain()
    utils.add_domain(domain)
    threading.Thread(target=utils.update_domain_cache, args=(domain, 2)).start()

    return redirect(url_for('welcome.routes2'))
    
@blueprint.route(root_url + 'welcome/routes2/')
def routes2():
    return render_template('admin/welcome/routes2.jinja',
        admin_uuid=config.get_admin_uuid(),
    )

@blueprint.route(root_url + 'welcome/country/', methods=['GET'])
def country():
    return render_template('admin/welcome/country.jinja',
        admin_uuid=config.get_admin_uuid(),
        route_direct_countries=config.ROUTE_IP_LISTS,
        route_direct_country_enabled={x['id']: settings.get_route_direct_country_enabled(x['id']) for x in config.ROUTE_IP_LISTS},
    )

@blueprint.route(root_url + 'welcome/country/', methods=['POST'])
def country_post():
    route_direct = {x['id']: request.form.get('route_direct_' + x['id'], None) for x in config.ROUTE_IP_LISTS}
    for x in config.ROUTE_IP_LISTS:
        settings.set_route_direct_country_enabled(x['id'], route_direct[x['id']] == 'on')

    return redirect(url_for('welcome.camouflage'))

@blueprint.route(root_url + 'welcome/camouflage/', methods=['GET'])
def camouflage():
    camouflage_error = request.args.get('camouflage_error', None)
    camouflage_domain = request.args.get('camouflage_domain', None)

    if camouflage_domain is None:
        saved_camouflage_domain = settings.get_camouflage_domain()
        if saved_camouflage_domain is None or saved_camouflage_domain == "":
            camouflage_domain = "https://"
        else:
            camouflage_domain = saved_camouflage_domain
            camouflage_domain_status, camouflage_domain = utils.check_camouflage_domain(camouflage_domain)
            if camouflage_domain_status != "":
                camouflage_error = camouflage_domain_status
    
    return render_template('admin/welcome/camouflage.jinja',
        admin_uuid=config.get_admin_uuid(),
        camouflage_domain=camouflage_domain,
        camouflage_error=camouflage_error,
    )

@blueprint.route(root_url + 'welcome/camouflage/', methods=['POST'])
def camouflage_post():
    camouflage_domain = request.form.get('camouflage_domain', None)
    if camouflage_domain == '' or camouflage_domain == 'https://':
        settings.set_camouflage_domain("")
    else:
        if not camouflage_domain.startswith('http'):
            camouflage_domain = 'https://' + camouflage_domain

        # check if domain is reachable
        camouflage_domain_status, camouflage_domain = utils.check_camouflage_domain(camouflage_domain)
        if camouflage_domain_status == "":
            settings.set_camouflage_domain(camouflage_domain)
        else:
            return redirect(root_url + 'welcome/camouflage/?camouflage_error=' + camouflage_domain_status + '&camouflage_domain=' + urllib.parse.quote(camouflage_domain))

    return redirect(url_for('welcome.finished'))

@blueprint.route(root_url + 'welcome/finished/')
def finished():
    return render_template('admin/welcome/finished.jinja',
        admin_uuid=config.get_admin_uuid(),
    )
