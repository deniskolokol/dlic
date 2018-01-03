from unipath import Path
API_SERVER='http://127.0.0.1:8000'
WORKER_KEY='uZ3uxJ6eaRxjTyX7uU1'
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 5672
BROKER_USER = "ersatz"
BROKER_PASSWORD = "ija9fj432ertuerthjfsa"
BROKER_VHOST = "ersatz"
S3_BUCKET = 'ersatzlabs'

LOGLEVEL = 'INFO'

PROJECT_DIR = Path(__file__).ancestor(2)
SPEARMINT = PROJECT_DIR.child('spearmint-lite')
CONVNET = PROJECT_DIR.child('convnet')
WORKING_DIR = PROJECT_DIR.child('work')
S3_CACHEDIR = WORKING_DIR.child('cache')
RUN_IN_SUBPROCESS = True
DATASET_VERSION = 2

MEDIA_ROOT = Path('/home/wtf/git/ersatz/media')
S3_ROOT = MEDIA_ROOT.child('s3')
LOCAL_SETUP = True
