"""
Banking Serializers.

DRF serializers for bank connections and accounts.
"""
from urllib.parse import urlparse
from django.conf import settings
from rest_framework import serializers
from .models import BankConnection, BankAccount, SyncLog


class BankConnectionSerializer(serializers.ModelSerializer):
    """
    Serializer for bank connections.

    Handles read/write operations for bank connection data.
    Sensitive fields are excluded from responses.
    """
    is_token_expired = serializers.BooleanField(read_only=True)
    is_consent_expired = serializers.BooleanField(read_only=True)
    needs_reauthorization = serializers.BooleanField(read_only=True)
    accounts_count = serializers.SerializerMethodField()

    class Meta:
        model = BankConnection
        fields = [
            'id', 'provider', 'institution_id', 'institution_name',
            'institution_logo_url', 'status', 'status_message',
            'consent_expires_at', 'last_sync_at', 'last_sync_status',
            'is_token_expired', 'is_consent_expired', 'needs_reauthorization',
            'accounts_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'institution_id', 'institution_name', 'institution_logo_url',
            'status', 'status_message', 'consent_expires_at',
            'last_sync_at', 'last_sync_status', 'created_at', 'updated_at'
        ]

    def get_accounts_count(self, obj):
        """Get number of accounts for this connection."""
        return obj.accounts.count()


class BankConnectionDetailSerializer(BankConnectionSerializer):
    """
    Detailed serializer for bank connections.

    Includes nested account information.
    """
    accounts = serializers.SerializerMethodField()

    class Meta(BankConnectionSerializer.Meta):
        fields = BankConnectionSerializer.Meta.fields + ['accounts']

    def get_accounts(self, obj):
        """Get accounts for this connection."""
        accounts = obj.accounts.filter(is_hidden=False)
        return BankAccountSerializer(accounts, many=True).data


class BankConnectionCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a new bank connection.

    Handles the initial connection setup.
    """
    provider = serializers.ChoiceField(
        choices=BankConnection.PROVIDER_CHOICES,
        required=True
    )
    redirect_uri = serializers.URLField(required=True)
    institution_id = serializers.CharField(required=False, allow_blank=True)

    def validate_provider(self, value):
        """Validate provider is supported."""
        valid_providers = [choice[0] for choice in BankConnection.PROVIDER_CHOICES]
        if value not in valid_providers:
            raise serializers.ValidationError(
                f"Provider must be one of: {', '.join(valid_providers)}"
            )
        return value

    def validate_redirect_uri(self, value):
        """Validate redirect_uri against allowed domains."""
        allowed_domains = getattr(settings, 'ALLOWED_REDIRECT_DOMAINS', [])
        if allowed_domains:
            parsed = urlparse(value)
            if parsed.hostname not in allowed_domains:
                raise serializers.ValidationError(
                    "redirect_uri domain is not allowed."
                )
        return value


class BankConnectionCallbackSerializer(serializers.Serializer):
    """
    Serializer for handling OAuth callback.

    Processes the authorization code from the provider.
    """
    code = serializers.CharField(required=True)
    state = serializers.CharField(required=True)
    redirect_uri = serializers.URLField(required=True)
    provider = serializers.ChoiceField(
        choices=BankConnection.PROVIDER_CHOICES,
        required=True
    )

    def validate_redirect_uri(self, value):
        """Validate redirect_uri against allowed domains."""
        allowed_domains = getattr(settings, 'ALLOWED_REDIRECT_DOMAINS', [])
        if allowed_domains:
            parsed = urlparse(value)
            if parsed.hostname not in allowed_domains:
                raise serializers.ValidationError(
                    "redirect_uri domain is not allowed."
                )
        return value


class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for bank accounts.

    Read/update operations for account data.
    """
    display_name = serializers.CharField(read_only=True)
    institution_name = serializers.CharField(read_only=True)
    provider = serializers.CharField(read_only=True)
    connection_status = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            'id', 'connection', 'name', 'official_name', 'display_name',
            'account_type', 'account_subtype', 'account_number_masked',
            'iban_masked', 'balance', 'available_balance', 'credit_limit',
            'currency', 'is_hidden', 'custom_name', 'color',
            'institution_name', 'provider', 'connection_status',
            'last_sync_at', 'balance_updated_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'connection', 'name', 'official_name', 'account_type',
            'account_subtype', 'account_number_masked', 'iban_masked',
            'balance', 'available_balance', 'credit_limit', 'currency',
            'last_sync_at', 'balance_updated_at', 'created_at', 'updated_at'
        ]

    def get_connection_status(self, obj):
        """Get the connection status."""
        return obj.connection.status


class BankAccountUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating bank account display settings.

    Allows users to customize account appearance.
    """

    class Meta:
        model = BankAccount
        fields = ['is_hidden', 'custom_name', 'color']


class BankAccountSummarySerializer(serializers.ModelSerializer):
    """
    Minimal serializer for account summaries.

    Used in list views and aggregations.
    """
    display_name = serializers.CharField(read_only=True)
    institution_name = serializers.CharField(read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            'id', 'display_name', 'account_type', 'balance',
            'currency', 'institution_name', 'color'
        ]


class SyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for sync logs.

    Provides sync history information.
    """
    duration_seconds = serializers.FloatField(read_only=True)
    connection_name = serializers.SerializerMethodField()

    class Meta:
        model = SyncLog
        fields = [
            'id', 'connection', 'connection_name', 'sync_type', 'status',
            'accounts_synced', 'transactions_synced', 'error_message',
            'started_at', 'completed_at', 'duration_seconds'
        ]
        read_only_fields = fields

    def get_connection_name(self, obj):
        """Get the connection institution name."""
        return obj.connection.institution_name


class InstitutionSerializer(serializers.Serializer):
    """
    Serializer for institution search results.

    Provides available institutions for connection.
    """
    institution_id = serializers.CharField()
    name = serializers.CharField()
    logo_url = serializers.URLField(allow_null=True)
    country = serializers.CharField(allow_null=True)
    bic = serializers.CharField(allow_null=True, required=False)


class SyncRequestSerializer(serializers.Serializer):
    """
    Serializer for sync requests.

    Validates sync operation parameters.
    """
    connection_id = serializers.UUIDField(required=False)
    sync_type = serializers.ChoiceField(
        choices=['full', 'incremental', 'balance'],
        default='incremental'
    )
    force = serializers.BooleanField(default=False)


class BalanceAggregateSerializer(serializers.Serializer):
    """
    Serializer for balance aggregation.

    Provides summary of all account balances.
    """
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_available = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        allow_null=True
    )
    currency = serializers.CharField()
    accounts_count = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.DecimalField(
        max_digits=15,
        decimal_places=2
    ))
    by_institution = serializers.DictField(child=serializers.DecimalField(
        max_digits=15,
        decimal_places=2
    ))


class ConnectionStatusSerializer(serializers.Serializer):
    """
    Serializer for connection status checks.

    Used for health checks and status monitoring.
    """
    connection_id = serializers.UUIDField()
    status = serializers.CharField()
    is_healthy = serializers.BooleanField()
    needs_reauthorization = serializers.BooleanField()
    last_sync_at = serializers.DateTimeField(allow_null=True)
    error_message = serializers.CharField(allow_blank=True)
