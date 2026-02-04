"""
Transactions URLs - API routing.

Provides REST API endpoints for transaction management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'categories', views.TransactionCategoryViewSet, basename='category')
router.register(r'recurring', views.RecurringTransactionViewSet, basename='recurring')
router.register(r'', views.TransactionViewSet, basename='transaction')

app_name = 'transactions'

urlpatterns = [
    path('', include(router.urls)),
]
