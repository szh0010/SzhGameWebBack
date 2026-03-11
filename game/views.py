from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator 
import json
import logging

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions 
from .models import GameRoom

# --- 核心新增：导入 Profile 模型 ---
from board.models import Profile 

logger = logging.getLogger(__name__)

# --- 1. 登录接口 ---
@ensure_csrf_cookie  # 确保在登录响应中包含 CSRF Cookie
@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # 1. 执行 Django 标准登录，建立 Session
                login(request, user)
                
                # 2. ✨ 关键修复：强制保存 Session
                # 确保 sessionid 能够立即写入数据库并生成响应 Cookie
                if not request.session.session_key:
                    request.session.create()
                request.session.save()
                
                # 3. 返回用户信息
                return JsonResponse({
                    'status': 'success', 
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


# --- 2. 注册接口 (类视图) ---
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
            # 1. 创建用户账号
            user = User.objects.create_user(username=username, password=password)
            
            # 2. --- 同步创建个人资料 ---
            # 确保新用户在 Profile 表中有记录，搜索功能才能工作
            Profile.objects.get_or_create(
                user=user, 
                defaults={'nickname': username}
            )
            
            return Response({'message': '注册成功', 'status': 'success'}, status=status.HTTP_201_CREATED)
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
        # 优先从 Session 获取已登录用户
        if request.user and request.user.is_authenticated:
            user = request.user
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'用户 {username} 不存在'}, status=400)
        else:
            return JsonResponse({'status': 'error', 'message': '必须指定用户名'}, status=400)

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