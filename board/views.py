from rest_framework import viewsets, permissions, status, decorators, views
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from .models import StickyNote, Profile, FriendRequest, ChatMessage
from .serializers import StickyNoteSerializer, ProfileSerializer, ChatMessageSerializer
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# --- 1. 一个“不检查 CSRF”的认证类 ---
class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # 直接返回，不执行任何 CSRF 检查

# --- 2. 便签墙 (Felt Board) ---
@method_decorator(csrf_exempt, name='dispatch')
class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all().order_by('-created_at')
    serializer_class = StickyNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [UnsafeSessionAuthentication] 

    def perform_create(self, serializer):
        # 创建时自动关联当前登录用户
        serializer.save(user=self.request.user)

    # 点赞/取消点赞 逻辑接口
    @decorators.action(detail=True, methods=['post'])
    def toggle_like(self, request, pk=None):
        note = self.get_object()
        user = request.user
        
        if note.likes.filter(id=user.id).exists():
            note.likes.remove(user)
            action_status = "unliked"
        else:
            note.likes.add(user)
            action_status = "liked"
        
        return Response({
            "status": action_status,
            "likes_count": note.likes_count,
            "is_liked": note.likes.filter(id=user.id).exists()
        })

    # 删除逻辑及其权限校验
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response(
                {"error": "你没有权限删除他人的便签"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

# --- 3. 个人资料与好友社交逻辑 ---
@method_decorator(csrf_exempt, name='dispatch')
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [UnsafeSessionAuthentication] 

    def get_queryset(self):
        return Profile.objects.all()

    # 处理 /api/board/profile/me/
    @decorators.action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        profile = request.user.profile
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        if request.method == 'PATCH':
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ✨ A. 搜索用户（修复加固版）
    def list(self, request, *args, **kwargs):
        uid_query = request.query_params.get('uid')
        
        if uid_query:
            # 1. 清洗输入数据
            uid_query = uid_query.strip().strip('/')
            
            target_profile = None
            
            # 2. 尝试按 ID 搜索
            if uid_query.isdigit():
                target_profile = Profile.objects.filter(user__id=int(uid_query)).first()
            
            # 3. 如果按 ID 没搜到，尝试按用户名（Username）直接搜索
            # 这样用户输入 ID 或 用户名 都能搜到人，体验更好
            if not target_profile:
                target_profile = Profile.objects.filter(user__username=uid_query).first()
            
            if target_profile:
                serializer = self.get_serializer(target_profile)
                return Response(serializer.data)
            
            # 4. 如果还是没搜到，说明可能真的没这个人，或者该用户没有 Profile 记录
            return Response({"error": "🔍 未找到该用户，请检查 ID 或用户名是否正确"}, status=404)
        
        # 如果没有传 uid 参数，默认返回自己的资料
        return Response(self.get_serializer(request.user.profile).data)

    # B. 发送申请
    @decorators.action(detail=False, methods=['post'])
    def add_friend(self, request):
        target_uid = request.data.get('to_uid')
        try:
            to_user = User.objects.get(id=int(target_uid))
            if to_user == request.user:
                return Response({"error": "不能加自己为好友"}, status=400)
            
            if FriendRequest.objects.filter(
                (Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)),
                status='accepted'
            ).exists():
                return Response({"error": "你们已经是好友了"}, status=400)

            obj, created = FriendRequest.objects.get_or_create(
                from_user=request.user,
                to_user=to_user,
                defaults={'status': 'pending'}
            )
            return Response({"message": "申请已发送" if created else "请勿重复发送"})
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "用户不存在"}, status=404)

    # C. 获取“申请通知”
    @decorators.action(detail=False, methods=['get'])
    def my_requests(self, request):
        reqs = FriendRequest.objects.filter(to_user=request.user, status='pending')
        data = [{
            "id": r.id,
            "from_uid": r.from_user.id,
            "from_name": r.from_user.username,
            "time": r.created_at.strftime("%Y-%m-%d %H:%M")
        } for r in reqs]
        return Response(data)

    # D. 获取“我的好友”
    @decorators.action(detail=False, methods=['get'])
    def my_friends(self, request):
        friend_conns = FriendRequest.objects.filter(
            (Q(from_user=request.user) | Q(to_user=request.user)),
            status='accepted'
        )
        friends_data = []
        for conn in friend_conns:
            friend_user = conn.to_user if conn.from_user == request.user else conn.from_user
            profile = friend_user.profile
            friends_data.append({
                "uid": friend_user.id,
                "username": friend_user.username,
                "nickname": profile.nickname,
                "avatar": profile.avatar.url if profile.avatar else None,
                "is_online": profile.is_online  
            })
        return Response(friends_data)

    # E. 同意/拒绝申请
    @decorators.action(detail=False, methods=['post'])
    def handle_request(self, request):
        req_id = request.data.get('req_id')
        action = request.data.get('action') 
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
            return Response({"error": "申请不存在"}, status=404)

# --- 4. 获取历史聊天记录接口 ---
class ChatHistoryView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [UnsafeSessionAuthentication]

    def get(self, request, friend_id):
        user = request.user
        messages = ChatMessage.objects.filter(
            (Q(sender=user) & Q(receiver_id=friend_id)) |
            (Q(sender_id=friend_id) & Q(receiver=user))
        ).order_by('timestamp')

        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)

def index_view(request):
    return render(request, 'board/index.html')