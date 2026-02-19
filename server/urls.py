from django.contrib import admin
from django.urls import path
from game.views import login_api  # 确保这里导入的是你最新的函数名

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),
    
    # 登录接口
    path('api/login/', login_api),
]