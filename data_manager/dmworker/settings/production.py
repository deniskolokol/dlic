from .base import *

BROKER_URL = 'amqp://ersatz:ija9fj432ertuerthjfsa@54.187.68.192:5672/dmworker'

AWS_S3_BUCKET = 'ersatz1dat'

API_HOST = 'http://api.ersatzlabs.com/'

CELERYBEAT_SCHEDULE['run-api-status-check-every-60-seconds']['args'] = (
    API_HOST.strip('/') + DMWORKER_COLLECT_URL_PATH,
)
