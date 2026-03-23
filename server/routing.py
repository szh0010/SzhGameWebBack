# server/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
import game.routing
import board.routing

# 合并两个 App 的路由列表
combined_websocket_urlpatterns = game.routing.websocket_urlpatterns + board.routing.websocket_urlpatterns

# 注意：这里我们只导出路径列表，供 asgi.py 使用