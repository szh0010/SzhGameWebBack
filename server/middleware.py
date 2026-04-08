# server/middleware.py
import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.apps import apps

# 配置日志，方便在终端看到验证过程
logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_token(token_key):
    """
    异步获取用户：
    使用动态获取模型 (apps.get_model) 彻底避开 ASGI 启动时的导入顺序冲突。
    """
    try:
        # 1. 动态获取 Token 模型，防止由于 App 尚未加载完成导致的 AttributeError
        Token = apps.get_model('authtoken', 'Token')
        
        # 2. 清理并验证 token 字符串
        if not token_key or not isinstance(token_key, str):
            return AnonymousUser()
            
        clean_key = token_key.strip()
        
        # 3. 查询数据库（关联查询 user 以提高效率）
        # 如果 Token 没搜到，这里会触发 Token.DoesNotExist
        token = Token.objects.select_related('user').get(key=clean_key)
        
        # 4. 检查用户是否被禁用
        if not token.user.is_active:
            print(f"[Socket Auth] 用户 {token.user.username} 已被禁用")
            return AnonymousUser()
            
        print(f"[Socket Auth] Token 验证通过: 用户 {token.user.username}")
        return token.user
        
    except Exception as e:
        # 捕获所有异常（包括 DoesNotExist, LookupError, 或者数据库连接失败）
        # 关键：决不能让中间件抛出异常导致 500，必须返回 AnonymousUser
        print(f"[Socket Auth] 验证失败: {str(e)}")
        return AnonymousUser()

class QueryTokenAuthMiddleware:
    """
    WebSocket Token 认证中间件
    解析 URL 格式: ws://.../?token=你的Token值
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # 1. 获取 URL 中的查询参数
        # scope['query_string'] 是字节串 (b'token=xxx')，需要解码
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        
        # 2. 提取 token 值
        token_list = query_params.get('token')

        # 3. 如果有 token，进行异步校验
        if token_list and token_list[0]:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            # 没有提供 token，设为匿名用户
            scope['user'] = AnonymousUser()

        # 4. 将处理后的 scope 传给下一层中间件 (通常是 AuthMiddlewareStack)
        return await self.inner(scope, receive, send)