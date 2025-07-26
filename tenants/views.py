from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import connection
from .models import Branch, Sales
import json
from datetime import datetime, date
from decimal import Decimal

# Branch related APIs

@csrf_exempt
def branch_list(request):
    """Branch list API - demonstrates RLS isolation"""
    if not hasattr(request, 'branch_id') or not request.branch_id:
        return JsonResponse({'error': 'Branch context required'}, status=400)
    
    if request.method == 'GET':
        try:
            # RLS ensures each branch only sees its own data
            branches = Branch.objects.filter(is_active=True)
            
            data = []
            for b in branches:
                branch_data = {
                    'id': str(b.id),
                    'name': b.name,
                    'code': b.code,
                    'address': b.address,
                    'phone': b.phone,
                    'is_active': b.is_active
                }
                data.append(branch_data)
            
            return JsonResponse({
                'branches': data,
                'count': len(data),
                'current_branch_id': str(request.branch_id)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Query failed: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Sales related APIs

@csrf_exempt
def sales_list(request):
    """Sales records API - RLS automatically filters by branch"""
    if not hasattr(request, 'branch_id') or not request.branch_id:
        return JsonResponse({'error': 'Branch context required'}, status=400)
    
    if request.method == 'GET':
        try:
            # Get query parameters
            limit = int(request.GET.get('limit', 20))
            
            # RLS automatically handles permission filtering
            sales = Sales.objects.select_related('branch').order_by('-date')[:limit]
            
            data = []
            total_amount = Decimal('0')
            
            for s in sales:
                sale_data = {
                    'id': str(s.id),
                    'branch_name': s.branch.name,
                    'date': s.date.isoformat(),
                    'amount': str(s.amount),
                    'transaction_count': s.transaction_count,
                    'product_category': s.product_category
                }
                data.append(sale_data)
                total_amount += s.amount
            
            return JsonResponse({
                'sales': data,
                'count': len(data),
                'total_amount': str(total_amount),
                'current_branch_id': str(request.branch_id)
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Query failed: {str(e)}'}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validate branch exists and is accessible
            try:
                branch = Branch.objects.get(id=data['branch_id'])
            except Branch.DoesNotExist:
                return JsonResponse({'error': 'Branch not found or access denied'}, status=404)
            
            sale = Sales.objects.create(
                branch=branch,
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                amount=Decimal(str(data['amount'])),
                transaction_count=data.get('transaction_count', 1),
                product_category=data.get('product_category', ''),
                notes=data.get('notes', '')
            )
            
            return JsonResponse({
                'success': True,
                'sale': {
                    'id': str(sale.id),
                    'branch_name': sale.branch.name,
                    'date': sale.date.isoformat(),
                    'amount': str(sale.amount)
                }
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Create failed: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# Simple sales summary for demo

@csrf_exempt
def sales_summary(request):
    """Simple sales summary - demonstrates RLS in action"""
    if not hasattr(request, 'branch_id') or not request.branch_id:
        return JsonResponse({'error': 'Branch context required'}, status=400)
    
    try:
        with connection.cursor() as cursor:
            # Simple statistics (RLS still applies)
            cursor.execute("""
                SELECT 
                    COUNT(s.id) as total_transactions,
                    SUM(s.amount) as total_revenue,
                    AVG(s.amount) as avg_amount
                FROM tenants_sales s
                JOIN tenants_branch b ON s.branch_id = b.id
            """)
            
            stats = cursor.fetchone()
            
            return JsonResponse({
                'summary': {
                    'total_transactions': stats[0] or 0,
                    'total_revenue': str(stats[1]) if stats[1] else '0',
                    'avg_amount': str(stats[2]) if stats[2] else '0'
                },
                'current_branch_id': str(request.branch_id),
                'note': 'RLS ensures isolation - each branch sees only its own data'
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Summary failed: {str(e)}'}, status=500)

# Debug endpoint for demo

@csrf_exempt
def context_status(request):
    """Check current branch context for demo purposes"""
    try:
        with connection.cursor() as cursor:
            # Check current context
            cursor.execute("SELECT * FROM current_branch_context")
            context_info = cursor.fetchone()
            
            visible_branches = Branch.objects.count()
            visible_sales = Sales.objects.count()
            
            return JsonResponse({
                'context': {
                    'current_user': context_info[0] if context_info else None,
                    'current_branch_id': context_info[1] if context_info else None,
                    'user_type': context_info[3] if context_info else None
                },
                'visibility': {
                    'branches': visible_branches,
                    'sales': visible_sales
                },
                'request_branch_id': str(request.branch_id) if hasattr(request, 'branch_id') and request.branch_id else None
            })
            
    except Exception as e:
        return JsonResponse({'error': f'Status check failed: {str(e)}'}, status=500)
