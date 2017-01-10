from datetime import datetime, timedelta
from flask_wtf import Form

import requests
from wtforms import HiddenField, StringField, IntegerField, BooleanField, \
    SelectField, SelectMultipleField, TextAreaField, SubmitField, DateTimeField, validators


from .models import db, User


def validate_url(self, field):
    try:
        r = requests.get(field.data)
    except:
        raise validators.ValidationError('URL is unreachable.')
    
    if r.status_code != 200:
        raise validators.ValidationError('URL is unreachable.')
    
    if 'gif' not in r.headers['content-type']:
        raise validators.ValidationError('URL is not a gif.')



# class EmailForm(Form):
#     audit_id = HiddenField('Audit ID', [validators.DataRequired('No Audit ID Detected')])
#     email = StringField('New User', [validators.InputRequired('Email Required'), validate_email])
#     button = SubmitField('Add Access')

class GroupForm(Form):
    name = StringField('Name', [validators.DataRequired('Name Required')])
    description = TextAreaField('Description', [validators.Optional()])
    pin = IntegerField('Access PIN, A # to allow people to join your group.', [validators.DataRequired('PIN Required')])

class PromptForm(Form):
    prompt = StringField('Prompt', [validators.DataRequired('Prompt Required')])

class ChallengeForm(Form):
    name = StringField('Name', [validators.DataRequired('Name Required')])
    description = TextAreaField('Description', [validators.Optional()])
    judge_id = SelectField('Judge', [validators.DataRequired('Please choose a judge.')], coerce=int, choices=[])
    start_time = DateTimeField('Start Time', [validators.DataRequired('Please Choose Start Time')], format='%Y-%m-%d %H:%M')
    end_time = DateTimeField('End Time', [validators.DataRequired('Please Choose End Time')], format='%Y-%m-%d %H:%M')
    

class ChallengeEntry(Form):
    url = StringField('URL', validators=[validate_url, validators.DataRequired('Please Enter a value')])
    prompt_id = HiddenField()
    entry_id = HiddenField()