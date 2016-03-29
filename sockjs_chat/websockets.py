from __future__ import unicode_literals, print_function

import json
from collections import defaultdict, Counter

import tornado.websocket

import tornado.web
import tornado.ioloop
import tornadoredis
import tornado.gen

from sockjs_chat.main import Channel
from sockjs_chat.mixins import SocketMixin


class WebSockHandler(SocketMixin, tornado.websocket.WebSocketHandler):
    channels = Channel()
    user_id = None

    def check_origin(self, origin):
        return True

    def on_message(self, msg):
        print(msg)
        if isinstance(msg, unicode):
            return
        if msg.kind == 'disconnect':
            # Do not try to reconnect, just send a message back
            # to the client and close the client connection
            self.write_message('The connection terminated '
                               'due to a Redis server error.')
            self.close()
        elif msg.kind == 'subscribe':
            pass
        else:
            action = getattr(self, msg.kind, None)
            action and action(msg)

    @tornado.gen.engine
    def open(self, *args, **kwargs):
        self.user_id = kwargs['user']
        self.client = tornadoredis.Client()
        self.client.connect()
        yield tornado.gen.Task(self.client.subscribe, self.user_id)
        self.client.listen(self.on_message)
        self.client.subscribers = defaultdict(Counter)
        self.subscribe(kwargs)

    @tornado.gen.coroutine
    def broadcast(self, clients, message):
        count = 0
        for client in clients:
            client.write_message(message)
            count += 1
            if count % 100 == 0:
                yield tornado.gen.moment

    def send(self, msg):
        self.write_message(msg)

    def save_message(self, message, users):
        pass

    def get_friends_list(self):
        return range(1, 6)


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'/websocket/(?P<user>\d+)', WebSockHandler),
        ]

        tornado.web.Application.__init__(self, handlers)


def main():
    application = Application()
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
