from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product
import json

@csrf_exempt
def product_list(request):
    if not hasattr(request, 'tenant_id') or not request.tenant_id:
        return JsonResponse({'error': '需要租戶上下文'}, status=400)
    
    if request.method == 'GET':
        products = Product.objects.all()
        data = [{
            'id': str(p.id),
            'name': p.name,
            'price': str(p.price),
            'description': p.description
        } for p in products]
        return JsonResponse({'products': data})
    
    return JsonResponse({'error': '不支援的方法'}, status=405)
