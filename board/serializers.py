from rest_framework import serializers
from .models import StickyNote, Profile, ChatMessage

# 1. ✨ 升级版便签序列化器：包含空间位置字段与作者头像
class StickyNoteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    # 只读字段：显示点赞总数
    likes_count = serializers.ReadOnlyField()
    # 动态字段：判断当前登录用户是否已点赞
    is_liked = serializers.SerializerMethodField()
    # ✨ 顺手加上便签作者的头像，方便前端未来调用
    user_avatar = serializers.SerializerMethodField()

    class Meta:
        model = StickyNote
        fields = [
            'id', 'title', 'content', 'image', 'user', 'user_avatar',
            'created_at', 'likes_count', 'is_liked',
            'x_position', 'y_position', 'rotation', 'z_index'
        ]

    def get_is_liked(self, obj):
        # 从 context 中获取当前的 request 对象
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 判断当前用户是否在点赞列表（ManyToManyField）中
            return obj.likes.filter(id=request.user.id).exists()
        return False

    def get_user_avatar(self, obj):
        try:
            if hasattr(obj.user, 'profile') and obj.user.profile.avatar:
                return obj.user.profile.avatar.url
        except Exception:
            pass
        return None


# 2. 个人资料序列化器
class ProfileSerializer(serializers.ModelSerializer):
    # 将 User 表的 id 映射为 uid
    uid = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    # gender_display 仅用于显示，不用于写入
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'uid', 'username', 'nickname', 'avatar', 
            'gender', 'gender_display', 'birthday', 'bio', 'is_online'
        ]
        # is_online 必须设为只读，由 WebSocket 逻辑控制状态
        read_only_fields = ['is_online']


# 3. ✨ 升级版好友私聊消息序列化器：带上发送者头像
class ChatMessageSerializer(serializers.ModelSerializer):
    # 增加一个只读字段，方便前端直接显示发送者的名字
    sender_name = serializers.ReadOnlyField(source='sender.username')
    # ✨ 核心修复：为聊天消息增加发送者头像字段
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 
            'sender', 
            'sender_name', 
            'sender_avatar', # 👈 新增头像字段
            'receiver', 
            'content', 
            'timestamp', 
            'is_read'
        ]

    def get_sender_avatar(self, obj):
        # 获取发送者的 Profile，如果有头像则返回相对 URL，交给前端清洗
        try:
            if hasattr(obj.sender, 'profile') and obj.sender.profile.avatar:
                return obj.sender.profile.avatar.url
        except Exception:
            pass
        return None