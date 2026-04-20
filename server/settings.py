import os
from pathlib import Path
from dotenv import load_dotenv  # ✨ 引入加载工具

# --- 0. 加载环境变量 ---
BASE_DIR = Path(__file__).resolve().parent.parent
# 自动寻找根目录下的 .env 文件并加载
load_dotenv(os.path.join(BASE_DIR, '.env'))

# --- 1. 基础路径与密钥 ---
SECRET_KEY = os.getenv('SECRET_KEY')

# ✨ 核心修改 1：强制开启 DEBUG 模式！
# 这样本地开发时，Django 才会帮你代理显示 /media/ 里的图片
DEBUG = True

# ✨ 核心修改 2：加入你的公网 IP，确保服务器能识别请求
ALLOWED_HOSTS = ['47.98.240.67', '127.0.0.1', 'localhost', '*']


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
# 提示：生产环境下也可以把数据库密码写进 .env
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'szh_game_db',
        'USER': 'root',
        'PASSWORD': os.getenv('DB_PASSWORD', '123456'), # 默认 123456，也可从 .env 读取
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
# 部署时运行 collectstatic 后的存放位置
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- 9. Channels 消息层配置 ---
CHANNEL_LAYERS = {
    "default": {
        # 开发阶段使用内存层。
        # ⚠️ 注意：如果未来部署多台服务器，需要改用 RedisChannelLayer
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# --- 10. Django REST Framework 配置 ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', 
    ],
}

# --- 11. 核心跨域与安全配置 ---
CORS_ALLOW_CREDENTIALS = True 

# ✨ 核心修改 3：允许跨域的白名单（加入了公网 IP）
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://47.98.240.67",
]

# ✨ 核心修改 4：CSRF 信任名单（加入了公网 IP）
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
    "http://47.98.240.67",
]

# Cookie 与 Session 安全策略
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False