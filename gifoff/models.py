from datetime import datetime, timedelta
from random import randint
from flask_security import UserMixin, RoleMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
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
    #return q.with_entities(func.count()).scalar()
    #return q.with_entities([func.count()]).order_by(None).scalar()
    return db.session.query(func.count(model.id)).filter_by(**filters).scalar() or 0
    
    
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
    
    def __repr__(self):
        return '{}'.format(self.email)


class Group(Base):
    __tablename__ = 'group'
    owner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    owner = db.relationship('User', backref=db.backref('groups', lazy='dynamic', cascade='all, delete'))
    
    name = db.Column(db.String(250), nullable=False, unique=True)
    description = db.Column(db.String(250), nullable=True, unique=False)
    pin  = db.Column(db.Integer(), nullable=False, unique=False)
    
    players = db.relationship('User', secondary='group_players')
    authors = db.relationship('User', secondary='group_authors')
    
    @hybrid_property
    def active_count(self):
        return len([c.id for c in self.challenges if c.active == True])
    
    @hybrid_property
    def pending_count(self):
        return len([c.id for c in self.challenges if c.pending == True])
    
    @hybrid_property
    def incomplete_count(self):
        return len([c.id for c in self.challenges if c.complete == False])
    
    @hybrid_property
    def last_winner(self):
        last_challenge = db.session.query(Challenge).filter(Challenge.group_id==self.id, Challenge.winner_id!=None).order_by(Challenge.id.desc()).first()
        if last_challenge:
            return last_challenge.winner
        else:
            return None
    
    def __repr__(self):
        return '{}'.format(self.name)
    

class Challenge(Base):
    __tablename__ = 'challenge'
    group_id = db.Column(db.Integer(), db.ForeignKey(Group.id))
    group = db.relationship('Group', backref=db.backref('challenges', lazy='dynamic', cascade='all, delete'))
    
    name = db.Column(db.String(250), nullable=False, unique=False)
    description = db.Column(db.String(250), nullable=True, unique=False)
    
    start_time = db.Column(db.DateTime(), default=datetime.now() + timedelta(minutes=10))
    end_time = db.Column(db.DateTime(), default=datetime.now() + timedelta(hours=4, minutes=10))
    
    author_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    author = db.relationship('User', foreign_keys=[author_id], backref=db.backref('authored', lazy='dynamic', cascade='all, delete'))
    
    judge_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    judge = db.relationship('User', foreign_keys=[judge_id], backref=db.backref('judged', lazy='dynamic', cascade='all, delete'))
    
    winner_id = db.Column(db.Integer(), db.ForeignKey(User.id))
    winner = db.relationship('User', foreign_keys=[winner_id], backref=db.backref('won', lazy='dynamic', cascade='all, delete'))
    
    @hybrid_property
    def entry_count(self):
        return get_count(Entry, challenge_id=self.id)
    
    @hybrid_property
    def complete(self):
        if self.winner_id:
            return True
        else:
            return False
    
    @hybrid_property
    def active(self):
        if self.complete or datetime.now() > self.end_time :
            return False
        elif datetime.now() < self.start_time:
            return False
        elif datetime.now() < self.end_time:
            return True
    
    @hybrid_property
    def pending(self):
        if self.complete is False and datetime.now() > self.end_time:
            return True
        else:
            return False
    
    @hybrid_property
    def upcoming(self):
        if self.complete is False and datetime.now() < self.start_time:
            return True
        else:
            return False
    
    @hybrid_property
    def status(self):
        if self.upcoming:
            return 'upcoming'
        elif self.active:
            return 'active'
        elif self.pending:
            return 'pending'
        elif self.complete:
            return 'complete'
        
        return False 
    
    @hybrid_property
    def time_left(self):
        if self.active or self.upcoming:
            left = (self.end_time - datetime.now()).total_seconds()
            return "{}h {}m".format(int(left//3600), int(left%3600//60))
        else:
            return None
    
    @hybrid_property
    def starts_in(self):
        if self.upcoming:
            left = (self.start_time - datetime.now()).total_seconds()
            return "{}h {}m".format(int(left//3600), int(left%3600//60))
        else:
            return None
    
    @hybrid_property
    def players(self):
        return [e.player for e in db.session.query(Entry).distinct(Entry.player_id).group_by(Entry.player_id).filter(Entry.challenge_id==self.id)]
    
    @hybrid_property
    def high_score(self):
        max_score = 0
        winner = None
        for p in self.players:
            p_score = db.session.query(func.sum(Entry.score)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar()
            if p_score:
                if p_score > max_score:
                    max_score = p_score
                    winner = p
                elif p_score == max_score:
                    coin = randint(0,1)
                    winner = [winner, p][coin]
        
        return (max_score, winner)
    
    @hybrid_method
    def player_score(self, p):
        return db.session.query(func.sum(Entry.score)).filter(Entry.challenge_id==self.id, Entry.player==p).scalar()
    
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
    score = db.Column(db.Integer())
    
    challenge_id = association_proxy('prompt', 'challenge_id')
    
    def __repr__(self):
        return '{}: {}'.format(self.prompt_id, self.player.username)



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