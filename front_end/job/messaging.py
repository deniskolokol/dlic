#coding: utf-8
import logging
import json
from django.conf import settings
import pika
from django.core.cache import cache


logger = logging.getLogger(__name__)


def connect():
    credentials = pika.PlainCredentials(settings.BROKER_USER,
                                        settings.BROKER_PASSWORD)
    parameters = pika.ConnectionParameters(settings.BROKER_HOST,
                                           settings.BROKER_PORT,
                                           settings.BROKER_VHOST,
                                           credentials)
    return pika.BlockingConnection(parameters)


def queue_job(message, queue='train', durable=True, delivery_mode=2):
    message = json.dumps(message)
    try:
        connection = connect()
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=durable,
                              exclusive=False, auto_delete=False)
    except Exception as e:
        logger.error('RabbitMQ connection error while sending job: %s', e)
        return False
    try:
        properties = pika.BasicProperties(content_type='text/plain',
                                          delivery_mode=delivery_mode)
        channel.basic_publish(exchange='', routing_key=queue, body=message,
                              properties=properties)
    except Exception as e:
        logger.error('RabbitMQ error while sending job: %s', e)
        return False
    channel.close()
    connection.close()
    if queue == 'train':
        cache.delete('queue:%s:size' % queue)
    return True


def _get_queue_size(queue='train'):
    try:
        connection = connect()
        channel = connection.channel()
        result = channel.queue_declare(queue=queue, durable=True,
                                       exclusive=False, auto_delete=False,
                                       passive=True)
    except Exception as e:
        logger.error('RabbitMQ error while checking queue size: %s', e)
        return None
    return result.method.message_count


def get_queue_size(queue='train'):
    size = cache.get('queue:%s:size' % queue)
    if size is None:
        size = _get_queue_size(queue=queue)
        if size is not None:
            cache.set('queue:%s:size' % queue, size, 30)
    # return None if error
    return size
