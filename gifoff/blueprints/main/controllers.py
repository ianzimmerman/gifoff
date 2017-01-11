from datetime import datetime, timedelta    
from threading import Thread

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, session, current_app, jsonify
from flask_mail import Message
from flask_security import current_user, login_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...models import db, db_commit, User, Group, Challenge, Entry, Prompt
from ...forms import GroupForm, ChallengeEntry, ChallengeForm, PromptForm
from ...mail import send_async_email

Blueprint.add_app_url_map_converter = add_app_url_map_converter

main = Blueprint('main', __name__, url_prefix='/', template_folder='templates')
main.add_app_url_map_converter(IDSlugConverter, 'id_slug')


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



@main.route('')
@login_required
def index():
    challenges = Challenge.query.filter(Challenge.group_id.in_([g.id for g in current_user.player_of]))
    
    c = dict()
    c['judging'] = challenges.filter(Challenge.judge==current_user, Challenge.winner_id==None).order_by(Challenge.end_time)
    c['active'] = challenges.filter(Challenge.judge!=current_user, Challenge.winner_id==None).order_by(Challenge.end_time)
    c['recent'] = challenges.filter(Challenge.winner_id!=None).order_by(Challenge.date_modified.desc()).limit(10)
    
    return render_template('main/index.html', challenges=c)
    
@main.route('<id_slug:group_id>')
@login_required
def group(group_id):
    group = Group.query.get_or_404(group_id)
    check_access(group)
    
    challenges = Challenge.query.filter(Challenge.group_id==group.id).order_by(Challenge.date_modified.desc())
    
    c = dict()
    c['active'] = challenges.filter(Challenge.winner_id==None)
    c['recent'] = challenges.filter(Challenge.winner_id!=None).limit(10)
    
    return render_template('main/group.html', group=group, challenges=c)
    
@main.route('<id_slug:group_id>/<id_slug:challenge_id>', methods=['GET', 'POST'])
@login_required
def challenge(group_id, challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    check_access(challenge.group)
    
    form = PromptForm()
    if form.validate_on_submit():
        p = Prompt(challenge=challenge, prompt=form.prompt.data)
        if db_commit():
            return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))
    
    return render_template('main/challenge.html', challenge=challenge, form=form)
    
@main.route('<id_slug:challenge_id>/entry/<int:user_id>', methods=['GET', 'POST'])
@login_required
def entry(challenge_id, user_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    check_access(challenge.group)
    
    user = User.query.get_or_404(user_id)
    
    return render_template('main/entry.html', challenge=challenge, user=user)
    
@main.route('challenge/<int:challenge_id>/entry/<int:entry_id>/score/<score>')
@login_required
def score(challenge_id, entry_id, score):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if current_user == challenge.judge:
        entry = Entry.query.get_or_404(entry_id)
        entry.score = float(score)
        if db_commit():
            return jsonify({'response':'OK'}), 200
        else:
            return jsonify({'response':'Not Modified'}), 304
    
    return jsonify({'response':'Not Authorized'}), 401

@main.route('challenge/<int:challenge_id>/close')
@login_required
def close(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if current_user == challenge.judge:
        max_score, winner = challenge.high_score
        
        if winner:
            challenge.winner = winner
            if db_commit():
                try:
                    msg = Message("{}: Challenge '{}' completed! Come see the winner".format(current_app.config['APP_NAME'], challenge.name),
                                    sender=(current_app.config['APP_NAME'], current_app.config['MAIL_DEFAULT_SENDER']),
                                    to=[current_user.email],
                                    bcc=[p.email for p in challenge.players])
                    
                    msg.body = "{} by {} has completed.\n".format(challenge.name, challenge.author.username)
                    msg.body += "{} has humbly selected the winner to be... {} \n".format(challenge.judge.username, challenge.winner.username)
                    msg.body += "---\n"
                    msg.body += "See {}'s and everyone else's entries at: {}\n".format(challenge.winner.username, url_for('main.challenge', group_id=challenge.group, challenge_id=challenge, _external=True))
                    
                    send_async_email(msg)
                    
                    flash('Mail sent, emails on their way!', 'success')
                except Exception as e:
                    flash('Mail send failed, send manually: {}'.format(e), 'danger')
        else:
            flash('No Winner Identified.', 'danger')
    
    return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))
    
@main.route('challenge/<int:challenge_id>/delete')
@login_required
def delete_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    
    if current_user in [challenge.group.owner, challenge.author]:
        group = challenge.group
        db.session.delete(challenge)
        if db_commit():
            flash('Challenge Deleted', 'success')
            return redirect(url_for('main.group', group_id=group))
        else:
            flash('Delete Failed', 'danger')
    else:
        flash('No Access.', 'danger')
    
    return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))

@main.route('<id_slug:challenge_id>/enter', methods=['GET', 'POST'])
@login_required
def enter(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    check_access(challenge.group)
    
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
@login_required
def new_challenge(group_id):
    group = Group.query.get_or_404(group_id)
    check_access(group)
    
    if group.last_winner:
        judge_id = group.last_winner.id
    else:
        judge_id = current_user.id
    
    date_range = {'s': datetime.now() + timedelta(minutes=10), 'e': datetime.now() + timedelta(hours=4, minutes=10)}
    form = ChallengeForm(start_time=date_range['s'], end_time=date_range['e'], judge_id=judge_id)
    form.judge_id.choices = [(p.id, p.username) for p in group.players]
    
    if form.validate_on_submit() and group.active_count == 0:
        c = Challenge(group=group,
                        author=current_user, 
                        name=form.name.data, 
                        description=form.description.data, 
                        judge_id=int(form.judge_id.data), 
                        start_time=form.start_time.data, 
                        end_time=form.end_time.data
                    )
        
        if db_commit():
            try:
                msg = Message("New Challenge Posted to {} at {}".format(group.name, current_app.config['APP_NAME']),
                                sender=(current_app.config['APP_NAME'], current_app.config['MAIL_DEFAULT_SENDER']),
                                to=['noreply@gifoff.com'],
                                bcc=[p.email for p in group.players])
                
                msg.body = "New Challenge by {}: '{}'\n".format(current_user.username, c.name)
                msg.body += "{}\n".format(c.description)
                msg.body += "---\n"
                msg.body += "The challenge starts at {} and will be judged by {}.\n".format(c.start_time, c.judge.username)
                msg.body += "Get Started: {}\n".format(url_for('main.challenge', group_id=group, challenge_id=c, _external=True))
                
                send_async_email(msg)
                
                flash('Mail sent; Hurry up and add some prompts!', 'success')
            except Exception as e:
                flash('Mail send failed, send manually: {}'.format(e), 'danger')
            
            return redirect(url_for('main.challenge', group_id=group, challenge_id=c))
    
    return render_template('main/new_challenge.html', group=group, form=form, date_range=date_range)
    
@main.route('edit-challenge/<id_slug:challenge_id>', methods=['GET', 'POST'])
@login_required
def edit_challenge(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    if current_user not in [challenge.author, challenge.group.owner]:
        abort(401)
    
    form = ChallengeForm(obj=challenge)
    form.judge_id.choices = [(p.id, p.username) for p in challenge.group.players]
    if form.validate_on_submit():
        challenge.name = form.name.data
        challenge.description = form.description.data 
        challenge.judge_id = int(form.judge_id.data)
        challenge.start_time = form.start_time.data
        challenge.end_time = form.end_time.data
        
        if db_commit():
            return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))
    
    return render_template('main/edit_challenge.html', challenge=challenge, form=form)

@main.route('new-group', methods=['GET', 'POST'])
@login_required
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
@login_required
def join_group():
    form = GroupForm(name=request.args.get('name'), pin=request.args.get('pin'))
    if request.method == 'POST':
        g = Group.query.filter(Group.name==form.name.data, Group.pin==form.pin.data).first()
        if g:
            g.players.append(current_user)
            if db_commit():
                return jsonify({'response': 'OK', 'url': url_for('main.group', group_id=g)}), 200
        else:
            return jsonify({'response': 'ERROR', 'error': 'Group or PIN not found'}), 200
            
    return render_template('main/join_group.html', form=form)

@main.route('<int:group_id>/update-authors', methods=['POST'])
@login_required
def update_authors(group_id):
    group = Group.query.get_or_404(group_id)
    if current_user == group.owner:
        current_authors = {a.id for a in group.authors}
        new_authors = set(map(int, request.form.getlist('authors')))
    
        to_add = new_authors - current_authors
        to_del = current_authors - new_authors
        
        for a_id in to_add:
            group.authors.append(User.query.get(a_id))
            
        for a_id in to_del:
            group.authors.remove(User.query.get(a_id))
        
        db_commit()
        
        return jsonify({'response':'OK'}), 200
    else:
        abort(401)
        
@main.route('<int:group_id>/leave-group', methods=['GET'])
@login_required
def leave_group(group_id):
    group = Group.query.get_or_404(group_id)
    
    if current_user != group.owner:
        if group in current_user.player_of:
            group.players.remove(current_user)
        
        if group in current_user.author_of:
            group.authors.remove(current_user)
        
        if db_commit():
            flash("Successfully left group.", 'success')
            return redirect(url_for('main.index'))
        else:
            flash("Something went wrong, you are stuck in this group forever.", 'danger')
    else:
        flash("You can't remove yourself if you are the owner, sorry! Delete the group instead.", 'warning')
        
    return redirect(url_for('main.group', group_id=group))


@main.route('delete/<model>/<int:model_id>')
@login_required
def delete(model, model_id):
    case = dict(prompt=Prompt)
    switch = case.get(model)
    
    if switch:
        obj = switch.query.get_or_404(model_id)
    else:
        abort(404)
    
    def auth_delete(model_obj):
        if isinstance(model_obj, Prompt):
            return current_user in [model_obj.challenge.author, model_obj.challenge.group.owner]
        
        return False
    
    if auth_delete(obj):
        db.session.delete(obj)
        db_commit()
        return jsonify({'response':'OK'}), 200
    else:
        abort(401)
        