"""
多租戶系統 MCP 工具

提供租戶和用戶管理功能的 MCP 工具集合
"""

from django_mcp import mcp_app
from django_mcp.decorators import log_mcp_tool_calls
from tenants.models import Tenant, User
from asgiref.sync import sync_to_async
from mcp import types
import json


@mcp_app.tool()
@log_mcp_tool_calls
async def list_tenants(limit: int = 10) -> str:
    """
    列出所有租戶
    
    Args:
        limit: 限制返回的租戶數量，預設為10
    
    Returns:
        JSON 格式的租戶列表
    """
    
    @sync_to_async
    def get_tenants():
        return list(Tenant.objects.all()[:limit].values(
            'id', 'name', 'subdomain', 'is_active', 'created_at'
        ))
    
    tenants = await get_tenants()
    
    # 格式化日期時間為字符串
    for tenant in tenants:
        if tenant['created_at']:
            tenant['created_at'] = tenant['created_at'].isoformat()
    
    return json.dumps({
        'tenants': tenants,
        'count': len(tenants)
    }, ensure_ascii=False, indent=2)


@mcp_app.tool()
@log_mcp_tool_calls
async def get_tenant_info(tenant_id: int) -> str:
    """
    獲取特定租戶的詳細信息
    
    Args:
        tenant_id: 租戶 ID
    
    Returns:
        JSON 格式的租戶詳細信息
    """
    
    @sync_to_async
    def get_tenant():
        try:
            return Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return None
    
    tenant = await get_tenant()
    
    if not tenant:
        return json.dumps({
            'success': False,
            'error': f'找不到 ID 為 {tenant_id} 的租戶'
        }, ensure_ascii=False)
    
    return json.dumps({
        'success': True,
        'tenant': {
            'id': tenant.id,
            'name': tenant.name,
            'subdomain': tenant.subdomain,
            'is_active': tenant.is_active,
            'created_at': tenant.created_at.isoformat()
        }
    }, ensure_ascii=False, indent=2)


@mcp_app.tool()
@log_mcp_tool_calls
async def list_tenant_users(tenant_id: int, limit: int = 20) -> str:
    """
    列出特定租戶的用戶
    
    Args:
        tenant_id: 租戶 ID
        limit: 限制返回的用戶數量，預設為20
    
    Returns:
        JSON 格式的用戶列表
    """
    
    @sync_to_async
    def get_users():
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            users = User.objects.filter(tenant=tenant)[:limit]
            return list(users.values(
                'id', 'username', 'email', 'first_name', 'last_name', 
                'is_active', 'date_joined', 'last_login'
            )), tenant
        except Tenant.DoesNotExist:
            return None, None
    
    users, tenant = await get_users()
    
    if not tenant:
        return json.dumps({
            'success': False,
            'error': f'找不到 ID 為 {tenant_id} 的租戶'
        }, ensure_ascii=False)
    
    # 格式化日期時間
    for user in users:
        if user['date_joined']:
            user['date_joined'] = user['date_joined'].isoformat()
        if user['last_login']:
            user['last_login'] = user['last_login'].isoformat()
    
    return json.dumps({
        'success': True,
        'tenant': {
            'id': tenant.id,
            'name': tenant.name
        },
        'users': users,
        'count': len(users)
    }, ensure_ascii=False, indent=2)


@mcp_app.tool()
@log_mcp_tool_calls
async def create_tenant(name: str, subdomain: str, description: str = "") -> str:
    """
    創建新租戶
    
    Args:
        name: 租戶名稱
        subdomain: 子域名
        description: 租戶描述（可選）
    
    Returns:
        JSON 格式的創建結果
    """
    
    @sync_to_async
    def create_tenant_sync():
        try:
            # 檢查是否已存在相同的 subdomain
            if Tenant.objects.filter(subdomain=subdomain).exists():
                return {
                    'success': False,
                    'error': f'子域名 "{subdomain}" 已存在',
                    'tenant': None
                }
            
            tenant = Tenant.objects.create(
                name=name,
                subdomain=subdomain,
                is_active=True
            )
            
            # 如果模型有 description 欄位，設置它
            if hasattr(tenant, 'description'):
                tenant.description = description
                tenant.save()
            
            return {
                'success': True,
                'message': f'成功創建租戶 "{name}"',
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'subdomain': tenant.subdomain,
                    'is_active': tenant.is_active,
                    'created_at': tenant.created_at.isoformat()
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'創建租戶失敗: {str(e)}',
                'tenant': None
            }
    
    result = await create_tenant_sync()
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp_app.tool()
@log_mcp_tool_calls
async def get_tenant_stats(random_string: str) -> str:
    """
    獲取租戶系統統計信息
    
    Returns:
        JSON 格式的統計信息
    """
    
    @sync_to_async
    def get_stats():
        try:
            total_tenants = Tenant.objects.count()
            active_tenants = Tenant.objects.filter(is_active=True).count()
            inactive_tenants = Tenant.objects.filter(is_active=False).count()
            total_users = User.objects.count()
            
            # 獲取最近創建的租戶
            recent_tenants = list(Tenant.objects.order_by('-created_at')[:5].values(
                'id', 'name', 'subdomain', 'is_active', 'created_at'
            ))
            
            # 格式化日期
            for tenant in recent_tenants:
                if tenant['created_at']:
                    tenant['created_at'] = tenant['created_at'].isoformat()
            
            return {
                'success': True,
                'stats': {
                    'total_tenants': total_tenants,
                    'active_tenants': active_tenants,
                    'inactive_tenants': inactive_tenants,
                    'total_users': total_users
                },
                'recent_tenants': recent_tenants
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'獲取統計失敗: {str(e)}'
            }
    
    result = await get_stats()
    return json.dumps(result, ensure_ascii=False, indent=2) 