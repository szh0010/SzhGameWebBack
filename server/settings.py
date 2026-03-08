"""
Django settings for server project.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-5&x+mh2m&wtbrk6euqfgcs+2!k46@kc7(n&$m8e9j@*gqo$!li'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*'] # 开发环境允许所有主机访问


# Application definition

INSTALLED_APPS = [
    'daphne',              # 必须放在第一行
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # 自定义 App
    'game',
    'board',               # <--- 留言板 App
    'rest_framework',      # 用于前后端分离的 API
    'corsheaders',         # 用于处理跨域
    'channels',            # WebSocket 核心
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',           # 必须在最顶端
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'server.urls'

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
                # 允许在模板中使用 MEDIA_URL
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'server.wsgi.application'
ASGI_APPLICATION = 'server.asgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'szh_game_db',
        'USER': 'root',          # 你的 MySQL 用户名
        'PASSWORD': '123456',    # 你的 MySQL 密码
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True


# --- 静态文件与媒体文件配置 ---

# 静态文件 (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件 (用户上传的图片、文件)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 配置 Channel Layer (内存模式)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# --- 新增：Django REST Framework 配置 ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',  # 识别 Session 登录状态
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',           # 默认需要登录
    ],
}

# --- 核心修改：跨域与安全配置 ---

# 1. CORS 配置：允许前端访问
CORS_ALLOW_ALL_ORIGINS = True  # 开发环境下允许所有来源
CORS_ALLOW_CREDENTIALS = True  # 允许携带 Cookie (用于登录状态)

# 2. CSRF 信任来源配置
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',    # Vue 默认开发端口
    'http://127.0.0.1:5173',
    'http://localhost:8000',    # Django 端口
    'http://127.0.0.1:8000',
    'http://106.54.x.x',        # 服务器公网 IP
]

# 3. 允许的请求头
from corsheaders.defaults import default_headers
CORS_ALLOW_HEADERS = list(default_headers) + [
    'x-csrftoken',
]