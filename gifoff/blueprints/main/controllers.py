from datetime import datetime

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from gifoff.models import User, Group, Challenge

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
    
@main.route('<id_slug:group_id>')
def group(group_id):
    group = Group.query.get_or_404(group_id)
    return render_template('main/group.html', group=group)
    
@main.route('<id_slug:group_id>/<id_slug:challenge_id>')
def challenge(group_id, challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    
    return render_template('main/challenge.html', challenge=challenge)
    
@main.route('<id_slug:challenge_id>/entry/<int:user_id>')
def entry(challenge_id, user_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    user = User.query.get_or_404(user_id)
    
    return render_template('main/entry.html', challenge=challenge, user=user)