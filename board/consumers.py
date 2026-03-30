import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.cache import cache  # 引入缓存来处理多连接计数
from .models import ChatMessage, Profile, FriendRequest
from django.db.models import Q

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            self.group_name = f"user_{self.user.id}"
            
            # 将当前连接加入到自己的频道组
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # --- ✨ 灵敏状态逻辑：增加连接数 ---
            cache_key = f"online_count_{self.user.id}"
            current_count = cache.get(cache_key, 0)
            
            # 只有当计数从 0 变 1 时，才去数据库写 True，并通知好友
            if current_count == 0:
                await self.update_user_online_status(True)
                await self.notify_friends_status(True)
            
            cache.set(cache_key, current_count + 1, timeout=None)
            print(f"[DEBUG] 用户 {self.user.id} 上线，当前连接数: {current_count + 1}")
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name') and self.user.is_authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
            # --- ✨ 灵敏状态逻辑：减少连接数 ---
            cache_key = f"online_count_{self.user.id}"
            current_count = cache.get(cache_key, 0)
            new_count = max(0, current_count - 1)
            cache.set(cache_key, new_count, timeout=None)

            # 只有当计数变成 0 时，才真正设置数据库为 False，并通知好友
            if new_count == 0:
                await self.update_user_online_status(False)
                await self.notify_friends_status(False)
            
            print(f"[DEBUG] 用户 {self.user.id} 断开，剩余连接数: {new_count}")

    # --- 接收并转发消息 ---
    async def receive(self, text_data):
        data = json.loads(text_data)
        receiver_id = data.get('receiver_id')
        message_text = data.get('message')

        if not receiver_id or not message_text:
            return

        await self.save_message(self.user.id, receiver_id, message_text)

        payload = {
            "type": "chat_payload",
            "message": message_text,
            "sender_id": self.user.id,
            "sender_name": self.user.username,
        }

        await self.channel_layer.group_send(f"user_{receiver_id}", payload)
        await self.channel_layer.group_send(f"user_{self.user.id}", payload)

    # 转发聊天内容
    async def chat_payload(self, event):
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
        }))

    # ✨ 新增：处理好友状态变化的推送
    async def status_update_payload(self, event):
        """
        当好友上线/下线时，前端会收到这个消息
        """
        await self.send(text_data=json.dumps({
            "type": "status_update",
            "uid": event["uid"],
            "is_online": event["is_online"]
        }))

    # --- 数据库与业务逻辑异步包装 ---

    @database_sync_to_async
    def update_user_online_status(self, status):
        """更新数据库在线状态位"""
        try:
            Profile.objects.filter(user=self.user).update(is_online=status)
        except Exception as e:
            print(f"Update status error: {e}")

    @database_sync_to_async
    def notify_friends_status(self, is_online):
        """
        ✨ 核心：找到所有好友，并通知他们我现在的状态
        """
        import asyncio
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()

        # 获取所有已接受的好友 ID
        friend_conns = FriendRequest.objects.filter(
            (Q(from_user=self.user) | Q(to_user=self.user)),
            status='accepted'
        )
        
        friend_ids = []
        for conn in friend_conns:
            f_id = conn.to_user.id if conn.from_user == self.user else conn.from_user.id
            friend_ids.append(f_id)

        # 构造状态通知载荷
        status_payload = {
            "type": "status_update_payload", # 对应上面的方法名
            "uid": self.user.id,
            "is_online": is_online
        }

        # 给每个在线的好友发通知
        for f_id in friend_ids:
            async_to_sync(channel_layer.group_send)(f"user_{f_id}", status_payload)

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        try:
            receiver = User.objects.get(id=receiver_id)
            return ChatMessage.objects.create(
                sender=self.user,
                receiver=receiver,
                content=content
            )
        except User.DoesNotExist:
            pass