-- =====================================
-- RLS 分店隔離測試 SQL 腳本
-- 測試不同分店之間的資料隔離
-- 每個分店只能看自己的資料
-- 
-- 執行前提：
-- 1. 已執行 init.sql
-- 2. 已執行 Django migrate (包含 RLS 策略設定)
-- =====================================

-- =====================================
-- 0. 切換到超級用戶身份
-- =====================================
SET ROLE postgres;

-- 清理現有測試資料（可選）
DELETE FROM tenants_sales;
DELETE FROM tenants_branch;

-- =====================================
-- 1. 插入測試分店資料
-- =====================================

-- 先清除任何現有的上下文設定
SET app.current_branch_id = '';

-- 暫時關閉 RLS 來插入初始資料
ALTER TABLE tenants_branch DISABLE ROW LEVEL SECURITY;
ALTER TABLE tenants_sales DISABLE ROW LEVEL SECURITY;

-- 插入測試分店
INSERT INTO tenants_branch (id, name, code, address, phone, is_active, created_at, updated_at) 
VALUES
    (gen_random_uuid(), '西門分店', 'BR001', '台北市萬華區西門町', '02-2345-6790', true, NOW() - INTERVAL '25 days', NOW()),
    (gen_random_uuid(), '東區分店', 'BR002', '台北市大安區忠孝東路四段', '02-2345-6791', true, NOW() - INTERVAL '20 days', NOW()),
    (gen_random_uuid(), '板橋分店', 'BR003', '新北市板橋區縣民大道', '02-2345-6792', true, NOW() - INTERVAL '15 days', NOW())
ON CONFLICT (code) DO NOTHING;

-- =====================================
-- 2. 為每個分店插入銷售資料
-- =====================================

-- 獲取分店 ID 並插入銷售資料
DO $$
DECLARE
    br001_id UUID;
    br002_id UUID;
    br003_id UUID;
    sale_date DATE;
    i INTEGER;
BEGIN
    -- 獲取分店 ID
    SELECT id INTO br001_id FROM tenants_branch WHERE code = 'BR001';
    SELECT id INTO br002_id FROM tenants_branch WHERE code = 'BR002';
    SELECT id INTO br003_id FROM tenants_branch WHERE code = 'BR003';
    
    -- 為西門分店插入銷售資料
    FOR i IN 1..20 LOOP
        sale_date := CURRENT_DATE - INTERVAL '1 day' * i;
        INSERT INTO tenants_sales (id, branch_id, date, amount, transaction_count, product_category, notes, created_at)
        VALUES (
            gen_random_uuid(),
            br001_id,
            sale_date,
            8000 + (i * 300) + (RANDOM() * 2000)::int,
            15 + (i % 8),
            CASE i % 3 
                WHEN 0 THEN '主餐'
                WHEN 1 THEN '飲料'
                ELSE '配菜'
            END,
            '西門分店第' || i || '天銷售記錄',
            NOW() - INTERVAL '1 day' * i
        );
    END LOOP;
    
    -- 為東區分店插入銷售資料
    FOR i IN 1..20 LOOP
        sale_date := CURRENT_DATE - INTERVAL '1 day' * i;
        INSERT INTO tenants_sales (id, branch_id, date, amount, transaction_count, product_category, notes, created_at)
        VALUES (
            gen_random_uuid(),
            br002_id,
            sale_date,
            12000 + (i * 400) + (RANDOM() * 3000)::int,
            18 + (i % 7),
            CASE i % 3 
                WHEN 0 THEN '主餐'
                WHEN 1 THEN '飲料'
                ELSE '配菜'
            END,
            '東區分店第' || i || '天銷售記錄',
            NOW() - INTERVAL '1 day' * i
        );
    END LOOP;
    
    -- 為板橋分店插入銷售資料
    FOR i IN 1..20 LOOP
        sale_date := CURRENT_DATE - INTERVAL '1 day' * i;
        INSERT INTO tenants_sales (id, branch_id, date, amount, transaction_count, product_category, notes, created_at)
        VALUES (
            gen_random_uuid(),
            br003_id,
            sale_date,
            9000 + (i * 350) + (RANDOM() * 2500)::int,
            16 + (i % 6),
            CASE i % 3 
                WHEN 0 THEN '主餐'
                WHEN 1 THEN '飲料'
                ELSE '配菜'
            END,
            '板橋分店第' || i || '天銷售記錄',
            NOW() - INTERVAL '1 day' * i
        );
    END LOOP;
    
    RAISE NOTICE '已為所有分店插入20天的銷售資料';
END $$;

-- 重新啟用 RLS
ALTER TABLE tenants_branch ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants_sales ENABLE ROW LEVEL SECURITY;

-- =====================================
-- 3. 檢查插入的資料統計
-- =====================================
SELECT 
    '資料插入完成' as "狀態",
    (SELECT COUNT(*) FROM tenants_branch) as "分店總數",
    (SELECT COUNT(*) FROM tenants_sales) as "銷售記錄總數";

-- 各分店銷售統計
SELECT 
    b.name as "分店名稱",
    b.code as "分店代碼",
    COUNT(s.id) as "銷售記錄數",
    ROUND(AVG(s.amount)::numeric, 2) as "平均銷售額",
    SUM(s.amount) as "總銷售額"
FROM tenants_branch b
LEFT JOIN tenants_sales s ON b.id = s.branch_id
GROUP BY b.id, b.name, b.code
ORDER BY b.code;

-- =====================================
-- 4. 測試 RLS 隔離效果
-- =====================================

-- 切換到應用程式用戶開始測試
SET ROLE app_user;

-- 4.1 測試沒有分店上下文時的查詢（應該返回 0 筆）
SET app.current_branch_id = '';
SELECT 
    COUNT(*) as "無上下文分店數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 隔離成功' 
        ELSE '❌ 隔離失敗' 
    END as "分店隔離測試"
FROM tenants_branch;

SELECT 
    COUNT(*) as "無上下文銷售記錄數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 隔離成功' 
        ELSE '❌ 隔離失敗' 
    END as "銷售記錄隔離測試"
FROM tenants_sales;

-- =====================================
-- 5. 測試西門分店員工權限
-- =====================================

DO $$
DECLARE
    br001_id UUID;
BEGIN
    -- 切換到 postgres 用戶來查詢分店ID
    SET ROLE postgres;
    SELECT id INTO br001_id FROM tenants_branch WHERE code = 'BR001' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br001_id);
END $$;

SELECT 
    COUNT(*) as "西門分店視角分店數量",
    '分店員工' as "用戶類型",
    'BR001' as "分店代碼"
FROM tenants_branch;

SELECT 
    b.name as "可見分店名稱",
    b.code as "分店代碼"
FROM tenants_branch b;

SELECT 
    COUNT(*) as "西門分店視角銷售記錄數量",
    ROUND(AVG(amount)::numeric, 2) as "平均銷售額",
    SUM(amount) as "總銷售額"
FROM tenants_sales;

-- =====================================
-- 6. 測試東區分店員工權限
-- =====================================

DO $$
DECLARE
    br002_id UUID;
BEGIN
    -- 切換到 postgres 用戶來查詢分店ID
    SET ROLE postgres;
    SELECT id INTO br002_id FROM tenants_branch WHERE code = 'BR002' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br002_id);
END $$;

SELECT 
    COUNT(*) as "東區分店視角分店數量",
    '分店員工' as "用戶類型",
    'BR002' as "分店代碼"
FROM tenants_branch;

SELECT 
    b.name as "可見分店名稱",
    b.code as "分店代碼"
FROM tenants_branch b;

SELECT 
    COUNT(*) as "東區分店視角銷售記錄數量",
    ROUND(AVG(amount)::numeric, 2) as "平均銷售額",
    SUM(amount) as "總銷售額"
FROM tenants_sales;

-- =====================================
-- 7. 測試板橋分店員工權限
-- =====================================

DO $$
DECLARE
    br003_id UUID;
BEGIN
    -- 切換到 postgres 用戶來查詢分店ID
    SET ROLE postgres;
    SELECT id INTO br003_id FROM tenants_branch WHERE code = 'BR003' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br003_id);
END $$;

SELECT 
    COUNT(*) as "板橋分店視角分店數量",
    '分店員工' as "用戶類型",
    'BR003' as "分店代碼"
FROM tenants_branch;

SELECT 
    b.name as "可見分店名稱",
    b.code as "分店代碼"
FROM tenants_branch b;

SELECT 
    COUNT(*) as "板橋分店視角銷售記錄數量",
    ROUND(AVG(amount)::numeric, 2) as "平均銷售額",
    SUM(amount) as "總銷售額"
FROM tenants_sales;

-- =====================================
-- 8. 測試跨分店存取防護
-- =====================================

-- 在西門分店上下文中，嘗試查看是否能看到其他分店的資料
DO $$
DECLARE
    br001_id UUID;
BEGIN
    -- 設定為西門分店上下文
    SET ROLE postgres;
    SELECT id INTO br001_id FROM tenants_branch WHERE code = 'BR001' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br001_id);
END $$;

-- 檢查是否能看到東區分店的銷售記錄（應該看不到）
SELECT 
    COUNT(*) as "西門分店上下文查看東區銷售記錄",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 跨分店防護成功' 
        ELSE '❌ 跨分店防護失敗' 
    END as "隔離測試結果"
FROM tenants_sales s
WHERE s.branch_id = (
    -- 這個子查詢應該返回 NULL，因為在西門分店上下文中看不到東區分店
    SELECT id FROM tenants_branch WHERE code = 'BR002'
);

-- =====================================
-- 9. 測試時間範圍查詢
-- =====================================

-- 西門分店：查看最近7天的銷售
DO $$
DECLARE
    br001_id UUID;
BEGIN
    SET ROLE postgres;
    SELECT id INTO br001_id FROM tenants_branch WHERE code = 'BR001' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br001_id);
END $$;

SELECT 
    '西門分店最近7天銷售' as "報表類型",
    COUNT(*) as "記錄數",
    SUM(amount) as "總銷售額",
    ROUND(AVG(amount)::numeric, 2) as "平均銷售額"
FROM tenants_sales
WHERE date >= CURRENT_DATE - INTERVAL '7 days';

-- 東區分店：查看最近7天的銷售
DO $$
DECLARE
    br002_id UUID;
BEGIN
    SET ROLE postgres;
    SELECT id INTO br002_id FROM tenants_branch WHERE code = 'BR002' LIMIT 1;
    SET ROLE app_user;
    EXECUTE format('SET app.current_branch_id = %L', br002_id);
END $$;

SELECT 
    '東區分店最近7天銷售' as "報表類型",
    COUNT(*) as "記錄數",
    SUM(amount) as "總銷售額",
    ROUND(AVG(amount)::numeric, 2) as "平均銷售額"
FROM tenants_sales
WHERE date >= CURRENT_DATE - INTERVAL '7 days';

-- =====================================
-- 10. 檢查 RLS 政策狀態
-- =====================================

-- 切換回 postgres 角色查看系統狀態
SET ROLE postgres;

-- 檢查 RLS 狀態
SELECT 
    schemaname,
    tablename,
    rowsecurity as "RLS啟用",
    CASE 
        WHEN rowsecurity THEN '✅ 已啟用' 
        ELSE '❌ 未啟用' 
    END as "狀態"
FROM pg_tables 
WHERE tablename IN ('tenants_branch', 'tenants_sales');

-- 查看所有 RLS 政策
SELECT 
    schemaname,
    tablename,
    policyname as "政策名稱",
    cmd as "命令類型",
    qual as "條件"
FROM pg_policies 
WHERE tablename IN ('tenants_branch', 'tenants_sales')
ORDER BY tablename, policyname;

-- =====================================
-- 11. 最終測試摘要
-- =====================================

-- 總體資料統計
SELECT 
    '系統總覽' as "類型",
    (SELECT COUNT(*) FROM tenants_branch) as "分店總數",
    (SELECT COUNT(*) FROM tenants_sales) as "銷售記錄總數",
    (SELECT SUM(amount) FROM tenants_sales) as "總銷售額",
    (SELECT ROUND(AVG(amount)::numeric, 2) FROM tenants_sales) as "平均銷售額";

-- 各分店統計
SELECT 
    b.name as "分店名稱",
    b.code as "分店代碼",
    COUNT(s.id) as "銷售記錄數",
    COALESCE(SUM(s.amount), 0) as "總銷售額",
    COALESCE(ROUND(AVG(s.amount)::numeric, 2), 0) as "平均銷售額"
FROM tenants_branch b
LEFT JOIN tenants_sales s ON b.id = s.branch_id
GROUP BY b.id, b.name, b.code
ORDER BY b.code;

-- 清理測試設定
SET app.current_branch_id = '';
RESET ROLE;

-- 顯示使用說明
SELECT 
    'RLS 分店隔離測試完成' as "狀態",
    '分店上下文由 Python middleware 自動設定' as "使用說明",
    '每個分店只能看到自己的資料' as "隔離說明"; 