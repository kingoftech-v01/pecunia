"""
AI Admin Configuration.

Django admin configuration for AI models.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import AIRecommendation, AICategorizationLog, AIAnalysisCache


@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    """Admin configuration for AI recommendations."""

    list_display = [
        'title',
        'user',
        'type',
        'priority_badge',
        'is_read',
        'is_dismissed',
        'created_at',
    ]
    list_filter = [
        'type',
        'priority',
        'is_read',
        'is_dismissed',
        'created_at',
    ]
    search_fields = [
        'title',
        'content',
        'user__email',
        'user__first_name',
        'user__last_name',
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'title', 'content')
        }),
        ('Classification', {
            'fields': ('type', 'priority', 'is_actionable')
        }),
        ('Status', {
            'fields': ('is_read', 'is_dismissed')
        }),
        ('Metadata', {
            'fields': ('metadata', 'confidence_score'),
            'classes': ('collapse',)
        }),
        ('Related Objects', {
            'fields': ('related_transaction', 'related_category'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    def priority_badge(self, obj):
        """Display priority as a colored badge."""
        colors = {
            'urgent': '#dc3545',
            'high': '#fd7e14',
            'medium': '#ffc107',
            'low': '#28a745',
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 4px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    priority_badge.admin_order_field = 'priority'

    actions = ['mark_as_read', 'mark_as_dismissed', 'reset_status']

    @admin.action(description='Mark selected recommendations as read')
    def mark_as_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} recommendations marked as read.')

    @admin.action(description='Mark selected recommendations as dismissed')
    def mark_as_dismissed(self, request, queryset):
        count = queryset.update(is_dismissed=True)
        self.message_user(request, f'{count} recommendations dismissed.')

    @admin.action(description='Reset status (unread, not dismissed)')
    def reset_status(self, request, queryset):
        count = queryset.update(is_read=False, is_dismissed=False)
        self.message_user(request, f'{count} recommendations reset.')


@admin.register(AICategorizationLog)
class AICategorizationLogAdmin(admin.ModelAdmin):
    """Admin configuration for categorization logs."""

    list_display = [
        'id',
        'user',
        'transaction',
        'suggested_category',
        'confidence_display',
        'was_accepted',
        'created_at',
    ]
    list_filter = [
        'was_accepted',
        'created_at',
        'suggested_category',
    ]
    search_fields = [
        'user__email',
        'transaction__description',
        'reasoning',
    ]
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'transaction')
        }),
        ('AI Response', {
            'fields': ('suggested_category', 'confidence_score', 'reasoning')
        }),
        ('User Feedback', {
            'fields': ('was_accepted', 'actual_category')
        }),
        ('Technical', {
            'fields': ('raw_response', 'processing_time_ms', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def confidence_display(self, obj):
        """Display confidence score as a progress bar."""
        score = obj.confidence_score * 100
        color = '#28a745' if score >= 80 else '#ffc107' if score >= 60 else '#dc3545'
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 4px;">'
            '<div style="width: {}%; background: {}; height: 8px; border-radius: 4px;"></div>'
            '</div><small>{:.1f}%</small>',
            score, color, score
        )
    confidence_display.short_description = 'Confidence'


@admin.register(AIAnalysisCache)
class AIAnalysisCacheAdmin(admin.ModelAdmin):
    """Admin configuration for analysis cache."""

    list_display = [
        'id',
        'user',
        'analysis_type',
        'cache_key',
        'is_expired_display',
        'created_at',
        'expires_at',
    ]
    list_filter = [
        'analysis_type',
        'created_at',
        'expires_at',
    ]
    search_fields = [
        'user__email',
        'cache_key',
    ]
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def is_expired_display(self, obj):
        """Display whether cache entry is expired."""
        if obj.is_expired:
            return format_html(
                '<span style="color: #dc3545;"><i class="bi bi-x-circle"></i> Expired</span>'
            )
        return format_html(
            '<span style="color: #28a745;"><i class="bi bi-check-circle"></i> Active</span>'
        )
    is_expired_display.short_description = 'Status'

    actions = ['clear_expired', 'clear_all']

    @admin.action(description='Clear expired cache entries')
    def clear_expired(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(expires_at__lt=timezone.now()).delete()[0]
        self.message_user(request, f'{count} expired cache entries cleared.')

    @admin.action(description='Clear all selected cache entries')
    def clear_all(self, request, queryset):
        count = queryset.delete()[0]
        self.message_user(request, f'{count} cache entries cleared.')
