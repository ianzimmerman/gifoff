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

def get_count(q):
    return q.with_entities(func.count()).scalar()

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

    def __repr__(self):
        return '{}'.format(self.email)


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
