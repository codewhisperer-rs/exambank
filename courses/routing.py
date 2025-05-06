from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/exercise/(?P<exercise_id>\d+)/$', consumers.ExerciseConsumer.as_asgi()),
    re_path(r'ws/ai_exercise/(?P<exercise_id>\d+)/$', consumers.AIExerciseConsumer.as_asgi()),
] 