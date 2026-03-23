from django.contrib import admin
from django.urls import path, include
from django.conf import settings  # 导入配置项
from django.conf.urls.static import static  # 导入静态/媒体文件处理函数

# 导入应用视图
from game.views import login_api, rooms_api, create_room_api, RegisterView 

urlpatterns = [
    # 1. 管理后台
    path('admin/', admin.site.urls),

    # 2. --- Game 应用接口 ---
    path('api/login/', login_api),
    path('api/register/', RegisterView.as_view()),
    path('api/rooms/', rooms_api),
    path('api/create-room/', create_room_api),

    # 3. --- Board 应用接口 (包含便签墙、社交、私聊逻辑) ---
    path('api/board/', include('board.urls')),

    # 4. DRF 提供的可视化调试登录接口
    path('api-auth/', include('rest_framework.urls')),
]

# ✨ 核心修改：配置媒体文件访问
# 当 DEBUG = True 时，Django 会充当“文件服务器”，让前端能通过 URL 看到上传的图片
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)