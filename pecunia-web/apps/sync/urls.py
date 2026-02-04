"""
Sync URLs - API routing.

Provides REST API endpoints for data synchronization.
"""
from django.urls import path
from . import views

app_name = 'sync'

urlpatterns = [
    # Main sync endpoints
    path('', views.SyncBidirectionalView.as_view(), name='sync'),
    path('push/', views.SyncPushView.as_view(), name='sync-push'),
    path('pull/', views.SyncPullView.as_view(), name='sync-pull'),

    # Status endpoint
    path('status/', views.SyncStatusView.as_view(), name='sync-status'),

    # Sync logs
    path('logs/', views.SyncLogListView.as_view(), name='sync-logs'),

    # Conflict resolution
    path('conflicts/', views.SyncConflictListView.as_view(), name='sync-conflicts'),
    path(
        'conflicts/<uuid:conflict_id>/resolve/',
        views.SyncConflictResolveView.as_view(),
        name='sync-conflict-resolve'
    ),
]
