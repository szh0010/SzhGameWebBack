from rest_framework import viewsets, permissions, status, decorators
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication # ✨ 引入认证类
from .models import StickyNote, Profile, FriendRequest
from .serializers import StickyNoteSerializer, ProfileSerializer
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# --- 新增：一个“不检查 CSRF”的认证类 ---
class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # 直接返回，不执行任何 CSRF 检查

# 1. 便签墙
@method_decorator(csrf_exempt, name='dispatch') # ✨ 加上这一行
class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all().order_by('-created_at')
    serializer_class = StickyNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # ✨ 核心修复：给便签墙也加上这个认证类，彻底解决 POST 时的 403/405 问题
    authentication_classes = [UnsafeSessionAuthentication] 

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# 2. 个人资料与好友社交逻辑
@method_decorator(csrf_exempt, name='dispatch')
class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    # ✨ 使用自定义的认证类，绕过 CSRF 检查
    authentication_classes = [UnsafeSessionAuthentication] 

    def get_queryset(self):
        return Profile.objects.all()

    # --- A. 搜索用户 ---
    def list(self, request, *args, **kwargs):
        uid = request.query_params.get('uid')
        if uid:
            uid = uid.strip().strip('/')
            target = Profile.objects.filter(user__id=uid).first()
            if target:
                return Response(self.get_serializer(target).data)
            return Response({"error": "找不到该用户"}, status=404)
        return Response(self.get_serializer(request.user.profile).data)

    # --- B. 发送申请 (POST) ---
    @decorators.action(detail=False, methods=['post'])
    def add_friend(self, request):
        target_uid = request.data.get('to_uid')
        try:
            to_user = User.objects.get(id=int(target_uid))
            if to_user == request.user:
                return Response({"error": "不能加自己为好友"}, status=400)
            
            # 检查是否已经是好友
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
        except User.DoesNotExist:
            return Response({"error": "用户不存在"}, status=404)

    # --- C. 获取“申请通知”列表 (GET) ---
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

    # --- D. 获取“我的好友”列表 (GET) ---
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
                "avatar": profile.avatar.url if profile.avatar else None
            })
        return Response(friends_data)

    # --- E. 同意/拒绝申请 (POST) ---
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

def index_view(request):
    return render(request, 'board/index.html')