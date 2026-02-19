import json
from channels.generic.websocket import AsyncWebsocketConsumer

# 内存存储房间状态（包含棋盘数据）
rooms_state = {}

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "room1"
        self.room_group_name = f"game_{self.room_name}"

        if self.room_group_name not in rooms_state:
            rooms_state[self.room_group_name] = {
                'players': [],
                'board': [[None for _ in range(15)] for _ in range(15)], # 15x15 棋盘
                'game_over': False
            }
        
        room = rooms_state[self.room_group_name]
        self.color = 'black' if len(room['players']) == 0 else 'white'
        room['players'].append(self.channel_name)

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({'type': 'init', 'color': self.color}))

    async def receive(self, text_data):
        data = json.loads(text_data)
        room = rooms_state[self.room_group_name]

        if data.get('type') == 'move' and not room['game_over']:
            x, y = data['x'], data['y']
            
            # 1. 记录落子到后端棋盘
            if room['board'][y][x] is not None: return # 防止重复落子
            room['board'][y][x] = self.color

            # 2. 检查胜负
            winner = None
            if self.check_win(x, y, room['board']):
                winner = self.color
                room['game_over'] = True

            # 3. 广播给所有人
            next_turn = 'white' if self.color == 'black' else 'black'
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_move',
                    'x': x, 'y': y,
                    'color': self.color,
                    'next_turn': next_turn,
                    'winner': winner # 如果有人赢了，这里会有颜色值
                }
            )

    async def game_move(self, event):
        await self.send(text_data=json.dumps(event))

    def check_win(self, x, y, board):
        color = board[y][x]
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)] # 横、竖、右斜、左斜
        for dx, dy in directions:
            count = 1
            # 正向检查
            nx, ny = x + dx, y + dy
            while 0 <= nx < 15 and 0 <= ny < 15 and board[ny][nx] == color:
                count += 1
                nx, ny = nx + dx, ny + dy
            # 反向检查
            nx, ny = x - dx, y - dy
            while 0 <= nx < 15 and 0 <= ny < 15 and board[ny][nx] == color:
                count += 1
                nx, ny = nx - dx, ny - dy
            if count >= 5: return True
        return False

    async def disconnect(self, close_code):
        if self.room_group_name in rooms_state:
            # 玩家退出，重置游戏状态
            rooms_state[self.room_group_name]['game_over'] = False
            rooms_state[self.room_group_name]['board'] = [[None for _ in range(15)] for _ in range(15)]
            if self.channel_name in rooms_state[self.room_group_name]['players']:
                rooms_state[self.room_group_name]['players'].remove(self.channel_name)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)