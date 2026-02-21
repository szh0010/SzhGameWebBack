import json
import logging
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import GameRoom

logger = logging.getLogger(__name__)
# 内存中维护房间状态
rooms_state = {}

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.room_id = str(self.scope['url_route']['kwargs']['room_id'])
        self.room_group_name = f"game_{self.game_id}_{self.room_id}"

        # 1. 获取 URL 中的用户名
        query_params = parse_qs(self.scope.get('query_string', b'').decode())
        username = query_params.get('username', [None])[0]
        self.user = await self.get_user_by_username(username)

        # 2. 判定颜色
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

        # 4. 同步身份到数据库
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
        try:
            room_obj = GameRoom.objects.select_related('creator').get(room_id=self.room_id)
            if room_obj.creator == self.user:
                return 'black'
            else:
                return 'white'
        except GameRoom.DoesNotExist:
            return 'error'

    @database_sync_to_async
    def sync_player_to_db(self):
        """将当前用户写入数据库对应位置并激活房间"""
        if self.color == 'black':
            GameRoom.objects.filter(room_id=self.room_id).update(player_black=self.user, is_active=True)
        else:
            GameRoom.objects.filter(room_id=self.room_id).update(player_white=self.user, is_active=True)

    @database_sync_to_async
    def get_user_by_username(self, username):
        try: return User.objects.get(username=username)
        except: return None

    # --- 游戏逻辑处理 ---

    async def receive(self, text_data):
        data = json.loads(text_data)
        room = rooms_state.get(self.room_group_name)
        if not room: return

        if data.get('type') == 'move' and not room['game_over']:
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

    # --- 退出与清理逻辑 (核心修复区) ---

    async def disconnect(self, close_code):
        # 1. 离开房间组
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        # 2. 从内存状态中移除玩家
        if self.room_group_name in rooms_state:
            if self.channel_name in rooms_state[self.room_group_name]['players']:
                rooms_state[self.room_group_name]['players'].remove(self.channel_name)
            
            # 如果内存中该房间已无 channel 活跃，清理内存
            if not rooms_state[self.room_group_name]['players']:
                del rooms_state[self.room_group_name]

        # 3. 数据库清理：移除玩家身份并销毁空房间
        await self.cleanup_room_db()
        logger.info(f"玩家已断开连接，尝试清理房间: {self.room_id}")

    @database_sync_to_async
    def cleanup_room_db(self):
        """核心销毁逻辑：在同步上下文中安全修改数据库"""
        try:
            # 重新获取房间对象
            room = GameRoom.objects.get(room_id=self.room_id)
            
            # 使用 connect 时已经确定的 self.user 避免访问 scope['user'] 报错
            current_username = self.user.username if self.user else None
            
            if not current_username:
                return

            # 移除对应位置的玩家记录
            updated = False
            if room.player_black and room.player_black.username == current_username:
                room.player_black = None
                updated = True
            elif room.player_white and room.player_white.username == current_username:
                room.player_white = None
                updated = True
            
            if updated:
                room.save()

            # 如果房间一个人都没了，彻底删除，防止出现“幽灵房间”
            # 重新查询一遍确保准确
            room.refresh_from_db()
            if not room.player_black and not room.player_white:
                room.delete()
                logger.info(f"房间 {self.room_id} 已无玩家，执行物理删除。")
            else:
                # 如果还有人在，确保 is_active 依然为 True
                room.is_active = True
                room.save()
                
        except GameRoom.DoesNotExist:
            pass
        except Exception as e:
            logger.error(f"清理房间数据库时发生异常: {e}")