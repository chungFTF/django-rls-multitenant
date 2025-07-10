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
            -- 如果您有更多需要租戶隔離的表格，也應該在這裡加入
            """,
            reverse_sql="""
            DROP POLICY IF EXISTS tenant_policy ON tenants_product;
            DROP POLICY IF EXISTS admin_policy ON tenants_product;
            ALTER TABLE tenants_product DISABLE ROW LEVEL SECURITY;
            GRANT ALL ON tenants_product TO PUBLIC;
            """
        )
    ]