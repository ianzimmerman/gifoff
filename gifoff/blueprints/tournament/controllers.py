import arrow
import trueskill

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, current_app, jsonify
from flask_mail import Message
from flask_security import current_user, login_required, roles_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...cache import cache, clear_keys
from ...forms import GroupForm, ChallengeEntry, ChallengeForm, PromptForm
from ...mail import send_async_email
from ...models import db, db_commit, User, Group, Challenge, Entry, Prompt, Rating, FFARating

Blueprint.add_app_url_map_converter = add_app_url_map_converter

tournament = Blueprint('tournament', __name__, url_prefix='/tournament', template_folder='templates')
tournament.add_app_url_map_converter(IDSlugConverter, 'id_slug')


# @main.before_request
# def before_request():
#     if request.url.startswith('http://') and current_app.config['DEBUG'] == False:
#         url = request.url.replace('http://', 'https://', 1)
#         code = 301
#         return redirect(url, code=code)

def check_access(group):
    if group:
        if current_user not in group.players:
            abort(401)


@tournament.route('')
def index():

    return "hello world"