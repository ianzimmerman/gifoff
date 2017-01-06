from functools import wraps

from flask import abort, flash
from flask_security import current_user
from inflection import parameterize
from werkzeug.routing import BaseConverter

from .models import db


def access_required(func):
    """ This decorator ensures that the current user is logged in before calling the actual view.
        Calls the unauthorized_view_function() when the user is not logged in."""

    @wraps(func)
    def decorated_view(*args, **kwargs):
        # User must be authenticated
        if not current_user.has_role('ADMIN'):
            if not current_user.is_user(kwargs.get('id')):
                # Redirect to unauthenticated page
                abort(401)

        # Call the actual view
        return func(*args, **kwargs)

    return decorated_view

def admin_required(func):
    """ This decorator ensures that the current user is logged in before calling the actual view.
        Calls the unauthorized_view_function() when the user is not logged in."""

    @wraps(func)
    def decorated_view(*args, **kwargs):
        # User must be authenticated
        if not current_user.is_admin(kwargs.get('id')):
            # Redirect to unauthenticated page
            abort(401)

        # Call the actual view
        return func(*args, **kwargs)

    return decorated_view

def add_app_url_map_converter(self, func, name=None):
    """
    Register a custom URL map converters, available application wide.

    :param name: the optional name of the filter, otherwise the function name
                 will be used.
    """

    def register_converter(state):
        state.app.url_map.converters[name or func.__name__] = func

    self.record_once(register_converter)


class IDSlugConverter(BaseConverter):
    """Matches an int id and optional slug, separated by "/".

    :param attr: name of field to slugify, or None for default of str(instance)
    :param length: max length of slug when building url
    """

    regex = r'-?\d+(?:/[\w\-]*)?'

    def __init__(self, map, attr='name', length=80):
        self.attr = attr
        self.length = int(length)
        super(IDSlugConverter, self).__init__(map)

    def to_python(self, value):
        id, slug = (value.split('/') + [None])[:2]
        return int(id)

    def to_url(self, value):
        raw = str(value) if self.attr is None else getattr(value, self.attr, '')
        slug = parameterize(raw)[:self.length].rstrip('-')
        return '{}/{}'.format(value.id, slug).rstrip('/')
