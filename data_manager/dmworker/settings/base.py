from datetime import timedelta
from unipath import Path
from kombu import Queue


CELERY_RESULT_BACKEND = 'amqp'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'America/Dawson'
CELERY_ENABLE_UTC = True
CELERYD_CONCURRENCY = 1

CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = (
    Queue('default',    routing_key='task.#'),
    Queue('parser', routing_key='parse.#'),
)
CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
CELERY_DEFAULT_ROUTING_KEY = 'task.default'
CELERY_ROUTES = {
        'dmworker.tasks.parse': {
            'queue': 'parser',
            'routing_key': 'parse.datafile',
        },
}


DMWORKER_PROJECT_DIR = Path(__file__).ancestor(2)
DMWORKER_MAX_DISK_USAGE = 1024 * 1024 * 1024 * 5  # 5Gb
DMWORKER_WORKING_DIR = DMWORKER_PROJECT_DIR.child('data')
DMWORKER_MAX_BYTES_IN_ONE_LINE = 1024 * 1024 * 100  # 100MB

DMWORKER_SINGLE_FILE_EXT = ('.ts', '.ts.gz', '.ts.bz', '.ts.bz2',
                            '.csv', '.csv.gz', '.csv.bz', '.csv.bz2')
DMWORKER_ARCHIVE_EXT = ('.tar.gz', '.tar.bz', '.tar.bz2', '.zip')
DMWORKER_IMAGES_EXT = ('.jpeg', '.jpg', '.bmp', '.png')
DMWORKER_TIMESERIES_EXT = ('.ts')
DMWORKER_GENERAL_EXT = ('.csv')
DMWORKER_COMPRESS_EXT = ('.ts', '.csv')
DMWORKER_VERSION = 3
DMWORKER_PROCCESS_NOTIFY_INTERVAL = 20
DMWORKER_NOTIFY_URL_PATH = '/data/parse-notify/'
DMWORKER_COLLECT_URL_PATH = '/data/parse-collect/'


AWS_ACCESS_KEY = 'AKIAJ2Z5C7C2QXRNFX5Q'
AWS_SECRET_KEY = '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'

CELERYBEAT_SCHEDULE = {
    'run-api-status-check-every-60-seconds': {
        'task': 'dmworker.tasks.api_post',
        'schedule': timedelta(seconds=60),
    },
}
