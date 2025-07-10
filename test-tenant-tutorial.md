# 租戶隔離測試指南

## 環境準備

### 1. 啟動資料庫

```bash
cd django-rls-multitenant
docker-compose up -d
```

### 2. 配置環境變數

將 `test_config.env` 複製為 `.env` 並根據需要調整：

```bash
cp test_config.env .env
```

### 3. 安裝依賴

```bash
pip install django psycopg2-binary python-decouple
```

### 4. 執行 migration

```bash
python manage.py migrate
```

## 測試方法

### 方法一：使用 Django 管理命令（推薦）

#### 基本測試

```bash
python manage.py test_tenant_isolation
```

#### 詳細測試

```bash
python manage.py test_tenant_isolation --verbose
```

#### 清理測試資料

```bash
python manage.py test_tenant_isolation --cleanup
```

### 方法二：使用獨立測試腳本

```bash
python test_tenant_isolation.py
```

## 測試項目說明

### 1. 基本租戶隔離測試

- 驗證租戶 1 只能看到自己的資料
- 驗證租戶 2 只能看到自己的資料

### 2. 跨租戶存取防護測試

- 確認在租戶 1 的上下文中無法存取租戶 2 的資料

### 3. 無租戶上下文測試

- 驗證沒有設定租戶上下文時無法存取任何資料

### 4. RLS 政策測試

- 檢查 Row Level Security 是否正確啟用
- 驗證相關政策是否存在

### 5. 租戶切換測試

- 測試在不同租戶上下文間切換的正確性

## 手動測試

### 1. 開啟 Django Shell

```bash
python manage.py shell
```

### 2. 執行手動測試

```python
from django.db import connection
from tenants.models import Tenant, Product
from decimal import Decimal

# 建立測試租戶
tenant1 = Tenant.objects.create(name="手動測試租戶1", subdomain="manual1", is_active=True)
tenant2 = Tenant.objects.create(name="手動測試租戶2", subdomain="manual2", is_active=True)

# 設定租戶1上下文並建立產品
with connection.cursor() as cursor:
    cursor.execute("SET app.current_tenant = %s", [tenant1.id])

Product.objects.create(name="手動產品1", price=Decimal("100.00"), tenant_id=tenant1.id)
print(f"租戶1產品數量: {Product.objects.count()}")  # 應該是 1

# 切換到租戶2
with connection.cursor() as cursor:
    cursor.execute("SET app.current_tenant = %s", [tenant2.id])

Product.objects.create(name="手動產品2", price=Decimal("200.00"), tenant_id=tenant2.id)
print(f"租戶2產品數量: {Product.objects.count()}")  # 應該是 1

# 切回租戶1
with connection.cursor() as cursor:
    cursor.execute("SET app.current_tenant = %s", [tenant1.id])

print(f"切回租戶1後的產品數量: {Product.objects.count()}")  # 應該是 1

# 重設租戶上下文
with connection.cursor() as cursor:
    cursor.execute("RESET app.current_tenant")

print(f"無租戶上下文的產品數量: {Product.objects.count()}")  # 應該是 0
```

## 透過 API 測試

### 1. 建立測試 API 視圖

創建 `tenants/views.py`：

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .models import Product
import json

@method_decorator(csrf_exempt, name='dispatch')
class ProductListView(View):
    def get(self, request):
        # 檢查是否有租戶上下文
        tenant_id = getattr(request, 'tenant_id', None)
        if not tenant_id:
            return JsonResponse({'error': '缺少租戶資訊'}, status=400)

        products = Product.objects.all()
        data = [{
            'id': str(p.id),
            'name': p.name,
            'price': str(p.price),
            'tenant_id': p.tenant_id
        } for p in products]

        return JsonResponse({
            'tenant_id': tenant_id,
            'products': data,
            'count': len(data)
        })
```

### 2. 設定 URL

在 `rls_project/urls.py` 中加入：

```python
from django.contrib import admin
from django.urls import path
from tenants.views import ProductListView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', ProductListView.as_view(), name='product-list'),
]
```

### 3. 測試 API

```bash
# 使用 Header 指定租戶
curl -H "X-Tenant-ID: 1" http://localhost:8000/api/products/

# 不指定租戶（應該回傳錯誤）
curl http://localhost:8000/api/products/
```

## 期望的測試結果

### 成功的測試應該顯示：

- ✅ 租戶 1 隔離測試: 期望看到 2 個產品，實際看到 2 個
- ✅ 租戶 2 隔離測試: 期望看到 1 個產品，實際看到 1 個
- ✅ 跨租戶存取防護測試: 在租戶 1 上下文中查詢租戶 2 的產品，結果數量: 0
- ✅ 無租戶上下文測試: 沒有租戶上下文時查詢產品，結果數量: 0
- ✅ RLS 啟用狀態: RLS 狀態: 已啟用
- ✅ RLS 政策存在: 找到 2 個政策
- ✅ 租戶切換測試: 租戶 1: 2 個產品, 租戶 2: 1 個產品, 切回租戶 1: 2 個產品

### 成功率應該是 100%

## 故障排除

### 1. 連接資料庫失敗

- 確認 PostgreSQL 容器正在運行
- 檢查 `.env` 文件中的資料庫連接設定

### 2. RLS 政策未生效

- 確認 migration 已正確執行
- 檢查資料庫中的政策是否存在：

```sql
SELECT * FROM pg_policies WHERE tablename = 'tenants_product';
```

### 3. 租戶隔離失效

- 確認 `app.current_tenant` 設定正確
- 檢查 middleware 是否正確載入

### 4. 權限問題

- 確認 `app_user` 有適當的權限
- 檢查 `init.sql` 是否正確執行

## 清理

### 清理測試資料

```bash
python manage.py test_tenant_isolation --cleanup
```

### 停止資料庫容器

```bash
docker-compose down
```
