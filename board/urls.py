from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StickyNoteViewSet, ProfileViewSet, ChatHistoryView, index_view

# 创建一个路由器
router = DefaultRouter()

# 1. 注册便签墙接口 (访问路径：/api/board/)
router.register(r'', StickyNoteViewSet, basename='stickynote')

# 2. 注册个人资料与社交接口 (访问路径：/api/board/profile/)
router.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    # --- ✨ 新增：获取历史聊天记录接口 ---
    # 访问路径：/api/board/chat/history/好友ID/
    path('chat/history/<int:friend_id>/', ChatHistoryView.as_view(), name='chat-history'),

    # 包含路由器生成的 API 路由 (便签墙和个人资料)
    path('', include(router.urls)),
    
    # HTML 测试页面：http://127.0.0.1:8000/api/board/view/
    path('view/', index_view, name='board_index'),
]