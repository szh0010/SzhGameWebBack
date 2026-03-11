from rest_framework import serializers
from .models import StickyNote, Profile

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
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)

    class Meta:
        model = Profile
        fields = ['uid', 'username', 'nickname', 'avatar', 'gender', 'gender_display', 'birthday', 'bio']