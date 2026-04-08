import os
from pathlib import Path

# --- 1. 基础路径与密钥 ---
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-5&x+mh2m&wtbrk6euqfgcs+2!k46@kc7(n&$m8e9j@*gqo$!li'
DEBUG = True
ALLOWED_HOSTS = ['*']

# --- 2. 应用定义 (顺序至关重要) ---
INSTALLED_APPS = [
    'daphne',               # ✨ 必须在第一行，接管 runserver 指令
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 功能插件
    'rest_framework',
    'rest_framework.authtoken',  # ✨ 提供 Token 数据库表支持
    'corsheaders',               # 处理跨域
    'channels',                  # 异步通讯框架

    # 自定义业务 App
    'game',
    'board',
]

# --- 3. 中间件配置 ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',        # 跨域中间件建议放在最前
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'server.urls'

# --- 4. 模板配置 ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- 5. 异步与入口配置 ---
WSGI_APPLICATION = 'server.wsgi.application'
ASGI_APPLICATION = 'server.asgi.application'  # ✨ 指向你的 asgi.py

# --- 6. 数据库配置 (MySQL) ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'szh_game_db',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

# --- 7. 国际化 ---
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# --- 8. 静态文件与媒体文件 ---
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 9. Channels 消息层配置 ---
CHANNEL_LAYERS = {
    "default": {
        # 开发阶段使用内存层，无需 Redis。生产环境请务必更换为 RedisChannelLayer
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# --- 10. Django REST Framework 配置 ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',   # ✨ 核心：后端识别 Authorization: Token xxx
        'rest_framework.authentication.SessionAuthentication', # 支持浏览器 Admin 登录
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        # ✨ 默认所有接口需要登录。注意：登录接口必须在 views.py 中使用 @AllowAny
        'rest_framework.permissions.IsAuthenticated', 
    ],
}

# --- 11. 核心跨域与安全配置 (解决 403 与 Cookie 问题) ---
CORS_ALLOW_CREDENTIALS = True  # 允许跨域携带 Token/Cookie

# 前端访问地址（Vite 默认端口）
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

# CSRF 信任名单
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
]

# Cookie 与 Session 安全策略
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # 如果前端需要读取 CSRFToken，设为 False