from datetime import datetime, timedelta
from flask import current_app
from flask_wtf import Form

import requests
from wtforms import HiddenField, StringField, IntegerField, BooleanField, \
    SelectField, SelectMultipleField, TextAreaField, SubmitField, DateTimeField, validators


from .models import db, get_count, User, Group, Challenge


def validate_url(self, field):
    try:
        r = requests.get(field.data)
    except:
        raise validators.ValidationError('URL is unreachable.')
    
    if r.status_code != 200:
        raise validators.ValidationError('URL is unreachable.')
    
    if 'gif' not in r.headers['content-type']:
        raise validators.ValidationError('URL is not a gif.')
    
def number_range(min, max):
    
    def _range(form, field):
        if field.data < min or field.data > max:
            raise validators.ValidationError('Max Players should be in range {} to {}'.format(min, max))
    
    return _range

def unique_name(model):
    message = 'Name must be unique.'

    def _name_count(form, field):
        count = get_count(model, name=field.data)
        if count > 0:
            raise validators.ValidationError(message)

    return _name_count


class GroupForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=30, message="Length: 1-30 characters"), unique_name(Group)])
    description = TextAreaField('Description', [validators.Length(max=140, message="Max Length is 140 characters"), validators.Optional()])

class PromptForm(Form):
    prompt = StringField('Add Prompt', [validators.Length(min=1, max=140, message="Length: 1-140 characters")])

class ChallengeForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=30, message="Length: 1-30 characters")])
    description = TextAreaField('Description', [validators.Length(max=140, message="Max Length is 140 characters"), validators.Optional()])
    judge_id = SelectField('Judge', [validators.DataRequired('Please choose a judge.')], coerce=int, choices=[])
    date_range = StringField('Active Times (US/PACIFIC)', [validators.DataRequired('Please Choose a Date Range')])
    # utc_end_time = DateTimeField('End Time', [validators.DataRequired('Please Choose End Time')], format='%Y-%m-%d %H:%M')
    

class ChallengeEntry(Form):
    url = StringField('URL', validators=[validate_url, validators.DataRequired('Please Enter a value')])
    prompt_id = HiddenField()
    entry_id = HiddenField()

class TournamentForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=30, message="Length: 1-30 characters")])
    description = TextAreaField('Description', [validators.Length(max=140, message="Max Length is 140 characters"), validators.Optional()])
    
    max_players = IntegerField('Max Players', [number_range(2, 64)])
    
    public_entry = BooleanField('Allow Public Entry')
    public_voting = BooleanField('Allow Public Voting')
    
    active = BooleanField('Active')
    
    entry_time = IntegerField('Entry Period (in hours)', [number_range(1, 24)])
    voting_time = IntegerField('Voting Period (in hours)', [number_range(1, 24)])
    