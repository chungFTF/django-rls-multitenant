from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def test_view(request):
    return JsonResponse({
        'message': 'Volume 掛載測試成功！',
        'status': 'working',
        'timestamp': '2025-07-16 16:36:00 - 實時更新測試'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test_view, name='test'),
    path('', test_view, name='home'),  # 根路由也指向測試
]
