import json
import time
import requests
from . misc import NPArrayEncoder
from . conf import settings
from . import get_logger


log = get_logger('ersatz.api')

def post(slug, params):
    params['worker_key'] = settings.WORKER_KEY
    while True:
        try:
            response = requests.post(settings.API_SERVER + slug,
                                     json.dumps(params, cls=NPArrayEncoder))
            log.debug(response.text)
            break
        except requests.ConnectionError:
            time.sleep(2)
            log.critical('Api server not available, trying again')
    return True if response.status_code == 200 else False


def get(slug, params={}, server=None):
    params['worker_key'] = settings.WORKER_KEY
    server = server or settings.API_SERVER
    while True:
        try:
            response = requests.get(server + slug, params=params)
            break
        except requests.ConnectionError:
            pass
    if response.status_code == 200:
        try:
            data = json.loads(response.text)
        except (ValueError, TypeError):
            return {'status': 'fail'}
        return data
    return {'status': 'fail'}


def rest_patch(slug, data):
    while True:
        try:
            response = requests.post(settings.API_SERVER + slug + '?worker_key=' + settings.WORKER_KEY,
                                     json.dumps(data, cls=NPArrayEncoder))
            log.debug(response.text)
            break
        except requests.ConnectionError:
            time.sleep(2)
            log.critical('Api server not available, trying again')
    return True if response.status_code == 200 else False
