#!/usr/bin/env python
"""
租戶隔離測試腳本
這個腳本會測試 RLS 政策是否正確實現了租戶隔離
"""

import os
import sys
import django
from django.conf import settings

# 設定 Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rls_project.settings')
django.setup()

from django.db import connection, transaction
from tenants.models import Tenant, Product, User
from django.contrib.auth.models import AnonymousUser
import uuid
from decimal import Decimal

class TenantIsolationTest:
    def __init__(self):
        self.test_results = []
        self.tenant1 = None
        self.tenant2 = None
        
    def log_test(self, test_name, passed, message=""):
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })
        print(f"{status}: {test_name}")
        if message:
            print(f"   {message}")
    
    def setup_test_data(self):
        """建立測試資料"""
        print("\n🔧 建立測試資料...")
        
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
        
        print(f"   建立租戶1: {self.tenant1.name} (ID: {self.tenant1.id})")
        print(f"   建立租戶2: {self.tenant2.name} (ID: {self.tenant2.id})")
        
        # 為租戶1建立產品
        self.set_tenant_context(self.tenant1.id)
        product1 = Product.objects.create(
            name="租戶1產品A",
            price=Decimal("100.00"),
            description="這是租戶1的產品",
            tenant_id=self.tenant1.id
        )
        
        product2 = Product.objects.create(
            name="租戶1產品B",
            price=Decimal("200.00"),
            description="這是租戶1的另一個產品",
            tenant_id=self.tenant1.id
        )
        
        # 為租戶2建立產品
        self.set_tenant_context(self.tenant2.id)
        product3 = Product.objects.create(
            name="租戶2產品C",
            price=Decimal("150.00"),
            description="這是租戶2的產品",
            tenant_id=self.tenant2.id
        )
        
        print(f"   為租戶1建立2個產品，為租戶2建立1個產品")
        
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
        print("\n🧪 測試基本租戶隔離...")
        
        # 測試租戶1只能看到自己的資料
        self.set_tenant_context(self.tenant1.id)
        tenant1_products = Product.objects.all()
        tenant1_count = tenant1_products.count()
        
        expected_count = 2
        passed = tenant1_count == expected_count
        self.log_test(
            "租戶1隔離測試",
            passed,
            f"期望看到 {expected_count} 個產品，實際看到 {tenant1_count} 個"
        )
        
        # 測試租戶2只能看到自己的資料
        self.set_tenant_context(self.tenant2.id)
        tenant2_products = Product.objects.all()
        tenant2_count = tenant2_products.count()
        
        expected_count = 1
        passed = tenant2_count == expected_count
        self.log_test(
            "租戶2隔離測試",
            passed,
            f"期望看到 {expected_count} 個產品，實際看到 {tenant2_count} 個"
        )
    
    def test_cross_tenant_access(self):
        """測試跨租戶存取防護"""
        print("\n🔒 測試跨租戶存取防護...")
        
        # 嘗試在租戶1上下文中存取租戶2的產品
        self.set_tenant_context(self.tenant1.id)
        
        # 直接通過 SQL 查詢確認隔離
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
        print("\n🚫 測試沒有租戶上下文的情況...")
        
        # 重設租戶上下文
        self.reset_tenant_context()
        
        # 查詢產品應該返回空結果
        products = Product.objects.all()
        count = products.count()
        
        passed = count == 0
        self.log_test(
            "無租戶上下文測試",
            passed,
            f"沒有租戶上下文時查詢產品，結果數量: {count} (應該為0)"
        )
    
    def test_rls_policies(self):
        """測試 RLS 政策"""
        print("\n📋 測試 RLS 政策...")
        
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
                passed = rls_enabled
                self.log_test(
                    "RLS 啟用狀態",
                    passed,
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
            
            passed = len(policies) >= 2  # 應該至少有 tenant_policy 和 admin_policy
            self.log_test(
                "RLS 政策存在",
                passed,
                f"找到 {len(policies)} 個政策"
            )
            
            for policy in policies:
                print(f"   政策: {policy[0]}, 命令: {policy[1]}")
    
    def test_tenant_switching(self):
        """測試租戶切換"""
        print("\n🔄 測試租戶切換...")
        
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
    
    def test_concurrent_access(self):
        """測試並發存取"""
        print("\n⚡ 測試並發存取...")
        
        import threading
        results = {}
        
        def query_tenant(tenant_id, result_key):
            try:
                self.set_tenant_context(tenant_id)
                count = Product.objects.count()
                results[result_key] = count
            except Exception as e:
                results[result_key] = f"錯誤: {str(e)}"
        
        # 建立執行緒並執行
        thread1 = threading.Thread(target=query_tenant, args=(self.tenant1.id, 'tenant1'))
        thread2 = threading.Thread(target=query_tenant, args=(self.tenant2.id, 'tenant2'))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        passed = (
            isinstance(results.get('tenant1'), int) and 
            isinstance(results.get('tenant2'), int) and
            results['tenant1'] == 2 and 
            results['tenant2'] == 1
        )
        
        self.log_test(
            "並發存取測試",
            passed,
            f"並發結果 - 租戶1: {results.get('tenant1')}, 租戶2: {results.get('tenant2')}"
        )
    
    def run_all_tests(self):
        """執行所有測試"""
        print("🚀 開始租戶隔離測試...")
        
        try:
            self.setup_test_data()
            self.test_basic_isolation()
            self.test_cross_tenant_access()
            self.test_without_tenant_context()
            self.test_rls_policies()
            self.test_tenant_switching()
            self.test_concurrent_access()
            
        except Exception as e:
            print(f"❌ 測試過程中發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.reset_tenant_context()
            self.print_summary()
    
    def print_summary(self):
        """印出測試摘要"""
        print("\n" + "="*60)
        print("📊 測試結果摘要")
        print("="*60)
        
        passed_count = sum(1 for result in self.test_results if result['passed'])
        total_count = len(self.test_results)
        
        print(f"總測試數: {total_count}")
        print(f"通過測試: {passed_count}")
        print(f"失敗測試: {total_count - passed_count}")
        print(f"成功率: {passed_count/total_count*100:.1f}%")
        
        if passed_count == total_count:
            print("\n🎉 所有測試都通過！租戶隔離功能正常運作。")
        else:
            print("\n⚠️  部分測試失敗，請檢查租戶隔離設定。")
            
            print("\n失敗的測試:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")

if __name__ == "__main__":
    test = TenantIsolationTest()
    test.run_all_tests() 