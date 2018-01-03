from __future__ import absolute_import
import os
from celery import Celery
from celery.utils.log import get_task_logger


app = Celery('dmworker')
config = os.environ.get('DMWORKER_SETTINGS', 'dmworker.settings.local')
app.config_from_object(config)
settings = app.conf
settings.DMWORKER_WORKING_DIR.mkdir()
log = get_task_logger('dmworker')
print '\n', '!' * 80, '\nUsing bucket: %s\n' % app.conf.AWS_S3_BUCKET, '!' * 80
