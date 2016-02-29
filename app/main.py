from __future__ import unicode_literals, print_function

# Run this with
# PYTHONPATH=. DJANGO_SETTINGS_MODULE=testsite.settings testsite/tornado_main.py
# Serves by default at
# http://localhost:8080/hello-tornado and
# http://localhost:8080/hello-django
import json
import urllib
# from django.contrib.auth import SESSION_KEY
import redis
from django.contrib.auth.models import User
# from django.contrib.sessions.models import Session
import uuid

import tornadoredis
import tornadoredis.pubsub
import tornadoredis.client
from tornado.options import options, define
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.wsgi
import tornado.websocket
import tornado.escape
import tornado.gen
import tornado.httpclient
import sockjs.tornado
from app.models import Message

from redis_collections import Dict


define('port', type=int, default=8080)

# Create synchronous redis client to publish messages to a channel
client = tornadoredis.Client()
client.connect()


#
# class WebSocketHandler(tornado.websocket.WebSocketHandler):
#     subscriber = tornadoredis.pubsub.BaseSubscriber(tornadoredis.Client())
#     user_id = None
#     channels = {}  # todo store to redis
#
#     def __init__(self, *args, **kwargs):
#         self.room = 'chat'
#         super(WebSocketHandler, self).__init__(*args, **kwargs)
#         self.listen()
#
#     def check_origin(self, origin):
#         return True
#
#     @tornado.gen.coroutine
#     def listen(self):
#         yield tornado.gen.Task(self.subscriber.redis.subscribe, self.room)
#         self.subscriber.redis.listen(self.on_message)
#         self.subscriber.subscribers[self.room][self] += 1
#
#     def on_message(self, msg):
#         # message = msg
#         # if isinstance(msg, unicode):
#         #     msg = json.loads(msg)
#         #     if 'type' in msg:
#         #         # self.client.unsubscribe(str(self.room))
#         #         self.room = str(msg['type'])
#         #         self.client.subscribe(self.room)
#         #         return
#         #
#         #     rooms = map(lambda x: int(x['value']), filter(lambda x: x['name'] == 'to_users', msg))
#         #     rooms.append(filter(lambda x: x['name'] == 'user', msg)[0]['value'])
#         #     rooms.sort()
#         #     for room in rooms:
#         #         self.application.c.publish(room, msg)
#         #     self.save_message(message)
#         #     return
#
#
#         if msg.kind == 'message':
#             self.write_message(str(msg.body))
#         elif msg.kind == 'subscribe':
#             self.user_id = unicode(msg.body)
#             # add user's friends to channel list
#             self.channels['public-{}'.format(self.user_id)] = self.get_friends_list()
#
#             self.subscriber.subscribe('public-{}'.format(self.user_id), self)
#             self.send_status_message('active')
#             print('%%%%%%%%%%%%%%555')
#
#         elif msg.kind == 'disconnect':
#             # Do not try to reconnect, just send a message back
#             # to the client and close the client connection
#             self.write_message('The connection terminated '
#                                'due to a Redis server error.')
#             self.close()
#
#     def on_close(self):
#         print('#############################')
#         if self.subscriber.redis.subscribed:
#             self.subscriber.redis.unsubscribe(self.room)
#             self.subscriber.redis.disconnect()
#
#     def get_friends_list(self):
#         return [range(1, 6)]
#
#     def send_status_message(self, status):
#         broadcasters = []
#         active_users = []
#         # get list active connections
#         for room in self.channels['public-{}'.format(self.user_id)]:
#             print(self.subscriber.subscribers)
#             if self.subscriber.subscribers.get('public-{}'.format(room)):
#                 broadcasters.extend(self.subscriber.redis.subscribers.get('public-{}'.format(room)).keys())
#                 active_users.append(room)
#         if broadcasters:
#             print('!!!!!!!!!!!!!!11')
#             self.ws_connection.broadcast(broadcasters, json.dumps({'type': status, 'users': [self.user_id]}))
#             self.write_message(json.dumps({'type': status, 'users': active_users}))


class Channel(object):
    _instance = None

    def __new__(cls, *args):
        if not cls._instance:
            cls._instance = super(Channel, cls).__new__(cls, *args)
        return cls._instance

    def __init__(self):
        self.redis_connection = redis.StrictRedis(host=client.connection.host, port=client.connection.port)

    def get(self, key):
        return self.redis_connection.lrange(key, 0, -1)

    def set(self, key, value):
        self.redis_connection.lpush(key, value)

    def pop(self, key):
        return self.redis_connection.rpop(key)


class SockJSHandler(sockjs.tornado.SockJSConnection):
    subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())
    user_id = None
    channels = Channel()

    def get_channel(self, users):
        for room, u in self.channels.items():
            if set(u) == set(users):
                return room.replace('private-', '')
        return str(uuid.uuid4())

    def on_message(self, message):
        msg = json.loads(message)

        if msg.get('type') == 'subscribe':
            self.user_id = unicode(msg['user'])
            # add user's friends to channel list
            self.channels.set('public-{}'.format(self.user_id), list(User.objects.all()
                                                                   .exclude(pk=self.user_id)
                                                                   .values_list('pk', flat=True)))

            self.subscriber.subscribe('public-{}'.format(self.user_id), self)
            self.send_status_message('active')
        elif msg.get('type') == 'invite':
            users = msg['users'] + [self.user_id]
            room = self.get_channel(users)
            self.channels.set('private-{}'.format(room), users)
            for user in users:
                if self.subscriber.subscribers.get('public-{}'.format(user)):
                    self.subscriber.subscribe('private-{}'.format(room),
                                              self.subscriber.subscribers.get('public-{}'.format(user)).keys()[0])

            self.send_invite_message(room, users)
        elif msg.get('type') == 'message':
            message = msg['message']
            room = msg['room']

            client.publish('private-{}'.format(room), json.dumps({'type': 'message',
                                                                  'users': self.channels.get('private-{}'.format(room)),
                                                                  'message': message, 'room': room}))
            self.save_message(msg)

    def on_close(self):
        print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        self.subscriber.unsubscribe('public-{}'.format(self.user_id), self)
        self.send_status_message('inactive')
        self.channels.pop('public-{}'.format(self.user_id))

    def send_invite_message(self, room, users):
        self.send(json.dumps({'type': 'invite', 'room': room, 'users': users}))

    def save_message(self, msg):
        message = Message.objects.create(
            user_id=self.user_id,
            message=msg['message']
        )
        message.to_users.add(*self.channels.get('private-{}'.format(msg['room'])))

    def send_status_message(self, status):
        broadcasters = []
        active_users = []

        # get list active connections
        for room in self.channels.get('public-{}'.format(self.user_id)):
            if self.subscriber.subscribers.get('public-{}'.format(room)):
                broadcasters.extend(self.subscriber.subscribers.get('public-{}'.format(room)).keys())
                active_users.append(room)
        if broadcasters:
            self.broadcast(broadcasters, json.dumps({'type': status, 'users': [self.user_id]}))
            self.send(json.dumps({'type': status, 'users': active_users}))
#
#
# class Application(tornado.web.Application):
#
#     def __init__(self):
#         handlers = [
#             (r'/websocket/(.*)', WebSocketHandler),
#             (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
#         ]
#         #  + sockjs.tornado.SockJSRouter(SockJSHandler, '/websocket').urls
#
#         tornado.web.Application.__init__(self, handlers)
#
#
# def main():
#     application = Application()
#     application.listen(options.port)
#     tornado.ioloop.IOLoop.instance().start()
#
#
# if __name__ == '__main__':
#     main()
