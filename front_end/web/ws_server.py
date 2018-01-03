import json
import tornado.httpserver
import tornado.web
import tornado.websocket
import tornado.ioloop
import tornado.gen
import redis
import tornadoredis
import tornadoredis.pubsub
import sockjs.tornado
from django.core import signing
from django.conf import settings


# Use the synchronous redis client to publish messages to a channel
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD
)
# Create the tornadoredis.Client instance
# and use it for redis channel subscriptions
subscriber = tornadoredis.pubsub.SockJSSubscriber(
    tornadoredis.Client(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        selected_db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD
    )
)


class MessageHandler(sockjs.tornado.SockJSConnection):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.authenticated = None
        self.channel = None

    def on_open(self, request):
        self.authenticated = False
        self.channel = None

    def on_message(self, msg):
        print msg
        try:
            msg = json.loads(msg)
        except ValueError:
            self.send('Invalid JSON')
            return
        try:
            channel = signing.loads(
                msg['token'],
                key=settings.WS_SECRET_KEY,
                salt=msg['salt'])
        except (signing.BadSignature, KeyError):
            self.send('Token invalid')
            return
        self.authenticated = True
        self.channel = channel
        subscriber.subscribe([channel], self)
        print 'Client subscribed to channel %s' % channel

    def on_close(self):
        subscriber.unsubscribe(self.channel, self)


application = tornado.web.Application(
    sockjs.tornado.SockJSRouter(MessageHandler, '/sockjs').urls
)


def run():
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(settings.WS_PORT)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    run()
