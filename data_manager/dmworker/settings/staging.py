from .base import *

BROKER_URL = 'amqp://ersatz:ija9fj432ertuerthjfsa@localhost:5672/dmworker'

AWS_S3_BUCKET = 'ersatz1dat'

API_HOST = 'http://54.86.111.206/'

CELERYBEAT_SCHEDULE['run-api-status-check-every-60-seconds']['args'] = (
    API_HOST.strip('/') + DMWORKER_COLLECT_URL_PATH,
)
