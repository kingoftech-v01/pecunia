"""
Django admin configuration for Budget models.
"""

from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Budget, BudgetItem, BudgetAlert


class BudgetItemInline(admin.TabularInline):
    """Inline admin for BudgetItem within Budget."""

    model = BudgetItem
    extra = 1
    min_num = 0
    fields = (
        'category',
        'planned_amount',
        'spent_amount',
        'alert_threshold',
        'is_alert_enabled',
        'notes',
    )
    readonly_fields = ('spent_amount',)
    autocomplete_fields = ['category']

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('category')


class BudgetAlertInline(admin.TabularInline):
    """Inline admin for BudgetAlert within BudgetItem."""

    model = BudgetAlert
    extra = 0
    fields = (
        'alert_type',
        'message',
        'percentage_reached',
        'is_read',
        'created_at',
    )
    readonly_fields = (
        'alert_type',
        'message',
        'percentage_reached',
        'created_at',
    )
    can_delete = True

    def has_add_permission(self, request, obj=None):
        """Prevent manual addition of alerts."""
        return False


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    """Admin configuration for Budget model."""

    list_display = (
        'name',
        'user',
        'period_type',
        'start_date',
        'end_date',
        'total_planned_display',
        'total_spent_display',
        'percentage_used_display',
        'is_active',
        'created_at',
    )
    list_filter = (
        'period_type',
        'is_active',
        'is_deleted',
        'created_at',
        'start_date',
    )
    search_fields = (
        'name',
        'description',
        'user__email',
        'user__username',
    )
    readonly_fields = (
        'id',
        'total_spent_display',
        'percentage_used_display',
        'remaining_amount_display',
        'days_remaining',
        'created_at',
        'updated_at',
    )
    autocomplete_fields = ['user']
    date_hierarchy = 'start_date'
    ordering = ['-created_at']
    inlines = [BudgetItemInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'name', 'description')
        }),
        (_('Period'), {
            'fields': ('period_type', 'start_date', 'end_date', 'days_remaining')
        }),
        (_('Amounts'), {
            'fields': (
                'total_planned',
                'total_spent_display',
                'remaining_amount_display',
                'percentage_used_display',
            )
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_deleted')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with annotations."""
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('items')

    def total_planned_display(self, obj):
        """Display total planned amount formatted."""
        return f"${obj.total_planned:,.2f}"
    total_planned_display.short_description = _('Total Planned')
    total_planned_display.admin_order_field = 'total_planned'

    def total_spent_display(self, obj):
        """Display total spent amount formatted."""
        return f"${obj.total_spent:,.2f}"
    total_spent_display.short_description = _('Total Spent')

    def remaining_amount_display(self, obj):
        """Display remaining amount with color coding."""
        remaining = obj.remaining_amount
        if remaining < 0:
            color = 'red'
        elif remaining < obj.total_planned * 0.1:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">${:,.2f}</span>',
            color,
            remaining
        )
    remaining_amount_display.short_description = _('Remaining')

    def percentage_used_display(self, obj):
        """Display percentage used with progress bar."""
        percentage = float(obj.percentage_used)
        if percentage >= 100:
            color = '#dc3545'  # red
        elif percentage >= 80:
            color = '#ffc107'  # yellow
        else:
            color = '#28a745'  # green

        return format_html(
            '''
            <div style="width: 100px; background-color: #e9ecef; border-radius: 4px;">
                <div style="width: {}%; background-color: {}; height: 20px;
                            border-radius: 4px; text-align: center; color: white;
                            font-size: 12px; line-height: 20px;">
                    {:.1f}%
                </div>
            </div>
            ''',
            min(percentage, 100),
            color,
            percentage
        )
    percentage_used_display.short_description = _('% Used')

    actions = ['activate_budgets', 'deactivate_budgets', 'recalculate_totals']

    @admin.action(description=_('Activate selected budgets'))
    def activate_budgets(self, request, queryset):
        """Activate selected budgets."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _(f'{updated} budget(s) have been activated.')
        )

    @admin.action(description=_('Deactivate selected budgets'))
    def deactivate_budgets(self, request, queryset):
        """Deactivate selected budgets."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _(f'{updated} budget(s) have been deactivated.')
        )

    @admin.action(description=_('Recalculate total amounts'))
    def recalculate_totals(self, request, queryset):
        """Recalculate total_planned for selected budgets."""
        for budget in queryset:
            budget.update_total_planned()
        self.message_user(
            request,
            _(f'Recalculated totals for {queryset.count()} budget(s).')
        )


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    """Admin configuration for BudgetItem model."""

    list_display = (
        'budget',
        'category',
        'planned_amount_display',
        'spent_amount_display',
        'remaining_display',
        'percentage_used_display',
        'alert_threshold',
        'is_alert_enabled',
    )
    list_filter = (
        'is_alert_enabled',
        'budget__period_type',
        'budget__is_active',
        'created_at',
    )
    search_fields = (
        'budget__name',
        'category__name',
        'notes',
    )
    readonly_fields = (
        'id',
        'spent_amount',
        'remaining_display',
        'percentage_used_display',
        'created_at',
        'updated_at',
    )
    autocomplete_fields = ['budget', 'category']
    inlines = [BudgetAlertInline]

    fieldsets = (
        (None, {
            'fields': ('id', 'budget', 'category')
        }),
        (_('Amounts'), {
            'fields': (
                'planned_amount',
                'spent_amount',
                'remaining_display',
                'percentage_used_display',
            )
        }),
        (_('Alerts'), {
            'fields': ('alert_threshold', 'is_alert_enabled')
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'budget',
            'budget__user',
            'category'
        )

    def planned_amount_display(self, obj):
        """Display planned amount formatted."""
        return f"${obj.planned_amount:,.2f}"
    planned_amount_display.short_description = _('Planned')
    planned_amount_display.admin_order_field = 'planned_amount'

    def spent_amount_display(self, obj):
        """Display spent amount formatted."""
        return f"${obj.spent_amount:,.2f}"
    spent_amount_display.short_description = _('Spent')
    spent_amount_display.admin_order_field = 'spent_amount'

    def remaining_display(self, obj):
        """Display remaining amount with color coding."""
        remaining = obj.remaining_amount
        if remaining < 0:
            color = 'red'
        elif remaining < obj.planned_amount * 0.1:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">${:,.2f}</span>',
            color,
            remaining
        )
    remaining_display.short_description = _('Remaining')

    def percentage_used_display(self, obj):
        """Display percentage used."""
        percentage = float(obj.percentage_used)
        if percentage >= 100:
            color = 'red'
        elif percentage >= 80:
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color,
            percentage
        )
    percentage_used_display.short_description = _('% Used')

    actions = ['update_spent_amounts', 'enable_alerts', 'disable_alerts']

    @admin.action(description=_('Update spent amounts from transactions'))
    def update_spent_amounts(self, request, queryset):
        """Update spent amounts for selected items."""
        for item in queryset:
            item.update_spent_from_transactions()
        self.message_user(
            request,
            _(f'Updated spent amounts for {queryset.count()} item(s).')
        )

    @admin.action(description=_('Enable alerts'))
    def enable_alerts(self, request, queryset):
        """Enable alerts for selected items."""
        updated = queryset.update(is_alert_enabled=True)
        self.message_user(
            request,
            _(f'Enabled alerts for {updated} item(s).')
        )

    @admin.action(description=_('Disable alerts'))
    def disable_alerts(self, request, queryset):
        """Disable alerts for selected items."""
        updated = queryset.update(is_alert_enabled=False)
        self.message_user(
            request,
            _(f'Disabled alerts for {updated} item(s).')
        )


@admin.register(BudgetAlert)
class BudgetAlertAdmin(admin.ModelAdmin):
    """Admin configuration for BudgetAlert model."""

    list_display = (
        'budget_item',
        'alert_type_display',
        'percentage_reached',
        'is_read',
        'created_at',
    )
    list_filter = (
        'alert_type',
        'is_read',
        'created_at',
    )
    search_fields = (
        'budget_item__budget__name',
        'budget_item__category__name',
        'message',
    )
    readonly_fields = (
        'id',
        'budget_item',
        'alert_type',
        'message',
        'percentage_reached',
        'created_at',
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        (None, {
            'fields': ('id', 'budget_item')
        }),
        (_('Alert Details'), {
            'fields': ('alert_type', 'message', 'percentage_reached')
        }),
        (_('Status'), {
            'fields': ('is_read',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related(
            'budget_item',
            'budget_item__budget',
            'budget_item__category'
        )

    def alert_type_display(self, obj):
        """Display alert type with color coding."""
        colors = {
            'approaching': '#17a2b8',  # info blue
            'warning': '#ffc107',       # warning yellow
            'exceeded': '#dc3545',      # danger red
        }
        color = colors.get(obj.alert_type, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_alert_type_display()
        )
    alert_type_display.short_description = _('Alert Type')
    alert_type_display.admin_order_field = 'alert_type'

    def has_add_permission(self, request):
        """Prevent manual addition of alerts."""
        return False

    def has_change_permission(self, request, obj=None):
        """Only allow changing is_read status."""
        return True

    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description=_('Mark selected alerts as read'))
    def mark_as_read(self, request, queryset):
        """Mark selected alerts as read."""
        updated = queryset.update(is_read=True)
        self.message_user(
            request,
            _(f'Marked {updated} alert(s) as read.')
        )

    @admin.action(description=_('Mark selected alerts as unread'))
    def mark_as_unread(self, request, queryset):
        """Mark selected alerts as unread."""
        updated = queryset.update(is_read=False)
        self.message_user(
            request,
            _(f'Marked {updated} alert(s) as unread.')
        )
