from django.db import models
from django.contrib.auth.models import User

class GameRoom(models.Model):
    room_id = models.CharField(max_length=20, unique=True, verbose_name="房间号")
    game_type = models.CharField(max_length=20, default='gomoku', verbose_name="游戏类型")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_rooms")
    player_black = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="black_player")
    player_white = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="white_player")
    is_active = models.BooleanField(default=True, verbose_name="是否正在对局")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"房间 {self.room_id}"