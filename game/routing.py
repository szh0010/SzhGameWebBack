# game/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 支持动态的 gameId 和 roomId
    # 比如：ws://127.0.0.1:8000/ws/game/gomoku/12345/
    re_path(r'ws/game/(?P<game_id>\w+)/(?P<room_id>\w+)/$', consumers.GameConsumer.as_asgi()),
]