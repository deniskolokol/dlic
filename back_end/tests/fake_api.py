import threading
import SimpleHTTPServer
import SocketServer
from contextlib import contextmanager
from collections import namedtuple
import json
from ersatz.conf import get_api_port


Call = namedtuple('Call', 'path body')


class ServerHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
        SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        length = int(self.headers['content-length'])
        data = self.rfile.read(length)
        self.server.calls.append(Call(self.path, data))
        response = self.server.responses.get(self.path)
        if response is None:
            response = self.server.responses.get('default')
        if response is None:
            self.send_error('Path %s is not specified and you don\'t set '
                            'default response' % self.path)
        if callable(response):
            response = response(self.path, data, self)
        self.wfile.write(response)


class TCPServer(SocketServer.TCPServer):
    allow_reuse_address = True
    timeout = 1

    def __init__(self, calls, responses, *args, **kwargs):
        self.calls = calls
        self.responses = responses
        SocketServer.TCPServer.__init__(self, *args, **kwargs)


def api_worker(stop_event, port, calls, responses):
    httpd = TCPServer(calls, responses, ("", port), ServerHandler)

    print "serving at port", port
    while not stop_event.is_set():
        httpd.handle_request()
    httpd.server_close()


@contextmanager
def fake_api(port, responses=None, default_response=None):
    stop_event = threading.Event()
    stop_event.clear()
    calls = []
    responses = responses if responses is not None else {}
    if default_response is not None:
        responses['default'] = default_response
    t = threading.Thread(target=api_worker, args=(stop_event, port,
                                                  calls, responses))
    t.start()
    try:
        yield calls
    finally:
        stop_event.set()
        t.join()


def default_fake_api():
    return fake_api(port=get_api_port(),
                    default_response=json.dumps({'status': 'success'}))


