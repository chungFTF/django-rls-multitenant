# MCP (Model Context Protocol) 建置到 Django App 完整指南

## 目錄

1. [MCP 簡介](#mcp-簡介)
2. [環境準備](#環境準備)
3. [安裝與設定](#安裝與設定)
4. [基本實現](#基本實現)
5. [進階功能](#進階功能)
6. [多租戶支援](#多租戶支援)
7. [部署與生產環境](#部署與生產環境)
8. [故障排除](#故障排除)
9. [最佳實踐](#最佳實踐)

## MCP 簡介

### 什麼是 MCP？

Model Context Protocol (MCP) 是一個開放標準協議，用於標準化 AI 模型與外部資源和工具的連接方式。它使 AI 工具（如 Claude、GPT）能夠安全地存取和使用外部數據源和工具。

### MCP 架構

```
AI 客戶端 (Claude, ChatGPT)
    ↓ (MCP Protocol)
Django MCP Server
    ↓ (Django ORM/API)
資料庫 & 業務邏輯
```

### 核心概念

- **Tools**: AI 可以調用的函數或操作
- **Resources**: AI 可以存取的數據資源
- **Prompts**: 預定義的提示模板
- **Context**: 請求上下文，包含路徑參數等資訊

## 環境準備

### 系統需求

- Python 3.8+
- Django 3.2+
- uvicorn (ASGI 服務器)

### 依賴套件

```bash
pip install django-mcp
pip install uvicorn
pip install python-decouple  # 用於環境變數管理
```

## 安裝與設定

### 1. 安裝 django-mcp

```bash
pip install django-mcp
```

### 2. Django 設定

在 `settings.py` 中添加：

```python
# settings.py
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_mcp',  # 添加 MCP 支援
    'your_app',    # 您的應用
]

# MCP 設定
MCP_SERVER_TITLE = "您的 Django MCP 服務器"
MCP_SERVER_INSTRUCTIONS = "提供企業資料查詢和操作工具"
MCP_SERVER_VERSION = "1.0.0"
MCP_LOG_LEVEL = "INFO"
MCP_LOG_TOOL_REGISTRATION = True
MCP_LOG_TOOL_DESCRIPTIONS = True

# 可選：啟用 URL 路徑參數支援
MCP_PATCH_SDK_GET_CONTEXT = True
MCP_PATCH_SDK_TOOL_LOGGING = True
```

### 3. ASGI 設定

創建或修改 `asgi.py`：

```python
# asgi.py
import os
import django
from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

# 設定 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')
django.setup()

# 獲取 Django HTTP 應用
django_http_app = get_asgi_application()

# 方案 1: 靜態路徑
application = mount_mcp_server(
    django_http_app=django_http_app,
    mcp_base_path='/mcp'
)

# 方案 2: 動態路徑（支援多租戶）
# application = mount_mcp_server(
#     django_http_app=django_http_app,
#     mcp_base_path='/mcp/<slug:tenant_id>'
# )
```

## 基本實現

### 1. 創建 MCP 工具模組

在您的 Django app 中創建 `mcp_tools.py`：

```python
# your_app/mcp_tools.py
from django_mcp import mcp_app as mcp
from mcp.server.fastmcp import Context
from .models import Product, User
from asgiref.sync import sync_to_async


@mcp.tool()
async def get_product_count(ctx: Context) -> str:
    """獲取商品總數"""
    try:
        await ctx.info("正在查詢商品數量...")
        count = await Product.objects.acount()
        await ctx.info(f"成功查詢到 {count} 個商品")
        return f"系統中共有 {count} 個商品"
    except Exception as e:
        await ctx.error(f"查詢商品數量時發生錯誤: {str(e)}")
        return f"錯誤：{str(e)}"


@mcp.tool()
async def search_products(name: str, ctx: Context) -> str:
    """根據名稱搜索商品"""
    try:
        await ctx.info(f"正在搜索包含 '{name}' 的商品...")

        products = []
        async for product in Product.objects.filter(name__icontains=name):
            products.append({
                'id': product.id,
                'name': product.name,
                'price': float(product.price) if product.price else 0,
                'description': product.description
            })

        if not products:
            return f"沒有找到包含 '{name}' 的商品"

        result = f"找到 {len(products)} 個商品：\n"
        for product in products[:10]:  # 限制顯示前10個
            result += f"- {product['name']} (ID: {product['id']}, 價格: ${product['price']})\n"

        if len(products) > 10:
            result += f"... 還有 {len(products) - 10} 個商品"

        return result

    except Exception as e:
        await ctx.error(f"搜索商品時發生錯誤: {str(e)}")
        return f"錯誤：{str(e)}"


@mcp.tool()
async def create_user(username: str, email: str, ctx: Context) -> str:
    """創建新用戶"""
    try:
        await ctx.info(f"正在創建用戶 {username}...")

        # 檢查用戶是否已存在
        if await User.objects.filter(username=username).aexists():
            return f"錯誤：用戶名 '{username}' 已存在"

        if await User.objects.filter(email=email).aexists():
            return f"錯誤：郵箱 '{email}' 已被使用"

        # 創建用戶
        user = await User.objects.acreate(
            username=username,
            email=email
        )

        await ctx.info(f"成功創建用戶：{username}")
        return f"成功創建用戶：{user.username} (ID: {user.id})"

    except Exception as e:
        await ctx.error(f"創建用戶時發生錯誤: {str(e)}")
        return f"錯誤：{str(e)}"
```

### 2. 確保模組被載入

在您的 `apps.py` 中確保 MCP 工具被載入：

```python
# your_app/apps.py
from django.apps import AppConfig

class YourAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'your_app'

    def ready(self):
        # 載入 MCP 工具
        try:
            import your_app.mcp_tools
        except ImportError:
            pass
```

### 3. 啟動服務器

```bash
uvicorn your_project.asgi:application --host 0.0.0.0 --port 8000
```

### 4. 測試 MCP 服務

使用 MCP Inspector 測試：

```bash
python manage.py mcp_inspector http://localhost:8000/mcp/sse
```

## 進階功能

### 1. 資源 (Resources)

```python
@mcp.resource("product://{product_id}")
async def get_product_details(product_id: str) -> str:
    """獲取指定商品的詳細資訊"""
    try:
        product = await Product.objects.aget(id=int(product_id))
        return f"""
商品詳情：
- 名稱：{product.name}
- 價格：${product.price}
- 描述：{product.description}
- 庫存：{product.stock}
- 創建時間：{product.created_at}
"""
    except Product.DoesNotExist:
        return f"商品 {product_id} 不存在"
    except Exception as e:
        return f"錯誤：{str(e)}"
```

### 2. 提示模板 (Prompts)

```python
@mcp.prompt()
async def sales_report_prompt() -> str:
    """生成銷售報告的提示模板"""
    return """
請生成一份詳細的銷售報告，包含以下內容：
1. 本月總銷售額
2. 熱銷商品排行
3. 客戶分析
4. 趨勢預測

使用可用的 MCP 工具來獲取所需數據。
"""
```

### 3. 進度報告

```python
@mcp.tool()
async def bulk_update_products(ctx: Context) -> str:
    """批量更新商品資訊"""
    products = await sync_to_async(list)(Product.objects.all())
    total = len(products)

    for i, product in enumerate(products):
        # 報告進度
        await ctx.report_progress(i, total)
        await ctx.info(f"正在處理商品：{product.name}")

        # 執行更新操作
        product.updated_at = timezone.now()
        await product.asave()

        # 模擬處理時間
        await asyncio.sleep(0.1)

    await ctx.info("批量更新完成")
    return f"成功更新 {total} 個商品"
```

## 多租戶支援

### 1. 動態路徑設定

```python
# asgi.py
application = mount_mcp_server(
    django_http_app=django_http_app,
    mcp_base_path='/mcp/<slug:tenant_id>'
)
```

### 2. 多租戶工具實現

```python
# tenants/mcp_tools.py
from django_mcp import mcp_app as mcp
from mcp.server.fastmcp import Context
from .models import Tenant, Product


@mcp.tool()
async def get_tenant_info(tenant_id: str, ctx: Context) -> str:
    """獲取租戶資訊"""
    try:
        # 從路徑參數中獲取 tenant_id
        path_params = getattr(ctx, 'path_params', {})
        if 'tenant_id' in path_params:
            tenant_id = path_params['tenant_id']
            await ctx.info(f"從路徑參數中獲取到租戶 ID: {tenant_id}")

        tenant = await Tenant.objects.aget(subdomain=tenant_id)

        return f"""
租戶資訊：
- 名稱：{tenant.name}
- 子域名：{tenant.subdomain}
- 狀態：{'啟用' if tenant.is_active else '停用'}
- 創建時間：{tenant.created_at}
"""
    except Tenant.DoesNotExist:
        return f"租戶 {tenant_id} 不存在"
    except Exception as e:
        return f"錯誤：{str(e)}"


@mcp.tool()
async def get_tenant_products(ctx: Context) -> str:
    """獲取當前租戶的商品列表"""
    path_params = getattr(ctx, 'path_params', {})
    tenant_id = path_params.get('tenant_id')

    if not tenant_id:
        return "錯誤：無法識別租戶"

    try:
        tenant = await Tenant.objects.aget(subdomain=tenant_id)
        products_count = await Product.objects.filter(tenant=tenant).acount()

        return f"租戶 {tenant.name} 共有 {products_count} 個商品"
    except Exception as e:
        return f"錯誤：{str(e)}"
```

### 3. 租戶中間件

```python
# tenants/middleware.py
class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 從 URL 或 Header 中提取租戶資訊
        tenant_id = request.META.get('HTTP_X_TENANT')
        if tenant_id:
            request.tenant_id = tenant_id

        response = self.get_response(request)
        return response
```

## 部署與生產環境

### 1. Docker 部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "your_project.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 環境變數設定

```bash
# .env.development
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/db
MCP_LOG_LEVEL=DEBUG

# .env.production
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql://user:pass@prod-db/db
MCP_LOG_LEVEL=INFO
SECURE_SSL_REDIRECT=True
```

### 3. 負載平衡設定

```nginx
# nginx.conf
upstream django_mcp {
    # 使用 IP hash 確保會話親和性
    ip_hash;
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name your-domain.com;

    location /mcp/ {
        proxy_pass http://django_mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 支援
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### 4. 會話親和性

```python
# settings.py
# 確保客戶端連接到同一個服務器實例
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
```

## 故障排除

### 1. 常見問題

**問題：RuntimeError: Received request before initialization was complete**

解決方案：

```python
# 確保在 settings.py 中啟用會話緩存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

**問題：工具未註冊**

解決方案：

```python
# 確保在 apps.py 中載入 MCP 工具
def ready(self):
    import your_app.mcp_tools
```

**問題：異步 ORM 錯誤**

解決方案：

```python
# 使用正確的異步 ORM 方法
await Model.objects.aget(pk=1)  # 不是 get()
await Model.objects.acreate()   # 不是 create()
```

### 2. 調試技巧

```python
# 啟用詳細日誌
import logging
logging.basicConfig(level=logging.DEBUG)

# 在工具中添加調試信息
@mcp.tool()
async def debug_tool(ctx: Context) -> str:
    await ctx.debug(f"Path params: {getattr(ctx, 'path_params', {})}")
    await ctx.info("工具執行中...")
    return "調試完成"
```

### 3. 性能監控

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} 執行時間: {end_time - start_time:.2f} 秒")
        return result
    return wrapper

@mcp.tool()
@monitor_performance
async def slow_operation(ctx: Context) -> str:
    # 耗時操作
    await asyncio.sleep(2)
    return "操作完成"
```

## 最佳實踐

### 1. 安全性

```python
# 輸入驗證
@mcp.tool()
async def secure_tool(user_id: str, ctx: Context) -> str:
    # 驗證輸入
    if not user_id.isdigit():
        return "錯誤：用戶 ID 必須是數字"

    # 權限檢查
    if not await has_permission(user_id, ctx):
        return "錯誤：沒有權限存取此資源"

    # 執行操作
    return "操作成功"

async def has_permission(user_id: str, ctx: Context) -> bool:
    # 實現權限檢查邏輯
    path_params = getattr(ctx, 'path_params', {})
    tenant_id = path_params.get('tenant_id')
    # ... 權限檢查邏輯
    return True
```

### 2. 錯誤處理

```python
@mcp.tool()
async def robust_tool(ctx: Context) -> str:
    try:
        # 主要邏輯
        result = await some_operation()
        await ctx.info("操作成功")
        return result
    except ValidationError as e:
        await ctx.warning(f"驗證錯誤：{str(e)}")
        return f"驗證失敗：{str(e)}"
    except PermissionError as e:
        await ctx.error(f"權限錯誤：{str(e)}")
        return f"權限不足：{str(e)}"
    except Exception as e:
        await ctx.error(f"系統錯誤：{str(e)}")
        return f"系統錯誤，請聯繫管理員"
```

### 3. 性能優化

```python
from django.core.cache import cache

@mcp.tool()
async def cached_tool(query: str, ctx: Context) -> str:
    # 檢查緩存
    cache_key = f"mcp_tool_result_{hash(query)}"
    cached_result = cache.get(cache_key)

    if cached_result:
        await ctx.info("從緩存返回結果")
        return cached_result

    # 執行查詢
    result = await expensive_query(query)

    # 緩存結果（5分鐘）
    cache.set(cache_key, result, 300)

    return result
```

### 4. 文檔化

```python
@mcp.tool()
async def well_documented_tool(
    name: str,
    age: int,
    email: str = None,
    ctx: Context = None
) -> str:
    """
    創建新用戶的工具

    Args:
        name: 用戶姓名（必填）
        age: 用戶年齡（必填，18-120）
        email: 用戶郵箱（可選）
        ctx: MCP 上下文（自動注入）

    Returns:
        成功訊息或錯誤訊息

    Raises:
        ValidationError: 當輸入數據無效時

    Example:
        創建用戶：create_user("張三", 25, "zhang@example.com")
    """
    # 實現邏輯
    pass
```

## 結論

通過這份指南，您可以成功地將 MCP 集成到您的 Django 應用中，為 AI 工具提供強大的後端支援。記住：

1. 從簡單的工具開始，逐步添加複雜功能
2. 確保適當的錯誤處理和日誌記錄
3. 在生產環境中實施適當的安全措施
4. 監控性能並優化響應時間
5. 保持文檔更新，便於維護

MCP 為您的 Django 應用開啟了與 AI 工具無縫集成的大門，讓您的業務邏輯能夠直接為 AI 助手所用。
