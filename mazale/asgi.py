"""
ASGI config for mazale project.

It exposes the ASGI callable as a module-level variable named ``application``.

Note: Django Channels (WebSocket) has been removed since real-time 
functionality is now handled by the Node.js application.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mazale.settings')

application = get_asgi_application()
