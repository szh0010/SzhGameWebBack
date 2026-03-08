from django.contrib import admin
from .models import StickyNote

# 基础版注册（最简单）：
# admin.site.register(StickyNote)

# 进阶版注册（强烈推荐，可以直接在列表看到标题、作者和时间）：
@admin.register(StickyNote)
class StickyNoteAdmin(admin.ModelAdmin):
    # 后台列表显示的字段
    list_display = ('id', 'title', 'user', 'created_at', 'image')
    # 点击哪个字段可以进入编辑页
    list_display_links = ('id', 'title')
    # 过滤器（右侧侧边栏）
    list_filter = ('created_at', 'user')
    # 搜索框
    search_fields = ('title', 'content')