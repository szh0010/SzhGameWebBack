import json
import uuid
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Q

# 导入应用模型
from .models import ChatMessage, Profile, FriendRequest
from game.models import GameRoom

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    # ---------------------------------------------------------
    # 1. 连接与断开逻辑
    # ---------------------------------------------------------
    async def connect(self):
        # 从 QueryTokenAuthMiddleware 获取解析出的用户
        self.user = self.scope.get("user")
        
        # 调试日志：确保在终端能看到用户身份
        print(f"--- [Socket Attempt] User: {self.user}, Auth: {self.user.is_authenticated if self.user else False} ---")

        if self.user and self.user.is_authenticated:
            self.u_id = int(self.user.id)
            self.group_name = f"user_{self.u_id}"
            
            # 加入个人频道组 (用于接收他人发给我的消息)
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            # --- ✨ 多连接状态管理：防止多开网页导致离线显示错误 ---
            cache_key = f"online_count_{self.u_id}"
            current_count = cache.get(cache_key, 0)
            
            # 只有当这是用户开启的第一个连接时，才在数据库更新为在线并广播
            if current_count == 0:
                await self.update_user_online_status(True)
                await self.broadcast_status_to_friends(True)
            
            # 增加计数器
            cache.set(cache_key, current_count + 1, timeout=None)
            
            # 立即拉取并同步当前所有在线好友的状态给自己
            await self.send_online_friends_to_self()
            
            print(f"[Socket Success] 用户 {self.user.username} (ID: {self.u_id}) 已成功建立连接")
        else:
            # 如果 Token 验证失败，拒绝连接
            print("[Socket Failed] 拒绝匿名连接：Token 无效、过期或未提供")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name') and self.user.is_authenticated:
            # 计数器递减
            cache_key = f"online_count_{self.u_id}"
            current_count = cache.get(cache_key, 0)
            new_count = max(0, current_count - 1)
            cache.set(cache_key, new_count, timeout=None)

            # 只有当用户关闭了最后一个网页标签页/连接时，才标记为离线
            if new_count == 0:
                await self.update_user_online_status(False)
                await self.broadcast_status_to_friends(False)
            
            # 退出频道组
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            print(f"[Socket Closed] 用户 {self.u_id} 连接断开，剩余活动连接: {new_count}")

    # ---------------------------------------------------------
    # 2. 消息接收逻辑 (前端发来的指令处理)
    # ---------------------------------------------------------
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            m_type = data.get('type')

            # --- A. 私聊消息 (new_message) ---
            if not m_type or m_type == 'new_message':
                rid = data.get('receiver_id')
                txt = data.get('message')
                if rid and txt:
                    # 1. 异步保存到数据库
                    await self.save_message_db(int(rid), str(txt))
                    
                    # 2. 构造广播载荷
                    payload = {
                        "type": "chat_handler", 
                        "message": str(txt),
                        "sender_id": int(self.u_id),
                        "sender_name": str(self.user.username),
                        "receiver_id": int(rid)
                    }
                    
                    # 3. 广播给接收者和自己 (自己也要收一份，用于多端同步和界面反馈)
                    await self.channel_layer.group_send(f"user_{int(rid)}", payload)
                    await self.channel_layer.group_send(self.group_name, payload)

            # --- B. 游戏邀请 (game_invite) ---
            elif m_type == 'game_invite':
                rid = data.get('receiver_id')
                if rid:
                    await self.channel_layer.group_send(f"user_{int(rid)}", {
                        "type": "game_invite_handler",
                        "sender_id": int(self.u_id),
                        "sender_name": str(self.user.username)
                    })

            # --- C. 游戏响应 (game_response: accept/reject) ---
            elif m_type == 'game_response':
                iid = data.get('inviter_id')
                action = data.get('action')
                if action == 'accept' and iid:
                    room_id = str(uuid.uuid4())[:8]
                    # 创建数据库房间记录
                    await self.create_game_room_db(room_id, int(iid), self.u_id)
                    
                    res_payload = {
                        "type": "game_accepted_handler", 
                        "room_id": str(room_id), 
                        "game_type": 'gomoku'
                    }
                    # 通知邀请者和我自己进入游戏
                    await self.channel_layer.group_send(f"user_{int(iid)}", res_payload)
                    await self.channel_layer.group_send(self.group_name, res_payload)

        except Exception as e:
            print(f"!!! WebSocket 运行报错: {e}")

    # ---------------------------------------------------------
    # 3. 内部转发处理器 (Group Send -> 最终推向前端)
    # ---------------------------------------------------------
    async def chat_handler(self, event):
        """推送私聊消息"""
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "message": str(event["message"]),
            "sender_id": int(event["sender_id"]),
            "sender_name": str(event["sender_name"]),
            "receiver_id": int(event.get("receiver_id", 0))
        }))

    async def game_invite_handler(self, event):
        """推送游戏邀请通知"""
        await self.send(text_data=json.dumps({
            "type": "game_invite",
            "sender_id": int(event["sender_id"]),
            "sender_name": str(event["sender_name"])
        }))

    async def game_accepted_handler(self, event):
        """推送进入游戏通知"""
        await self.send(text_data=json.dumps({
            "type": "game_invite_accepted",
            "room_id": str(event["room_id"]),
            "game_type": str(event["game_type"])
        }))

    async def status_update_handler(self, event):
        """推送好友在线/离线状态"""
        await self.send(text_data=json.dumps({
            "type": "status_update", 
            "uid": int(event["uid"]), 
            "is_online": bool(event["is_online"])
        }))

    # ---------------------------------------------------------
    # 4. 数据库异步操作 (database_sync_to_async)
    # ---------------------------------------------------------
    @database_sync_to_async
    def update_user_online_status(self, s):
        Profile.objects.filter(user_id=self.u_id).update(is_online=s)

    @database_sync_to_async
    def save_message_db(self, rid, txt):
        try:
            receiver = User.objects.get(id=rid)
            ChatMessage.objects.create(sender=self.user, receiver=receiver, content=str(txt))
        except Exception as e:
            print(f"Save msg DB error: {e}")

    @database_sync_to_async
    def create_game_room_db(self, rid, iid, aid):
        try:
            GameRoom.objects.create(
                room_id=str(rid), 
                game='gomoku', 
                creator_id=int(iid), 
                player_black_id=int(iid), 
                player_white_id=int(aid), 
                is_active=True
            )
        except Exception as e:
            print(f"Create room DB error: {e}")

    @database_sync_to_async
    def get_friends_ids_db(self):
        """获取所有已接受好友的 UID 列表"""
        qs = FriendRequest.objects.filter((Q(from_user_id=self.u_id) | Q(to_user_id=self.u_id)), status='accepted')
        return [ (c.to_user_id if c.from_user_id == self.u_id else c.from_user_id) for c in qs ]

    @database_sync_to_async
    def get_online_friends_db(self):
        """获取当前在线的好友 UID 列表"""
        qs = FriendRequest.objects.filter(
            (Q(from_user_id=self.u_id) | Q(to_user_id=self.u_id)), status='accepted'
        ).select_related('from_user__profile', 'to_user__profile')
        
        online_ids = []
        for c in qs:
            friend = c.to_user if c.from_user_id == self.u_id else c.from_user
            if hasattr(friend, 'profile') and friend.profile.is_online:
                online_ids.append(friend.id)
        return online_ids

    # ---------------------------------------------------------
    # 5. 业务通知辅助
    # ---------------------------------------------------------
    async def broadcast_status_to_friends(self, is_online):
        """将我的状态同步给所有好友"""
        ids = await self.get_friends_ids_db()
        for f_id in ids:
            await self.channel_layer.group_send(f"user_{int(f_id)}", {
                "type": "status_update_handler", 
                "uid": int(self.u_id), 
                "is_online": is_online
            })

    async def send_online_friends_to_self(self):
        """上线时主动拉取在线好友并通知前端更新界面"""
        ids = await self.get_online_friends_db()
        for f_id in ids:
            await self.send(json.dumps({
                "type": "status_update", 
                "uid": int(f_id), 
                "is_online": True
            }))