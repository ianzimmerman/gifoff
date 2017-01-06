from functools import wraps

from flask import abort, flash
from flask_security import current_user

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


