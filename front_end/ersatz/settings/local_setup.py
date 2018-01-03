import os
from .base import *

S3_BUCKET = 'ersatzlabs'  # should be changed to client company name
DEBUG = True
LOCAL_SETUP = True
S3_ROOT = MEDIA_ROOT.child('s3')
WS_SERVER_URL = 'http://127.0.0.1:8887/sockjs'
ALLOWED_HOSTS = ('*', )

EMAIL_HOST = 'localhost'
EMAIL_PORT = '1025'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''


STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

DMWORKER_REMOTE_ADDRESSES = ('127.0.0.1', )
DMWORKER_CALLBACK_URL = 'http://127.0.0.1:8000'
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

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
