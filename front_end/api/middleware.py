import logging


class LoggingMiddleware(object):
    def __init__(self):
        self.logger = logging.getLogger('api.request')

    def process_response(self, request, response):
        path = request.get_full_path()
        if response.status_code >= 400 and \
           path.startswith('/api') and \
           hasattr(response, 'data'):
            self.logger.warn(
                '%s %s %s --- RESPONSE: %s' %
                (request.method, path, response.status_code, response.data)
            )
        return response
