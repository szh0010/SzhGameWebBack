import os
import django
from django.core.asgi import get_asgi_application

# 1. 必须最先设置环境变量
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

# 2. 手动初始化 Django (解决 ImproperlyConfigured 的核心，确保 Daphne 正常启动)
django.setup()

# 3. 在 setup 之后导入 Channels 相关组件
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

# 4. 导入刚才创建的总路由模块
import server.routing  

application = ProtocolTypeRouter({
    # 处理普通 HTTP 请求
    "http": get_asgi_application(),
    
    # 处理 WebSocket 请求
    "websocket": AuthMiddlewareStack(
        URLRouter(
            # 使用 server/routing.py 中合并后的路由列表
            server.routing.combined_websocket_urlpatterns
        )
    ),
})