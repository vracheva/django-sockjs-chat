"""chat URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from channels import route
from django.conf.urls import include, url
from django.contrib import admin

from app.views import IndexView
from channels_example.app.consumers import ws_message, ws_add, ws_disconnect

urlpatterns = [
    url(r'^$', IndexView.as_view()),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('django.contrib.auth.urls')),

]

channel_routing = [
    route("websocket.receive", ws_message),
    route("websocket.connect", ws_add),
    route("websocket.disconnect", ws_disconnect),
]
