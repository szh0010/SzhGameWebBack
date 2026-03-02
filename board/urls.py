from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StickyNoteViewSet, index_view

# 创建一个路由器并注册我们的 ViewSet
router = DefaultRouter()
router.register(r'notes', StickyNoteViewSet)

# API 链接现在由路由器自动决定
urlpatterns = [
    path('view/', index_view),
    path('', include(router.urls)),
]