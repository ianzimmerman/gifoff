from datetime import datetime, timedelta    

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...models import db_commit, User, Group, Challenge, Entry, Prompt
from ...forms import GroupForm, ChallengeEntry, ChallengeForm, PromptForm

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
    
@main.route('<id_slug:group_id>/<id_slug:challenge_id>', methods=['GET', 'POST'])
def challenge(group_id, challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    form = PromptForm()
    if form.validate_on_submit():
        p = Prompt(challenge=challenge, prompt=form.prompt.data)
        if db_commit():
            return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))
        else:
            print(form.errors)
    
    return render_template('main/challenge.html', challenge=challenge, form=form)
    
@main.route('<id_slug:challenge_id>/entry/<int:user_id>', methods=['GET', 'POST'])
def entry(challenge_id, user_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    user = User.query.get_or_404(user_id)
    
    return render_template('main/entry.html', challenge=challenge, user=user)
    
@main.route('challenge/<int:challenge_id>/entry/<int:entry_id>/score/<score>')
def score(challenge_id, entry_id, score):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if current_user in [challenge.judge, challenge.author]:
        entry = Entry.query.get_or_404(entry_id)
        entry.score = float(score)
        if db_commit():
            return jsonify({'response':'OK'}), 200
        else:
            return jsonify({'response':'Not Modified'}), 304
    
    return jsonify({'response':'Not Authorized'}), 510

@main.route('challenge/<int:challenge_id>/close')
def close(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if current_user in [challenge.judge, challenge.author]:
        max_score, winner = challenge.high_score
        
        if winner:
            challenge.winner = winner
            if db_commit():
                flash('Challenge completed', 'success')
        else:
            flash('No Winner Identified.', 'danger')
    
    return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))

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
                return jsonify({'response': 'OK', 'prompt_id': f.prompt_id.data, 'url': entry.url }), 200
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
    
    
    
    return render_template('main/new_challenge.html', group=group, form=form, date_range=date_range)

@main.route('new-group', methods=['GET', 'POST'])
def new_group():
    form = GroupForm()
    if form.validate_on_submit():
        g = Group(owner=current_user, 
                    name=form.name.data, 
                    description=form.description.data, 
                    pin=form.pin.data
                )
                
        g.players.append(g.owner)
        g.authors.append(g.owner)
                    
        if db_commit():
            return redirect(url_for('main.group', group_id=g))
    
    return render_template('main/new_group.html', group=group, form=form)

@main.route('join-group', methods=['GET', 'POST'])
def join_group():
    form = GroupForm(name=request.args.get('name'), pin=request.args.get('pin'))
    if form.validate_on_submit():
        g = Group.query.filter(Group.name==form.name.data, Group.pin==form.pin.data).first()
        if g:
            g.players.append(current_user)
            if db_commit():
                return jsonify({'response': 'OK', 'url': url_for('main.group', group_id=g)}), 200
        else:
            return jsonify({'response': 'ERROR', 'error': 'Group or PIN not found'}), 200
    
    elif form.errors:
        return jsonify({'response': 'ERROR', 'error': 'Empty Fields'}), 200
            
    return render_template('main/join_group.html', form=form)