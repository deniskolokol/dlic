import requests
from boto.exception import BotoClientError, BotoServerError
from celery.exceptions import SoftTimeLimitExceeded
from .app import app, log, settings
from .notify import Notify
from .aws import delete_key
from .exception import ApiResponseNotOk


@app.task(bind=True, time_limit=121*60, soft_time_limit=120*60, max_retries=3)
def parse(self, key, callback_url, api_file=None):
    import parser
    notify = Notify(self.request.id, callback_url)
    try:
        result = parser.run(key, notify, api_file=api_file)
        api_post.apply_async(kwargs={'url': callback_url, 'retry': True}, countdown=1)
        return result
    except SoftTimeLimitExceeded as e:
        notify.send('Timeout, stop job')
        api_parse_collect(countdown=2)
        raise e
    except (BotoClientError, BotoServerError) as e:
        msg = 'Sorry, error occure, will try to repeat after 3 minutes.'
        notify.send(msg)
        notify.admin_send('AWS ERROR: %s' % e.message)
        log.error(msg)
        raise self.retry(exc=e, countdown=60*2)
    except Exception as e:
        log.critical(e.message)
        notify.admin_send('parse raised: %s' % e.message)
        notify.send('Sorry, parser terminated with error, '
                    'we will fix it and reply to you, thanks!')
        api_parse_collect(countdown=2)
        raise e


@app.task(ignore_result=True)
def delete(key, callback_url):
    delete_key(key)
    api_post.apply_async(kwargs={'url': callback_url, 'retry': True}, countdown=1)


@app.task(bind=True, max_retries=3, ignore_result=True)
def delete_not_compressed(self, key):
    try:
        delete_key(key)
    except (BotoClientError, BotoServerError) as e:
        self.retry(exc=e, countdown=60*60)


@app.task(bind=True, max_retries=100, ignore_result=True)
def api_post(self, url, data=None, retry=False):
    try:
        response = requests.post(url, data=data)
        if response.status_code not in (200, 404):
            log.error('Api response has status %s' % response.status_code)
            raise ApiResponseNotOk(response.text)
    except (requests.exceptions.RequestException, ApiResponseNotOk) as exc:
        if retry:
            raise self.retry(exc=exc, countdown=60*5)
        log.error('Can\'t connect to api: %s' % exc.message)


def api_parse_collect(countdown=1):
    url = settings.API_HOST.strip('/') + settings.DMWORKER_COLLECT_URL_PATH
    api_post.apply_async(kwargs={'url': url}, countdown=countdown)
