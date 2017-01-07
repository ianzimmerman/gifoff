from datetime import datetime, timedelta
from flask_wtf import Form

import requests
from wtforms import HiddenField, StringField, BooleanField, \
    SelectField, SelectMultipleField, TextAreaField, SubmitField, DateTimeField, validators


from .models import db, User


def validate_url(self, field):
    r = requests.get(field.data)
    if r.status_code != 200:
        raise validators.ValidationError('URL is unreachable.')
    if 'gif' not in r.headers['content-type']:
        raise validators.ValidationError('URL is not a gif.')



# class EmailForm(Form):
#     audit_id = HiddenField('Audit ID', [validators.DataRequired('No Audit ID Detected')])
#     email = StringField('New User', [validators.InputRequired('Email Required'), validate_email])
#     button = SubmitField('Add Access')

class GroupForm(Form):
    name = StringField('Name', [validators.DataRequired('Name Required'), validators.Regexp(r'^[a-zA-Z0-9 -+]+$')])
    description = TextAreaField('Description', [validators.Optional()])
    pin = StringField('Access PIN', [validators.DataRequired('PIN Required'), validators.NumberRange(0,999999)])

class PromptForm(Form):
    prompt = StringField('Prompt', [validators.DataRequired('prompt Required'), validators.Regexp(r'^[a-zA-Z0-9 -+?!]+$')])

class ChallengeForm(Form):
    name = StringField('Name', [validators.DataRequired('Name Required'), validators.Regexp(r'^[a-zA-Z0-9 -+]+$')])
    description = TextAreaField('Description', [validators.Optional()])
    start_time = DateTimeField('Start Time', [validators.DataRequired('Please Choose Start Time')], format='%Y-%d-%m %H:%M')
    end_time = DateTimeField('End Time', [validators.DataRequired('Please Choose End Time')], format='%Y-%d-%m %H:%M')
    

class ChallengeEntry(Form):
    url = StringField('URL', validators=[validate_url, validators.DataRequired('Please Enter a value')])
    prompt_id = HiddenField()
    entry_id = HiddenField()