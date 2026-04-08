import json
import logging
from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator 

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions 
from rest_framework.authtoken.models import Token  # ✨ 核心导入：Token 模型

from .models import GameRoom
from board.models import Profile 

logger = logging.getLogger(__name__)

# --- 1. 登录接口 (修复版) ---
@ensure_csrf_cookie
@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # 1. 执行 Session 登录 (用于普通 API)
                login(request, user)
                
                if not request.session.session_key:
                    request.session.create()
                request.session.save()

                # 2. ✨ 核心修复：获取或创建该用户的 Token (用于 WebSocket)
                # 这就是你缺少的“发钥匙”环节
                token, _ = Token.objects.get_or_create(user=user)
                
                # 3. 返回包含 token 的完整数据
                return JsonResponse({
                    'status': 'success', 
                    'token': token.key,  # 👈 前端存入 localStorage 的就是它！
                    'id': user.id,          
                    'user': user.username,
                    'msg': '登录成功'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': '用户名或密码错误'
                }, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'请求解析失败: {str(e)}'}, status=400)
            
    return JsonResponse({'status': 'error', 'message': '仅支持 POST 请求'}, status=405)


# --- 2. 注册接口 (修复版) ---
@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    authentication_classes = [] 
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': '用户名和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 1. 创建用户
            user = User.objects.create_user(username=username, password=password)
            
            # 2. 创建资料
            Profile.objects.get_or_create(
                user=user, 
                defaults={'nickname': username}
            )

            # 3. ✨ 顺手也为新注册用户预创建 Token
            token, _ = Token.objects.get_or_create(user=user)
            
            return Response({
                'message': '注册成功', 
                'status': 'success',
                'token': token.key  # 注册完也可以直接给钥匙
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'注册失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 3. 创建房间接口 ---
@csrf_exempt
@require_http_methods(["POST"])
def create_room_api(request):
    try:
        data = json.loads(request.body)
        game_id = data.get('game', 'gomoku')
        room_id = data.get('room_id')
        username = data.get('username')

        if not room_id:
            return JsonResponse({'status': 'error', 'message': '房间 ID 不能为空'}, status=400)

        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'用户 {username} 不存在'}, status=400)

        room, created = GameRoom.objects.get_or_create(
            room_id=str(room_id),
            defaults={
                'game_type': game_id,
                'creator': user,
                'player_black': user,
                'is_active': True
            }
        )

        player_count = 1 if room.player_black else 0
        if room.player_white: player_count += 1

        return JsonResponse({
            'status': 'success',
            'created': created,
            'message': '房间创建成功' if created else '房间已存在',
            'room': {
                'id': room.room_id,
                'playerCount': player_count,
                'game': game_id
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# --- 4. 获取房间列表接口 ---
@csrf_exempt
@require_http_methods(["GET"])
def rooms_api(request):
    all_rooms = GameRoom.objects.filter(is_active=True)
    rooms_data = []
    for room in all_rooms:
        count = 0
        if room.player_black: count += 1
        if room.player_white: count += 1
        rooms_data.append({
            'id': room.room_id,
            'playerCount': count,
            'status': '等待中' if count < 2 else '游戏中'
        })
    return JsonResponse({'status': 'success', 'rooms': rooms_data})