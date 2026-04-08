# server/routing.py
import board.routing
import game.routing

# ✨ 仅负责组合所有应用的 WebSocket 路由列表
# 注意：使用星号 (*) 展开列表进行合并，确保格式为纯粹的 list
combined_websocket_urlpatterns = [
    *board.routing.websocket_urlpatterns,
    *game.routing.websocket_urlpatterns,
]