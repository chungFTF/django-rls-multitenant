"""
URL configuration for rls_project project.
"""
from django.contrib import admin
from django.urls import path
from tenants import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/branches/', views.branch_list, name='branch_list'),
    path('api/sales/', views.sales_list, name='sales_list'),
    path('api/sales-summary/', views.sales_summary, name='sales_summary'),
    path('api/context-status/', views.context_status, name='context_status'),
]
