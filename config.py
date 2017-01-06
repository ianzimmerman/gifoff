import os

DEBUG   = int(os.environ.get("DEBUG", True))
TESTING = int(os.environ.get("TESTING", False))
HOST    = os.environ.get("HOST", 'localhost')
PORT    = int(os.environ.get("PORT", 5000))

# Use a secure, unique and absolutely secret key for
# signing the data.
CSRF_SESSION_KEY = os.getenv('CSRF_SESSION_KEY', '')

# Secret key for signing cookies
SECRET_KEY = os.getenv('SECRET_KEY', '')

# Dev DB
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', '')
SQLALCHEMY_TRACK_MODIFICATIONS = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)

# Flask-Mail settings
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', '')
MAIL_SERVER = os.getenv('MAIL_SERVER', '')
MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
MAIL_USE_SSL = int(os.getenv('MAIL_USE_SSL', True))

# app settings
APP_NAME = os.getenv('APP_NAME', '')
APP_ADMIN = os.getenv('APP_ADMIN', '')
APP_EMAIL = os.getenv('APP_EMAIL', '')
APP_PASSWORD = os.getenv('APP_PASSWORD', '')

SECURITY_PASSWORD_HASH = os.getenv('SECURITY_PASSWORD_HASH', 'bcrypt')
SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT', '')
SECURITY_EMAIL_SENDER = os.getenv('SECURITY_EMAIL_SENDER', 'no-reply@localhost')
SECURITY_REGISTERABLE = os.getenv('SECURITY_REGISTERABLE', True)
SECURITY_CONFIRMABLE = os.getenv('SECURITY_CONFIRMABLE', True)
SECURITY_RECOVERABLE = os.getenv('SECURITY_RECOVERABLE', True)

GOOGLE_SITE_VERIFICATION = os.getenv('GOOGLE_SITE_VERIFICATION', '')
GOOGLE_ANALYTICS = os.getenv('GOOGLE_ANALYTICS', '')

print('Production Config Loaded.')