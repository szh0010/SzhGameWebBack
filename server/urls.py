from django.contrib import admin
from django.urls import path, include  # 1. 确保这里导入了 include
from game.views import login_api, rooms_api, create_room_api 
from game.views import RegisterView 

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),

    # --- Game 应用接口 ---
    path('api/login/', login_api),
    path('api/register/', RegisterView.as_view()),
    path('api/rooms/', rooms_api),
    path('api/create-room/', create_room_api),

    # --- Board 应用接口 ---
    # 2. 将 board 的所有路由挂载在 api/board/ 路径下
    path('api/board/', include('board.urls')),

    # 3. DRF 可视化界面的登录/登出（可选，方便在浏览器里直接点登录）
    path('api-auth/', include('rest_framework.urls')),
]