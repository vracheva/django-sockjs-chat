from __future__ import unicode_literals, print_function

import json
import uuid

import redis
import sockjs.tornado
import tornadoredis
import tornadoredis.client
import tornadoredis.pubsub


# Create synchronous redis client to publish messages to a channel
client = tornadoredis.Client()
client.connect()


class Channel(object):
    _instance = None

    def __new__(cls, *args):
        if not cls._instance:
            cls._instance = super(Channel, cls).__new__(cls, *args)
        return cls._instance

    def __init__(self):
        self.redis_connection = redis.StrictRedis(host=client.connection.host, port=client.connection.port)

    def ltrim(self, key):
        return self.redis_connection.ltrim(key, 0, -1)

    def lrem(self, key, value):
        return self.redis_connection.lrem(key, 0, value)

    def lpush(self, key, value):
        self.redis_connection.lpush(key, *value)

    def lget(self, key):
        return set(self.redis_connection.lrange(key, 0, -1))

    def get_channel(self, user_id, channel=None):
        rooms = self.lget('channels-{}'.format(user_id))
        if channel and channel in rooms:
            return channel
        users = self.lget('public-{}'.format(user_id))
        for room in rooms:
            if self.lget('private-{}'.format(room)) == users:
                return room.replace('private-', '')
        return str(uuid.uuid4())

    def has_public_channel(self, user_id):
        return bool(self.lget('public-{}'.format(user_id)))


class BaseSockJSHandler(sockjs.tornado.SockJSConnection):
    subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())
    user_id = None
    channels = Channel()

    def on_message(self, message):
        msg = json.loads(message)
        getattr(self, msg.get('type'), None)(msg)

    def on_close(self):
        self.subscriber.unsubscribe('public-{}'.format(self.user_id), self)
        self.send_status_message('inactive')

    def subscribe(self, msg):
        self.user_id = unicode(msg['user'])
        self.subscriber.subscribe('public-{}'.format(self.user_id), self)
        if not self.channels.has_public_channel(self.user_id):
            # add user's friends to channel list
            self.channels.lpush('public-{}'.format(self.user_id), self.get_friends_list())
        else:
            rooms = self.channels.lget('channels-{}'.format(self.user_id))
            for room in rooms:
                self.subscriber.subscribe('private-{}'.format(room), self)
        self.send_status_message('active')

    def invite(self, msg):
        users = msg['users'] + [self.user_id]
        room = self.channels.get_channel(self.user_id, msg.get('channel'))

        # unsubscribe users
        old_users = self.channels.lget('private-{}'.format(room))
        for user in old_users - set(users):
            self.channels.lrem('private-{}'.format(room), user)
            if self.subscriber.subscribers.get('public-{}'.format(user)):
                self.subscriber.unsubscribe('private-{}'.format(room),
                                            self.subscriber.subscribers.get('public-{}'.format(user)).keys()[0])

        self.channels.ltrim('private-{}'.format(room))
        self.channels.lpush('private-{}'.format(room), users)
        self.channels.lpush('channels-{}'.format(self.user_id), [room])
        for user in users:
            self.channels.lpush('channels-{}'.format(user), [room])
            if self.subscriber.subscribers.get('public-{}'.format(user)):
                self.subscriber.subscribe('private-{}'.format(room),
                                          self.subscriber.subscribers.get('public-{}'.format(user)).keys()[0])

        self.send_invite_message(room, users)

    def message(self, msg):
        message = msg['message']
        room = msg['room']
        client.publish('private-{}'.format(room), json.dumps({'type': 'message',
                                                              'users': list(self.channels.lget('private-{}'.format(room))),
                                                              'message': message, 'room': room}))
        self.save_message(msg['message'], self.channels.lget('private-{}'.format(msg['room'])))

    def send_invite_message(self, room, users):
        self.send(json.dumps({'type': 'invite', 'room': room, 'users': users}))

    def send_status_message(self, status):
        broadcasters = []
        active_users = []

        # get list active connections
        for room in self.channels.lget('public-{}'.format(self.user_id)):
            if self.subscriber.subscribers.get('public-{}'.format(room)):
                broadcasters.extend(self.subscriber.subscribers.get('public-{}'.format(room)).keys())
                active_users.append(room)
        if broadcasters:
            self.broadcast(broadcasters, json.dumps({'type': status, 'users': [self.user_id]}))
            self.send(json.dumps({'type': status, 'users': active_users}))

    def save_message(self, message, users):
        raise NotImplementedError

    def get_friends_list(self):
        raise NotImplementedError


# class Application(tornado.web.Application):
#
#     def __init__(self):
#         handlers = [
#             (r'/websocket/(.*)', WebSocketHandler),
#             (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
#         ]
#         #  + sockjs.tornado.SockJSRouter(BaseSockJSHandler, '/websocket').urls
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
