from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # 新增：导入设置
from django.conf.urls.static import static  # 新增：导入静态文件处理函数
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
    path('api/board/', include('board.urls')),

    # DRF 可视化界面的登录/登出
    path('api-auth/', include('rest_framework.urls')),
]

# 核心修改：在开发环境下，开启媒体文件（图片）的访问路径
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)