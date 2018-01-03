import json
import threading
import time
import requests

from .rabbit import get_connection
from . conf import settings
from . misc import NPArrayEncoder


class LogsBufferWatcher(threading.Thread):
    """ Watcher's passed pipe's buffer age and then flushes once it's mature. """

    def __init__(self, logs_pipe, buffer_age):
        super(LogsBufferWatcher, self).__init__()
        self.logs_pipe = logs_pipe
        self.buffer_age = buffer_age
        self.is_stop = threading.Event()

    def stop(self):
        self.is_stop.set()

    def stopped(self):
        return self.is_stop.isSet()

    def run(self):
        while not self.stopped():
            self.logs_pipe.flush()
            time.sleep(self.buffer_age)


class RabbitPipe(object):
    """
    Callable that broadcasts data to specified
    queue, exchange and channel number.
    """

    def __init__(self, rabbit_conn, exchange_name, queue_name=None,
        exchange_type='fanout', routing_key='', channel_number=None,
        buffer_age=0, pre_hooks=[], post_hooks=[], publish_conditions=[],
        donotflush=False):

        self.buffer = []
        self.publish_conditions = publish_conditions
        self.pre_hooks = pre_hooks
        self.post_hooks = post_hooks
        self.buffer_lock = threading.Lock()
        self.buffer_age = buffer_age
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.routing_key = routing_key
        self.channel = rabbit_conn.channel(channel_number=channel_number)
        self.channel.exchange_declare(exchange=self.exchange_name,
                                      exchange_type=self.exchange_type)
        self.donotflush = donotflush

        # only create queue and bind to exchange if queue_name is present
        if self.queue_name:
            self.channel.queue_declare(queue=self.queue_name)
            self.channel.queue_bind(exchange=self.exchange_name,
                                    routing_key=self.routing_key,
                                    queue=self.queue_name)

        # if buffered, create watcher
        self.buffer_watcher = None
        if self.buffer_age > 0:
            self.buffer_watcher = LogsBufferWatcher(self, self.buffer_age)
            self.buffer_watcher.start()

    def __call__(self, data):
        """ Whenever the instance is called, buffer or broadcast data. """

        if not self._must_buffer() and self._can_publish():
            self.flush(data)
        else:
            self.buffer_lock.acquire()
            self.buffer.append(data)
            self.buffer_lock.release()

    def _must_buffer(self):
        """Only buffer if there's indefinite buffer (-1) or aging buffer w/ a watcher
        """
        return self.buffer_age == -1 or (self.buffer_watcher and self.buffer_age > 0)

    def _can_publish(self):
        """Check non-timing related conditions that must be true before the buffer
        can be flushed and published.
        """
        if self.publish_conditions:
            return all(cond(self.buffer) for cond in self.publish_conditions)
        else:
            return True

    def close(self):
        if self.buffer_watcher:
            self.buffer_watcher.stop()
            self.buffer_watcher.join()

    def flush(self, last_data=None):
        if last_data:
            self.buffer.append(last_data)
        if not self.buffer:
            return

        size = len(self.buffer)
        data = ''.join(self.buffer[0:size])
        self._publish(data)

        # then slice the published data
        if not self.donotflush:
            self.buffer_lock.acquire()
            self.buffer = self.buffer[size:]
            self.buffer_lock.release()

        #TODO refactor this to prevent the unnecessary buffer slice for null
        #     initial buffer ^^^
        # BUT: the line `if not self.buffer:` will catch falsy buffer ^^^

    def _publish(self, data):
        pre_data = reduce(lambda a, func: func(a), self.pre_hooks, data)
        self.channel.basic_publish(exchange=self.exchange_name,
                                   routing_key=self.routing_key,
                                   body=pre_data)
        reduce(lambda a, func: func(a), self.post_hooks, data)


class RabbitReporterMixin(object):
    """ Report mixin that publishes stats to RabbitMQ. """

    def initialize_stats_reporter(self, channel_number=None):
        """ Creates channel and exchange to which stats will be published. """
        conn = get_connection()
        self.report_pipe = RabbitPipe(rabbit_conn=conn,
                                      exchange_name='livestats',
                                      channel_number=channel_number)

    def stats_publish(self, payload):
        """ Publishes stats payload. """
        self.report_pipe(payload)


def logs_transformer(model_id):
    """ Returns decorated function that returns json string of the logs. """

    def _transformer(data):
        return json.dumps({'modelId': model_id, 'data': data})
    return _transformer


def logs_saver(model_id):
    logs_saver.is_new = True
    def _saver(data):
        payload = {
            'model': model_id,
            'data': data,
            'is_new': logs_saver.is_new,
            'worker_key': settings.WORKER_KEY
        }
        url = '%s/api/logs/' % settings.API_SERVER
        requests.post(url, json.dumps(payload, cls=NPArrayEncoder))
        logs_saver.is_new = False
    return _saver


def build_train_pipe(ensemble_id, model_id, buffer_age=2):
    routing_key = 'ensemble.%d.model.%d' % (ensemble_id, model_id)
    pre_hooks = [logs_transformer(model_id)]
    post_hooks = [logs_saver(model_id)]
    return RabbitPipe(get_connection(),
                      exchange_name='training_logs',
                      exchange_type='topic',
                      routing_key=routing_key,
                      buffer_age=buffer_age,
                      pre_hooks=pre_hooks,
                      post_hooks=post_hooks)
