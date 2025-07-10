# SQL 測試 RLS 隔離指南

### 1. 啟動資料庫

```bash
cd django-rls-multitenant/config
docker-compose up -d
cd ..
```

### 2. 連接到資料庫

```bash
# 使用 psql 連接到資料庫
psql -h localhost -p 5433 -U postgres -d rls_db

# 或者使用 Docker 內部連接
docker exec -it django-rls-multitenant-postgres-1 psql -U postgres -d rls_db
```

### 3. 準備測試資料

首先確保已經執行了 Django migrations：

```bash
python manage.py migrate
```

然後使用 Django 管理命令創建測試資料：

```bash
python manage.py test_tenant_isolation
```

### 4. 執行 SQL 測試

```bash
# 在 psql 中執行
\i scripts/test_rls.sql

# 或者從外部執行
psql -h localhost -p 5433 -U postgres -d rls_db -f scripts/test_rls.sql
```

## 測試

### 1. 檢查 RLS 狀態

```sql
SELECT
    tablename,
    rowsecurity as "RLS啟用",
    CASE
        WHEN rowsecurity THEN '✅ 已啟用'
        ELSE '❌ 未啟用'
    END as "狀態"
FROM pg_tables
WHERE tablename LIKE '%product%';
```

**期望結果：**

```
 tablename      | RLS啟用 | 狀態
----------------+---------+--------
 tenants_product|    t    | ✅ 已啟用
```

### 2. 檢查 RLS 政策

```sql
SELECT
    policyname as "政策名稱",
    cmd as "命令",
    qual as "條件"
FROM pg_policies
WHERE tablename = 'tenants_product';
```

**期望結果：**

```
 政策名稱    | 命令 | 條件
-----------+------+----------------------------------
 tenant_policy | ALL  | (tenant_id = COALESCE(...)::integer)
 admin_policy  | ALL  | (tenant_id = COALESCE(...)::integer)
```

### 3. 測試無租戶上下文（最重要）

```sql
SET ROLE app_user;
RESET app.current_tenant;
SELECT COUNT(*) as "無租戶上下文產品數量" FROM tenants_product;
```

**期望結果：**

```
 無租戶上下文產品數量
--------------------
                  0
```

### 4. 測試租戶隔離

```sql
-- 設定租戶1
SET app.current_tenant = '1';
SELECT COUNT(*) as "租戶1產品數量" FROM tenants_product;

-- 設定租戶2
SET app.current_tenant = '2';
SELECT COUNT(*) as "租戶2產品數量" FROM tenants_product;
```

**期望結果：**

```
 租戶1產品數量
-------------
           2

 租戶2產品數量
-------------
           1
```

### 5. 測試跨租戶防護

```sql
-- 在租戶1上下文中查詢租戶2的資料
SET app.current_tenant = '1';
SELECT COUNT(*) FROM tenants_product WHERE tenant_id = 2;
```

**期望結果：**

```
 count
-------
     0
```

## 手動驗證步驟

### 步驟 1：檢查基礎設置

```sql
-- 1. 檢查資料庫連接
SELECT current_database(), current_user, current_role;

-- 2. 檢查表是否存在
\dt tenants_*

-- 3. 檢查 RLS 狀態
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'tenants_product';
```

### 步驟 2：檢查政策

```sql
-- 查看所有政策
SELECT * FROM pg_policies WHERE tablename = 'tenants_product';

-- 查看政策詳情
\d+ tenants_product
```

### 步驟 3：測試隔離

```sql
-- 切換到應用程式用戶
SET ROLE app_user;

-- 測試1：無租戶上下文
RESET app.current_tenant;
SELECT COUNT(*) FROM tenants_product; -- 應該是 0

-- 測試2：租戶1上下文
SET app.current_tenant = '1';
SELECT COUNT(*) FROM tenants_product; -- 應該是租戶1的產品數量

-- 測試3：租戶2上下文
SET app.current_tenant = '2';
SELECT COUNT(*) FROM tenants_product; -- 應該是租戶2的產品數量

-- 測試4：跨租戶查詢
SET app.current_tenant = '1';
SELECT COUNT(*) FROM tenants_product WHERE tenant_id = 2; -- 應該是 0
```

### 步驟 4：確認資料

```sql
-- 使用超級用戶查看所有資料
SET ROLE postgres;
SELECT tenant_id, COUNT(*) FROM tenants_product GROUP BY tenant_id;
```

## 成功的測試結果

如果 RLS 正常運作，應該看到：

1. **RLS 啟用狀態：** ✅ 已啟用
2. **無租戶上下文產品數量：** 0
3. **租戶 1 產品數量：** 2（或建立的數量）
4. **租戶 2 產品數量：** 1（或建立的數量）
5. **跨租戶查詢結果：** 0
6. **所有防護測試：** ✅ 成功

## 常用 SQL 命令

```sql
-- 查看目前租戶設定
SELECT current_setting('app.current_tenant', true);

-- 查看目前用戶
SELECT current_user, current_role;

-- 重設所有設定
RESET app.current_tenant;
RESET ROLE;

-- 查看表結構
\d tenants_product

-- 查看政策
\d+ tenants_product
```
