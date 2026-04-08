import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import GameRoom

logger = logging.getLogger(__name__)

# 内存中维护房间内的下棋状态
rooms_state = {}

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_id = str(self.scope['url_route']['kwargs']['room_id'])
        self.room_group_name = f"game_{self.game_id}_{self.room_id}"
        
        params = parse_qs(self.scope.get('query_string', b'').decode())
        username = params.get('username', [None])[0]
        role = params.get('role', [None])[0]
        
        self.user = await self.get_user_by_username(username)
        if not self.user:
            await self.close()
            return

        self.color = await self.determine_color_db(role)
        
        # 1. 初始化内存房间状态
        if self.room_group_name not in rooms_state:
            rooms_state[self.room_group_name] = {
                'board': [[None for _ in range(15)] for _ in range(15)],
                'game_over': False,
                'current_turn': 'black',
                'active_users': set() # 用于追踪在线人数
            }
        
        rooms_state[self.room_group_name]['active_users'].add(self.user.username)
        
        # 2. 同步数据库并加入频道
        await self.sync_db()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 3. ✨ 关键：有人进入，立刻向全房间广播成员名单和就绪状态
        await self.broadcast_room_info()

    async def broadcast_room_info(self):
        """同步黑白双方姓名及是否就绪"""
        info = await self.get_players_db()
        # 只要内存里有两个不同的人，或者数据库里两个席位都满了，就设为 ready
        is_ready = len(rooms_state[self.room_group_name]['active_users']) >= 2 or info['full']
        
        # ⚠️ 注意：这里传递给 group_send 的必须是可序列化的类型（字符串/布尔值）
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "room_init_send",
                "black": str(info['black']),
                "white": str(info['white']),
                "ready": bool(is_ready)
            }
        )

    async def room_init_send(self, e):
        """发送给前端 init 消息"""
        # ✨ 修复 TypeError: 这里的 e['black'] 等已经是字符串，不再是 User 对象
        await self.send(text_data=json.dumps({
            "type": "init",
            "color": self.color,
            "black_player": e["black"],
            "white_player": e["white"],
            "is_ready": e["ready"]
        }))

    async def receive(self, text_data):
        data = json.loads(text_data)
        room = rooms_state.get(self.room_group_name)
        if not room or room['game_over']:
            return

        if data.get('type') == 'move':
            # ✨ 判定：必须有两人在房间才允许落子
            if len(room['active_users']) < 2:
                await self.send(text_data=json.dumps({
                    "type": "info", 
                    "message": "等待对手入场..."
                }))
                return

            if room['current_turn'] != self.color:
                return
                
            x, y = data['x'], data['y']
            if room['board'][y][x] is not None:
                return
            
            # 执行落子
            room['board'][y][x] = self.color
            win = self.check_win(x, y, room['board'])
            next_t = 'white' if self.color == 'black' else 'black'
            room['current_turn'] = next_t
            
            if win:
                room['game_over'] = True
            
            # 广播落子结果
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "move_send",
                    "x": x, "y": y,
                    "color": self.color,
                    "next": next_t,
                    "win": bool(win)
                }
            )

    async def move_send(self, e):
        await self.send(json.dumps({
            "type": "game_move",
            "x": e["x"],
            "y": e["y"],
            "color": e["color"],
            "next_turn": e["next"],
            "winner": e["color"] if e["win"] else None
        }))

    @database_sync_to_async
    def determine_color_db(self, r):
        try:
            room = GameRoom.objects.get(room_id=self.room_id)
            if r in ['black', 'white']: return r
            return 'black' if room.creator == self.user else 'white'
        except:
            return 'black'

    @database_sync_to_async
    def get_players_db(self):
        """从数据库获取玩家名，确保返回的是字符串而非 User 对象"""
        try:
            r = GameRoom.objects.get(room_id=self.room_id)
            bn = r.player_black.username if r.player_black else "等待中..."
            wn = r.player_white.username if r.player_white else "等待中..."
            return {
                "black": str(bn), 
                "white": str(wn), 
                "full": (r.player_black is not None and r.player_white is not None)
            }
        except:
            return {"black": "未知", "white": "未知", "full": False}

    @database_sync_to_async
    def sync_db(self):
        f = 'player_black' if self.color == 'black' else 'player_white'
        GameRoom.objects.filter(room_id=self.room_id).update(**{f: self.user, 'is_active': True})

    @database_sync_to_async
    def get_user_by_username(self, u):
        try:
            return User.objects.get(username=u)
        except:
            return None

    def check_win(self, x, y, board):
        color = board[y][x]
        for dx, dy in [(1,0), (0,1), (1,1), (1,-1)]:
            cnt = 1
            for i in [1, -1]:
                nx, ny = x + dx*i, y + dy*i
                while 0<=nx<15 and 0<=ny<15 and board[ny][nx] == color:
                    cnt += 1
                    nx, ny = nx + dx*i, ny + dy*i
            if cnt >= 5: return True
        return False

    async def disconnect(self, code):
        # 从内存活跃列表中移除
        if self.room_group_name in rooms_state:
            rooms_state[self.room_group_name]['active_users'].discard(self.user.username)
        
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        
        # 4. ✨ 核心清理：更新数据库席位
        await self.cleanup_db()
        
        # 有人离开后，通知剩下的那个人更新名单
        await self.broadcast_room_info()

    @database_sync_to_async
    def cleanup_db(self):
        try:
            r = GameRoom.objects.get(room_id=self.room_id)
            # 如果是当前用户断开，清空对应的坑位
            if r.player_black == self.user:
                r.player_black = None
            elif r.player_white == self.user:
                r.player_white = None
            r.save()
            
            # 如果两个人都走了，或者房间空了，删除房间记录
            if not r.player_black and not r.player_white:
                r.delete()
        except:
            pass