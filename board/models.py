from django.db import models
from django.contrib.auth.models import User

class StickyNote(models.Model):
    title = models.CharField(max_length=100, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    
    # 修正点：将 on_relative_model_field_name 改为 related_name
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    def __str__(self):
        return self.title