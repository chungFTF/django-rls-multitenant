-- =====================================
-- RLS 租戶隔離測試 SQL 腳本
-- =====================================

-- 1. 檢查 RLS 狀態
-- =====================================
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS啟用",
    CASE 
        WHEN rowsecurity THEN '✅ 已啟用' 
        ELSE '❌ 未啟用' 
    END as "狀態"
FROM pg_tables 
WHERE tablename LIKE '%product%';

-- 2. 查看所有 RLS 政策
-- =====================================
SELECT 
    schemaname,
    tablename,
    policyname as "政策名稱",
    cmd as "命令",
    roles as "角色",
    qual as "條件"
FROM pg_policies 
WHERE tablename LIKE '%product%';

-- 3. 檢查租戶表資料
-- =====================================
SELECT 
    id,
    name,
    subdomain,
    is_active,
    created_at
FROM tenants_tenant
ORDER BY id;

-- 4. 查看產品表結構和資料（不受 RLS 限制的系統檢視）
-- =====================================
-- 使用 postgres 超級用戶身份查看所有資料
SET ROLE postgres;
SELECT 
    id,
    name,
    price,
    tenant_id,
    created_at
FROM tenants_product
ORDER BY tenant_id, created_at;

-- 5. 測試 RLS 隔離 - 切換到應用程式用戶
-- =====================================
SET ROLE app_user;

-- 5.1 測試沒有租戶上下文時的查詢（應該返回 0 筆）
RESET app.current_tenant;
SELECT 
    COUNT(*) as "無租戶上下文產品數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 隔離成功' 
        ELSE '❌ 隔離失敗' 
    END as "測試結果"
FROM tenants_product;

-- 5.2 查看目前的租戶設定
SELECT 
    current_setting('app.current_tenant', true) as "目前租戶設定",
    CASE 
        WHEN current_setting('app.current_tenant', true) = '' THEN '無設定'
        ELSE current_setting('app.current_tenant', true)
    END as "租戶值";

-- 6. 測試租戶1的隔離
-- =====================================
-- 設定租戶1（假設租戶1的 ID 是 1）
SET app.current_tenant = '1';

SELECT 
    COUNT(*) as "租戶1產品數量",
    current_setting('app.current_tenant', true) as "當前租戶ID"
FROM tenants_product;

-- 查看租戶1的具體產品
SELECT 
    id,
    name,
    price,
    tenant_id,
    '租戶1查詢' as "測試類型"
FROM tenants_product
ORDER BY created_at;

-- 7. 測試租戶2的隔離
-- =====================================
-- 設定租戶2（假設租戶2的 ID 是 2）
SET app.current_tenant = '2';

SELECT 
    COUNT(*) as "租戶2產品數量",
    current_setting('app.current_tenant', true) as "當前租戶ID"
FROM tenants_product;

-- 查看租戶2的具體產品
SELECT 
    id,
    name,
    price,
    tenant_id,
    '租戶2查詢' as "測試類型"
FROM tenants_product
ORDER BY created_at;

-- 8. 測試跨租戶存取防護
-- =====================================
-- 在租戶1上下文中嘗試查詢租戶2的資料
SET app.current_tenant = '1';

-- 這個查詢應該返回 0，因為 RLS 會阻止跨租戶存取
SELECT 
    COUNT(*) as "租戶1上下文查詢租戶2資料",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 跨租戶防護成功' 
        ELSE '❌ 跨租戶防護失敗' 
    END as "測試結果"
FROM tenants_product 
WHERE tenant_id = 2;

-- 9. 測試租戶切換
-- =====================================
-- 切換到租戶1
SET app.current_tenant = '1';
SELECT COUNT(*) as "租戶1產品數量" FROM tenants_product;

-- 切換到租戶2
SET app.current_tenant = '2';
SELECT COUNT(*) as "租戶2產品數量" FROM tenants_product;

-- 再切回租戶1
SET app.current_tenant = '1';
SELECT COUNT(*) as "切回租戶1產品數量" FROM tenants_product;

-- 10. 測試 RLS 政策的具體邏輯
-- =====================================
-- 檢查政策條件
SELECT 
    policyname,
    cmd,
    qual as "政策條件"
FROM pg_policies 
WHERE tablename = 'tenants_product'
ORDER BY policyname;

-- 11. 測試無效租戶ID
-- =====================================
-- 設定一個不存在的租戶ID
SET app.current_tenant = '999';
SELECT 
    COUNT(*) as "無效租戶ID產品數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 無效租戶防護成功' 
        ELSE '❌ 無效租戶防護失敗' 
    END as "測試結果"
FROM tenants_product;

-- 12. 測試負數租戶ID
-- =====================================
-- 設定負數租戶ID
SET app.current_tenant = '-1';
SELECT 
    COUNT(*) as "負數租戶ID產品數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 負數租戶防護成功' 
        ELSE '❌ 負數租戶防護失敗' 
    END as "測試結果"
FROM tenants_product;

-- 13. 清理測試設定
-- =====================================
RESET app.current_tenant;
RESET ROLE;

-- 14. 最終驗證摘要
-- =====================================
-- 使用 postgres 身份查看總體資料
SET ROLE postgres;
SELECT 
    tenant_id,
    COUNT(*) as "產品數量",
    STRING_AGG(name, ', ') as "產品名稱"
FROM tenants_product
GROUP BY tenant_id
ORDER BY tenant_id;

-- 重設角色
RESET ROLE; 