"""
Budgets URLs - API routing.

Provides REST API endpoints for budget management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'items', views.BudgetItemViewSet, basename='budget-item')
router.register(r'', views.BudgetViewSet, basename='budget')

app_name = 'budgets'

urlpatterns = [
    path('', include(router.urls)),
]
