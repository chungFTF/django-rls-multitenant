# MCP Django 租戶管理系統操作記錄與實作步驟

## 概述

本文檔記錄了使用 Model Context Protocol (MCP) 與 Django 多租戶系統進行交互的完整過程，包括查詢租戶資訊、分析系統架構，以及創建完整的 MCP 建置指南的詳細步驟。

## 目錄

1. [初始查詢：檢視系統租戶](#初始查詢檢視系統租戶)
2. [深入分析：租戶詳細資訊](#深入分析租戶詳細資訊)
3. [功能限制發現與分析](#功能限制發現與分析)
4. [系統架構研究](#系統架構研究)
5. [文檔創建過程](#文檔創建過程)
6. [技術原理與實現細節](#技術原理與實現細節)
7. [遇到的挑戰與解決方案](#遇到的挑戰與解決方案)
8. [總結與建議](#總結與建議)

---

## 初始查詢：檢視系統租戶

### 操作目標

用戶要求查看當前 Django 多租戶系統中有多少租戶。

### 使用的工具

```
mcp_django-tenant-mcp_list_tenants
```

### 執行步驟

#### 步驟 1: 調用租戶列表工具

```python
# 工具調用
mcp_django-tenant-mcp_list_tenants(random_string="list")
```

#### 步驟 2: 分析返回結果

```
租戶列表:
- 測試租戶1 (test1) - 啟用 - 0 用戶 - 創建於 2025-07-10 06:53:11
- 測試租戶2 (test2) - 啟用 - 0 用戶 - 創建於 2025-07-10 06:53:11
```

### 技術原理

#### MCP 工具架構

MCP (Model Context Protocol) 是一個標準協議，允許 AI 工具與外部系統進行結構化交互。在這個案例中：

1. **客戶端**: Claude AI 助手
2. **協議**: MCP over HTTP
3. **服務端**: Django MCP 服務器
4. **數據源**: Django ORM + PostgreSQL 數據庫

#### 工具實現原理

```python
@mcp.tool()
async def list_tenants(random_string: str) -> str:
    """列出所有租戶"""
    tenants = await Tenant.objects.all()
    result = "租戶列表:\n"
    async for tenant in tenants:
        user_count = await User.objects.filter(tenant=tenant).acount()
        status = "啟用" if tenant.is_active else "停用"
        result += f"- {tenant.name} ({tenant.subdomain}) - {status} - {user_count} 用戶 - 創建於 {tenant.created_at}\n"
    return result
```

### 發現的資訊

- 系統中存在 **2 個租戶**
- 兩個租戶都處於**啟用狀態**
- 目前**沒有用戶**註冊
- 租戶創建時間相同，表明是**測試數據**

---

## 深入分析：租戶詳細資訊

### 操作目標

用戶要求查看租戶 2 的商品數量。

### 使用的工具

```
mcp_django-tenant-mcp_get_tenant_info
```

### 執行步驟

#### 步驟 1: 查詢特定租戶資訊

```python
# 工具調用
mcp_django-tenant-mcp_get_tenant_info(tenant_id="test2")
```

#### 步驟 2: 分析租戶詳細資訊

```
租戶資訊:
- 名稱: 測試租戶2
- 子域名: test2
- 創建時間: 2025-07-10 06:53:11.870087+00:00
- 狀態: 啟用
- 用戶數量: 0
```

### 技術原理

#### 多租戶架構設計

這個系統採用了 **Schema-per-tenant** 或 **Row-level Security (RLS)** 的多租戶架構：

```python
# 租戶模型
class Tenant(models.Model):
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

# 用戶模型（與租戶關聯）
class User(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    email = models.EmailField()
```

#### 工具實現細節

```python
@mcp.tool()
async def get_tenant_info(tenant_id: str, ctx: Context) -> str:
    """獲取租戶資訊"""
    try:
        # 支持從路徑參數獲取租戶ID
        path_params = getattr(ctx, 'path_params', {})
        if 'tenant_id' in path_params:
            tenant_id = path_params['tenant_id']

        # 使用異步ORM查詢
        tenant = await Tenant.objects.aget(subdomain=tenant_id)
        user_count = await User.objects.filter(tenant=tenant).acount()

        return format_tenant_info(tenant, user_count)
    except Tenant.DoesNotExist:
        return f"租戶 {tenant_id} 不存在"
```

---

## 功能限制發現與分析

### 發現的問題

在嘗試查詢租戶 2 的商品數量時，發現當前的 django-tenant-mcp 服務器**沒有提供商品查詢功能**。

### 可用功能分析

當前 MCP 服務器提供的功能：

- ✅ `list_tenants` - 列出所有租戶
- ✅ `get_tenant_info` - 獲取租戶基本資訊
- ✅ `get_tenant_users` - 獲取租戶用戶列表
- ✅ `create_demo_data` - 創建示例數據
- ✅ `add_numbers` - 數學運算工具（測試用）

### 缺失功能

- ❌ 商品管理相關工具
- ❌ 訂單查詢功能
- ❌ 庫存管理
- ❌ 銷售統計

### 解決方案建議

#### 方案 1: 擴展現有 MCP 服務器

```python
@mcp.tool()
async def get_tenant_products(ctx: Context) -> str:
    """獲取租戶商品列表"""
    path_params = getattr(ctx, 'path_params', {})
    tenant_id = path_params.get('tenant_id')

    if not tenant_id:
        return "錯誤：無法識別租戶"

    tenant = await Tenant.objects.aget(subdomain=tenant_id)
    products = await Product.objects.filter(tenant=tenant)

    return format_products_list(products)

@mcp.tool()
async def get_product_stats(tenant_id: str, ctx: Context) -> str:
    """獲取商品統計資訊"""
    tenant = await Tenant.objects.aget(subdomain=tenant_id)

    total_products = await Product.objects.filter(tenant=tenant).acount()
    active_products = await Product.objects.filter(
        tenant=tenant,
        is_active=True
    ).acount()

    return f"租戶 {tenant.name}: 總商品 {total_products}, 啟用商品 {active_products}"
```

#### 方案 2: 直接查詢數據庫

```sql
-- 查詢租戶商品數量
SELECT COUNT(*) FROM products WHERE tenant_id = (
    SELECT id FROM tenants WHERE subdomain = 'test2'
);
```

#### 方案 3: 使用其他工具

- Django Admin 界面
- 數據庫管理工具
- 自定義管理命令

---

## 系統架構研究

為了更好地理解如何實現完整的 MCP 解決方案，我進行了深入的架構研究。

### 研究方法

#### 步驟 1: 語義搜索分析

```python
# 使用 codebase_search 了解 MCP 實現
codebase_search(
    query="How is MCP implemented in Django projects?",
    target_directories=[],
    explanation="了解現有項目中 MCP 的實現方式"
)
```

#### 步驟 2: 關鍵文件分析

並行讀取多個關鍵文件：

- `django-mcp/README.md` - 主要文檔
- `django-rls-multitenant/django_mcp_stdio.py` - stdio 實現
- 其他相關配置文件

### 發現的架構模式

#### 1. ASGI 集成模式

```python
# asgi.py 架構
import os
import django
from django.core.asgi import get_asgi_application
from django_mcp import mount_mcp_server

# Django 初始化
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

# 獲取 Django 應用
django_http_app = get_asgi_application()

# 掛載 MCP 服務器
application = mount_mcp_server(
    django_http_app=django_http_app,
    mcp_base_path='/mcp/<slug:tenant_id>'  # 支持動態路徑
)
```

#### 2. 工具註冊機制

```python
# 自動發現機制
class MCPConfig(AppConfig):
    def ready(self):
        # 載入 MCP 模組
        register_mcp_modules()

        # 應用補丁
        if settings.MCP_PATCH_SDK_TOOL_LOGGING:
            patch_mcp_tool_decorator(mcp_app)
```

#### 3. 上下文傳遞模式

```python
class DjangoMCPContext(BaseContext):
    """自定義 MCP 上下文"""
    path_params: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, *, path_params: dict[str, Any] | None = None, **kwargs):
        super().__init__(**kwargs)
        self.path_params = path_params if path_params else {}
```

### 關鍵技術發現

#### 1. 異步 ORM 支持

```python
# Django 4.1+ 異步 ORM
await Model.objects.aget(pk=1)      # 獲取單個對象
await Model.objects.acount()        # 計數
await Model.objects.acreate(**data) # 創建對象
```

#### 2. 會話管理

- 使用 Redis 緩存來保持會話狀態
- 支持客戶端重連時的狀態恢復
- 負載平衡環境下的會話親和性

#### 3. 傳輸協議支持

- **SSE (Server-Sent Events)**: 用於實時通信
- **HTTP POST**: 用於消息傳遞
- **stdio**: 用於命令行集成

---

## 文檔創建過程

### 目標設定

創建一份完整的 MCP 建置到 Django App 的指南文檔。

### 文檔結構設計

#### 內容規劃

1. **基礎概念**: MCP 協議介紹、架構說明
2. **環境準備**: 系統需求、依賴安裝
3. **基本實現**: 安裝、設定、工具開發
4. **進階功能**: 資源、提示、進度報告
5. **多租戶支援**: 動態路徑、租戶隔離
6. **部署指南**: Docker、負載平衡、生產環境
7. **故障排除**: 常見問題、調試技巧
8. **最佳實踐**: 安全性、性能、文檔化

#### 實現方法

```python
edit_file(
    target_file="MCP_Django_Integration_Guide.md",
    instructions="創建一個完整的 MCP 建置到 Django app 的指南文檔",
    code_edit="# MCP (Model Context Protocol) 建置到 Django App 完整指南\n..."
)
```

### 文檔特色

#### 1. 實戰導向

- 基於真實項目經驗
- 提供可直接使用的代碼範例
- 涵蓋完整的實現流程

#### 2. 多層次內容

- **初學者**: 基本概念和簡單實現
- **中級**: 進階功能和最佳實踐
- **專家**: 生產部署和性能優化

#### 3. 問題解決

- 常見錯誤和解決方案
- 調試技巧和工具
- 性能監控方法

---

## 技術原理與實現細節

### MCP 協議原理

#### 1. 協議架構

```
┌─────────────────┐    MCP Protocol    ┌─────────────────┐
│   AI Client     │ ◄──────────────── │   MCP Server    │
│   (Claude)      │                    │   (Django)      │
└─────────────────┘                    └─────────────────┘
         │                                        │
         │                                        │
         ▼                                        ▼
┌─────────────────┐                    ┌─────────────────┐
│   Tool Calls    │                    │   Django ORM    │
│   Resources     │                    │   Business      │
│   Prompts       │                    │   Logic         │
└─────────────────┘                    └─────────────────┘
```

#### 2. 消息流程

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "get_tenant_info",
    "arguments": {
      "tenant_id": "test2"
    }
  }
}
```

### Django 集成機制

#### 1. ASGI 中間件層

```python
def mount_mcp_server(django_http_app, mcp_base_path='/mcp'):
    """掛載 MCP 服務器到 Django ASGI 應用"""

    # 創建 FastMCP 實例
    mcp_app = FastMCP()

    # 創建 Starlette 路由
    combined_app = Starlette(routes=[
        Route(f'{mcp_base_path}/sse', endpoint=handle_sse),
        Mount(f'{mcp_base_path}/messages/', app=sse.handle_post_message),
        Mount('/', app=django_http_app),
    ])

    return combined_app
```

#### 2. 工具自動發現

```python
def register_mcp_modules():
    """自動註冊 MCP 工具模組"""
    for app_config in apps.get_app_configs():
        if module_has_submodule(app_config.module, "mcp"):
            mcp_module_name = f"{app_config.name}.mcp"
            importlib.import_module(mcp_module_name)
```

#### 3. 上下文注入

```python
@functools.wraps(original_get_context)
def patched_get_context(self: FastMCP) -> DjangoMCPContext:
    """注入路徑參數到 MCP 上下文"""
    request_context = self._mcp_server.request_context
    path_params = mcp_connection_path_params.get(None)

    return DjangoMCPContext(
        request_context=request_context,
        fastmcp=self,
        path_params=path_params,
    )
```

### 多租戶實現原理

#### 1. 路徑參數提取

```python
# URL: /mcp/test2/sse
# 路徑模式: /mcp/<slug:tenant_id>/sse
# 提取結果: {"tenant_id": "test2"}

def extract_path_params(url_path, pattern):
    """從 URL 路徑中提取參數"""
    converter = URLConverter()
    match = converter.resolve(url_path, pattern)
    return match.kwargs if match else {}
```

#### 2. 租戶上下文管理

```python
# 上下文變數存儲
mcp_connection_path_params = contextvars.ContextVar(
    "mcp_connection_path_params",
    default=None
)

# 在工具中使用
@mcp.tool()
async def tenant_aware_tool(ctx: Context) -> str:
    path_params = getattr(ctx, 'path_params', {})
    tenant_id = path_params.get('tenant_id')

    # 基於租戶ID執行操作
    tenant = await Tenant.objects.aget(subdomain=tenant_id)
    return f"操作租戶: {tenant.name}"
```

---

## 遇到的挑戰與解決方案

### 挑戰 1: 功能限制

#### 問題描述

現有 MCP 服務器缺少商品查詢功能。

#### 根本原因

- MCP 工具定義不完整
- 業務邏輯覆蓋不全
- 數據模型未充分暴露

#### 解決方案

1. **短期方案**: 使用現有工具獲取基本資訊
2. **中期方案**: 擴展 MCP 工具集
3. **長期方案**: 建立完整的業務 API 層

```python
# 擴展工具實現
@mcp.tool()
async def get_comprehensive_tenant_stats(tenant_id: str, ctx: Context) -> str:
    """獲取租戶完整統計資訊"""
    tenant = await Tenant.objects.aget(subdomain=tenant_id)

    stats = {
        'users': await User.objects.filter(tenant=tenant).acount(),
        'products': await Product.objects.filter(tenant=tenant).acount(),
        'orders': await Order.objects.filter(tenant=tenant).acount(),
        'revenue': await calculate_revenue(tenant),
    }

    return format_stats(tenant, stats)
```

### 挑戰 2: 異步操作複雜性

#### 問題描述

Django ORM 異步操作的學習曲線和最佳實踐。

#### 解決方案

```python
# 正確的異步 ORM 使用
async def correct_async_pattern():
    # ✅ 使用異步方法
    user = await User.objects.aget(pk=1)
    count = await User.objects.acount()
    users = [user async for user in User.objects.all()]

    # ✅ 同步操作包裝
    sync_result = await sync_to_async(some_sync_function)()

    # ❌ 避免混合同步/異步
    # user = User.objects.get(pk=1)  # 錯誤：在異步上下文中使用同步方法
```

### 挑戰 3: 會話管理

#### 問題描述

MCP 客戶端重連時會話狀態丟失。

#### 解決方案

```python
# 會話狀態緩存
class SessionCacheManager:
    def __init__(self):
        self.cache = cache

    async def save_session_state(self, session_id, state):
        """保存會話狀態"""
        cache_key = f"mcp_session_{session_id}"
        self.cache.set(cache_key, state, timeout=3600)

    async def restore_session_state(self, session_id):
        """恢復會話狀態"""
        cache_key = f"mcp_session_{session_id}"
        return self.cache.get(cache_key)
```

---

## 總結與建議

### 完成的工作

#### 1. 系統調研

- ✅ 查詢租戶系統現狀
- ✅ 分析可用 MCP 工具
- ✅ 識別功能限制

#### 2. 架構分析

- ✅ 研究 MCP 實現模式
- ✅ 理解多租戶架構
- ✅ 掌握關鍵技術細節

#### 3. 文檔創建

- ✅ 建立完整實施指南
- ✅ 提供實戰代碼範例
- ✅ 涵蓋最佳實踐

#### 4. 知識整理

- ✅ 記錄操作過程
- ✅ 分析技術原理
- ✅ 總結經驗教訓

### 技術收穫

#### 1. MCP 協議深度理解

- 掌握 Model Context Protocol 的工作原理
- 了解 AI 工具與後端服務的集成方式
- 學會設計符合 MCP 標準的 API

#### 2. Django 異步編程

- 熟悉 Django 4.1+ 的異步 ORM 操作
- 理解 ASGI 應用的架構設計
- 掌握上下文管理和會話處理

#### 3. 多租戶架構模式

- 學習多租戶系統的設計原則
- 理解數據隔離和權限管理
- 掌握動態路徑參數的處理

### 建議的後續步驟

#### 1. 功能擴展

```python
# 建議實現的新工具
@mcp.tool()
async def get_business_insights(tenant_id: str, period: str) -> str:
    """獲取業務洞察報告"""
    pass

@mcp.tool()
async def manage_tenant_settings(tenant_id: str, settings: dict) -> str:
    """管理租戶設定"""
    pass

@mcp.tool()
async def export_tenant_data(tenant_id: str, format: str) -> str:
    """導出租戶數據"""
    pass
```

#### 2. 性能優化

- 實現查詢結果緩存
- 添加數據庫查詢優化
- 建立性能監控機制

#### 3. 安全強化

- 實現細粒度權限控制
- 添加審計日誌功能
- 建立數據訪問限制

#### 4. 部署自動化

- 創建 Docker 容器編排
- 建立 CI/CD 流水線
- 實現自動化測試

### 最佳實踐總結

#### 1. 開發流程

1. **需求分析** → 明確 MCP 工具的業務目標
2. **原型開發** → 快速驗證技術可行性
3. **迭代改進** → 根據用戶反饋持續優化
4. **文檔維護** → 保持技術文檔的時效性

#### 2. 代碼品質

```python
# 推薦的工具結構
@mcp.tool()
async def well_structured_tool(
    required_param: str,
    optional_param: str = None,
    ctx: Context = None
) -> str:
    """
    詳細的工具描述

    Args:
        required_param: 必需參數說明
        optional_param: 可選參數說明
        ctx: MCP 上下文（自動注入）

    Returns:
        操作結果描述
    """
    try:
        # 輸入驗證
        validate_input(required_param)

        # 權限檢查
        await check_permissions(ctx)

        # 業務邏輯
        result = await execute_business_logic(required_param, optional_param)

        # 日誌記錄
        await ctx.info(f"操作完成: {result}")

        return result

    except ValidationError as e:
        await ctx.warning(f"輸入驗證失敗: {e}")
        return f"參數錯誤: {e}"
    except PermissionError as e:
        await ctx.error(f"權限不足: {e}")
        return f"權限錯誤: {e}"
    except Exception as e:
        await ctx.error(f"系統錯誤: {e}")
        return f"系統錯誤，請聯繫管理員"
```

#### 3. 測試策略

```python
# MCP 工具測試範例
import pytest
from django_mcp import mcp_app

@pytest.mark.asyncio
async def test_get_tenant_info():
    """測試租戶資訊查詢工具"""
    # 準備測試數據
    tenant = await create_test_tenant()

    # 模擬 MCP 上下文
    ctx = MockContext(path_params={'tenant_id': tenant.subdomain})

    # 執行工具
    result = await get_tenant_info(tenant.subdomain, ctx)

    # 驗證結果
    assert tenant.name in result
    assert tenant.subdomain in result
    assert "啟用" in result
```

這份操作記錄詳細展示了我們從問題識別到解決方案實施的完整過程，為後續的 MCP 系統開發和維護提供了寶貴的參考資料。
