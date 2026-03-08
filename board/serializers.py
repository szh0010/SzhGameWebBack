from rest_framework import serializers
from .models import StickyNote

class StickyNoteSerializer(serializers.ModelSerializer):
    # 显示用户名称而不是 ID，且设置为只读
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = StickyNote
        # 将 'image' 添加到字段列表中
        fields = ['id', 'title', 'content', 'image', 'user', 'created_at']