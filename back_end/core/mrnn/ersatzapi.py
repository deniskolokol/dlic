import requests
import json
import numpy as np
API_SERVER='http://api.ersatz1.com'

class NPArrayEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)

def api_post(slug, params):
    try:
        response = requests.post(API_SERVER + slug,
                                 json.dumps(params, cls=NPArrayEncoder))
    except requests.ConnectionError:
        print 'Api server not available'
    return response


def api_get(slug, params={}):
    try:
        response = requests.get(API_SERVER + slug, params=params)
    except requests.ConnectionError:
        print 'Api server not available'
    return response


def predict(key, models, input_data=None):
    ngmodels = []
    if models:
        if isinstance(models, dict):
            for model, iteration in models.iteritems():
                ngmodels.append({'id': model, 'iteration': iteration})
        elif isinstance(models[0], int):
            for model in models:
                ngmodels.append({'id': model})
    else:
        return None
    if input_data:
        response = api_post('/api/predict/',
                {'models': ngmodels, 'input_data': input_data, 'key': key})
    else:
        response = api_post('/api/ensemble/run/',
                {'models': ngmodels, 'key': key})
    content = json.loads(response.content)
    return content


def results(key, predict_id):
    response = api_get('/api/predict/',
            {'ensemble': predict_id, 'key': key})
    content = json.loads(response.content)
    return content

