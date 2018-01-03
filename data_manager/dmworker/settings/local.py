from .base import *

BROKER_URL = 'amqp://ersatz:ija9fj432ertuerthjfsa@localhost:5672/dmworker'

DMWORKER_PROCCESS_NOTIFY_INTERVAL = 2

AWS_S3_BUCKET = 'ersatz1test'

API_HOST = 'http://127.0.0.1:8000/'

CELERYBEAT_SCHEDULE['run-api-status-check-every-60-seconds']['args'] = (
    API_HOST.strip('/') + DMWORKER_COLLECT_URL_PATH,
)
