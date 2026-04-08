from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StickyNoteViewSet, ProfileViewSet, ChatHistoryView, index_view

# 使用 DefaultRouter 会自动处理结尾斜杠
router = DefaultRouter()

# 1. 注册个人资料与社交接口
# 访问路径：/api/board/profile/
router.register(r'profile', ProfileViewSet, basename='profile')

# 2. 注册便签墙接口
# 访问路径：/api/board/notes/ 或直接 /api/board/
router.register(r'notes', StickyNoteViewSet, basename='stickynote')
router.register(r'', StickyNoteViewSet, basename='stickynote_root')

urlpatterns = [
    # --- 1. 获取历史聊天记录接口 ---
    # ✨ 核心修复：路径修改为 chat/history/ 以匹配前端请求的 URL
    # 访问路径：/api/board/chat/history/好友ID/
    path('chat/history/<int:friend_id>/', ChatHistoryView.as_view(), name='chat-history'),

    # --- 2. 包含路由器生成的 API 路由 ---
    # 包含上面注册的 profile 和 notes 路径
    path('', include(router.urls)),
    
    # --- 3. HTML 测试页面 ---
    # 访问路径：/api/board/view/
    path('view/', index_view, name='board_index'),
]