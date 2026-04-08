import logging
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render

from rest_framework import viewsets, permissions, status, decorators, views
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from .models import StickyNote, Profile, FriendRequest, ChatMessage
from .serializers import StickyNoteSerializer, ProfileSerializer, ChatMessageSerializer

logger = logging.getLogger(__name__)

# --- 1. 认证类：跳过 CSRF 检查以支持多端发布 ---
class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return 

# --- 2. 便签墙 (Felt Board) ---
@method_decorator(csrf_exempt, name='dispatch')
class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all().order_by('-created_at')
    serializer_class = StickyNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, UnsafeSessionAuthentication]

    def perform_create(self, serializer):
        # 自动将当前登录用户保存为发布者
        serializer.save(user=self.request.user)

    @decorators.action(detail=True, methods=['post'])
    def toggle_like(self, request, pk=None):
        note = self.get_object()
        user = request.user
        if note.likes.filter(id=user.id).exists():
            note.likes.remove(user)
            is_liked = False
        else:
            note.likes.add(user)
            is_liked = True
        return Response({
            "likes_count": note.likes.count(),
            "is_liked": is_liked
        })

# --- 3. 个人资料与好友社交逻辑 ---
@method_decorator(csrf_exempt, name='dispatch')
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, UnsafeSessionAuthentication]

    def get_queryset(self):
        return Profile.objects.all()

    # 获取/修改个人资料
    @decorators.action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ✨ 核心搜索修复：根据搜索结果数量自动切换 [{}, {}] 或 {} 格式
    def list(self, request, *args, **kwargs):
        # 获取查询参数
        uid_param = request.query_params.get('uid')
        q_param = request.query_params.get('q')
        user_param = request.query_params.get('username')
        query = uid_param or q_param or user_param
        
        if query:
            clean_query = str(query).strip().strip('/')
            
            # 1. 构造搜索条件：用户名模糊匹配或 ID 精确匹配
            user_filter = Q(username__iexact=clean_query)
            if clean_query.isdigit():
                user_filter |= Q(id=int(clean_query))
            
            target_users = User.objects.filter(user_filter)

            if not target_users.exists():
                return Response({"error": f"🔍 未找到用户 '{clean_query}'"}, status=404)

            # 2. 检查是否搜到自己
            if target_users.count() == 1 and target_users.first() == request.user:
                return Response({"error": "这是你自己哦，不能添加自己"}, status=400)

            # 3. 确保 Profile 记录存在并排除自己
            profiles = []
            for u in target_users.exclude(id=request.user.id):
                p, _ = Profile.objects.get_or_create(user=u)
                profiles.append(p)

            # ✨ 关键：如果通过 uid 搜，或结果只有一个，直接返回对象 {} 而非数组 []
            if (uid_param or len(profiles) == 1) and len(profiles) > 0:
                serializer = self.get_serializer(profiles[0])
                return Response(serializer.data)
            else:
                serializer = self.get_serializer(profiles, many=True)
                return Response(serializer.data)
        
        return Response([])

    # B. 发送好友申请
    @decorators.action(detail=False, methods=['post'])
    def add_friend(self, request):
        target_uid = request.data.get('to_uid')
        if not target_uid:
            return Response({"error": "缺少目标用户ID"}, status=400)
        
        try:
            to_user = User.objects.get(id=int(target_uid))
            if to_user == request.user:
                return Response({"error": "不能加自己"}, status=400)
            
            # 检查是否已经是好友
            is_friend = FriendRequest.objects.filter(
                (Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)),
                status='accepted'
            ).exists()
            if is_friend:
                return Response({"error": "你们已经是好友了"}, status=400)

            # 检查是否有待处理的申请
            FriendRequest.objects.get_or_create(
                from_user=request.user,
                to_user=to_user,
                defaults={'status': 'pending'}
            )
            return Response({"message": "申请已发送"})
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "用户不存在"}, status=404)

    # C. 获取好友列表 (WebSocket 状态灯的基础)
    @decorators.action(detail=False, methods=['get'])
    def my_friends(self, request):
        friend_conns = FriendRequest.objects.filter(
            (Q(from_user=request.user) | Q(to_user=request.user)), status='accepted'
        ).select_related('from_user__profile', 'to_user__profile')
        
        data = []
        for conn in friend_conns:
            friend = conn.to_user if conn.from_user == request.user else conn.from_user
            p, _ = Profile.objects.get_or_create(user=friend)
            data.append({
                "uid": int(friend.id),
                "username": str(friend.username),
                "nickname": str(p.nickname or friend.username),
                "avatar": p.avatar.url if p.avatar else None,
                "is_online": bool(p.is_online)
            })
        return Response(data)

    # D. 获取好友请求列表
    @decorators.action(detail=False, methods=['get'])
    def my_requests(self, request):
        reqs = FriendRequest.objects.filter(to_user=request.user, status='pending')
        data = [{
            "id": r.id,
            "from_uid": int(r.from_user.id),
            "from_name": str(r.from_user.username),
            "time": r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in reqs]
        return Response(data)

    # E. 处理好友申请
    @decorators.action(detail=False, methods=['post'])
    def handle_request(self, request):
        req_id = request.data.get('req_id')
        action = request.data.get('action') # 'accept' 或 'reject'
        try:
            req_obj = FriendRequest.objects.get(id=req_id, to_user=request.user)
            if action == 'accept':
                req_obj.status = 'accepted'
                req_obj.save()
                return Response({"message": "已同意申请"})
            else:
                req_obj.delete()
                return Response({"message": "已忽略申请"})
        except FriendRequest.DoesNotExist:
            return Response({"error": "该申请已失效或已处理"}, status=404)

# --- 4. 历史记录接口 ---
class ChatHistoryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication, UnsafeSessionAuthentication]
    
    def get(self, request, friend_id):
        # 查询当前用户与指定好友之间的所有消息
        messages = ChatMessage.objects.filter(
            (Q(sender=request.user) & Q(receiver_id=friend_id)) | 
            (Q(sender_id=friend_id) & Q(receiver=request.user))
        ).order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

def index_view(request):
    return render(request, 'board/index.html')