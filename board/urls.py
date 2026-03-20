from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StickyNoteViewSet, ProfileViewSet, index_view

# 创建一个路由器
router = DefaultRouter()

# 1. 注册便签墙接口 (核心修改：路径设为空 '')
# 这样访问 /api/board/ 就会直接对应到便签墙的增删改查
router.register(r'', StickyNoteViewSet, basename='stickynote')

# 2. 注册个人资料接口 (路径：/api/board/profile/)
router.register(r'profile', ProfileViewSet, basename='profile')

urlpatterns = [
    # 包含路由器生成的 API 路由
    path('', include(router.urls)),
    
    # HTML 测试页面：http://127.0.0.1:8000/api/board/view/
    path('view/', index_view, name='board_index'),
]