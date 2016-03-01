from __future__ import unicode_literals

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import CreateView

from app.models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('message',)


class IndexView(LoginRequiredMixin, CreateView):
    template_name = 'base.html'
    form_class = MessageForm

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['users'] = User.objects.all().exclude(pk=self.request.user.pk)
        context['form'] = MessageForm()
        return context
