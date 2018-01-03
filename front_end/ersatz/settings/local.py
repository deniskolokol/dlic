from .base import *

DEBUG = True
TEMPLATE_DEBUG = True

EMAIL_HOST = 'localhost'
EMAIL_PORT = '1025'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

ADMINS = ()
S3_REDIRECT_URL = "http://localhost:8000/uploaded/"
ALLOWED_HOSTS = ('localhost',)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'ersatz',                      # Or path to database file if using sqlite3.
        'USER': 'ersatz',                      # Not used with sqlite3.
        'PASSWORD': 'ija9fj432ertuerthjfsa',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

MIDDLEWARE_CLASSES += ('debug_panel.middleware.DebugPanelMiddleware', )
INTERNAL_IPS = ('127.0.0.1', )
INSTALLED_APPS += ('debug_toolbar', 'debug_panel',)

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

STRIPE_SECRET_KEY = 'sk_test_3ydNNDQAsTejKB8nHcYY0swh'
STRIPE_PUBLIC_KEY = 'pk_test_I1LGN0g9i2VnLRZXzPtoi6xJ'
INTERCOM_API_SECRET = 'xkF4yLJu-Ve2XnexH0NLvQLR-C8PAUrxOnWo-ov3'

DMWORKER_REMOTE_ADDRESSES = ('127.0.0.1', )
DMWORKER_CALLBACK_URL = 'http://127.0.0.1:8000'

WS_SERVER_URL = 'http://127.0.0.1:8887/sockjs'

SOCKET_URL = 'localhost:4000'
