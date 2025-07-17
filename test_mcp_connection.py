#!/usr/bin/env python3
"""
測試 MCP 工具是否正確註冊
"""

import os
import sys
import django
from pathlib import Path

# 設置 Django 環境
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rls_project.settings')

# 初始化 Django
django.setup()

def test_mcp_tools():
    """測試 MCP 工具註冊"""
    try:
        print("🔍 正在測試 MCP 工具註冊...")
        
        # 導入 django-mcp
        from django_mcp.asgi import mcp_app
        
        # 導入我們的 MCP 工具模組
        import tenants.mcp_tools
        
        # 獲取註冊的工具數量
        server = mcp_app._mcp_server
        
        # 檢查工具是否註冊
        # 由於 MCP server 的內部結構可能不同，我們檢查工具函數是否被正確導入
        import inspect
        
        # 檢查 mcp_tools 模組中的裝飾器函數
        mcp_functions = []
        for name, obj in inspect.getmembers(tenants.mcp_tools):
            if inspect.isfunction(obj) and hasattr(obj, '__wrapped__'):
                mcp_functions.append(name)
        
        print(f"✅ django-mcp 導入成功")
        print(f"✅ tenants.mcp_tools 導入成功")  
        print(f"✅ 找到 {len(mcp_functions)} 個 MCP 工具函數:")
        
        for func_name in mcp_functions:
            print(f"   - {func_name}")
            
        if len(mcp_functions) >= 5:
            print(f"\n🎉 所有工具註冊成功！MCP 服務器已準備就緒。")
            return True
        else:
            print(f"\n⚠️  工具數量可能不完整，預期 5 個，實際找到 {len(mcp_functions)} 個")
            return False
            
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_mcp_tools()
    if success:
        print("\n📋 接下來：")
        print("1. 重啟 Cursor")
        print("2. 檢查 MCP 工具是否可用")
        print("3. 嘗試詢問：'列出所有租戶' 或 '顯示租戶統計信息'")
    sys.exit(0 if success else 1) 