from rest_framework import serializers
from .models import StickyNote, Profile, ChatMessage

# 1. 便签序列化器
class StickyNoteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = StickyNote
        fields = ['id', 'title', 'content', 'image', 'user', 'created_at']

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
        # ✨ 重要：is_online 必须设为只读，由 WebSocket 逻辑控制状态
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