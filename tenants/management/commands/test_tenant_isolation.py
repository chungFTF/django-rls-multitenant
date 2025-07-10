from django.core.management.base import BaseCommand
from django.db import connection
from tenants.models import Tenant, Product
from decimal import Decimal
import sys

class Command(BaseCommand):
    help = '測試租戶隔離功能'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_results = []
        self.tenant1 = None
        self.tenant2 = None
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='清理測試資料',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='顯示詳細資訊',
        )
    
    def handle(self, *args, **options):
        self.verbosity = options.get('verbosity', 1)
        self.verbose = options.get('verbose', False)
        
        if options.get('cleanup'):
            self.cleanup_test_data()
            return
        
        self.stdout.write(self.style.SUCCESS('🚀 開始租戶隔離測試...'))
        
        try:
            self.setup_test_data()
            self.test_basic_isolation()
            self.test_cross_tenant_access()
            self.test_without_tenant_context()
            self.test_rls_policies()
            self.test_tenant_switching()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 測試過程中發生錯誤: {str(e)}'))
            if self.verbose:
                import traceback
                traceback.print_exc()
        
        finally:
            self.reset_tenant_context()
            self.print_summary()
    
    def log_test(self, test_name, passed, message=""):
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        
        if passed:
            self.stdout.write(self.style.SUCCESS(f"{status}: {test_name}"))
        else:
            self.stdout.write(self.style.ERROR(f"{status}: {test_name}"))
            
        if message:
            self.stdout.write(f"   {message}")
    
    def setup_test_data(self):
        """建立測試資料"""
        self.stdout.write("\n🔧 建立測試資料...")
        
        # 清理現有測試資料
        Tenant.objects.filter(subdomain__startswith='test').delete()
        
        # 建立兩個測試租戶
        self.tenant1 = Tenant.objects.create(
            name="測試租戶1",
            subdomain="test1",
            is_active=True
        )
        self.tenant2 = Tenant.objects.create(
            name="測試租戶2", 
            subdomain="test2",
            is_active=True
        )
        
        self.stdout.write(f"   建立租戶1: {self.tenant1.name} (ID: {self.tenant1.id})")
        self.stdout.write(f"   建立租戶2: {self.tenant2.name} (ID: {self.tenant2.id})")
        
        # 為租戶1建立產品
        self.set_tenant_context(self.tenant1.id)
        Product.objects.create(
            name="租戶1產品A",
            price=Decimal("100.00"),
            description="這是租戶1的產品",
            tenant_id=self.tenant1.id
        )
        
        Product.objects.create(
            name="租戶1產品B",
            price=Decimal("200.00"),
            description="這是租戶1的另一個產品",
            tenant_id=self.tenant1.id
        )
        
        # 為租戶2建立產品
        self.set_tenant_context(self.tenant2.id)
        Product.objects.create(
            name="租戶2產品C",
            price=Decimal("150.00"),
            description="這是租戶2的產品",
            tenant_id=self.tenant2.id
        )
        
        self.stdout.write("   為租戶1建立2個產品，為租戶2建立1個產品")
    
    def set_tenant_context(self, tenant_id):
        """設定租戶上下文"""
        with connection.cursor() as cursor:
            cursor.execute("SET app.current_tenant = %s", [tenant_id])
    
    def reset_tenant_context(self):
        """重設租戶上下文"""
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")
    
    def test_basic_isolation(self):
        """測試基本的租戶隔離"""
        self.stdout.write("\n🧪 測試基本租戶隔離...")
        
        # 測試租戶1只能看到自己的資料
        self.set_tenant_context(self.tenant1.id)
        tenant1_count = Product.objects.count()
        
        passed = tenant1_count == 2
        self.log_test(
            "租戶1隔離測試",
            passed,
            f"期望看到 2 個產品，實際看到 {tenant1_count} 個"
        )
        
        # 測試租戶2只能看到自己的資料
        self.set_tenant_context(self.tenant2.id)
        tenant2_count = Product.objects.count()
        
        passed = tenant2_count == 1
        self.log_test(
            "租戶2隔離測試",
            passed,
            f"期望看到 1 個產品，實際看到 {tenant2_count} 個"
        )
    
    def test_cross_tenant_access(self):
        """測試跨租戶存取防護"""
        self.stdout.write("\n🔒 測試跨租戶存取防護...")
        
        # 在租戶1上下文中查詢租戶2的資料
        self.set_tenant_context(self.tenant1.id)
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tenants_product WHERE tenant_id = %s", [self.tenant2.id])
            count = cursor.fetchone()[0]
        
        passed = count == 0
        self.log_test(
            "跨租戶存取防護測試",
            passed,
            f"在租戶1上下文中查詢租戶2的產品，結果數量: {count} (應該為0)"
        )
    
    def test_without_tenant_context(self):
        """測試沒有租戶上下文的情況"""
        self.stdout.write("\n🚫 測試沒有租戶上下文的情況...")
        
        self.reset_tenant_context()
        count = Product.objects.count()
        
        passed = count == 0
        self.log_test(
            "無租戶上下文測試",
            passed,
            f"沒有租戶上下文時查詢產品，結果數量: {count} (應該為0)"
        )
    
    def test_rls_policies(self):
        """測試 RLS 政策"""
        self.stdout.write("\n📋 測試 RLS 政策...")
        
        with connection.cursor() as cursor:
            # 檢查 RLS 是否啟用
            cursor.execute("""
                SELECT schemaname, tablename, rowsecurity 
                FROM pg_tables 
                WHERE tablename = 'tenants_product'
            """)
            result = cursor.fetchone()
            
            if result:
                rls_enabled = result[2]
                self.log_test(
                    "RLS 啟用狀態",
                    rls_enabled,
                    f"RLS 狀態: {'已啟用' if rls_enabled else '未啟用'}"
                )
            else:
                self.log_test("RLS 啟用狀態", False, "無法找到 tenants_product 表")
            
            # 檢查政策是否存在
            cursor.execute("""
                SELECT policyname, cmd, qual 
                FROM pg_policies 
                WHERE tablename = 'tenants_product'
            """)
            policies = cursor.fetchall()
            
            passed = len(policies) >= 2
            self.log_test(
                "RLS 政策存在",
                passed,
                f"找到 {len(policies)} 個政策"
            )
            
            if self.verbose:
                for policy in policies:
                    self.stdout.write(f"   政策: {policy[0]}, 命令: {policy[1]}")
    
    def test_tenant_switching(self):
        """測試租戶切換"""
        self.stdout.write("\n🔄 測試租戶切換...")
        
        # 在租戶1上下文中查詢
        self.set_tenant_context(self.tenant1.id)
        count1 = Product.objects.count()
        
        # 切換到租戶2
        self.set_tenant_context(self.tenant2.id)
        count2 = Product.objects.count()
        
        # 再切回租戶1
        self.set_tenant_context(self.tenant1.id)
        count1_again = Product.objects.count()
        
        passed = count1 == count1_again and count1 != count2
        self.log_test(
            "租戶切換測試",
            passed,
            f"租戶1: {count1} 個產品, 租戶2: {count2} 個產品, 切回租戶1: {count1_again} 個產品"
        )
    
    def cleanup_test_data(self):
        """清理測試資料"""
        self.stdout.write("🧹 清理測試資料...")
        
        deleted_count = Tenant.objects.filter(subdomain__startswith='test').delete()[0]
        self.stdout.write(self.style.SUCCESS(f"已刪除 {deleted_count} 個測試租戶"))
    
    def print_summary(self):
        """印出測試摘要"""
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 測試結果摘要")
        self.stdout.write("="*60)
        
        passed_count = sum(1 for result in self.test_results if result['passed'])
        total_count = len(self.test_results)
        
        self.stdout.write(f"總測試數: {total_count}")
        self.stdout.write(f"通過測試: {passed_count}")
        self.stdout.write(f"失敗測試: {total_count - passed_count}")
        self.stdout.write(f"成功率: {passed_count/total_count*100:.1f}%")
        
        if passed_count == total_count:
            self.stdout.write(self.style.SUCCESS("\n🎉 所有測試都通過！租戶隔離功能正常運作。"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  部分測試失敗，請檢查租戶隔離設定。"))
            
            self.stdout.write("\n失敗的測試:")
            for result in self.test_results:
                if not result['passed']:
                    self.stdout.write(self.style.ERROR(f"  - {result['test']}: {result['message']}")) 