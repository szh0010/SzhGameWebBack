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

    def __str__(self):
        return f"{self.user.username} 的个人资料"

# 3. ✨ 新增：好友申请模型
class FriendRequest(models.Model):
    # 发送者 (from_user)
    from_user = models.ForeignKey(
        User, 
        related_name='sent_requests', 
        on_delete=models.CASCADE, 
        verbose_name="发送者"
    )
    # 接收者 (to_user)
    to_user = models.ForeignKey(
        User, 
        related_name='received_requests', 
        on_delete=models.CASCADE, 
        verbose_name="接收者"
    )
    
    # 申请状态
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
        # 核心设置：防止重复发送申请（同一个人对同一个人只能存在一条记录）
        unique_together = ('from_user', 'to_user')
        verbose_name = "好友申请记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"

# --- 4. 自动化信号 (Signals) ---
# 逻辑：当 User 表有新数据创建时，自动触发创建 Profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # 使用 get_or_create 增强健壮性，防止重复创建报错
        Profile.objects.get_or_create(user=instance)

# 逻辑：当 User 数据保存时，同步保存 Profile
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # 确保 instance 有 profile 属性再进行保存
    if hasattr(instance, 'profile'):
        instance.profile.save()