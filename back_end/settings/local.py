from unipath import Path
API_SERVER = 'http://localhost:8000'
WORKER_KEY = 'uZ3uxJ6eaRxjTyX7uU1'
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "ersatz"
BROKER_PASSWORD = "ija9fj432ertuerthjfsa"
BROKER_VHOST = "ersatz"
AWS_ACCESS_KEY = "AKIAJ2Z5C7C2QXRNFX5Q"
AWS_SECRET_KEY = "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"
S3_BUCKET = 'ersatz1test'

LOGLEVEL = 'DEBUG'

PROJECT_DIR = Path(__file__).ancestor(2)
SPEARMINT = PROJECT_DIR.child('spearmint-lite')
CONVNET = PROJECT_DIR.child('convnet')
WORKING_DIR = PROJECT_DIR.child('work')
S3_CACHEDIR = WORKING_DIR.child('cache')
RUN_IN_SUBPROCESS = False
DATASET_VERSION = 2
