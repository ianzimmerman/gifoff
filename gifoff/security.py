from flask_security import Security, SQLAlchemyUserDatastore, utils
from flask_security.forms import RegisterForm, ConfirmRegisterForm
from sqlalchemy import func
from wtforms import StringField, validators
from wtforms.validators import DataRequired, Regexp

from .models import db, db_commit, get_count, User, Role

user_datastore = SQLAlchemyUserDatastore(db, User, Role)

def unique_name(self, field):
    u = get_count(User, username=field.data)
    if u:
        raise validators.ValidationError('Name Taken.')

ext_reg = ('Username', [validators.Length(min=3, max=12, message="Length is 3-12 characters"), unique_name, Regexp(r'^[\w.@+-]+$', message="No special characters.")])

class ExtendedRegisterForm(RegisterForm):
    username = StringField(*ext_reg)


class ExtendedConfirmRegisterForm(ConfirmRegisterForm):
    username = StringField(*ext_reg)


def create_admin(app, db, user_datastore):
    
    if not user_datastore.get_user(app.config['APP_EMAIL']):

        admin_roles = ('ADMIN', 'SUPER_ADMIN')

        for role in admin_roles:
            user_datastore.find_or_create_role(name=role)

        user_datastore.create_user(username=app.config['APP_ADMIN'],
                                   email=app.config['APP_EMAIL'],
                                   password=utils.encrypt_password(app.config['APP_PASSWORD']),
                                   confirmed_at=db.func.current_timestamp()
                                   )
        if db_commit():
            for role in admin_roles:
                user_datastore.add_role_to_user(app.config['APP_EMAIL'], role)

            db_commit()

security = Security(datastore=user_datastore)
