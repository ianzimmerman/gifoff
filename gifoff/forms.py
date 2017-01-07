from flask_wtf import Form
from wtforms import HiddenField, StringField, BooleanField, \
    SelectField, SelectMultipleField, TextAreaField, SubmitField, validators


from .models import db, User


# def validate_email(self, field):
#     if not db.session.query(db.func.count(User.id)).filter_by(email=field.data).scalar():
#         raise validators.ValidationError('Email not registered.')
# 
# 
# class EmailForm(Form):
#     audit_id = HiddenField('Audit ID', [validators.DataRequired('No Audit ID Detected')])
#     email = StringField('New User', [validators.InputRequired('Email Required'), validate_email])
#     button = SubmitField('Add Access')

class GroupForm(Form):
    name = StringField('Name', [validators.DataRequired('Name Required'), validators.Regexp(r'^[\w.@+-]+$')])
    description = TextAreaField('Description', [validators.Optional()])
    pin = StringField('Access PIN', [validators.DataRequired('PIN Required'), validators.NumberRange(0,999999)])
    

class ChallengeEntry(Form):
    url = StringField('URL', validators=[validators.URL('Please enter a valid URL'), validators.DataRequired('Please Enter a value')])
    prompt_id = HiddenField()
    entry_id = HiddenField()