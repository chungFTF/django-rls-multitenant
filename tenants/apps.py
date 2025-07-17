from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenants"

    def ready(self):
        """當應用準備就緒時，載入 MCP 工具"""
        try:
            # 載入 MCP 工具
            from . import mcp_tools
        except ImportError:
            # 如果載入失敗（例如在開發階段），忽略錯誤
            pass