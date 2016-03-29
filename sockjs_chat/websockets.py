from __future__ import unicode_literals, print_function

import tornado.websocket

import tornado.web
import tornado.ioloop
import tornadoredis
import tornado.gen

from sockjs_chat.main import Channel
from sockjs_chat.mixins import SocketMixin


class WebSockHandler(SocketMixin, tornado.websocket.WebSocketHandler):
    channels = Channel()

    def __init__(self, *args, **kwargs):
        super(WebSockHandler, self).__init__(*args, **kwargs)
        self.listen()

    def check_origin(self, origin):
        return True

    @tornado.gen.engine
    def listen(self):
        self.client = tornadoredis.Client()
        self.client.connect()
        yield tornado.gen.Task(self.client.subscribe, 'test_channel')
        self.client.listen(self.on_message)

    def on_message(self, msg):
        if msg.kind == 'message':
            self.write_message(str(msg.body))
        if msg.kind == 'disconnect':
            # Do not try to reconnect, just send a message back
            # to the client and close the client connection
            self.write_message('The connection terminated '
                               'due to a Redis server error.')
            self.close()

    def open(self, *args, **kwargs):
        super(WebSockHandler, self).open(*args, **kwargs)
        self.subscribe(kwargs)

    @tornado.gen.coroutine
    def broadcast(self, clients, message):
        count = 0
        for client in clients:
            client.write_message(message)
            count += 1
            if count % 100 == 0:
                yield tornado.gen.moment




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
