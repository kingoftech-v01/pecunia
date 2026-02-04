"""
Budgets Serializers.

DRF serializers for budget planning and tracking.
"""
from rest_framework import serializers
from decimal import Decimal
from .models import Budget, BudgetItem


class BudgetItemSerializer(serializers.ModelSerializer):
    """
    Serializer for budget items.

    Handles CRUD operations for budget line items.
    """
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    category_color = serializers.CharField(
        source='category.color',
        read_only=True
    )
    remaining_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_over_budget = serializers.BooleanField(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = BudgetItem
        fields = [
            'id', 'budget', 'category', 'category_name', 'category_color',
            'name', 'display_name', 'planned_amount', 'spent_amount',
            'remaining_amount', 'progress_percentage', 'is_over_budget',
            'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BudgetItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating budget items.

    Used when creating items as part of budget creation.
    """

    class Meta:
        model = BudgetItem
        fields = ['category', 'name', 'planned_amount', 'notes']


class BudgetSerializer(serializers.ModelSerializer):
    """
    Serializer for budgets.

    Handles CRUD operations for budget planning.
    """
    items = BudgetItemSerializer(many=True, read_only=True)
    remaining_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_over_budget = serializers.BooleanField(read_only=True)
    is_near_limit = serializers.BooleanField(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'description', 'period_type',
            'start_date', 'end_date',
            'total_planned_amount', 'total_spent_amount',
            'remaining_amount', 'progress_percentage',
            'is_over_budget', 'is_near_limit',
            'is_active', 'is_rollover',
            'alert_threshold', 'notify_on_exceed',
            'items', 'item_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_planned_amount', 'total_spent_amount',
            'created_at', 'updated_at'
        ]

    def get_item_count(self, obj):
        """Return the number of budget items."""
        return obj.items.count()

    def create(self, validated_data):
        """Create budget with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class BudgetListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for budget lists.

    Optimized for list views with minimal data.
    """
    remaining_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    is_over_budget = serializers.BooleanField(read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'period_type',
            'start_date', 'end_date',
            'total_planned_amount', 'total_spent_amount',
            'remaining_amount', 'progress_percentage',
            'is_over_budget', 'is_active', 'item_count'
        ]

    def get_item_count(self, obj):
        """Return the number of budget items."""
        return obj.items.count()


class BudgetWithItemsSerializer(serializers.ModelSerializer):
    """
    Serializer for creating budgets with items in one request.

    Allows nested creation of budget items.
    """
    items = BudgetItemCreateSerializer(many=True, required=False)
    remaining_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )
    progress_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Budget
        fields = [
            'id', 'name', 'description', 'period_type',
            'start_date', 'end_date',
            'total_planned_amount', 'total_spent_amount',
            'remaining_amount', 'progress_percentage',
            'is_active', 'is_rollover',
            'alert_threshold', 'notify_on_exceed',
            'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_planned_amount', 'total_spent_amount',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Create budget with nested items."""
        items_data = validated_data.pop('items', [])
        validated_data['user'] = self.context['request'].user
        budget = Budget.objects.create(**validated_data)

        for item_data in items_data:
            BudgetItem.objects.create(budget=budget, **item_data)

        return budget

    def update(self, instance, validated_data):
        """Update budget and optionally its items."""
        items_data = validated_data.pop('items', None)

        # Update budget fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update items if provided
        if items_data is not None:
            # Clear existing items and create new ones
            instance.items.all().delete()
            for item_data in items_data:
                BudgetItem.objects.create(budget=instance, **item_data)

        return instance


class BudgetStatsSerializer(serializers.Serializer):
    """
    Serializer for budget statistics.

    Used for dashboard summaries and reports.
    """
    total_budgets = serializers.IntegerField()
    active_budgets = serializers.IntegerField()
    total_planned = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_spent = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_remaining = serializers.DecimalField(max_digits=15, decimal_places=2)
    overall_progress = serializers.DecimalField(max_digits=5, decimal_places=2)
    budgets_over_limit = serializers.IntegerField()
    budgets_near_limit = serializers.IntegerField()
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField()


class BudgetProgressSerializer(serializers.Serializer):
    """
    Serializer for detailed budget progress.

    Used for progress tracking views.
    """
    budget_id = serializers.UUIDField()
    budget_name = serializers.CharField()
    period_type = serializers.CharField()
    planned_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    progress_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    days_remaining = serializers.IntegerField()
    daily_budget = serializers.DecimalField(max_digits=15, decimal_places=2)
    daily_spending_rate = serializers.DecimalField(max_digits=15, decimal_places=2)
    projected_spending = serializers.DecimalField(max_digits=15, decimal_places=2)
    is_on_track = serializers.BooleanField()
    items = BudgetItemSerializer(many=True)


class CategoryBudgetSummarySerializer(serializers.Serializer):
    """
    Serializer for category-wise budget summary.

    Shows budget allocation and spending by category.
    """
    category_id = serializers.UUIDField(allow_null=True)
    category_name = serializers.CharField()
    category_color = serializers.CharField()
    planned_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    spent_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    remaining_amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    progress_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    is_over_budget = serializers.BooleanField()
