"""ASGI config for web_app project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_app.settings')

application = get_asgi_application()
