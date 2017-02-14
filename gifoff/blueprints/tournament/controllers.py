import arrow
import trueskill
import pprint

from flask import Blueprint, url_for, render_template, request, redirect, abort, flash, current_app, jsonify
from flask_mail import Message
from flask_security import current_user, login_required, roles_required

from sqlalchemy import func

from gifoff.helpers import Bracket
from .helpers import IDSlugConverter, add_app_url_map_converter

from ...cache import cache, clear_keys
from ...forms import TournamentForm
from ...mail import send_async_email
from ...models import db, db_commit, Tournament, TournamentEntry, TournamentPlayers, TournamentRound, TournamentVote, Rating

Blueprint.add_app_url_map_converter = add_app_url_map_converter

tourney = Blueprint('tourney', __name__, url_prefix='/tournaments', template_folder='templates')
tourney.add_app_url_map_converter(IDSlugConverter, 'id_slug')


# @tourney.before_request
# def before_request():
#     if request.url.startswith('http://') and current_app.config['DEBUG'] == False:
#         url = request.url.replace('http://', 'https://', 1)
#         code = 301
#         return redirect(url, code=code)

def check_access(group):
    if group:
        if current_user not in group.players:
            abort(401)


@tourney.route('')
def index():
    
    playing = [tp.tournament for tp in current_user.tournaments]

    return render_template("tournament/tournaments.html", playing=playing)

@tourney.route('/new', methods=['GET', 'POST'])
def new():
    form = TournamentForm()
    form.group_id.choices = [(g.id, g.name) for g in current_user.author_of]

    if form.validate_on_submit():
        t = Tournament(organizer=current_user, **form.data)
        if db_commit():
            pass
        
        print(t.__dict__)
    
    return render_template("tournament/new_tournament.html", form=form)

@tourney.route('/<id_slug:tournament_id>')
def tournament(tournament_id):
    t = Tournament.query.get_or_404(tournament_id)
    
    # bracket maker
    # say 16:
    # [
    #    [
    #       [
    #           [(1,16)],
    #           [(8,9)]
    #       ],
    #       [
    #           [(5,12)]
    #           [(4,13)]
    #       ]
    #    ],
    #    [
    #       [
    #           [(3,14)],
    #           [(6,11)]
    #       ],
    #       [
    #           [(7,10)]
    #           [(2,15)]
    #       ]
    #    ]
    # ]
    
    pp = pprint.PrettyPrinter(indent=4)
    
    b = Bracket(t.max_players)
    pp.pprint(b.bracket)
        

    return render_template("tournament/tournament.html", t=t)
    