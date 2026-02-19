# game/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 比如：ws://127.0.0.1:8000/ws/game/房间号/
    re_path(r'ws/game/(?P<room_name>\w+)/$', consumers.GameConsumer.as_asgi()),
]