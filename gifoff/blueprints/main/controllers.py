from uuid import uuid4
from random import shuffle

import arrow

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, current_app, jsonify
from flask_mail import Message
from flask_security import current_user, login_required, roles_required

from .helpers import IDSlugConverter, add_app_url_map_converter
from ...cache import cache, clear_keys
from ...forms import GroupForm, ChallengeEntry, ChallengeForm, PromptForm
from ...mail import send_async_email
from ...models import db, db_commit, User, Group, Challenge, Entry, Prompt

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
def index():
    c = dict()
    if current_user.is_authenticated:
        challenges = Challenge.query.filter(Challenge.group_id.in_([g.id for g in current_user.player_of]))

        c['judging'] = challenges.filter(Challenge.judge == current_user, Challenge.winner_id == None).order_by(
            Challenge.utc_end_time)
        c['active'] = challenges.filter(Challenge.judge != current_user, Challenge.winner_id == None).order_by(
            Challenge.utc_end_time)
        c['recent'] = challenges.filter(Challenge.winner_id != None).order_by(Challenge.date_modified.desc()).limit(5)

    return render_template('main/index.html', challenges=c)


@main.route('<id_slug:group_id>')
@login_required
def group(group_id):
    group = Group.query.get_or_404(group_id)
    check_access(group)

    challenges = Challenge.query.filter(Challenge.group_id == group.id).order_by(Challenge.date_modified.desc())

    c = dict()
    c['active'] = challenges.filter(Challenge.winner_id == None)
    c['recent'] = challenges.filter(Challenge.winner_id != None).limit(5)

    return render_template('main/group.html', group=group, challenges=c)


@main.route('<id_slug:group_id>/<id_slug:challenge_id>', methods=['GET', 'POST'])
@login_required
def challenge(group_id, challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    check_access(challenge.group)

    if challenge.active and current_user not in [challenge.author, challenge.judge]:
        return redirect(url_for('main.enter', challenge_id=challenge))
    elif challenge.active and current_user == challenge.judge: 
        entries = challenge.players
        shuffle(entries)

    else:
        entries = []  
    
    form = PromptForm()
    if form.validate_on_submit():
        p = Prompt(challenge=challenge, prompt=form.prompt.data)
        if db_commit():
            return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))

    return render_template('main/challenge.html', challenge=challenge, form=form, entries=entries)


@main.route('<id_slug:challenge_id>/enter', methods=['GET', 'POST'])
@login_required
def enter(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)
    check_access(challenge.group)

    if current_user == challenge.judge:
        flash('You cannot enter, you are the judge.', 'danger')
        return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))

    forms = dict()
    for p in challenge.prompts:
        f = ChallengeEntry(prompt_id=p.id, url=p.user_entry(current_user).url, entry_id=p.user_entry(current_user).id)
        if f.validate_on_submit():
            entry = Entry.query.get(int(f.entry_id.data))
            entry.url = f.url.data
            if db_commit():
                return jsonify({'response': 'OK', 'prompt_id': f.prompt_id.data, 'url': entry.url}), 200
            else:
                return jsonify({'response': 'ERROR', 'prompt_id': f.prompt_id.data}), 304
        elif f.errors:
            return jsonify({'response': 'ERROR', 'errors': f.errors, 'prompt_id': f.prompt_id.data}), 200

        forms[p.id] = f

    return render_template('main/enter.html', challenge=challenge, forms=forms)


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
            return jsonify({'response': 'OK'}), 200
        else:
            return jsonify({'response': 'Not Modified'}), 304

    return jsonify({'response': 'Not Authorized'}), 401


@main.route('challenge/<int:challenge_id>/close')
@login_required
def close(challenge_id):
    challenge = Challenge.query.get_or_404(challenge_id)

    if current_user == challenge.judge:
        max_score, winner = challenge.high_score

        if winner:
            challenge.winner = winner
            if db_commit():
                clear_keys(cache, ['leaders{}'.format(challenge.group.id),
                                   'recent{}'.format(challenge.group.id)]
                           )
                try:
                    msg = Message(
                        "{}: Challenge '{}' completed! Come see the winner".format(current_app.config['APP_NAME'],
                                                                                   challenge.name),
                        sender=(current_app.config['APP_NAME'], current_app.config['MAIL_DEFAULT_SENDER']),
                        recipients=[current_user.email],
                        bcc=[p.email for p in challenge.players])

                    msg.body = "{} by {} has completed.\n".format(challenge.name, challenge.author.username)
                    msg.body += "{} has humbly selected the winner to be... {} \n".format(challenge.judge.username,
                                                                                          challenge.winner.username)
                    msg.body += "---\n"
                    msg.body += "See {}'s and everyone else's entries at: {}\n".format(challenge.winner.username,
                                                                                       url_for('main.challenge',
                                                                                               group_id=challenge.group,
                                                                                               challenge_id=challenge,
                                                                                               _external=True))
                    msg.body += "---\n"
                    msg.body += "Group Invite Link: {}".format(
                        url_for('main.join_group', uuid=challenge.group.pin, _external=True))

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


@main.route('<id_slug:group_id>/new-challenge', methods=['GET', 'POST'])
@login_required
def new_challenge(group_id):
    group = Group.query.get_or_404(group_id)
    check_access(group)

    if group.last_winner:
        judge_id = group.last_winner.id
    else:
        judge_id = current_user.id

    a = arrow.utcnow()

    date_range = {
        's': a.replace(minutes=+10).to(current_app.config['DEFAULT_TIMEZONE']).naive,
        'e': a.replace(hours=+4, minutes=+10).to(current_app.config['DEFAULT_TIMEZONE']).naive
    }

    form = ChallengeForm(date_range="{} - {}".format(date_range['s'], date_range['e']), judge_id=judge_id)
    form.judge_id.choices = [(p.id, p.username) for p in group.players]

    # print(request.form)

    if form.validate_on_submit() and group.active_count == 0:
        date_range = form.date_range.data.split(" - ")
        st = arrow.get(date_range[0])
        et = arrow.get(date_range[1])

        c = Challenge(group=group,
                      author=current_user,
                      name=form.name.data,
                      description=form.description.data,
                      judge_id=int(form.judge_id.data),
                      utc_start_time=arrow.get(st.naive, current_app.config['DEFAULT_TIMEZONE']).to('utc').datetime,
                      utc_end_time=arrow.get(et.naive, current_app.config['DEFAULT_TIMEZONE']).to('utc').datetime
                      )

        ps = [Prompt(challenge=c, prompt=p) for p in request.form.getlist('prompts') if p != '']
        db.session.add_all(ps)

        if db_commit():
            try:
                msg = Message("New Challenge Posted to {} at {}".format(group.name, current_app.config['APP_NAME']),
                              sender=(current_app.config['APP_NAME'], current_app.config['MAIL_DEFAULT_SENDER']),
                              recipients=[current_app.config['MAIL_DEFAULT_SENDER']],
                              bcc=[p.email for p in group.players])

                msg.body = "New Challenge by {}: '{}'\n".format(current_user.username, c.name)
                msg.body += "{}\n".format(c.description)
                msg.body += "---\n"
                msg.body += "The challenge starts at {} ({}) and will be judged by {}.\n".format(
                    st.format('YYYY-MM-DD HH:mm'), current_app.config['DEFAULT_TIMEZONE'], c.judge.username)
                msg.body += "Get Started: {}\n".format(
                    url_for('main.challenge', group_id=group, challenge_id=c, _external=True))
                msg.body += "---\n"
                msg.body += "Group Invite Link: {}".format(url_for('main.join_group', uuid=group.pin, _external=True))

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

    a = arrow.utcnow()

    min_time = a.to(current_app.config['DEFAULT_TIMEZONE']).naive

    if request.method != 'POST':
        challenge.utc_start_time = challenge.start_time.to(current_app.config['DEFAULT_TIMEZONE']).datetime
        challenge.utc_end_time = challenge.end_time.to(current_app.config['DEFAULT_TIMEZONE']).datetime

    c_obj = dict(
        judge_id=challenge.judge_id,
        name=challenge.name,
        description=challenge.description,
        date_range="{} - {}".format(challenge.utc_start_time, challenge.utc_end_time)
    )

    form = ChallengeForm(**c_obj)
    form.judge_id.choices = [(p.id, p.username) for p in challenge.group.players]

    if form.validate_on_submit():
        date_range = form.date_range.data.split(" - ")
        st = arrow.get(date_range[0])
        et = arrow.get(date_range[1])

        challenge.name = form.name.data
        challenge.description = form.description.data
        challenge.judge_id = int(form.judge_id.data)
        challenge.utc_start_time = arrow.get(st.naive, current_app.config['DEFAULT_TIMEZONE']).to('utc').datetime
        challenge.utc_end_time = arrow.get(et.naive, current_app.config['DEFAULT_TIMEZONE']).to('utc').datetime

        if db_commit():
            return redirect(url_for('main.challenge', group_id=challenge.group, challenge_id=challenge))

    return render_template('main/edit_challenge.html', challenge=challenge, form=form, min_time=min_time)


@main.route('new-group', methods=['GET', 'POST'])
@login_required
def new_group():
    form = GroupForm()
    if form.validate_on_submit():
        g = Group(owner=current_user,
                  name=form.name.data,
                  description=form.description.data)

        g.pin = str(uuid4())

        g.players.append(g.owner)
        g.authors.append(g.owner)

        if db_commit():
            return redirect(url_for('main.group', group_id=g))

    return render_template('main/new_group.html', group=group, form=form)


@main.route('join/<uuid>', methods=['GET'])
@login_required
def join_group(uuid):
    g = Group.query.filter(Group.pin == uuid).first()
    if g:
        if current_user not in g.players:
            g.players.append(current_user)
            if db_commit():
                flash('Successfully joined group {}'.format(g.name), 'success')
        else:
            flash('You are already a member of this group. Try right clicking the link to share.', 'info')

        return redirect(url_for('main.group', group_id=g))

    flash('Group not found.', 'warning')
    return redirect(url_for('main.index'))


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

        return jsonify({'response': 'OK'}), 200
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
    case = dict(prompt=Prompt, group=Group)
    switch = case.get(model)

    if switch:
        obj = switch.query.get_or_404(model_id)
    else:
        abort(404)

    def auth_delete(model_obj):
        if isinstance(model_obj, Prompt):
            if current_user in [model_obj.challenge.author, model_obj.challenge.group.owner]:
                return 'json'

        if isinstance(model_obj, Group):
            if current_user == model_obj.owner:
                return 'redirect'

        return False

    response = auth_delete(obj)
    if response:
        db.session.delete(obj)
        db_commit()

        if response == 'json':
            return jsonify({'response': 'OK'}), 200
        else:
            return redirect(url_for('main.index'))
    else:
        abort(401)


@main.route('clear-cache')
@roles_required(['ADMIN'])
def clear_cache():
    cache.clear()
    flash('Site cache cleared', 'success')
    return redirect(url_for('main.index'))
