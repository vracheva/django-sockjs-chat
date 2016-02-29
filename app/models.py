from __future__ import unicode_literals, print_function

from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Message(models.Model):
    user = models.ForeignKey(User)
    to_users = models.ManyToManyField(User, related_name='messages')
    message = models.TextField()

    def __unicode__(self):
        return '{} - {}'.format(self.user, self.message)
