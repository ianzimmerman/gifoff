from datetime import datetime, timedelta
from random import randint
from collections import defaultdict, OrderedDict

import arrow
import trueskill
import json

from flask_security import UserMixin, RoleMixin
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import func, select, desc, and_
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

db = SQLAlchemy()

def db_commit():
    try:
        db.session.commit()
        return True
    except Exception as e:
        print('Database Commit Failed: {}'.format(e), 'alert')
        db.session.rollback()
        db.session.flush()
        return False

def get_count(model, **filters):
    # return q.with_entities([func.count()]).order_by(None).scalar()
    return db.session.query(func.count(model.id)).filter_by(**filters).scalar() or 0

def q_count(q):
    return q.count() or 0

    
class Base(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime, default=db.func.current_timestamp(),
                              onupdate=db.func.current_timestamp())

    @hybrid_method
    def get_or_create(self, **kwargs):
        instance = self.query.filter_by(**kwargs).first()
        if instance:
            return instance
        else:
            instance = self(**kwargs)
            db.session.add(instance)
            if db_commit():
                return instance
            else:
                return False


# User Classes


class User(Base, UserMixin):
    __tablename__ = "user"
    # User authentication information
    username = db.Column(db.String(250), nullable=True, unique=False)
    password = db.Column(db.String(250), nullable=False, server_default='')
    reset_password_token = db.Column(db.String(250), nullable=False, server_default='')

    # User email information
    email = db.Column(db.String(250), nullable=False, unique=True)
    confirmed_at = db.Column(db.DateTime())

    # User information
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))
    
    player_of = db.relationship('Group', secondary='group_players')
    author_of = db.relationship('Group', secondary='group_authors')
        
    @hybrid_method
    def group_entries(self, group):  
        return db.session.query(func.count(Entry.id)).filter(Entry.player_id==self.id).filter(Entry.prompt_id.in_(group.prompts)).scalar() or 0
    
    @hybrid_method
    def group_score(self, group):  
        this = db.session.query(func.sum(Entry.score)).filter(Entry.player_id==self.id).filter(Entry.prompt_id.in_(group.prompts))
        return round(this.scalar() or 0, 1)
    
    @group_score.expression
    def group_score(self, group):
        return select([func.sum(Entry.score)]).where(Entry.player_id==self.id).where(Entry.prompt_id.in_(group.prompts))
    
    @hybrid_method
    def group_wins(self, group):
        return q_count(db.session.query(Challenge).filter(Challenge.winner_id==self.id, Challenge.group_id==group.id))
    
    @group_wins.expression
    def group_wins(self, group):
        return select([func.count(Challenge.winner_id)]).where(Challenge.winner_id==self.id).where(Challenge.group_id==group.id)
    
    @hybrid_method
    def group_avg_score(self, group):
        return round(self.group_score(group)/(self.group_entries(group) or 1), 1)
    
    @hybrid_method
    def group_rating(self, group, challenge=None):
        rate_obj = db.session.query(FFARating)\
                             .filter(FFARating.player==self, FFARating.group==group)\
                             .order_by(FFARating.id.desc()).first()
        if rate_obj:
            return rate_obj.rating
        else:
            rate_obj = FFARating(player=self, group=group, challenge=challenge)
            rate_obj.rating = trueskill.Rating()
            if db_commit():
                return rate_obj.rating
            else:
                return False
    
    @hybrid_method
    def update_group_rating(self, challenge, rating):
        rate_obj = FFARating(player=self, group=challenge.group, challenge=challenge)
        rate_obj.rating = rating
        
        if db_commit():
            return rate_obj
        else:
            return False
    
    def __repr__(self):
        return '{}'.format(self.email)


class Group(Base):
    __tablename__ = 'group'
    owner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    owner = db.relationship('User', backref=db.backref('groups', lazy='dynamic', cascade='all, delete'))
    
    name = db.Column(db.String(250), nullable=False, unique=True)
    description = db.Column(db.String(250), nullable=True, unique=False)
    pin  = db.Column(db.String(250), nullable=False, unique=True)
    
    players = db.relationship('User', secondary='group_players')
    authors = db.relationship('User', secondary='group_authors')
    
    @hybrid_property
    def prompts(self):
        return [p.id for c in self.challenges for p in c.prompts if c.complete==True]
    
    @hybrid_property
    def active_count(self):
        return db.session.query(func.count(Challenge.id))\
                .filter(Challenge.winner_id==None, Challenge.group_id==self.id, Challenge.utc_end_time > arrow.utcnow().naive).scalar()
#     
#     @hybrid_property
#     def pending_count(self):
#         return db.session.query(func.count(Challenge.id)).filter(Challenge.pending==True, Challenge.group_id==self.id).scalar()
    
    @hybrid_property
    def incomplete_count(self):
        return db.session.query(func.count(Challenge.id)).filter(Challenge.winner_id==None, Challenge.group_id==self.id).scalar()
    
    @hybrid_property
    def last_winner(self):
        last_challenge = db.session.query(Challenge)\
                                   .filter(Challenge.group_id==self.id, Challenge.winner_id!=None)\
                                   .order_by(Challenge.id.desc()).first()
                                   
        if last_challenge:
            return last_challenge.winner
        else:
            return None
    
    @hybrid_property
    def player_ratings(self):
        q = db.session.query(FFARating)\
                      .filter(FFARating.group==group)\
                      .order_by(FFARating.id.desc()).first()
    
    @hybrid_method
    def leaders(self, top=None):
        sub_q = db.session.query(func.max(FFARating.id).label("max_id"))\
                          .filter(FFARating.group==self)\
                          .group_by(FFARating.player_id).subquery()
        
        q = db.session.query(FFARating)\
                      .filter(FFARating.group==self)\
                      .join(sub_q, and_(FFARating.id == sub_q.c.max_id))\
                      .order_by(FFARating._mu.desc())
        
        if top: q = q.limit(top)
        
        return q
    
    @hybrid_property
    def leaderboard(self):
        players = sorted([(p.username, p.id) for p in self.players], key=lambda player: player[0].lower())                
        
        results = {
            'cols': [{'id': 'c_id', 'label': 'Challenge ID', 'type': 'string'}]
                  + [{'id': 'p_id_{}'.format(p[1]), 'label': p[0], 'type': 'number'} for p in players],
            'rows': []
        }
        
        data = defaultdict(dict)
        challenges = dict()
        for r in db.session.query(FFARating).filter(FFARating.group==self):
            data[r.challenge_id][r.player_id] = r.mu
            if r.challenge: challenges[r.challenge_id] = r.challenge.name
        
        
        results['rows'].append({'c': [{'v': 'Baseline' }] + [{'v': 25.00} for p in players]})
        
        for c in self.challenges[-5:]:
            ds = data.get(c.id)
            if ds:
                results['rows'].append({'c': [{'v': c.name }] + [{'v': ds.get(p[1], None)} for p in players]})
        
        current_scores = {p.player.id: p.mu for p in self.leaders()}
        #print(current_scores)
        
        results['rows'].append({'c': [{'v': 'Current Standings' }] + [{'v': current_scores.get(p[1], None)} for p in players]})
        
        return json.dumps(results)
          
    def __repr__(self):
        return self.name
    

class Challenge(Base):
    __tablename__ = 'challenge'
    group_id = db.Column(db.Integer(), db.ForeignKey(Group.id))
    group = db.relationship('Group', backref=db.backref('challenges', lazy='dynamic', cascade='all, delete'))
    
    name = db.Column(db.String(250), nullable=False, unique=False)
    description = db.Column(db.String(250), nullable=True, unique=False)
    
    #always store UTC time
    utc_start_time = db.Column(db.DateTime())
    utc_end_time = db.Column(db.DateTime())
    
    author_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('authored', lazy='dynamic', cascade='all, delete'))
    
    judge_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    judge = db.relationship('User', foreign_keys=[judge_id], backref=db.backref('judged', lazy='dynamic', cascade='all, delete'))
    
    winner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    winner = db.relationship('User', foreign_keys=[winner_id], backref=db.backref('challenge_wins', lazy='dynamic', cascade='all, delete'))
    
    @hybrid_property
    def start_time(self):
        return arrow.get(self.utc_start_time)
    
    @hybrid_property
    def end_time(self):
        return arrow.get(self.utc_end_time)
        
    @hybrid_property
    def entry_count(self):
        return get_count(Entry, challenge_id=self.id)
    
#     @hybrid_property
#     def entry_count(self):
#         return get_count(Entry, challenge_id=self.id)
    
    @hybrid_property
    def complete(self):
        if self.winner_id:
            return True
        
        return False
    
    @hybrid_property
    def upcoming(self):
        if self.complete is False and arrow.utcnow() < self.start_time:
            return True
        
        return False
    
    @hybrid_property
    def pending(self):
        if self.complete is False and arrow.utcnow() > self.end_time:
            return True
        
        return False
    
    @hybrid_property
    def active(self):
        if True in (self.complete, self.pending, self.upcoming):
            return False
        
        return True
    
    @hybrid_property
    def status_tag(self):
        if self.upcoming:
            return ('<i class="fa fa-clock-o"></i> Starts {}'.format(self.starts_in), 'info')
        elif self.active:
            return ('<i class="fa fa-clock-o"></i> Ends {}'.format(self.time_left), 'warning')
        elif self.pending:
            return ('<i class="fa fa-gavel"></i> With {}'.format(self.judge.username), 'default')
        elif self.complete:
            return ('<i class="fa fa-check"></i> Complete', 'success')
        
        return False 
    
    @hybrid_property
    def time_left(self):
        if self.active or self.upcoming:
            return self.end_time.humanize()
        else:
            return None
    
    @hybrid_property
    def starts_in(self):
        if self.upcoming:
            return self.start_time.humanize()
        else:
            return None
    
    @hybrid_property
    def players(self):
        return [e.player for e in db.session.query(Entry).distinct(Entry.player_id).group_by(Entry.player_id).filter(Entry.challenge_id==self.id)]
    
    @hybrid_property
    def high_score(self):
        max_score = 0
        winners = list()
        for p in self.players:
            p_score = db.session.query(func.sum(Entry.score)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar()
            if p_score:
                if p_score > max_score:
                    max_score = p_score
                    winners = [p]
                elif p_score == max_score:
                    winners.append(p)
        
        dice = randint(0,len(winners)-1)
        
        return (round(max_score or 0,1), winners[dice])
    
    @hybrid_method
    def player_score(self, p):
        return round(db.session.query(func.sum(Entry.score)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar() or 0,1)
    
    @hybrid_method
    def player_status(self, p):
        entries = db.session.query(func.count(Entry.url)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar() or 0
        scored = db.session.query(func.count(Entry.score)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar() or 0
        
        return (entries, scored)
    
    def __repr__(self):
        return '{}'.format(self.name)
    
    
class Prompt(Base):
    __tablename__ = 'prompt'
    challenge_id = db.Column(db.Integer(), db.ForeignKey(Challenge.id))
    challenge = db.relationship('Challenge', backref=db.backref('prompts', lazy='dynamic', cascade='all, delete'))
    
    prompt = db.Column(db.String(250), nullable=False, unique=False)
    
    @hybrid_property
    def high_score(self):
        return db.session.query(Entry).with_entities(Entry.score).filter(Entry.prompt_id==self.id).order_by(Entry.score.desc()).first()[0]
        
    @hybrid_method
    def user_entry(self, user):
        return Entry.get_or_create(prompt_id=self.id, player=user)
    
    def __repr__(self):
        return '{} > {}'.format(self.challenge.name, self.prompt)
    
    
class Entry(Base):
    __tablename__ = 'entry'
    prompt_id = db.Column(db.Integer(), db.ForeignKey(Prompt.id))
    prompt = db.relationship('Prompt', backref=db.backref('entries', lazy='dynamic', cascade='all, delete'))
    
    player_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    player = db.relationship('User', backref=db.backref('entries', lazy='dynamic', cascade='all, delete'))
    
    url = db.Column(db.String(250), nullable=True, unique=False)
    score = db.Column(db.Float())
    
    challenge_id = association_proxy('prompt', 'challenge_id')
    
    def __repr__(self):
        return '{}: {}'.format(self.prompt_id, self.player.username)

class Tournament(Base):
    pass
#     __tablename__ = 'tournament'
#     
#     organizer_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     organizer = db.relationship('User', foreign_keys=[organizer_id], backref=db.backref('owned_tournaments', lazy='dynamic', cascade='all, delete'))  
#     
#     name = db.Column(db.String(250), nullable=False, unique=False)
#     description = db.Column(db.String(250), nullable=True, unique=False)
#     # pin  = db.Column(db.String(250), nullable=False, unique=True)
#     
#     max_players = db.Column(db.Integer(), nullable=False, default=64)
#     
#     public_entry = db.Column('has_public_entry', db.Boolean(), nullable=False, server_default='0')
#     public_voting = db.Column('has_public_voting', db.Boolean(), nullable=False, server_default='0')
#     
#     group_id = db.Column(db.Integer(), db.ForeignKey(Group.id))
#     group = db.relationship('Group', backref=db.backref('tournaments', lazy='dynamic', cascade='all, delete'))
#     
#     active = db.Column('is_active', db.Boolean(), nullable=False, server_default='0')
#     
#     bracket = db.Column(db.Text())
#     
#     winner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     winner = db.relationship('User', foreign_keys=[winner_id], backref=db.backref('tournament_wins', lazy='dynamic', cascade='all, delete'))
#     
#     entry_time = db.Column(db.Integer(), nullable=False, default=60*60*24) # length in seconds, default 1 day
#     voting_time = db.Column(db.Integer(), nullable=False, default=60*60*24) # length in seconds, default 1 day
#     
#     @hybrid_property
#     def full(self):
#         return q_count(self.players) >= self.max_players 
# 
#     def __repr__(self):
#         return self.name


class TournamentPlayers(Base):
    pass
#     __tablename__ = "tournament_players"
#     
#     tournament_id = db.Column(db.Integer(), db.ForeignKey('tournament.id', ondelete='CASCADE'))
#     tournament = db.relationship('Tournament', backref=db.backref('players', lazy='dynamic', cascade='all, delete'))
#     
#     player_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
#     player = db.relationship('User', backref=db.backref('tournaments', lazy='dynamic', cascade='all, delete'))
#     
#     seed = db.Column(db.Integer(), nullable=True)
#     
#     def __repr__(self):
#         return '{} ({})'.format(self.player.username, self.player.solo_rating or 0)

class TournamentRound(Base):
    pass
#     __tablename__ = 'tournament_round'
#     
#     tournament_id = db.Column(db.Integer(), db.ForeignKey('tournament.id', ondelete='CASCADE'))
# 
#     #always store UTC time
#     utc_entry_start_time = db.Column(db.DateTime())  
#     utc_vote_start_time = db.Column(db.DateTime())
    

    
class TournamentEntry(Base):
    pass
#     __tablename__ = 'tournament_entry'
#     
#     tournament_round_id = db.Column(db.Integer(), db.ForeignKey('tournament_round.id', ondelete='CASCADE'))
#     round = db.relationship('TournamentRound', backref=db.backref('entries', lazy='dynamic', cascade='all, delete'))
#     
#     player_one_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     player_one = db.relationship('User', foreign_keys=[player_one_id])
#     
#     player_two_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     player_two = db.relationship('User', foreign_keys=[player_two_id])
#     
#     player_one_entry = db.Column(db.String(250), nullable=True, unique=False)
#     player_two_entry = db.Column(db.String(250), nullable=True, unique=False)
#     
#     winner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     winner = db.relationship('User', foreign_keys=[winner_id])


class TournamentVote(Base):
    pass
#     __tablename__ = 'tournament_vote'
#     
#     tournament_entry_id = db.Column(db.Integer(), db.ForeignKey('tournament_entry.id', ondelete='CASCADE'))
#     
#     voter_id = db.Column(db.Integer(), db.ForeignKey(User.id))
#     voter = db.relationship('User', foreign_keys=[voter_id])
#     
#     player_one_score = db.Column(db.Float())
#     player_two_score = db.Column(db.Float())

class FFARating(Base):
    __tablename__ = 'ffa_rating'
    
    group_id = db.Column(db.Integer(), db.ForeignKey(Group.id))
    group = db.relationship('Group', backref=db.backref('ffa_ratings', lazy='dynamic', cascade='all, delete'))
    
    challenge_id = db.Column(db.Integer(), db.ForeignKey(Challenge.id))
    challenge = db.relationship('Challenge', backref=db.backref('ffa_ratings', lazy='dynamic', cascade='all, delete'))
    
    player_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    player = db.relationship('User', backref=db.backref('ffa_rating', lazy='dynamic', cascade='all, delete'))
    
    _mu = db.Column(db.Float(), nullable=False, default=25.000) #skill
    _sigma = db.Column(db.Float(), nullable=False, default=8.333) #certainty
    
    @hybrid_property
    def mu(self):
        return round(self._mu, 2)
    
    @mu.setter
    def mu(self, value):
        self._mu = value
        
    @hybrid_property
    def sigma(self):
        return round(self._sigma, 2)
    
    @sigma.setter
    def sigma(self, value):
        self._sigma = value
    
    @hybrid_property
    def rating(self):
        return trueskill.Rating(mu=self._mu, sigma=self._sigma)
    
    @rating.setter
    def rating(self, obj):
        self._mu = obj.mu
        self._sigma = obj.sigma
    
    def __repr__(self):
        return str(int(self.mu * 100))
    

class Rating(Base): # 1v1 rating
    __tablename__ = 'rating'
    player_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    player = db.relationship('User', backref=db.backref('solo_rating', uselist=False, cascade='all, delete'))
    
    _mu = db.Column(db.Float(), nullable=False, default=25.0) #skill
    _sigma = db.Column(db.Float(), nullable=False, default=8.333333333) #certainty
    
    @hybrid_property
    def mu(self):
        return round(self._mu, 2)
    
    @mu.setter
    def mu(self, value):
        self._mu = value
        
    @hybrid_property
    def sigma(self):
        return round(self._sigma, 2)
    
    @sigma.setter
    def sigma(self, value):
        self._sigma = value
    
    @hybrid_property
    def rating(self):
        return trueskill.Rating(mu=self._mu, sigma=self._sigma)
    
    @rating.setter
    def rating(self, obj):
        self.mu = obj.mu
        self.sigma = obj.sigma
    
    def __repr__(self):
        return str(int(self.mu * 100))

# Define Role model
class Role(Base, RoleMixin):
    __tablename__ = "role"
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '{}'.format(self.name)


# Helpers for Many to Many Relationship

# user relationships
class UserRoles(Base):
    __tablename__ = "user_roles"
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE'))
    
class GroupPlayers(Base):
    __tablename__ = "group_players"
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    group_id = db.Column(db.Integer(), db.ForeignKey('group.id', ondelete='CASCADE'))

class GroupAuthors(Base):
    __tablename__ = "group_authors"
    user_id = db.Column(db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE'))
    group_id = db.Column(db.Integer(), db.ForeignKey('group.id', ondelete='CASCADE'))