from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import StickyNote
from .serializers import StickyNoteSerializer
from django.shortcuts import render

class StickyNoteViewSet(viewsets.ModelViewSet):
    queryset = StickyNote.objects.all()
    serializer_class = StickyNoteSerializer
    
    # 核心权限：必须登录才能访问接口
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # 在保存数据时，自动将当前请求的登录用户存入 user 字段
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        # 获取要删除的便签实例
        instance = self.get_object()
        # 权限校验：如果便签的主人不是当前请求的用户，报 403 错误
        if instance.user != request.user:
            return Response(
                {"detail": "你只能删除自己贴的便签哦！"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

# --- 注意：下面这个函数要移出 class，取消缩进 ---
def index_view(request):
    return render(request, 'board/index.html')