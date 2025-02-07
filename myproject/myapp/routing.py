from django.urls import path
from .consumers import VideoCallConsumer

websocket_urlpatterns = [
    path('ws/video-call/<room_name>/', VideoCallConsumer.as_asgi()),
]
