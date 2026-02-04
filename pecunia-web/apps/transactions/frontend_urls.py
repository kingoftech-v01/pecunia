"""
Transactions Frontend URLs - HTML page routing.

Provides URL patterns for user-facing HTML pages.
"""
from django.urls import path
from . import template_views

app_name = 'transactions'

urlpatterns = [
    # Transaction pages
    path('', template_views.transaction_list, name='transaction_list'),
    path('create/', template_views.transaction_create, name='transaction_create'),
    path('<uuid:pk>/', template_views.transaction_detail, name='transaction_detail'),
    path('<uuid:pk>/edit/', template_views.transaction_update, name='transaction_update'),
    path('<uuid:pk>/delete/', template_views.transaction_delete, name='transaction_delete'),

    # Category pages
    path('categories/', template_views.category_list, name='category_list'),
    path('categories/create/', template_views.category_create, name='category_create'),

    # Recurring transaction pages
    path('recurring/', template_views.recurring_list, name='recurring_list'),
    path('recurring/create/', template_views.recurring_create, name='recurring_create'),
]
