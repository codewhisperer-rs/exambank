from django.urls import re_path
from . import consumers
import logging
import datetime

logger = logging.getLogger(__name__)

async def handle_missing_ws(scope, receive, send):
    """处理已删除的WebSocket路由连接尝试"""
    # 记录时间信息
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = scope.get('path', 'unknown path')
    client = f"{scope.get('client', ['unknown', 0])[0]}:{scope.get('client', ['unknown', 0])[1]}"
    
    # 记录连接尝试
    logger.info(f"[{current_time}] WebSocket尝试连接不存在的路由: {path} 来自: {client}")
    
    # 发送关闭消息
    await send({"type": "websocket.close", "code": 4004})
    
    # 记录连接关闭
    logger.info(f"[{current_time}] WebSocket已关闭连接: {path}")

websocket_urlpatterns = [
    re_path(r'ws/exercise/(?P<exercise_id>\d+)/$', consumers.ExerciseConsumer.as_asgi()),
    re_path(r'ws/ai_exercise/(?P<exercise_id>\d+)/$', consumers.AIExerciseConsumer.as_asgi()),
] 