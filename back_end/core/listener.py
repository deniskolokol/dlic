import time
import json
from multiprocessing import Process
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosed
from . import get_logger
from .conf import settings


log = get_logger('ersatz.listener')


class Consumer(object):
    def __init__(self, default_queue=None):
        self.queue = default_queue
        self.credentials = pika.PlainCredentials(settings.BROKER_USER,
                                                 settings.BROKER_PASSWORD)
        self.parameters = pika.ConnectionParameters(settings.BROKER_HOST,
                settings.BROKER_PORT, settings.BROKER_VHOST, self.credentials)
        self.connection = None
        self._create_connection()
        self._create_channel()
        log.info('Consumer for queue %s created.' % default_queue)

    def _create_connection(self):
        print 'PIKA: creating connection to a rabbitmq server'
        while True:
            try:
                self.connection = pika.BlockingConnection(self.parameters)
                print 'PIKA: Connected to the queue server'
                return self.connection
            except AMQPConnectionError:
                print "PIKA: Cant't connect to the queue server"
                time.sleep(5)

    def _create_channel(self):
        #print 'PIKA: creating channel to a rabbitmq server'
        while True:
            try:
                self.channel = self.connection.channel()
                return
            except Exception as e:
                print ("PIKA: cant't create channel: %s" % e)
                self.close()
                self._create_connection()

    def _check_up_state(self):
        while self.channel.is_closed or self.channel.is_closing:
            self._create_channel()

    def check_stop_message(self, queue=None, seconds_wait=0):
        _, _, body = self.get_message_wait(queue, seconds_wait)
        return body == 'STOP'

    def get_message_wait(self, queue=None, seconds_wait=None):
        timer = 0
        queue = queue or self.queue
        if not queue:
            raise ValueError('Queue not defined')
        method_frame = header_frame = body = None
        while True:
            self._check_up_state()
            try:
                method_frame, header_frame, body = self.channel.basic_get(
                        queue, no_ack=True)
            except (AMQPConnectionError, AMQPChannelError):
                pass
            except ConnectionClosed:
                print "PIKA: disconnected"
                self._create_connection()
                self._create_channel()

            if method_frame:
                return method_frame, header_frame, json.loads(body)
            if seconds_wait is not None and timer >= seconds_wait:
                return None, None, None
            time.sleep(1)
            timer += 1

    def close(self):
        log.info('Consumer exiting...')
        try:
            self.connection.close()
        except Exception:
            pass


class ApiListener(object):
    def __init__(self, runners, queue='train'):
        self.runners = runners
        self.consumer = Consumer(default_queue=queue)

    def loop(self):
        log.info('Listening for new api messages.')
        run_in_subprocess = settings.RUN_IN_SUBPROCESS
        while True:
            for runner, queue in self.runners:
                method_frame, _, body = self.consumer.get_message_wait(
                        queue=queue, seconds_wait=1)
                if method_frame:
                    # TODO replace it with pool which can run several
                    # job at once
                    if run_in_subprocess:
                        p = Process(target=runner, args=(body,))
                        p.start()
                        while p.is_alive():
                            time.sleep(1)
                        p.join()
                    else:
                        runner(body)
                    log.info('Listening for new api messages.')

    def close(self):
        self.consumer.close()
