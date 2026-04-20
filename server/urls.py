from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# 导入应用视图
from game.views import login_api, rooms_api, create_room_api, RegisterView 

urlpatterns = [
    # 1. 管理后台
    path('admin/', admin.site.urls),

    # 2. --- Game 应用接口 ---
    # 💡 建议：确保这些 API 结尾也带斜杠，与 Django 的规范保持一致
    path('api/login/', login_api),
    path('api/register/', RegisterView.as_view()),
    path('api/rooms/', rooms_api),
    path('api/create-room/', create_room_api),

    # 3. --- Board 应用接口 ---
    # ✨ 这里挂载了便签、个人资料、搜索、好友申请等所有逻辑
    # 访问示例：/api/board/profile/?uid=10003
    path('api/board/', include('board.urls')),

    # 4. DRF 可视化调试接口
    path('api-auth/', include('rest_framework.urls')),
]

# ✨ 核心：配置媒体文件访问（头像、便签图片等）
# 当 DEBUG = True 时，Django 会接管这些静态/媒体文件的代理
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)