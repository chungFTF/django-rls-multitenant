#!/usr/bin/env python3
"""
Django MCP Stdio Server
為 Cursor 全域配置提供的 stdio 接口
"""

import os
import sys
import django
from pathlib import Path

# 添加專案根目錄到 Python 路徑
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# 設置 Django 環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rls_project.settings')

# 初始化 Django
django.setup()

# 導入 django-mcp 相關模組
from django_mcp.asgi import mcp_app
from mcp.server import stdio

# 導入我們的 MCP 工具模組以確保工具被註冊
import tenants.mcp_tools

def main():
    """啟動 MCP 服務器（stdio 模式）"""
    try:
        # 導入 asyncio 並使用正確的 API
        import asyncio
        from mcp.server.stdio import stdio_server
        
        async def run_server():
            async with stdio_server() as (read_stream, write_stream):
                await mcp_app._mcp_server.run(
                    read_stream, write_stream, mcp_app._mcp_server.create_initialization_options()
                )
        
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nMCP 服務器已停止")
    except Exception as e:
        print(f"MCP 服務器啟動失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 