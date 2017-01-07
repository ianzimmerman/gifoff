from datetime import datetime, timedelta    

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...models import db_commit, User, Group, Challenge, Entry, Prompt
from ...forms import GroupForm, ChallengeEntry, ChallengeForm

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
                return jsonify({'response': 'OK', 'prompt_id': f.prompt_id.data}), 200
            else:
                return jsonify({'response': 'ERROR', 'prompt_id': f.prompt_id.data}), 304
        elif f.errors:
            return jsonify({'response': 'ERROR', 'errors':f.errors, 'prompt_id': f.prompt_id.data}), 200
        
        forms[p.id] = f
    
    return render_template('main/enter.html', challenge=challenge, forms=forms)
    
@main.route('<id_slug:group_id>/new-challenge', methods=['GET', 'POST'])
def new_challenge(group_id):
    group = Group.query.get_or_404(group_id)
    
    date_range = {'s': datetime.now(), 'e': datetime.now() + timedelta(hours=4)}
    print(request.form)
    form = ChallengeForm(start_time=date_range['s'], end_time=date_range['e'])
    if form.validate_on_submit():
        c = Challenge(group=group,
                        author=current_user, 
                        name=form.name.data, 
                        description=form.description.data, 
                        start_time=form.start_time.data, 
                        end_time=form.end_time.data
                    )
                    
        if db_commit():
            return redirect(url_for('main.challenge', group_id=group, challenge_id=c))
    
    
    
    return render_template('main/create.html', group=group, form=form, date_range=date_range)