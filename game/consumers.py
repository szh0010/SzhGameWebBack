import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import GameRoom

logger = logging.getLogger(__name__)
rooms_state = {}

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_id = str(self.scope['url_route']['kwargs']['room_id'])
        self.room_group_name = f"game_{self.game_id}_{self.room_id}"

        # 1. 获取用户名
        query_params = parse_qs(self.scope.get('query_string', b'').decode())
        username = query_params.get('username', [None])[0]
        self.user = await self.get_user_by_username(username)

        # 2. 【核心修复】：在同步函数里判定颜色，避开异步外键访问报错
        self.color = await self.determine_player_color()
        
        if not self.user or self.color == 'error':
            logger.warning(f"拒绝连接: 用户={username}, 颜色状态={self.color}")
            await self.close(code=4001)
            return

        # 3. 初始化内存房间状态
        if self.room_group_name not in rooms_state:
            rooms_state[self.room_group_name] = {
                'players': [],
                'board': [[None for _ in range(15)] for _ in range(15)],
                'game_over': False,
                'current_turn': 'black'
            }
        
        if self.channel_name not in rooms_state[self.room_group_name]['players']:
            rooms_state[self.room_group_name]['players'].append(self.channel_name)

        # 4. 同步身份到数据库，确保前端看到 2/2
        await self.sync_player_to_db()

        # 5. 加入群组并接受连接
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 6. 发送初始化数据
        await self.send(text_data=json.dumps({
            'type': 'init',
            'color': self.color,
            'username': self.user.username
        }))
        logger.info(f"玩家 {self.user.username} 已连接，颜色: {self.color}")

    # --- 数据库同步工具方法 ---

    @database_sync_to_async
    def determine_player_color(self):
        """在同步上下文中安全比对 creator 身份"""
        try:
            # 使用 select_related 预加载 creator，防止深度访问报错
            room_obj = GameRoom.objects.select_related('creator').get(room_id=self.room_id)
            if room_obj.creator == self.user:
                return 'black'
            else:
                return 'white'
        except GameRoom.DoesNotExist:
            return 'error'

    @database_sync_to_async
    def sync_player_to_db(self):
        """将当前用户写入数据库对应位置"""
        if self.color == 'black':
            GameRoom.objects.filter(room_id=self.room_id).update(player_black=self.user, is_active=True)
        else:
            GameRoom.objects.filter(room_id=self.room_id).update(player_white=self.user, is_active=True)

    @database_sync_to_async
    def get_user_by_username(self, username):
        try: return User.objects.get(username=username)
        except: return None

    # --- 游戏逻辑 ---

    async def receive(self, text_data):
        data = json.loads(text_data)
        room = rooms_state.get(self.room_group_name)
        if not room: return

        if data.get('type') == 'move' and not room['game_over']:
            # 只有轮到自己的回合才能下棋
            if room['current_turn'] != self.color: return
            
            x, y = data['x'], data['y']
            if room['board'][y][x] is not None: return
            
            room['board'][y][x] = self.color
            winner = self.color if self.check_win(x, y, room['board']) else None
            next_turn = 'white' if self.color == 'black' else 'black'
            room['current_turn'] = next_turn

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_move', 
                    'x': x, 'y': y, 
                    'color': self.color, 
                    'next_turn': next_turn, 
                    'winner': winner
                }
            )

    async def game_move(self, event):
        await self.send(text_data=json.dumps(event))

    def check_win(self, x, y, board):
        color = board[y][x]
        for dx, dy in [(1,0), (0,1), (1,1), (1,-1)]:
            count = 1
            for i in [1, -1]:
                nx, ny = x + dx*i, y + dy*i
                while 0<=nx<15 and 0<=ny<15 and board[ny][nx] == color:
                    count += 1
                    nx, ny = nx + dx*i, ny + dy*i
            if count >= 5: return True
        return False

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)