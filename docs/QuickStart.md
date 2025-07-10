# Django RLS 多租戶隔離 Quickstart 指南

從零開始建立一個使用 PostgreSQL Row Level Security (RLS) 的多租戶 Django 應用程式。

## 步驟 1: 環境準備

### 建立專案目錄和虛擬環境

```bash
mkdir django-rls-simple && cd django-rls-simple
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或者 Windows: venv\Scripts\activate
pip install django psycopg2-binary python-decouple
```

## 步驟 2: Django 專案設定

### 建立 Django 專案

```bash
django-admin startproject rls_project .
python manage.py startapp tenants
```

### 建立 .env 檔案

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=rls_db
DB_USER=app_user
DB_PASSWORD=app_pass
DB_HOST=localhost
DB_PORT=5433
```

### 更新 settings.py

```python
from decouple import config

# 基本設定
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tenants',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'tenants.middleware.TenantMiddleware',  # 租戶中介軟體
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rls_project.urls'

# 資料庫設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'CONN_MAX_AGE': 0,  # 重要：禁用連線重用
    }
}

AUTH_USER_MODEL = 'tenants.User'

LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

## 步驟 3: Docker PostgreSQL 設定

### 建立 docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: rls_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres123
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql

volumes:
  postgres_data:
```

### 建立 init.sql

```sql
-- 建立應用程式使用者
CREATE USER app_user WITH PASSWORD 'app_pass';
GRANT CONNECT ON DATABASE rls_db TO app_user;

-- 切換到應用程式資料庫
\c rls_db;

-- 建立角色和權限
CREATE ROLE app_role;
GRANT USAGE ON SCHEMA public TO app_role;
GRANT CREATE ON SCHEMA public TO app_role;
GRANT app_role TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO app_role;
```

### 啟動 PostgreSQL

```bash
docker-compose up -d
```

## 步驟 4: 建立模型

### 編輯 tenants/models.py

```python
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import connection
import uuid
import re

class Tenant(models.Model):
    name = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # 驗證子域名格式
        if self.subdomain:
            if not re.match(r'^[a-z0-9-]+$', self.subdomain):
                raise ValidationError('子域名只能包含小寫字母、數字和連字符')
            if len(self.subdomain) < 3:
                raise ValidationError('子域名至少需要3個字符')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class User(AbstractUser):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

    def clean(self):
        super().clean()
        # 確保使用者屬於 active 的租戶
        if self.tenant and not self.tenant.is_active:
            raise ValidationError('無法分配到非活躍租戶')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class TenantAwareModel(models.Model):
    """所有需要租戶隔離的模型的基類"""
    tenant_id = models.IntegerField(db_index=True)

    class Meta:
        abstract = True

    def clean(self):
        # 確保 tenant_id 是正數
        if self.tenant_id and self.tenant_id <= 0:
            raise ValidationError('租戶 ID 必須是正數')

        # 驗證租戶存在且 active
        if self.tenant_id:
            from .models import Tenant
            if not Tenant.objects.filter(id=self.tenant_id, is_active=True).exists():
                raise ValidationError('無效的租戶')

    def save(self, *args, **kwargs):
        # 自動設定 tenant_id（如果未設定且有上下文）
        if not self.tenant_id:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_setting('app.current_tenant', true)")
                    result = cursor.fetchone()
                    if result and result[0]:
                        self.tenant_id = int(result[0])
            except:
                pass

        self.full_clean()
        super().save(*args, **kwargs)

class Product(TenantAwareModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant_id']),
            models.Index(fields=['tenant_id', 'name']),
        ]
        # 防止同一租戶內重複的產品名稱
        unique_together = ['tenant_id', 'name']

    def __str__(self):
        return self.name
```

## 步驟 5: 建立中介軟體

### 建立 tenants/middleware.py

```python
from django.utils.deprecation import MiddlewareMixin
from django.db import connection, transaction
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from .models import Tenant
import logging

logger = logging.getLogger(__name__)

class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 重設租戶上下文
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET app.current_tenant")
        except Exception as e:
            logger.error(f"Failed to reset tenant context: {e}")
            return JsonResponse({'error': '系統錯誤'}, status=500)

        # 從多種來源取得租戶識別
        tenant_id = self._get_tenant_id(request)

        if tenant_id:
            try:
                tenant_id = int(tenant_id)

                # 驗證租戶存在且 active
                if not Tenant.objects.filter(id=tenant_id, is_active=True).exists():
                    logger.warning(f"Invalid tenant access attempt: {tenant_id}")
                    return JsonResponse({'error': '無效的租戶'}, status=403)

                # 如果有登入使用者，驗證使用者是否屬於該租戶
                if not isinstance(request.user, AnonymousUser):
                    if hasattr(request.user, 'tenant') and request.user.tenant.id != tenant_id:
                        logger.warning(f"User {request.user.id} attempted to access tenant {tenant_id}")
                        return JsonResponse({'error': '無權存取此租戶'}, status=403)

                # 設定租戶上下文
                with connection.cursor() as cursor:
                    cursor.execute("SET app.current_tenant = %s", [tenant_id])

                request.tenant_id = tenant_id

                # 稽核日誌
                logger.info(f"Tenant context set: {tenant_id}, User: {getattr(request.user, 'id', 'anonymous')}")

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid tenant ID format: {tenant_id}")
                return JsonResponse({'error': '無效的租戶 ID'}, status=400)
            except Exception as e:
                logger.error(f"Error setting tenant context: {e}")
                return JsonResponse({'error': '系統錯誤'}, status=500)
        else:
            request.tenant_id = None
            # 對於需要租戶的 API，應該返回錯誤
            if request.path.startswith('/api/'):
                return JsonResponse({'error': '缺少租戶資訊'}, status=400)

    def _get_tenant_id(self, request):
        """從多種來源取得租戶 ID"""
        # 1. 從 Header 取得（API 使用）
        tenant_id = request.META.get('HTTP_X_TENANT_ID')
        if tenant_id:
            return tenant_id

        # 2. 從 subdomain 取得（網頁使用）
        host = request.get_host()
        subdomain = host.split('.')[0]
        if subdomain != 'www' and subdomain != host:  # 避免 IP 或單一域名
            try:
                tenant = Tenant.objects.get(subdomain=subdomain, is_active=True)
                return tenant.id
            except Tenant.DoesNotExist:
                pass

        # 3. 從 session 取得（後備方案）
        return request.session.get('tenant_id')

    def process_response(self, request, response):
        """清理租戶上下文"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("RESET app.current_tenant")
        except Exception as e:
            logger.error(f"Failed to reset tenant context in response: {e}")

        return response
```

## 步驟 6: 執行遷移

### 建立初始遷移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 建立 RLS 遷移

```bash
python manage.py makemigrations --empty tenants --name enable_rls
```

### 編輯 RLS 遷移檔案

編輯 `tenants/migrations/000X_enable_rls.py`：

```python
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- 啟用 RLS
            ALTER TABLE tenants_product ENABLE ROW LEVEL SECURITY;
            ALTER TABLE tenants_product FORCE ROW LEVEL SECURITY;

            -- 更安全的租戶政策
            CREATE POLICY tenant_policy ON tenants_product
            FOR ALL
            USING (
                tenant_id = COALESCE(
                    NULLIF(current_setting('app.current_tenant', true), ''),
                    '0'  -- 預設為 0，確保沒有設定時無法存取任何資料
                )::int
                AND tenant_id > 0  -- 防止負數或零值
            );

            -- 防止管理員角色意外存取所有資料的政策
            CREATE POLICY admin_policy ON tenants_product
            FOR ALL
            TO app_role
            USING (
                tenant_id = COALESCE(
                    NULLIF(current_setting('app.current_tenant', true), ''),
                    '0'
                )::int
                AND tenant_id > 0
            );

            -- 確保只有應用程式角色可以存取
            REVOKE ALL ON tenants_product FROM PUBLIC;
            GRANT SELECT, INSERT, UPDATE, DELETE ON tenants_product TO app_role;

            -- 為其他需要 RLS 的表格做準備
            -- 如果有更多需要租戶隔離的表格，也要在這裡加入
            """,
            reverse_sql="""
            DROP POLICY IF EXISTS tenant_policy ON tenants_product;
            DROP POLICY IF EXISTS admin_policy ON tenants_product;
            ALTER TABLE tenants_product DISABLE ROW LEVEL SECURITY;
            GRANT ALL ON tenants_product TO PUBLIC;
            """
        )
    ]
```

### 執行 RLS 遷移

```bash
python manage.py migrate
```

## 步驟 7: 建立測試資料

### 建立管理命令

```bash
mkdir -p tenants/management/commands
touch tenants/management/__init__.py
touch tenants/management/commands/__init__.py
```

### 建立 tenants/management/commands/setup_data.py

```python
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from tenants.models import Tenant, Product
from decimal import Decimal

class Command(BaseCommand):
    help = '建立測試資料'

    def handle(self, *args, **options):
        with transaction.atomic():
            # 建立租戶
            tenant1 = Tenant.objects.create(name='公司 A', subdomain='company-a')
            tenant2 = Tenant.objects.create(name='公司 B', subdomain='company-b')

            # 租戶 1 的產品
            with connection.cursor() as cursor:
                cursor.execute("SET app.current_tenant = %s", [tenant1.id])
            Product.objects.create(name='產品A1', price=Decimal('100'), tenant_id=tenant1.id)
            Product.objects.create(name='產品A2', price=Decimal('200'), tenant_id=tenant1.id)

            # 租戶 2 的產品
            with connection.cursor() as cursor:
                cursor.execute("SET app.current_tenant = %s", [tenant2.id])
            Product.objects.create(name='產品B1', price=Decimal('300'), tenant_id=tenant2.id)
            Product.objects.create(name='產品B2', price=Decimal('400'), tenant_id=tenant2.id)

            self.stdout.write(self.style.SUCCESS('測試資料建立完成！'))
```

### 執行命令建立資料

```bash
python manage.py setup_data
```

## 步驟 8: 測試隔離

### 使用 Django Shell 測試

```bash
python manage.py shell
```

```python
from django.db import connection
from tenants.models import Tenant, Product

# 取得租戶
tenant1 = Tenant.objects.get(subdomain='company-a')
tenant2 = Tenant.objects.get(subdomain='company-b')

# 測試租戶 1
with connection.cursor() as cursor:
    cursor.execute("SET app.current_tenant = %s", [tenant1.id])
print("租戶 1 產品:", [p.name for p in Product.objects.all()])

# 測試租戶 2
with connection.cursor() as cursor:
    cursor.execute("SET app.current_tenant = %s", [tenant2.id])
print("租戶 2 產品:", [p.name for p in Product.objects.all()])

# 測試無租戶上下文
with connection.cursor() as cursor:
    cursor.execute("RESET app.current_tenant")
print("無租戶上下文產品數:", Product.objects.count())
```

## 步驟 9: 建立 API 視圖

### 編輯 tenants/views.py

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product
import json

@csrf_exempt
def product_list(request):
    if not hasattr(request, 'tenant_id') or not request.tenant_id:
        return JsonResponse({'error': '需要租戶上下文'}, status=400)

    if request.method == 'GET':
        products = Product.objects.all()
        data = [{
            'id': str(p.id),
            'name': p.name,
            'price': str(p.price),
            'description': p.description
        } for p in products]
        return JsonResponse({'products': data})

    return JsonResponse({'error': '不支援的方法'}, status=405)
```

### 編輯 rls_project/urls.py

```python
from django.contrib import admin
from django.urls import path
from tenants.views import product_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', product_list),
]
```

## 步驟 10: 測試 API

### 啟動開發伺服器

```bash
python manage.py runserver
```

### 在另一個終端測試 API

```bash
# 測試租戶 1
curl -H "X-Tenant-ID: 1" http://localhost:8000/api/products/

# 測試租戶 2
curl -H "X-Tenant-ID: 2" http://localhost:8000/api/products/

# 測試沒有租戶 ID（應該返回錯誤）
curl http://localhost:8000/api/products/
```

## 預期結果

如果一切設定正確，應該看到：

- **租戶 1** 只能看到自己的產品（產品 A1、產品 A2）
- **租戶 2** 只能看到自己的產品（產品 B1、產品 B2）
- **無租戶上下文** 時看不到任何產品（數量為 0）
- **API 測試** 顯示不同租戶獲得不同的產品列表

## 下一步

現在已經成功建立了基本的 RLS 多租戶系統，後續可以：

1. 閱讀 [完整技術文檔](RLS_完整說明文件.md) 了解更多細節
2. 執行 [完整測試套件](../tenants/management/commands/test_tenant_isolation.py) 測試完整的租戶隔離
3. 查看 [SQL 測試指南](SQL-test-tutorial.md) 進行 SQL 測試
