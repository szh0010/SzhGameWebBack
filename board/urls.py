from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StickyNoteViewSet, index_view

# 创建一个路由器并注册我们的 ViewSet
router = DefaultRouter()

# 核心修改：将 'notes' 改为 '' (空字符串)
# 这样访问 /api/board/ 就等同于访问便签列表/发布接口
router.register(r'', StickyNoteViewSet, basename='stickynote')

urlpatterns = [
    # 1. 优先匹配 API 路由
    path('', include(router.urls)),
    
    # 2. 你的测试 HTML 页面，访问地址为：http://127.0.0.1:8000/api/board/view/
    path('view/', index_view),
]