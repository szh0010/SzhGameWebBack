# """
# ASGI config for server project.

# It exposes the ASGI callable as a module-level variable named ``application``.

# For more information on this file, see
# https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
# """

# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import game.routing  # 我们等下会创建这个文件

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings.py')

# application = ProtocolTypeRouter({
#     # 处理普通 HTTP 请求
#     "http": get_asgi_application(),
    
#     # 处理 WebSocket 请求
#     "websocket": AuthMiddlewareStack(
#         URLRouter(
#             game.routing.websocket_urlpatterns
#         )
#     ),
# })

import os
import django
from django.core.asgi import get_asgi_application

# 1. 必须最先设置环境变量，且不要带 .py 后缀
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

# 2. 必须手动初始化 Django (解决 ImproperlyConfigured 的核心)
django.setup()

# 3. 只有在 setup 之后，才能导入 channels 相关组件和业务路由
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import game.routing  

application = ProtocolTypeRouter({
    # 处理普通 HTTP 请求
    "http": get_asgi_application(),
    
    # 处理 WebSocket 请求
    "websocket": AuthMiddlewareStack(
        URLRouter(
            game.routing.websocket_urlpatterns
        )
    ),
})