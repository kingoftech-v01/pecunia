"""
Transactions Serializers.

DRF serializers for transaction and category data.
"""
from rest_framework import serializers
from .models import Transaction, TransactionCategory, RecurringTransaction


class TransactionCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for transaction categories.

    Handles CRUD operations for categories.
    """
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = TransactionCategory
        fields = [
            'id', 'name', 'type', 'icon', 'color',
            'is_default', 'transaction_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_transaction_count(self, obj):
        """Return the number of transactions in this category."""
        return obj.transactions.count()

    def create(self, validated_data):
        """Create category with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for transactions.

    Handles CRUD operations for financial transactions.
    """
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    signed_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'bank_account', 'category', 'category_name',
            'amount', 'signed_amount', 'type', 'description',
            'merchant', 'reference', 'transaction_date',
            'is_recurring', 'is_manual',
            'ai_category_suggestion', 'ai_confidence',
            'tags', 'notes', 'attachments',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ai_category_suggestion', 'ai_confidence',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        """Create transaction with current user."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TransactionListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for transaction lists.

    Optimized for list views with minimal data.
    """
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )
    category_color = serializers.CharField(
        source='category.color',
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'type', 'description',
            'merchant', 'category_name', 'category_color',
            'transaction_date'
        ]


class RecurringTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for recurring transactions.

    Handles recurring transaction templates.
    """
    category_name = serializers.CharField(
        source='category.name',
        read_only=True
    )

    class Meta:
        model = RecurringTransaction
        fields = [
            'id', 'name', 'category', 'category_name',
            'amount', 'type', 'description',
            'frequency', 'start_date', 'end_date',
            'next_occurrence', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'next_occurrence', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create recurring transaction with current user."""
        validated_data['user'] = self.context['request'].user
        validated_data['next_occurrence'] = validated_data['start_date']
        return super().create(validated_data)


class TransactionStatsSerializer(serializers.Serializer):
    """
    Serializer for transaction statistics.

    Used for dashboard summaries.
    """
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
