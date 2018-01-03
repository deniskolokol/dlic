import datetime as dt
from urlparse import urlparse
from .app import app, settings


class Notify(object):
    def __init__(self, task_id, url):
        pr = urlparse(url)
        self.url = pr.scheme + '://' + pr.netloc + \
            settings.DMWORKER_NOTIFY_URL_PATH
        self.task_id = task_id

    def send(self, msg):
        timestamp = dt.datetime.utcnow().isoformat()
        data = {'task_id': self.task_id, 'msg': msg, 'timestamp': timestamp}
        app.send_task('dmworker.tasks.api_post', args=(self.url, data))

    def admin_send(self, msg):
        pass
