from __future__ import unicode_literals, print_function

import json
import uuid

import redis
import sockjs.tornado
import tornadoredis
import tornadoredis.client
import tornadoredis.pubsub


# Create synchronous redis client to publish messages to a channel
from sockjs_chat.mixins import SocketMixin

client = tornadoredis.Client()
client.connect()


class Channel(object):
    _instance = None
    time = 60 * 60 * 24

    def __new__(cls, *args):
        if not cls._instance:
            cls._instance = super(Channel, cls).__new__(cls, *args)
        return cls._instance

    def __init__(self):
        self.redis_connection = redis.StrictRedis(host=client.connection.host, port=client.connection.port)

    def ltrim(self, key):
        return self.redis_connection.ltrim(key, -1, 0)

    def lrem(self, key, value):
        return self.redis_connection.lrem(key, 0, value)

    def lpush(self, key, value):
        """
        clear key if not used
        """
        self.redis_connection.lpush(key, *value)
        self.redis_connection.expire(key, self.time)

    def lget(self, key):
        self.redis_connection.expire(key, self.time)
        return set(self.redis_connection.lrange(key, 0, -1))

    def get_channel(self, user_id, users, channel=None):
        rooms = self.lget('channels-{}'.format(user_id))
        users = set(users)
        if channel and channel in rooms:
            return channel
        for room in rooms:
            if self.lget(room) == users:
                return room
        return str(uuid.uuid4())

    def has_public_channel(self, user_id):
        return bool(self.lget(user_id))

    def update(self, key, value):
        self.ltrim(key)
        self.lpush(key, value)


class BaseSockJSHandler(SocketMixin, sockjs.tornado.SockJSConnection):
    client = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())
    user_id = None
    channels = Channel()

    def on_message(self, message):
        msg = json.loads(message)
        action = getattr(self, msg.get('type'), None)
        action and action(msg)

    def on_close(self):
        self.client.subscribers[self.user_id][self] -= 1
        if self.client.subscribers[self.user_id][self] <= 0:
            del self.client.subscribers[self.user_id][self]
        self.send_status_message('inactive')

    def invite(self, msg):
        """
        Create room if not exists and subscribe users.
        Unsubscribe users who not in users msg["users"].
        :param msg: {
          "users": [<user_id>, <user_id>]
          "type": "invite",
          "room": <room>
        }
        """
        users = msg['users'] + [self.user_id]
        room = self.channels.get_channel(self.user_id, users, msg.get('room'))

        # unsubscribe users
        _users = self.channels.lget(room)
        unsub_users = _users - set(users)
        if unsub_users:
            broadcasters = []
            unsub_msg = json.dumps({'type': 'unsubscribe', 'users': list(unsub_users), 'room': room})
            client.publish(room, unsub_msg)
            for user in unsub_users:
                self.channels.lrem(room, user)
                if self.client.subscribers.get(user):
                    sub = self.client.subscribers.get(user).keys()[0]
                    broadcasters.append(sub)
                    self.client.subscribers[room][sub] = 0
                    self.client.unsubscribe(room, sub)
            self.broadcast(broadcasters, unsub_msg)

        self.channels.update(room, users)
        self.channels.lpush('channels-{}'.format(self.user_id), [room])
        # subscribe new users
        for user in set(users) - _users:
            self.channels.lpush('channels-{}'.format(user), [room])
            if self.client.subscribers.get(user):
                self.client.subscribe(room, self.client.subscribers.get(user).keys()[0])

        self.send_invite_message(room, users)

    def message(self, msg):
        """
        Publish and save message
        :param msg: {
            "room": <channel>
            "type": "message"
            "message": <message>
          }
        :return: {
           "type": "message",
           "users": <list of channel users>
           "message": <message>
        }
        """

        room = msg['room']
        if room in self.channels.lget('channels-{}'.format(self.user_id)):
            message = msg['message']
            client.publish(room, json.dumps({'type': 'message',
                                             'users': list(self.channels.lget(room)),
                                             'message': message, 'room': room}))
            self.save_message(msg['message'], self.channels.lget(msg['room']))

    def send_invite_message(self, room, users):
        self.send(json.dumps({'type': 'invite', 'room': room, 'users': users}))



    def save_message(self, message, users):
        raise NotImplementedError

    def get_friends_list(self):
        raise NotImplementedError


# # for debug
# import tornado.web
# import tornado.ioloop
#
#
# class SockJSHandler(BaseSockJSHandler):
#     def save_message(self, message, users):
#         pass
#
#     def get_friends_list(self):
#         return range(1, 6)
#
#
# class Application(tornado.web.Application):
#
#     def __init__(self):
#         handlers = [
#             (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
#         ] + sockjs.tornado.SockJSRouter(SockJSHandler, '/websocket').urls
#
#         tornado.web.Application.__init__(self, handlers)
#
#
# def main():
#     application = Application()
#     application.listen(8080)
#     tornado.ioloop.IOLoop.instance().start()
#
#
# if __name__ == '__main__':
#     main()
