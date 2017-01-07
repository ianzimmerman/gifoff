from datetime import datetime

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...models import db_commit, User, Group, Challenge, Entry, Prompt
from ...forms import GroupForm, ChallengeEntry

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
    
@main.route('<id_slug:challenge_id>/enter', methods=['GET', 'POST'])
def enter(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    forms = dict()
    for p in challenge.prompts:
        f = ChallengeEntry(prompt_id=p.id, url=p.user_entry(current_user).url, entry_id=p.user_entry(current_user).id)
        if f.validate_on_submit():
            entry = Entry.query.get(int(f.entry_id.data))
            entry.url = f.url.data
            if db_commit():
                return jsonify('{status: complete}')
            else:
                return jsonify('{status: error}')
        
        forms[p.id] = f
        
        
    
    return render_template('main/enter.html', challenge=challenge, forms=forms)
    
