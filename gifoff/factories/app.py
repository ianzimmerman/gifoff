import os

from flask import Flask


def create_app():
    APP_PATH = os.path.dirname(os.path.realpath(__file__))
    BASE_PATH = os.path.abspath(os.path.join(APP_PATH, os.pardir))

    app = Flask(__name__,
                instance_path=os.path.join(BASE_PATH, 'instance'),
                instance_relative_config=True,
                template_folder=os.path.join(BASE_PATH, 'templates'),
                static_folder=os.path.join(BASE_PATH, 'static')
                )

#     class ReverseProxied(object):
#         def __init__(self, app):
#             self.app = app
# 
#         def __call__(self, environ, start_response):
#             scheme = environ.get('HTTP_X_FORWARDED_PROTO')
#             if scheme:
#                 environ['wsgi.url_scheme'] = scheme
#             return self.app(environ, start_response)
# 
# 
#     app.wsgi_app = ReverseProxied(app.wsgi_app)

    # default config
    app.config.from_object('config')

    # local config outside git /instance/config.py
    app.config.from_pyfile('config.py', silent=True)

    from ..models import db
    db.app = app
    db.init_app(app)

    from ..cache import cache
    cache.init_app(app)

    from flask_mail import Mail
    mail = Mail(app)  # Initialize Flask-Mail

    from flask_jsglue import JSGlue
    jsglue = JSGlue(app)

    # import blueprints
    from ..blueprints.main.controllers import main
    app.register_blueprint(main)

    db.create_all()

    # Setup Flask-Security
    from ..security import security, create_admin, ExtendedConfirmRegisterForm, ExtendedRegisterForm
    security.init_app(app,
                      register_form=ExtendedRegisterForm,
                      confirm_register_form=ExtendedConfirmRegisterForm
                      )

    # IF NO ADMIN USER INIT DB WITH VALUE FROM CONFIG
    with app.app_context():
        create_admin(app, db, security.datastore)

    # Flask-Admin
    from ..admin import admin
    admin.init_app(app)

    return app
