from django.urls import re_path

from main.consumer import Consumer

websocket_urlpatterns = [
    re_path(r'ws/watch/bch/(?P<address>[\w+:]+)/$', Consumer.as_asgi()),
    re_path(r'ws/watch/slp/(?P<address>[\w+:]+)/$', Consumer.as_asgi()),
    re_path(r'ws/watch/slp/(?P<address>[\w+:]+)/(?P<tokenid>[\w+]+)/', Consumer.as_asgi()),
]

