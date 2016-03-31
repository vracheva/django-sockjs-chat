from __future__ import unicode_literals, print_function

import json

import tornado.websocket
import tornado.web
import tornado.ioloop
import tornadoredis
import tornado.gen

from tornadoredis.pubsub import BaseSubscriber

from sockjs_chat.main import SocketMixin


class WebSocketSubscriber(tornadoredis.pubsub.BaseSubscriber):
    def on_message(self, msg):
        """Handle new message on the Redis channel."""
        if msg and msg.kind == 'message':
            try:
                message = json.loads(msg.body)
                sender = message['sender']
                message = message['message']
            except (ValueError, KeyError):
                message = msg.body
                sender = None
            subscribers = list(self.subscribers[msg.channel].keys())
            for subscriber in subscribers:
                if sender is None or sender != subscriber.uid:
                    try:
                        subscriber.write_message(message)
                    except tornado.websocket.WebSocketClosedError:
                        # Remove dead peer
                        self.unsubscribe(msg.channel, subscriber)
        super(WebSocketSubscriber, self).on_message(msg)


class WebSockHandler(SocketMixin, tornado.websocket.WebSocketHandler):
    client = WebSocketSubscriber(tornadoredis.Client())

    def check_origin(self, origin):
        return True

    @tornado.gen.coroutine
    def broadcast(self, clients, message):
        count = 0
        for client in clients:
            client.write_message(message)
            count += 1
            if count % 100 == 0:
                yield tornado.gen.moment

    # @tornado.gen.engine
    def open(self, *args, **kwargs):
        super(WebSockHandler, self).open(*args, **kwargs)
        # yield tornado.gen.Task(self.client.redis.subscribe, 'test_channel')
        # self.client.redis.listen(self.on_message)
        self.subscribe(kwargs)

    def send(self, msg):
        if self.ws_connection:
            self.write_message(msg)

    def save_message(self, message, users):
        pass

    def get_friends_list(self):
        return range(1, 6)

    def on_connection_close(self):
        self.client.subscribers[self.user_id][self] -= 1
        if self.client.subscribers[self.user_id][self] <= 0:
            del self.client.subscribers[self.user_id][self]
        self.send_status_message('inactive')
        super(WebSockHandler, self).on_connection_close()


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'/websocket/(?P<user>\d+)', WebSockHandler, {}, 'websocket'),
        ]

        tornado.web.Application.__init__(self, handlers)


def main():
    application = Application()
    application.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
