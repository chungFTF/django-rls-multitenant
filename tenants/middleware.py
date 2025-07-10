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