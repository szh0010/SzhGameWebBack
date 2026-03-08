from django.db import models
from django.contrib.auth.models import User

class StickyNote(models.Model):
    title = models.CharField(max_length=100, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    
    # 新增图片字段：
    # upload_to='note_images/' 表示图片会上传到 media/note_images/ 文件夹下
    # null=True, blank=True 表示这张便签可以不传图片
    image = models.ImageField(upload_to='note_images/', null=True, blank=True, verbose_name="图片")
    
    # 关联用户
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    def __str__(self):
        return self.title