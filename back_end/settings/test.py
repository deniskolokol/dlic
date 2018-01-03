from unipath import Path
TEST_RUN = True
API_SERVER = 'http://localhost:8999'
WORKER_KEY = ''
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "ersatz_test"
BROKER_PASSWORD = "Jladsfw23421Jasdasd123sdasd"
BROKER_VHOST = "/ersatz_test"
AWS_ACCESS_KEY = "AKIAJ2Z5C7C2QXRNFX5Q"
AWS_SECRET_KEY = "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"
S3_BUCKET = 'ersatz1test'

LOGLEVEL = 'WARNING'

PROJECT_DIR = Path(__file__).ancestor(2)
SPEARMINT = PROJECT_DIR.child('spearmint-lite')
CONVNET = PROJECT_DIR.child('convnet')
WORKING_DIR = PROJECT_DIR.child('work', 'test')
S3_CACHEDIR = WORKING_DIR.child('cache')
RUN_IN_SUBPROCESS = True
DATASET_VERSION = 1
