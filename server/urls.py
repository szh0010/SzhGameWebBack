from django.contrib import admin
from django.urls import path
from game.views import login_api, rooms_api, create_room_api  # 确保这里导入的是你最新的函数名
from game.views import RegisterView  # 导入注册视图
urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),

    # 登录接口
    path('api/login/', login_api),
    # 注册接口
    path('api/register/', RegisterView.as_view()),
    # 房间列表接口
    path('api/rooms/', rooms_api),
    # 创建房间接口
    path('api/create-room/', create_room_api),
]

