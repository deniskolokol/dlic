import os
from .base import *


ALLOWED_HOSTS = ('54.86.111.206', '127.0.0.1', 'localhost')

S3_BUCKET = 'ersatz1dat'

STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")

DMWORKER_REMOTE_ADDRESSES = ('127.0.0.1', '54.86.111.206')
DMWORKER_CALLBACK_URL = 'http://54.86.111.206'

SOCKET_URL = '54.86.111.206:4000'
