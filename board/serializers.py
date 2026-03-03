from rest_framework import serializers
from .models import StickyNote

class StickyNoteSerializer(serializers.ModelSerializer):
    # 显示用户名称而不是 ID，且设置为只读
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = StickyNote
        fields = ['id', 'title', 'content', 'user', 'created_at']