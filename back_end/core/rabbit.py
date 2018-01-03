import pika

from .conf import settings


def get_connection():
    """ Returns a blocking RabbitMQ connection. """
    credentials = pika.PlainCredentials(
        settings.BROKER_USER,
        settings.BROKER_PASSWORD)
    conn_params = pika.ConnectionParameters(
        settings.BROKER_HOST,
        settings.BROKER_PORT,
        settings.BROKER_VHOST,
        credentials,
        connection_attempts=3)
    return pika.BlockingConnection(conn_params)
