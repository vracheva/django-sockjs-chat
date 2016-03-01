from __future__ import unicode_literals, print_function

from django.contrib.auth import get_user_model

from app.models import Message
from sockjs_chat.main import BaseSockJSHandler


class SockJSHandler(BaseSockJSHandler):
    def get_friends_list(self):
        return list(get_user_model().objects.all().exclude(pk=self.user_id).values_list('pk', flat=True))

    def save_message(self, message, users):
        message = Message.objects.create(
            user_id=self.user_id,
            message=message
        )
        message.to_users.add(*users)
