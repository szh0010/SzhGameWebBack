import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. 获取当前用户
        self.user = self.scope["user"]

        # 2. 检查用户是否登录
        if self.user.is_authenticated:
            self.group_name = f"user_{self.user.id}"
            
            # 将当前连接加入到自己的频道组里
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # ✨ 新增：上线时更新数据库状态为 True
            await self.update_user_online_status(True)
        else:
            # 未登录用户拒绝连接
            await self.close()

    async def disconnect(self, close_code):
        # 离开时退出频道组
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            
            # ✨ 新增：下线时更新数据库状态为 False
            if self.user.is_authenticated:
                await self.update_user_online_status(False)

    # 3. 接收从前端发来的消息
    async def receive(self, text_data):
        data = json.loads(text_data)
        receiver_id = data.get('receiver_id')
        message_text = data.get('message')

        if not receiver_id or not message_text:
            return

        # 保存消息到数据库
        await self.save_message(self.user.id, receiver_id, message_text)

        # 构造统一的消息载荷
        payload = {
            "type": "chat_payload",
            "message": message_text,
            "sender_id": self.user.id,
            "sender_name": self.user.username,
        }

        # 4. 推送到接收者的组
        await self.channel_layer.group_send(f"user_{receiver_id}", payload)

        # 5. 推送到发送者自己的组（修复自己看不见消息的问题）
        await self.channel_layer.group_send(f"user_{self.user.id}", payload)

    # 6. 定义发送给前端的消息格式
    async def chat_payload(self, event):
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
        }))

    # --- 数据库操作异步包装 ---

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

    @database_sync_to_async
    def update_user_online_status(self, status):
        """
        ✨ 更新用户的在线状态位
        """
        try:
            # 这里的 self.user.profile 依赖于你在 models.py 写的 Signal 自动创建
            profile = self.user.profile
            profile.is_online = status
            # 使用 update_fields 指定更新，效率更高
            profile.save(update_fields=['is_online'])
        except Exception as e:
            print(f"更新在线状态失败: {e}")