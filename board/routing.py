# board/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 这里的路径要和前端连接的路径一致
    re_path(r'ws/chat/$', consumers.ChatConsumer.as_asgi()),
]