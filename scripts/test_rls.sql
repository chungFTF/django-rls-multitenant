-- =====================================
-- RLS 租戶隔離測試 SQL 腳本
-- =====================================

-- =====================================
-- 0. 清理並準備測試環境
-- =====================================
-- 切換到超級用戶身份以插入測試資料
SET ROLE postgres;

-- 清理現有測試資料（可選）
-- DELETE FROM tenants_product;
-- DELETE FROM tenants_tenant;

-- =====================================
-- 1. 插入測試租戶資料
-- =====================================
INSERT INTO tenants_tenant (name, subdomain, is_active, created_at) VALUES
    ('科技公司', 'tech-corp', true, NOW() - INTERVAL '30 days'),
    ('電商平台', 'ecommerce', true, NOW() - INTERVAL '25 days'),
    ('餐飲集團', 'restaurant', true, NOW() - INTERVAL '20 days'),
    ('時尚品牌', 'fashion', true, NOW() - INTERVAL '15 days'),
    ('教育機構', 'education', true, NOW() - INTERVAL '10 days'),
    ('醫療診所', 'medical', false, NOW() - INTERVAL '5 days')  -- 非活躍租戶
ON CONFLICT (subdomain) DO NOTHING;

-- =====================================
-- 2. 插入豐富的產品測試資料
-- =====================================

-- 租戶1：科技公司的產品
SET app.current_tenant = '1';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), '智慧手機 Pro Max', 35999.00, '最新旗艦級智慧手機，配備頂級處理器和相機系統', 1, NOW() - INTERVAL '25 days'),
    (gen_random_uuid(), '無線藍牙耳機', 4999.00, '主動降噪技術，超長續航力', 1, NOW() - INTERVAL '24 days'),
    (gen_random_uuid(), '筆記型電腦', 45999.00, '輕薄高效能商務筆電', 1, NOW() - INTERVAL '23 days'),
    (gen_random_uuid(), '智慧手錶', 12999.00, '健康監測與運動追蹤', 1, NOW() - INTERVAL '22 days'),
    (gen_random_uuid(), '平板電腦', 18999.00, '創作者專用高解析度平板', 1, NOW() - INTERVAL '21 days'),
    (gen_random_uuid(), '無線充電器', 1299.00, '快速無線充電，支援多設備', 1, NOW() - INTERVAL '20 days'),
    (gen_random_uuid(), '藍牙喇叭', 2999.00, '360度環繞音效，防水設計', 1, NOW() - INTERVAL '19 days'),
    (gen_random_uuid(), '行動電源', 899.00, '大容量快充行動電源', 1, NOW() - INTERVAL '18 days');

-- 租戶2：電商平台的產品
SET app.current_tenant = '2';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), '有機咖啡豆', 650.00, '100%阿拉比卡豆，公平貿易認證', 2, NOW() - INTERVAL '20 days'),
    (gen_random_uuid(), '手工陶瓷杯', 380.00, '職人手工製作，獨特釉色', 2, NOW() - INTERVAL '19 days'),
    (gen_random_uuid(), '竹製砧板', 450.00, '天然竹材，抗菌防霉', 2, NOW() - INTERVAL '18 days'),
    (gen_random_uuid(), '純棉床單組', 1280.00, '埃及長絨棉，親膚透氣', 2, NOW() - INTERVAL '17 days'),
    (gen_random_uuid(), '香氛蠟燭', 580.00, '天然大豆蠟，薰衣草香調', 2, NOW() - INTERVAL '16 days'),
    (gen_random_uuid(), '保溫水瓶', 890.00, '304不鏽鋼，24小時保溫', 2, NOW() - INTERVAL '15 days'),
    (gen_random_uuid(), '瑜珈墊', 1200.00, '環保TPE材質，防滑加厚', 2, NOW() - INTERVAL '14 days'),
    (gen_random_uuid(), '精油擴香器', 1580.00, '超音波霧化，七彩夜燈', 2, NOW() - INTERVAL '13 days'),
    (gen_random_uuid(), '有機蜂蜜', 720.00, '台灣龍眼蜜，無添加防腐劑', 2, NOW() - INTERVAL '12 days'),
    (gen_random_uuid(), '手工皂禮盒', 480.00, '天然植物油製作，多種香味', 2, NOW() - INTERVAL '11 days');

-- 租戶3：餐飲集團的產品
SET app.current_tenant = '3';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), '招牌牛肉麵', 180.00, '獨家湯頭，軟嫩牛肉', 3, NOW() - INTERVAL '15 days'),
    (gen_random_uuid(), '小籠包 (8顆)', 120.00, '現包現蒸，皮薄餡多', 3, NOW() - INTERVAL '14 days'),
    (gen_random_uuid(), '宮保雞丁', 160.00, '川菜經典，麻辣香鮮', 3, NOW() - INTERVAL '13 days'),
    (gen_random_uuid(), '蒸蛋', 80.00, '嫩滑蒸蛋，配料豐富', 3, NOW() - INTERVAL '12 days'),
    (gen_random_uuid(), '糖醋排骨', 220.00, '酸甜開胃，老少皆宜', 3, NOW() - INTERVAL '11 days'),
    (gen_random_uuid(), '麻婆豆腐', 140.00, '四川口味，香麻入味', 3, NOW() - INTERVAL '10 days'),
    (gen_random_uuid(), '炒河粉', 100.00, '港式炒法，煙火氣十足', 3, NOW() - INTERVAL '9 days'),
    (gen_random_uuid(), '紅燒獅子頭', 200.00, '家常口味，肉質鮮美', 3, NOW() - INTERVAL '8 days'),
    (gen_random_uuid(), '珍珠奶茶', 65.00, '手搖現做，可調糖度', 3, NOW() - INTERVAL '7 days'),
    (gen_random_uuid(), '芒果刨冰', 85.00, '新鮮芒果，夏日解暑', 3, NOW() - INTERVAL '6 days');

-- 租戶4：時尚品牌的產品
SET app.current_tenant = '4';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), '真皮手提包', 8900.00, '義大利進口牛皮，經典設計', 4, NOW() - INTERVAL '12 days'),
    (gen_random_uuid(), '羊毛圍巾', 2800.00, '100%羊毛，保暖時尚', 4, NOW() - INTERVAL '11 days'),
    (gen_random_uuid(), '絲質襯衫', 3200.00, '真絲面料，優雅剪裁', 4, NOW() - INTERVAL '10 days'),
    (gen_random_uuid(), '牛仔褲', 1800.00, '彈性舒適，修身版型', 4, NOW() - INTERVAL '9 days'),
    (gen_random_uuid(), '羊絨大衣', 12800.00, '頂級羊絨，雙面穿搭', 4, NOW() - INTERVAL '8 days'),
    (gen_random_uuid(), '珍珠項鍊', 5600.00, '淡水珍珠，經典百搭', 4, NOW() - INTERVAL '7 days'),
    (gen_random_uuid(), '太陽眼鏡', 3800.00, '防UV鏡片，時尚鏡框', 4, NOW() - INTERVAL '6 days'),
    (gen_random_uuid(), '帆布鞋', 2200.00, '經典設計，舒適透氣', 4, NOW() - INTERVAL '5 days'),
    (gen_random_uuid(), '腰帶', 1500.00, '真皮材質，金屬扣頭', 4, NOW() - INTERVAL '4 days'),
    (gen_random_uuid(), '毛線帽', 680.00, '針織保暖，多色可選', 4, NOW() - INTERVAL '3 days');

-- 租戶5：教育機構的產品
SET app.current_tenant = '5';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), 'Python程式設計課程', 4800.00, '零基礎到實戰，12週完整課程', 5, NOW() - INTERVAL '8 days'),
    (gen_random_uuid(), '英語會話班', 3200.00, '小班制教學，外師授課', 5, NOW() - INTERVAL '7 days'),
    (gen_random_uuid(), '數據分析證照班', 6500.00, '實務導向，包含證照考試', 5, NOW() - INTERVAL '6 days'),
    (gen_random_uuid(), '數學基礎班', 2800.00, '國高中數學重點複習', 5, NOW() - INTERVAL '5 days'),
    (gen_random_uuid(), 'UI/UX設計課程', 7200.00, '設計思維與實作並重', 5, NOW() - INTERVAL '4 days'),
    (gen_random_uuid(), '多益考試準備班', 4200.00, '針對性訓練，高分保證', 5, NOW() - INTERVAL '3 days'),
    (gen_random_uuid(), '創業課程', 5500.00, '從想法到實現的完整指南', 5, NOW() - INTERVAL '2 days'),
    (gen_random_uuid(), '投資理財班', 3800.00, '基礎理財知識與實務', 5, NOW() - INTERVAL '1 day');

-- 租戶6：醫療診所的產品（非活躍租戶，用於測試）
SET app.current_tenant = '6';
INSERT INTO tenants_product (id, name, price, description, tenant_id, created_at) VALUES
    (gen_random_uuid(), '健康檢查套餐', 3500.00, '全身基礎健康檢查', 6, NOW() - INTERVAL '3 days'),
    (gen_random_uuid(), '疫苗接種', 800.00, '成人疫苗接種服務', 6, NOW() - INTERVAL '2 days');

-- 重置租戶設定
RESET app.current_tenant;

-- =====================================
-- 3. 檢查插入的資料統計
-- =====================================
SELECT 
    '資料插入完成' as "狀態",
    (SELECT COUNT(*) FROM tenants_tenant) as "租戶總數",
    (SELECT COUNT(*) FROM tenants_product) as "產品總數"
;

-- 各租戶產品統計
SELECT 
    t.id as "租戶ID",
    t.name as "租戶名稱",
    t.subdomain as "子域名",
    t.is_active as "是否活躍",
    COUNT(p.id) as "產品數量"
FROM tenants_tenant t
LEFT JOIN tenants_product p ON t.id = p.tenant_id
GROUP BY t.id, t.name, t.subdomain, t.is_active
ORDER BY t.id;

-- =====================================
-- 以下是原有的 RLS 測試部分
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

-- 6. 測試租戶1的隔離（科技公司）
-- =====================================
-- 設定租戶1
SET app.current_tenant = '1';

SELECT 
    COUNT(*) as "租戶1產品數量",
    current_setting('app.current_tenant', true) as "當前租戶ID"
FROM tenants_product;

-- 查看租戶1的具體產品
SELECT 
    LEFT(id::text, 8) as "產品ID",
    name,
    price,
    tenant_id,
    '租戶1查詢' as "測試類型"
FROM tenants_product
ORDER BY created_at;

-- 7. 測試租戶2的隔離（電商平台）
-- =====================================
-- 設定租戶2
SET app.current_tenant = '2';

SELECT 
    COUNT(*) as "租戶2產品數量",
    current_setting('app.current_tenant', true) as "當前租戶ID"
FROM tenants_product;

-- 查看租戶2的具體產品
SELECT 
    LEFT(id::text, 8) as "產品ID",
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
SELECT COUNT(*) as "租戶1產品數量", '科技公司' as "租戶名稱" FROM tenants_product;

-- 切換到租戶2
SET app.current_tenant = '2';
SELECT COUNT(*) as "租戶2產品數量", '電商平台' as "租戶名稱" FROM tenants_product;

-- 切換到租戶3
SET app.current_tenant = '3';
SELECT COUNT(*) as "租戶3產品數量", '餐飲集團' as "租戶名稱" FROM tenants_product;

-- 切換到租戶4
SET app.current_tenant = '4';
SELECT COUNT(*) as "租戶4產品數量", '時尚品牌' as "租戶名稱" FROM tenants_product;

-- 切換到租戶5
SET app.current_tenant = '5';
SELECT COUNT(*) as "租戶5產品數量", '教育機構' as "租戶名稱" FROM tenants_product;

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

-- 13. 測試非活躍租戶存取
-- =====================================
-- 設定非活躍租戶ID (租戶6)
SET app.current_tenant = '6';
SELECT 
    COUNT(*) as "非活躍租戶產品數量",
    CASE 
        WHEN COUNT(*) = 0 THEN '✅ 非活躍租戶防護成功' 
        ELSE '❌ 非活躍租戶防護失敗（或需檢查RLS策略）' 
    END as "測試結果"
FROM tenants_product;

-- 14. 測試價格範圍查詢（在不同租戶上下文）
-- =====================================
-- 租戶1：高價位科技產品
SET app.current_tenant = '1';
SELECT 
    COUNT(*) as "高價產品數量(>10000)",
    AVG(price) as "平均價格"
FROM tenants_product 
WHERE price > 10000;

-- 租戶2：中低價位生活用品
SET app.current_tenant = '2';
SELECT 
    COUNT(*) as "中低價產品數量(<2000)",
    AVG(price) as "平均價格"
FROM tenants_product 
WHERE price < 2000;

-- 租戶3：餐飲產品價格分析
SET app.current_tenant = '3';
SELECT 
    MIN(price) as "最低價格",
    MAX(price) as "最高價格",
    AVG(price) as "平均價格",
    COUNT(*) as "總產品數"
FROM tenants_product;

-- 15. 清理測試設定
-- =====================================
RESET app.current_tenant;
RESET ROLE;

-- 16. 最終驗證摘要
-- =====================================
-- 使用 postgres 身份查看總體資料
SET ROLE postgres;
SELECT 
    t.name as "租戶名稱",
    t.subdomain as "子域名",
    t.is_active as "活躍狀態",
    COUNT(p.id) as "產品數量",
    COALESCE(AVG(p.price), 0) as "平均價格",
    COALESCE(MIN(p.price), 0) as "最低價格",
    COALESCE(MAX(p.price), 0) as "最高價格"
FROM tenants_tenant t
LEFT JOIN tenants_product p ON t.id = p.tenant_id
GROUP BY t.id, t.name, t.subdomain, t.is_active
ORDER BY t.id;

-- 顯示各租戶的產品類別分佈
SELECT 
    t.name as "租戶名稱",
    CASE 
        WHEN t.id = 1 THEN '科技產品'
        WHEN t.id = 2 THEN '生活用品'
        WHEN t.id = 3 THEN '餐飲美食'
        WHEN t.id = 4 THEN '時尚服飾'
        WHEN t.id = 5 THEN '教育課程'
        WHEN t.id = 6 THEN '醫療服務'
        ELSE '其他'
    END as "產品類別",
    STRING_AGG(
        CASE 
            WHEN LENGTH(p.name) > 15 THEN LEFT(p.name, 15) || '...'
            ELSE p.name
        END, 
        ', ' ORDER BY p.created_at
    ) as "產品清單"
FROM tenants_tenant t
LEFT JOIN tenants_product p ON t.id = p.tenant_id
GROUP BY t.id, t.name
ORDER BY t.id;

-- 重設角色
RESET ROLE; 