"""
Accounts URLs - API routing.

Provides REST API endpoints for authentication and user management.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

# API Router
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'profile', views.UserProfileViewSet, basename='profile')

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', views.LoginAPIView.as_view(), name='login'),
    path('logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Router URLs
    path('', include(router.urls)),
]
