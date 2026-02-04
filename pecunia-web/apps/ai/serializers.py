"""
AI Serializers.

Serializers for AI-related API endpoints.
"""
from rest_framework import serializers
from .models import AIRecommendation, AICategorizationLog, AIAnalysisCache


class AIRecommendationSerializer(serializers.ModelSerializer):
    """Serializer for AI recommendations."""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = AIRecommendation
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'content',
            'priority',
            'priority_display',
            'is_read',
            'is_dismissed',
            'is_actionable',
            'metadata',
            'confidence_score',
            'related_transaction',
            'related_category',
            'created_at',
            'updated_at',
            'expires_at',
            'time_ago',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'updated_at',
            'type_display',
            'priority_display',
        ]

    def get_time_ago(self, obj):
        """Return human-readable time since creation."""
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(obj.created_at, timezone.now())


class AIRecommendationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for recommendation lists."""

    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = AIRecommendation
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'priority',
            'priority_display',
            'is_read',
            'is_actionable',
            'created_at',
        ]


class AIRecommendationActionSerializer(serializers.Serializer):
    """Serializer for recommendation actions (mark read, dismiss)."""

    action = serializers.ChoiceField(choices=['mark_read', 'dismiss'])


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for chat messages."""

    role = serializers.ChoiceField(
        choices=['user', 'assistant', 'system'],
        default='user'
    )
    content = serializers.CharField(
        max_length=10000,
        trim_whitespace=True
    )
    timestamp = serializers.DateTimeField(read_only=True)

    def validate_content(self, value):
        """Validate message content."""
        if not value.strip():
            raise serializers.ValidationError("Message content cannot be empty.")
        return value.strip()


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat requests."""

    message = serializers.CharField(
        max_length=10000,
        trim_whitespace=True,
        help_text="The user's message to the AI assistant"
    )
    context_type = serializers.ChoiceField(
        choices=[
            ('general', 'General Finance'),
            ('transactions', 'Transaction Analysis'),
            ('budgets', 'Budget Help'),
            ('savings', 'Savings Advice'),
            ('investments', 'Investment Guidance'),
        ],
        default='general',
        required=False
    )
    include_history = serializers.BooleanField(
        default=True,
        help_text="Include conversation history in context"
    )
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text="Optional session ID to continue a conversation"
    )

    def validate_message(self, value):
        """Validate and sanitize user message."""
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        # Basic sanitization
        return value.strip()


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses."""

    message = serializers.CharField()
    session_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    tokens_used = serializers.IntegerField(required=False)
    context_type = serializers.CharField(required=False)


class CategorizeRequestSerializer(serializers.Serializer):
    """Serializer for transaction categorization requests."""

    transaction_id = serializers.UUIDField(
        required=False,
        help_text="ID of existing transaction to categorize"
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Transaction description for categorization"
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="Transaction amount (optional, helps with context)"
    )
    merchant = serializers.CharField(
        max_length=255,
        required=False,
        help_text="Merchant name (optional)"
    )
    include_confidence = serializers.BooleanField(
        default=True,
        help_text="Include confidence score in response"
    )
    include_alternatives = serializers.BooleanField(
        default=False,
        help_text="Include alternative category suggestions"
    )

    def validate(self, data):
        """Ensure either transaction_id or description is provided."""
        if not data.get('transaction_id') and not data.get('description'):
            raise serializers.ValidationError(
                "Either 'transaction_id' or 'description' must be provided."
            )
        return data


class CategorizeResponseSerializer(serializers.Serializer):
    """Serializer for categorization responses."""

    category_id = serializers.UUIDField()
    category_name = serializers.CharField()
    category_icon = serializers.CharField(required=False)
    confidence_score = serializers.FloatField(required=False)
    reasoning = serializers.CharField(required=False)
    alternatives = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )


class BulkCategorizeRequestSerializer(serializers.Serializer):
    """Serializer for bulk categorization requests."""

    transaction_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50,
        help_text="List of transaction IDs to categorize"
    )
    auto_apply = serializers.BooleanField(
        default=False,
        help_text="Automatically apply categorizations with high confidence"
    )
    confidence_threshold = serializers.FloatField(
        default=0.85,
        min_value=0.5,
        max_value=1.0,
        help_text="Minimum confidence to auto-apply (if auto_apply is True)"
    )


class InsightsSerializer(serializers.Serializer):
    """Serializer for financial insights."""

    period = serializers.ChoiceField(
        choices=[
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('quarter', 'This Quarter'),
            ('year', 'This Year'),
            ('custom', 'Custom Period'),
        ],
        default='month'
    )
    start_date = serializers.DateField(
        required=False,
        help_text="Start date for custom period"
    )
    end_date = serializers.DateField(
        required=False,
        help_text="End date for custom period"
    )
    insight_types = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'spending_summary',
            'category_breakdown',
            'trends',
            'anomalies',
            'savings_opportunities',
            'budget_status',
            'forecast',
        ]),
        required=False,
        default=['spending_summary', 'category_breakdown', 'trends']
    )
    include_comparisons = serializers.BooleanField(
        default=True,
        help_text="Include comparison with previous period"
    )

    def validate(self, data):
        """Validate date range for custom period."""
        if data.get('period') == 'custom':
            if not data.get('start_date') or not data.get('end_date'):
                raise serializers.ValidationError(
                    "start_date and end_date are required for custom period."
                )
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError(
                    "start_date must be before end_date."
                )
        return data


class InsightsResponseSerializer(serializers.Serializer):
    """Serializer for insights response."""

    period_label = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    # Spending summary
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_savings = serializers.DecimalField(max_digits=12, decimal_places=2)
    savings_rate = serializers.FloatField()

    # Comparisons
    income_change = serializers.FloatField(required=False)
    expense_change = serializers.FloatField(required=False)
    savings_change = serializers.FloatField(required=False)

    # Category breakdown
    category_breakdown = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    # Trends
    daily_spending = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )

    # AI insights
    ai_summary = serializers.CharField(required=False)
    recommendations = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    anomalies = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    forecast = serializers.DictField(required=False)

    generated_at = serializers.DateTimeField()


class SpendingPatternSerializer(serializers.Serializer):
    """Serializer for spending pattern data."""

    category = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    percentage = serializers.FloatField()
    trend = serializers.ChoiceField(choices=['up', 'down', 'stable'])
    trend_percentage = serializers.FloatField()
    average_transaction = serializers.DecimalField(max_digits=12, decimal_places=2)


class SavingsOpportunitySerializer(serializers.Serializer):
    """Serializer for savings opportunity suggestions."""

    title = serializers.CharField()
    description = serializers.CharField()
    estimated_savings = serializers.DecimalField(max_digits=12, decimal_places=2)
    confidence = serializers.FloatField()
    category = serializers.CharField(required=False)
    action_type = serializers.ChoiceField(
        choices=['reduce', 'switch', 'cancel', 'negotiate', 'budget']
    )
    action_url = serializers.CharField(required=False)


class AICategorizationLogSerializer(serializers.ModelSerializer):
    """Serializer for categorization logs."""

    class Meta:
        model = AICategorizationLog
        fields = [
            'id',
            'transaction',
            'suggested_category',
            'confidence_score',
            'reasoning',
            'was_accepted',
            'actual_category',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']
