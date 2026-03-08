from django.contrib.auth import authenticate, login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie # 1. 引入 ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json
import logging

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import GameRoom

logger = logging.getLogger(__name__)

# 2. 添加 @ensure_csrf_cookie，强制响应包含 csrftoken 饼干
@ensure_csrf_cookie
@csrf_exempt  # 保留 exempt 是为了兼容你目前前端没带令牌的登录请求
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # 这一步会创建 Session，由于加了 ensure_csrf_cookie，
                # 浏览器会同时收到 sessionid 和 csrftoken 两个饼干。
                login(request, user)
                return JsonResponse({
                    'status': 'success', 
                    'user': user.username,
                    'msg': '登录成功'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': '用户名或密码错误'
                })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': '仅支持 POST 请求'}, status=405)

class RegisterView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': '用户名和密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(username=username).exists():
            return Response({'error': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建用户
        user = User.objects.create_user(username=username, password=password)
        return Response({'message': '注册成功'}, status=status.HTTP_201_CREATED)


@csrf_exempt
@require_http_methods(["POST"])
def create_room_api(request):
    """创建房间 API"""
    try:
        data = json.loads(request.body)
        game_id = data.get('game', 'gomoku')
        room_id = data.get('room_id')
        username = data.get('username')

        if not room_id:
            return JsonResponse({
                'status': 'error',
                'message': '房间 ID 不能为空'
            }, status=400)

        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        elif username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'用户 {username} 不存在'
                }, status=400)
        else:
            return JsonResponse({
                'status': 'error',
                'message': '必须指定用户名'
            }, status=400)

        logger.info(f"创建房间: room_id={room_id}, game_id={game_id}, user={user}")

        room, created = GameRoom.objects.get_or_create(
            room_id=str(room_id),
            defaults={
                'game_type': game_id,
                'creator': user,
                'player_black': user,
                'is_active': True
            }
        )

        player_count = 0
        if room.player_black:
            player_count += 1
        if room.player_white:
            player_count += 1

        logger.info(f"房间创建成功: {room_id}, created={created}, 当前玩家数={player_count}")

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
        logger.error(f"创建房间出错: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)


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