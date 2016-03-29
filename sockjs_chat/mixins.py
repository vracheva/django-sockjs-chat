from __future__ import unicode_literals, print_function

import json


class SocketMixin(object):
    def subscribe(self, msg):
        self.user_id = unicode(msg['user'])
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