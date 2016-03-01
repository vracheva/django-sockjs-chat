from __future__ import unicode_literals, print_function

from django.conf import settings
from django.db import models


class Message(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    to_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='messages')
    message = models.TextField()
    created = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return '{} - {}'.format(self.user, self.message)
