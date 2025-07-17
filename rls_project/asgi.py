"""
ASGI config for rls_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

# 新增 django-mcp 導入
from django_mcp import mount_mcp_server

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rls_project.settings")

# 初始化 Django
django.setup()

# 獲取 Django HTTP 應用
django_http_app = get_asgi_application()

# 使用 MCP 掛載 Django 應用，並提供動態路徑參數支援
application = mount_mcp_server(django_http_app=django_http_app, mcp_base_path='/mcp/<slug:tenant_id>')
