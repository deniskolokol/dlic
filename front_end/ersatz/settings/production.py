import os
from .base import *

S3_BUCKET = 'ersatz1dat'

STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

DMWORKER_REMOTE_ADDRESSES = ('54.83.131.56', )
DMWORKER_CALLBACK_URL = 'http://api.ersatzlabs.com'
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

CAMPAIGNMONITOR_KEY = '2b980b45dac8fd0c8712add8f7306c6d'
CAMPAIGNMONITOR_LIST = 'ba3c28e505739a763ca9299d283c4619'

SOCKET_URL = '54.187.68.192:4000'

PRODUCTION = True
