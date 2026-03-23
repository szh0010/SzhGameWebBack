from rest_framework import serializers
from .models import StickyNote, Profile, ChatMessage

# 1. ✨ 升级版便签序列化器：包含空间位置字段
class StickyNoteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    # 只读字段：显示点赞总数
    likes_count = serializers.ReadOnlyField()
    # 动态字段：判断当前登录用户是否已点赞
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = StickyNote
        # ✨ 新增了 x_position, y_position, rotation, z_index 到 fields 中
        fields = [
            'id', 'title', 'content', 'image', 'user', 
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

# 2. 个人资料序列化器
class ProfileSerializer(serializers.ModelSerializer):
    # 将 User 表的 id 映射为 uid
    uid = serializers.ReadOnlyField(source='user.id')
    username = serializers.ReadOnlyField(source='user.username')
    # gender_display 仅用于显示，不用于写入
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = Profile
        # 确保包含新增加的 is_online 字段
        fields = [
            'uid', 'username', 'nickname', 'avatar', 
            'gender', 'gender_display', 'birthday', 'bio', 'is_online'
        ]
        # is_online 必须设为只读，由 WebSocket 逻辑控制状态
        read_only_fields = ['is_online']

# 3. 好友私聊消息序列化器
class ChatMessageSerializer(serializers.ModelSerializer):
    # 增加一个只读字段，方便前端直接显示发送者的名字
    sender_name = serializers.ReadOnlyField(source='sender.username')

    class Meta:
        model = ChatMessage
        fields = [
            'id', 
            'sender', 
            'sender_name', 
            'receiver', 
            'content', 
            'timestamp', 
            'is_read'
        ]