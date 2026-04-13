from django.urls import path, include
from rest_framework.routers import DefaultRouter
# ✨ 核心改动：导入 ai_chat_proxy
from .views import StickyNoteViewSet, ProfileViewSet, ChatHistoryView, index_view, ai_chat_proxy

# 使用 DefaultRouter 会自动处理结尾斜杠
router = DefaultRouter()

# 1. 注册个人资料与社交接口
router.register(r'profile', ProfileViewSet, basename='profile')

# 2. 注册便签墙接口
router.register(r'notes', StickyNoteViewSet, basename='stickynote')
router.register(r'', StickyNoteViewSet, basename='stickynote_root')

urlpatterns = [
    # --- 1. AI 聊天中转接口 ---
    # ✨ 新增：全站 AI 助手、五子棋建议、便签润色都走这个口
    # 访问路径：/api/board/ai/chat/
    path('ai/chat/', ai_chat_proxy, name='ai-chat'),

    # --- 2. 获取历史聊天记录接口 ---
    path('chat/history/<int:friend_id>/', ChatHistoryView.as_view(), name='chat-history'),

    # --- 3. 包含路由器生成的 API 路由 ---
    path('', include(router.urls)),
    
    # --- 4. HTML 测试页面 ---
    path('view/', index_view, name='board_index'),
]