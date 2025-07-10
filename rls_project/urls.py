from django.contrib import admin
from django.urls import path
from tenants.views import product_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', product_list),
]
