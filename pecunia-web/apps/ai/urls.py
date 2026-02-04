"""
AI URL Configuration.

URL patterns for AI features including API endpoints and template views.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from . import template_views

app_name = 'ai'

# API Router
router = DefaultRouter()
router.register(r'recommendations', views.AIRecommendationViewSet, basename='recommendation')

# API URL patterns
api_urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Categorization
    path('categorize/', views.CategorizeView.as_view(), name='api-categorize'),
    path('categorize/bulk/', views.BulkCategorizeView.as_view(), name='api-categorize-bulk'),

    # Chat
    path('chat/', views.ChatView.as_view(), name='api-chat'),
    path('chat/history/', views.ChatHistoryView.as_view(), name='api-chat-history'),
    path('chat/history/<uuid:session_id>/', views.ChatHistoryView.as_view(), name='api-chat-session'),

    # Insights
    path('insights/', views.InsightsView.as_view(), name='api-insights'),
]

# Template URL patterns
template_urlpatterns = [
    # Recommendations
    path('recommendations/', template_views.recommendations_list, name='recommendations'),
    path('recommendations/<uuid:pk>/action/', template_views.recommendation_action, name='recommendation-action'),
    path('recommendations/mark-all-read/', template_views.mark_all_read, name='mark-all-read'),

    # Chat
    path('chat/', template_views.chat_interface, name='chat'),
    path('chat/send/', template_views.chat_send, name='chat-send'),
    path('chat/stream/<uuid:session_id>/', template_views.chat_stream, name='chat-stream'),
    path('chat/new/', template_views.chat_new_session, name='chat-new'),
    path('chat/delete/<uuid:session_id>/', template_views.chat_delete_session, name='chat-delete'),

    # Insights
    path('insights/', template_views.insights_dashboard, name='insights'),
]

# Combined URL patterns
urlpatterns = [
    # API endpoints
    path('api/', include((api_urlpatterns, 'api'))),

    # Template views
    path('', include(template_urlpatterns)),
]
