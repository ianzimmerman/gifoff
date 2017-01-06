from flask_wtf import Form
from wtforms import TextField, HiddenField, StringField, FileField, BooleanField, \
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
