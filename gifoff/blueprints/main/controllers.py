from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter

Blueprint.add_app_url_map_converter = add_app_url_map_converter

main = Blueprint('main', __name__, url_prefix='/', template_folder='templates')
main.add_app_url_map_converter(IDSlugConverter, 'id_slug')


# @main.before_request
# def before_request():
#     if request.url.startswith('http://') and current_app.config['DEBUG'] == False:
#         url = request.url.replace('http://', 'https://', 1)
#         code = 301
#         return redirect(url, code=code)


@main.route('')
def index():
    return render_template('main/index.html')