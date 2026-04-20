import logging
import json
import os
import traceback
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from rest_framework import viewsets, permissions, status, decorators, views
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

# ✨ 导入工具
from dotenv import load_dotenv
from openai import OpenAI

from .models import StickyNote, Profile, FriendRequest, ChatMessage
from .serializers import StickyNoteSerializer, ProfileSerializer, ChatMessageSerializer

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# --- 0. AI 逻辑配置 ---
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), 
    base_url="https://api.deepseek.com"
)

# --- ✨ 五子棋博弈引擎 (Gomoku Engine) ---
class GomokuEngine:
    def __init__(self, board, ai_color):
        self.board = board  # 15x15 矩阵
        self.size = 15
        self.ai_val = 1 if ai_color == 'black' else 2
        self.player_val = 2 if ai_color == 'black' else 1

    def get_best_move(self):
        best_score = -1
        best_move = (7, 7)
        
        # 扫描所有空位
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 0:
                    score = self.evaluate_point(r, c)
                    if score > best_score:
                        best_score = score
                        best_move = (r, c)
        return best_move

    def evaluate_point(self, r, c):
        # 防守权重稍微调高 (1.2)，让 AI 在困难模式下更难对付
        ai_attack = self.calculate_score(r, c, self.ai_val)
        player_threat = self.calculate_score(r, c, self.player_val)
        return ai_attack + (player_threat * 1.2)

    def calculate_score(self, r, c, color):
        total_score = 0
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dr, dc in directions:
            line = self.get_line_context(r, c, dr, dc, color)
            total_score += self.pattern_match(line, color)
        return total_score

    def get_line_context(self, r, c, dr, dc, color):
        line = []
        for i in range(-4, 5):
            if i == 0:
                line.append(color)
                continue
            nr, nc = r + i*dr, c + i*dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                line.append(self.board[nr][nc])
            else:
                line.append(-1) # 边界
        return line

    def pattern_match(self, line, color):
        s = "".join([str(x) if x != -1 else "B" for x in line])
        target = str(color)
        
        # 评分标准
        if target*5 in s: return 100000
        if "0"+target*4+"0" in s: return 10000
        if "0"+target*4 in s or target*4+"0" in s: return 5000
        if "0"+target*3+"0" in s: return 2000
        if "0"+target*2+"0" in s: return 500
        return s.count(target) * 10

# --- 1. 认证类 ---
class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return 

# --- 2 & 3. 视图集 ---
@method_decorator(csrf_exempt, name='dispatch')
class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all().order_by('-created_at')
    serializer_class = StickyNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, UnsafeSessionAuthentication]
    
    def perform_create(self, serializer): 
        serializer.save(user=self.request.user)
        
    @decorators.action(detail=True, methods=['post'])
    def toggle_like(self, request, pk=None):
        note = self.get_object(); user = request.user
        if note.likes.filter(id=user.id).exists(): note.likes.remove(user); is_liked = False
        else: note.likes.add(user); is_liked = True
        return Response({"likes_count": note.likes.count(), "is_liked": is_liked})

@method_decorator(csrf_exempt, name='dispatch')
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, UnsafeSessionAuthentication]
    
    def get_queryset(self): 
        return Profile.objects.all()
        
    @decorators.action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if request.method == 'GET': return Response(self.get_serializer(profile).data)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid(): serializer.save(); return Response(serializer.data)
        return Response(serializer.errors, status=400)
        
    def list(self, request, *args, **kwargs):
        # ✨ 护盾：添加 try-except 防止查询崩溃导致 500
        try:
            query = request.query_params.get('uid') or request.query_params.get('q') or request.query_params.get('username')
            if query:
                clean_query = str(query).strip().strip('/')
                target_users = User.objects.filter(Q(username__iexact=clean_query) | Q(id=clean_query if clean_query.isdigit() else -1))
                profiles = [Profile.objects.get_or_create(user=u)[0] for u in target_users.exclude(id=request.user.id)]
                return Response(self.get_serializer(profiles, many=True).data)
            return Response([])
        except Exception as e:
            logger.error(f"Search error: {e}")
            return Response({"error": "搜索时发生错误"}, status=500)

    @decorators.action(detail=False, methods=['post'])
    def add_friend(self, request):
        try:
            to_user = User.objects.get(id=int(request.data.get('to_uid')))
            if to_user == request.user:
                return Response({"error": "不能添加自己"}, status=400)
            
            # 检查是否已经是好友
            is_friend = FriendRequest.objects.filter(
                (Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)), 
                status='accepted'
            ).exists()
            if is_friend: return Response({"error": "已经是好友"}, status=400)
            
            FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user, defaults={'status': 'pending'})
            return Response({"message": "申请已发送"})
        except Exception: 
            return Response({"error": "用户不存在"}, status=404)

    @decorators.action(detail=False, methods=['get'])
    def my_friends(self, request):
        friend_conns = FriendRequest.objects.filter((Q(from_user=request.user) | Q(to_user=request.user)), status='accepted')
        data = []
        for conn in friend_conns:
            friend = conn.to_user if conn.from_user == request.user else conn.from_user
            p, _ = Profile.objects.get_or_create(user=friend)
            data.append({"uid": friend.id, "username": friend.username, "nickname": p.nickname or friend.username, "avatar": p.avatar.url if p.avatar else None, "is_online": p.is_online})
        return Response(data)

    # ✨ 核心修复：添加前端苦苦寻找的 my_requests 接口！
    @decorators.action(detail=False, methods=['get'])
    def my_requests(self, request):
        incoming_requests = FriendRequest.objects.filter(to_user=request.user, status='pending')
        data = []
        for req in incoming_requests:
            sender = req.from_user
            p, _ = Profile.objects.get_or_create(user=sender)
            data.append({
                "request_id": req.id,
                "uid": sender.id,
                "username": sender.username,
                "nickname": p.nickname or sender.username,
                "avatar": p.avatar.url if p.avatar else None,
                "created_at": req.created_at
            })
        return Response(data)

    # ✨ 核心修复：统一处理同意/拒绝的逻辑
    @decorators.action(detail=False, methods=['post'])
    def handle_request(self, request):
        action = request.data.get('action') # 'accept' 或 'reject'
        req_id = request.data.get('request_id') or request.data.get('id')
        from_uid = request.data.get('uid') or request.data.get('from_uid')
        
        try:
            if req_id:
                req_obj = FriendRequest.objects.get(id=req_id, to_user=request.user, status='pending')
            elif from_uid:
                req_obj = FriendRequest.objects.get(from_user_id=from_uid, to_user=request.user, status='pending')
            else:
                return Response({"error": "缺少参数"}, status=400)
                
            if action == 'accept':
                req_obj.status = 'accepted'
                req_obj.save()
                return Response({"message": "已添加为好友"})
            elif action == 'reject':
                req_obj.status = 'rejected'
                req_obj.save()
                return Response({"message": "已拒绝申请"})
            else:
                return Response({"error": "未知操作"}, status=400)
        except FriendRequest.DoesNotExist:
            return Response({"error": "申请不存在或已处理"}, status=404)

class ChatHistoryView(views.APIView):
    def get(self, request, friend_id):
        msgs = ChatMessage.objects.filter((Q(sender=request.user) & Q(receiver_id=friend_id)) | (Q(sender_id=friend_id) & Q(receiver=request.user))).order_by('timestamp')
        return Response(ChatMessageSerializer(msgs, many=True).data)

# --- 5. ✨ 混合动力 AI 助手接口 ---
@decorators.api_view(['POST'])
@decorators.permission_classes([permissions.IsAuthenticated])
@decorators.authentication_classes([TokenAuthentication, UnsafeSessionAuthentication])
def ai_chat_proxy(request):
    user_msg = request.data.get('message', '')
    chat_type = request.data.get('type', 'general')
    page_context = request.data.get('page', '首页')

    if chat_type == 'gomoku_move':
        board = request.data.get('board', [])
        difficulty = request.data.get('difficulty', 'medium')
        ai_color = request.data.get('ai_color', 'white') 

        if difficulty == 'hard':
            engine = GomokuEngine(board, ai_color)
            row, col = engine.get_best_move()
            return Response({'status': 'success', 'move': {'row': row, 'col': col}})
        
        col_header = "    0 1 2 3 4 5 6 7 8 9 a b c d e"
        board_rows = [f"{format(i, 'x')} | " + " ".join(map(str, r)) for i, r in enumerate(board)]
        readable_board = col_header + "\n" + "\n".join(board_rows)

        system_prompt = (
            f"You are a Gomoku player. Board: 15x15. Level: {difficulty}.\n"
            f"MAP:\n{readable_board}\n"
            "Pick an EMPTY (0) spot. Return ONLY JSON: {\"row\": r, \"col\": c}."
        )

        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": "Your move."}],
                response_format={'type': 'json_object'},
                temperature=0.7,
                timeout=20.0 
            )
            move_data = json.loads(response.choices[0].message.content)
            r, c = move_data.get('row'), move_data.get('col')
            if board[r][c] != 0:
                r, c = GomokuEngine(board, ai_color).get_best_move()
            return Response({'status': 'success', 'move': {'row': r, 'col': c}})
        except Exception as e:
            r, c = GomokuEngine(board, ai_color).get_best_move()
            return Response({'status': 'success', 'move': {'row': r, 'col': c}})

    if not user_msg: return Response({'status': 'error', 'message': '内容为空'}, status=400)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"你叫“SZH 小管家”，是 Ciallo 网站的助手。"},
                {"role": "user", "content": f"当前页面：{page_context}\n用户说：{user_msg}"},
            ],
            timeout=25.0
        )
        return Response({'status': 'success', 'reply': response.choices[0].message.content})
    except Exception as e:
        return Response({'status': 'error', 'message': 'AI 走神了'}, status=500)

def index_view(request):
    return render(request, 'board/index.html')