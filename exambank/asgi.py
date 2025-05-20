"""
ASGI config for exambank project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import courses.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "exambank.settings")

# 获取Django ASGI应用程序
django_asgi_app = get_asgi_application()

# 创建ASGI应用程序
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            courses.routing.websocket_urlpatterns
        )
    ),
})
