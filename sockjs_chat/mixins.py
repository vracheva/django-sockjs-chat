from __future__ import unicode_literals, print_function

import json

import tornadoredis

client = tornadoredis.Client()
client.connect()


class SocketMixin(object):
    def subscribe(self, msg):
        self.client.subscribers[self.user_id][self] += 1
        if not self.channels.has_public_channel(self.user_id):
            # add user's friends to channel list
            self.channels.lpush(self.user_id, self.get_friends_list())
        else:
            # get all user's channel and subscribe to them
            rooms = self.channels.lget('channels-{}'.format(self.user_id))
            for room in rooms:
                self.client.subscribe(room)
        self.send_status_message('active')

    def send_status_message(self, status):
        """
        Broadcast message on status was changed
        :param status: active / inactive
        :return: {"type": <status>, "users": [<list of friends users>]}
        """
        broadcasters = []
        active_users = []

        # get list active connections
        for user in self.channels.lget(self.user_id):
            if self.client.subscribers.get(user):
                broadcasters.extend(self.client.subscribers.get(user).keys())
                active_users.append(user)
        if broadcasters:
            self.broadcast(broadcasters, json.dumps({'type': status, 'users': [self.user_id]}))
            self.send(json.dumps({'type': status, 'users': active_users}))

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
