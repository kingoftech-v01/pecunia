"""
Accounts Frontend URLs - HTML page routing.

Provides URL patterns for user-facing HTML pages.
"""
from django.urls import path
from . import template_views

app_name = 'accounts'

urlpatterns = [
    # Authentication pages
    path('', template_views.dashboard_view, name='dashboard'),
    path('register/', template_views.register_view, name='register'),
    path('login/', template_views.login_view, name='login'),
    path('logout/', template_views.logout_view, name='logout'),

    # Profile pages
    path('profile/', template_views.profile_view, name='profile'),
    path('profile/edit/', template_views.profile_edit_view, name='profile-edit'),
    path('profile/change-password/', template_views.change_password_view, name='change-password'),

    # Settings
    path('settings/', template_views.settings_view, name='settings'),
]
