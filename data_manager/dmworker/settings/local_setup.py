from .base import *
from unipath import Path


BROKER_URL = 'amqp://ersatz:ija9fj432ertuerthjfsa@127.0.0.1:5672/dmworker'
LOCAL_SETUP = True
MEDIA_ROOT = Path('/home/wtf/git/ersatz/media/')  # change to api MEDIA path
S3_ROOT = MEDIA_ROOT.child('s3')

AWS_S3_BUCKET = 'ersatzlabs'

API_HOST = 'http://127.0.0.1:8000/'

CELERYBEAT_SCHEDULE['run-api-status-check-every-60-seconds']['args'] = (
    API_HOST.strip('/') + DMWORKER_COLLECT_URL_PATH,
)
