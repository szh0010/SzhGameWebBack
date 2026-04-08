# server/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# ---------------------------------------------------------
# 1. 环境变量设置
# ---------------------------------------------------------
# 必须在任何 Django 内部组件导入之前设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

# ---------------------------------------------------------
# 2. 手动初始化 Django
# ---------------------------------------------------------
# 这一步是修复 "AppRegistryNotReady" 错误的核心。
# 它确保了模型(Models)在被 WebSocket 消费者(Consumers)引用前已完全加载。
django.setup()

# ---------------------------------------------------------
# 3. 预加载 HTTP ASGI 应用
# ---------------------------------------------------------
# 这里的 django_asgi_app 负责处理所有标准的 REST API 和 HTTP 请求
django_asgi_app = get_asgi_application()

# ---------------------------------------------------------
# 4. 后加载 Channels 组件
# ---------------------------------------------------------
# 必须在 django.setup() 之后导入，否则会导致循环导入或模型未加载错误
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from server.middleware import QueryTokenAuthMiddleware  # 你的自定义 Token 中间件
import server.routing  # 包含所有 App 的 WebSocket 路由

# ---------------------------------------------------------
# 5. 定义总入口协议路由 (ProtocolTypeRouter)
# ---------------------------------------------------------
application = ProtocolTypeRouter({
    # A. 处理常规 HTTP 请求 (API, Admin, etc.)
    "http": django_asgi_app,
    
    # B. 处理 WebSocket 请求 (实时聊天, 状态更新, 对战)
    "websocket": QueryTokenAuthMiddleware(  # 第一层：解析 URL 参数 ?token= 并认证
        AuthMiddlewareStack(                # 第二层：兼容 Session 认证 (标准 Django 认证)
            URLRouter(
                # 指向 server/routing.py 中合并后的路由列表
                server.routing.combined_websocket_urlpatterns
            )
        )
    ),
})