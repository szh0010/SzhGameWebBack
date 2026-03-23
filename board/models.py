from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. 原有的便签模型
class StickyNote(models.Model):
    title = models.CharField(max_length=100, verbose_name="标题")
    content = models.TextField(verbose_name="内容")
    image = models.ImageField(upload_to='note_images/', null=True, blank=True, verbose_name="图片")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    def __str__(self):
        return self.title

# 2. 个人资料模型
class Profile(models.Model):
    GENDER_CHOICES = (
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称/ID名")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="头像")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='O', verbose_name="性别")
    birthday = models.DateField(null=True, blank=True, verbose_name="生日")
    bio = models.TextField(max_length=500, blank=True, verbose_name="个人简介")
    
    # ✨ 新增：在线状态字段
    is_online = models.BooleanField(default=False, verbose_name="是否在线")

    def __str__(self):
        return f"{self.user.username} 的个人资料"

# 3. 好友申请模型
class FriendRequest(models.Model):
    from_user = models.ForeignKey(
        User, 
        related_name='sent_requests', 
        on_delete=models.CASCADE, 
        verbose_name="发送者"
    )
    to_user = models.ForeignKey(
        User, 
        related_name='received_requests', 
        on_delete=models.CASCADE, 
        verbose_name="接收者"
    )
    
    status = models.CharField(
        max_length=10, 
        choices=[
            ('pending', '待处理'), 
            ('accepted', '已同意'), 
            ('rejected', '已拒绝')
        ], 
        default='pending',
        verbose_name="状态"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申请时间")

    class Meta:
        unique_together = ('from_user', 'to_user')
        verbose_name = "好友申请记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"

# 4. 好友私聊记录模型
class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages', 
        verbose_name="发送者"
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages', 
        verbose_name="接收者"
    )
    content = models.TextField(verbose_name="消息内容")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="发送时间")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")

    class Meta:
        ordering = ['timestamp']
        verbose_name = "私聊消息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username}: {self.content[:20]}"

# --- 5. 自动化信号 (Signals) ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()