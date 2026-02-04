"""
Dashboard URL Configuration.

Defines URL patterns for both API and frontend dashboard routes.
"""
from django.urls import path
from . import views, template_views, landing_views

app_name = 'dashboard'

# API URL patterns (for /api/v1/dashboard/)
api_urlpatterns = [
    path('summary/', views.DashboardSummaryView.as_view(), name='api-summary'),
    path('balance/', views.DashboardBalanceView.as_view(), name='api-balance'),
    path('spending/', views.DashboardSpendingView.as_view(), name='api-spending'),
    path('insights/', views.DashboardInsightsView.as_view(), name='api-insights'),
    path('quick-actions/', views.QuickActionsView.as_view(), name='api-quick-actions'),
]

# Frontend URL patterns (for template views)
frontend_urlpatterns = [
    path('', template_views.dashboard_home, name='home'),

    # HTMX widget endpoints
    path('widgets/balance/', template_views.get_balance_data, name='widget-balance'),
    path('widgets/transactions/', template_views.get_recent_transactions, name='widget-transactions'),
    path('widgets/budget/', template_views.get_budget_overview, name='widget-budget'),
    path('widgets/insights/', template_views.get_ai_insights, name='widget-insights'),

    # Chart data endpoints
    path('charts/spending/', template_views.get_spending_chart_data, name='chart-spending'),
    path('charts/balance/', template_views.get_balance_chart_data, name='chart-balance'),
]

# Landing page URL patterns (public pages)
landing_urlpatterns = [
    path('', landing_views.landing_home, name='index'),
    path('features/', landing_views.features_page, name='features'),
    path('pricing/', landing_views.pricing_page, name='pricing'),
    path('about/', landing_views.about_page, name='about'),
    path('contact/', landing_views.contact_page, name='contact'),
    path('privacy/', landing_views.privacy_page, name='privacy'),
    path('terms/', landing_views.terms_page, name='terms'),
]

# Combined URL patterns for inclusion
urlpatterns = frontend_urlpatterns
