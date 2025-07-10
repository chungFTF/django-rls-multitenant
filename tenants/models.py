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