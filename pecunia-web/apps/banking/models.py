"""
Banking Models.

Bank connections and account data models with secure credential storage.

This module implements:
- Secure token encryption using Fernet (AES-128-CBC with HMAC)
- Bank connection management for multiple providers (Plaid, TrueLayer, Powens)
- Account synchronization tracking and error handling
- Audit logging for compliance and debugging

Security Considerations:
- All access/refresh tokens are encrypted at rest using Fernet
- Encryption key MUST be set via BANK_ENCRYPTION_KEY environment variable
- Keys should be rotated periodically (see SECURITY_GUIDELINES.md)
- Never log decrypted token values

Related Documentation:
- See SECURITY_GUIDELINES.md for token storage requirements
- See SCALABILITY_GUIDELINES.md for sync optimization
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet
import base64
import os


class EncryptedFieldMixin:
    """
    Mixin for encrypted field handling using Fernet symmetric encryption.

    Fernet Encryption Details:
    - Algorithm: AES-128-CBC with PKCS7 padding
    - Authentication: HMAC-SHA256
    - Key format: URL-safe base64-encoded 32 bytes

    Usage:
        class MyModel(models.Model, EncryptedFieldMixin):
            _secret_encrypted = models.TextField()

            @property
            def secret(self):
                return self.decrypt_value(self._secret_encrypted)

            @secret.setter
            def secret(self, value):
                self._secret_encrypted = self.encrypt_value(value)

    Security Notes:
    - The encryption key MUST be stored securely (environment variable or vault)
    - Generate keys with: Fernet.generate_key()
    - Never commit keys to version control
    - Implement key rotation for production systems
    """

    @staticmethod
    def get_encryption_key():
        """
        Retrieve the encryption key from settings or environment.

        Key Resolution Order:
        1. Django settings: BANK_ENCRYPTION_KEY
        2. Environment variable: BANK_ENCRYPTION_KEY

        Returns:
            bytes: The Fernet-compatible encryption key.

        Raises:
            ValueError: If no encryption key is configured.

        Security Warning:
            In production, ALWAYS set this via environment variable.
            Never hardcode or commit encryption keys.
        """
        key = getattr(settings, 'BANK_ENCRYPTION_KEY', None)
        if not key:
            # In production, this should always be set in settings
            key = os.environ.get('BANK_ENCRYPTION_KEY')
        if not key:
            raise ValueError(
                "BANK_ENCRYPTION_KEY must be set in settings or environment"
            )
        return key.encode() if isinstance(key, str) else key

    @staticmethod
    def encrypt_value(value):
        """
        Encrypt a plaintext value using Fernet symmetric encryption.

        Args:
            value (str): The plaintext value to encrypt.

        Returns:
            str | None: Base64-encoded encrypted ciphertext, or None if value is empty.

        Technical Details:
        - Input is UTF-8 encoded before encryption
        - Output is URL-safe base64-encoded string
        - Includes timestamp for key rotation support
        - HMAC ensures integrity verification on decrypt
        """
        if not value:
            return None
        key = EncryptedFieldMixin.get_encryption_key()
        f = Fernet(key)
        return f.encrypt(value.encode()).decode()

    @staticmethod
    def decrypt_value(encrypted_value):
        """
        Decrypt a Fernet-encrypted value back to plaintext.

        Args:
            encrypted_value (str): The base64-encoded ciphertext to decrypt.

        Returns:
            str | None: The original plaintext value, or None if input is empty.

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails due to:
                - Wrong encryption key
                - Corrupted ciphertext
                - Tampered data (HMAC verification failure)

        Security Note:
            Catch InvalidToken exceptions at the application layer
            to handle key rotation or corruption gracefully.
        """
        if not encrypted_value:
            return None
        key = EncryptedFieldMixin.get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_value.encode()).decode()


class BankConnection(models.Model, EncryptedFieldMixin):
    """
    Bank connection model for managing connections to banking providers.

    This model stores:
    - Provider credentials (encrypted access/refresh tokens)
    - Institution metadata (name, logo, provider-specific IDs)
    - Connection status and health tracking
    - Sync history and error counts

    Supported Providers:
    - Powens (Budget Insight): European banks, PSD2 compliant
    - TrueLayer: UK/European banks, Open Banking
    - Plaid: US/Canadian banks

    Token Lifecycle:
    1. User initiates connection via OAuth flow
    2. Provider returns access_token + refresh_token
    3. Tokens encrypted via EncryptedFieldMixin before storage
    4. On sync, decrypt token, make API call, re-encrypt if refreshed
    5. Token expiry tracked via token_expires_at field

    Status Transitions:
        pending -> active (successful first sync)
        active -> expired (token/consent expired)
        active -> error (3+ consecutive sync failures)
        expired/error -> active (successful reauthorization)
        * -> revoked (user manually disconnected)

    Security:
    - Access tokens NEVER stored in plaintext
    - Token values NEVER logged (see SECURITY_GUIDELINES.md)
    - Expired tokens should trigger re-authorization flow
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_connections'
    )

    # Provider information
    PROVIDER_CHOICES = [
        ('budget_insight', 'Powens (Budget Insight)'),
        ('truelayer', 'TrueLayer'),
        ('plaid', 'Plaid'),
    ]
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)

    # Institution information
    institution_id = models.CharField(max_length=255)
    institution_name = models.CharField(max_length=255)
    institution_logo_url = models.URLField(blank=True, null=True)

    # Encrypted credentials
    _access_token_encrypted = models.TextField(
        db_column='access_token_encrypted',
        blank=True,
        null=True
    )
    _refresh_token_encrypted = models.TextField(
        db_column='refresh_token_encrypted',
        blank=True,
        null=True
    )

    # Provider-specific connection ID
    provider_connection_id = models.CharField(max_length=255, blank=True)

    # Connection status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('expired', 'Expired'),
        ('error', 'Error'),
        ('revoked', 'Revoked'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    status_message = models.TextField(blank=True)

    # Consent and expiration
    consent_expires_at = models.DateTimeField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Sync information
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=50, blank=True)
    sync_error_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'bank connection'
        verbose_name_plural = 'bank connections'
        ordering = ['-created_at']
        unique_together = ['user', 'provider', 'institution_id']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['provider', 'status']),
        ]

    def __str__(self):
        return f"{self.institution_name} ({self.provider})"

    @property
    def access_token(self):
        """Decrypt and return access token."""
        return self.decrypt_value(self._access_token_encrypted)

    @access_token.setter
    def access_token(self, value):
        """Encrypt and store access token."""
        self._access_token_encrypted = self.encrypt_value(value)

    @property
    def refresh_token(self):
        """Decrypt and return refresh token."""
        return self.decrypt_value(self._refresh_token_encrypted)

    @refresh_token.setter
    def refresh_token(self, value):
        """Encrypt and store refresh token."""
        self._refresh_token_encrypted = self.encrypt_value(value)

    @property
    def is_token_expired(self):
        """
        Check if the access token has expired.

        Returns:
            bool: True if token_expires_at is not set (assumes expired for
                  safety) or if current time >= expiry.
                  False only if token_expires_at is set and not yet reached.

        Security Note:
            Defaults to True when token_expires_at is not set, forcing
            a refresh check. This is the safer default as it ensures
            tokens without known expiry are always verified.
        """
        if not self.token_expires_at:
            return True
        return timezone.now() >= self.token_expires_at

    @property
    def is_consent_expired(self):
        """
        Check if the user's consent has expired (PSD2/Open Banking).

        PSD2 Compliance:
            Under PSD2, consent must be renewed every 90 days.
            Banks may require re-authentication even sooner.

        Returns:
            bool: True if consent_expires_at is set AND current time >= expiry.
                  False if consent_expires_at is not set (assumes valid).
        """
        if not self.consent_expires_at:
            return False
        return timezone.now() >= self.consent_expires_at

    @property
    def needs_reauthorization(self):
        """
        Check if the connection requires user reauthorization.

        Reauthorization is needed when:
        1. Connection status is 'expired', 'error', or 'revoked'
        2. Access token has expired (is_token_expired)
        3. User consent has expired (is_consent_expired)

        Returns:
            bool: True if reauthorization flow should be initiated.

        Usage:
            if connection.needs_reauthorization:
                redirect_to_oauth(connection.provider)
        """
        return (
            self.status in ['expired', 'error', 'revoked'] or
            self.is_token_expired or
            self.is_consent_expired
        )

    def mark_sync_success(self):
        """Mark connection as successfully synced."""
        self.last_sync_at = timezone.now()
        self.last_sync_status = 'success'
        self.sync_error_count = 0
        self.status = 'active'
        self.save(update_fields=[
            'last_sync_at', 'last_sync_status',
            'sync_error_count', 'status', 'updated_at'
        ])

    def mark_sync_error(self, error_message):
        """Mark connection with sync error."""
        self.last_sync_at = timezone.now()
        self.last_sync_status = 'error'
        self.sync_error_count += 1
        self.status_message = error_message
        if self.sync_error_count >= 3:
            self.status = 'error'
        self.save(update_fields=[
            'last_sync_at', 'last_sync_status',
            'sync_error_count', 'status_message', 'status', 'updated_at'
        ])


class BankAccount(models.Model):
    """
    Bank account model.

    Represents a bank account retrieved from a connected institution.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bank_accounts'
    )
    connection = models.ForeignKey(
        BankConnection,
        on_delete=models.CASCADE,
        related_name='accounts'
    )

    # Provider-specific account ID
    provider_account_id = models.CharField(max_length=255)

    # Account information
    name = models.CharField(max_length=255)
    official_name = models.CharField(max_length=255, blank=True)

    ACCOUNT_TYPE_CHOICES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('credit', 'Credit Card'),
        ('loan', 'Loan'),
        ('investment', 'Investment'),
        ('mortgage', 'Mortgage'),
        ('other', 'Other'),
    ]
    account_type = models.CharField(
        max_length=50,
        choices=ACCOUNT_TYPE_CHOICES,
        default='other'
    )
    account_subtype = models.CharField(max_length=100, blank=True)

    # Account identifiers (masked)
    account_number_masked = models.CharField(max_length=50, blank=True)
    iban_masked = models.CharField(max_length=50, blank=True)

    # Balance information
    balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )
    available_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    credit_limit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Currency
    CURRENCY_CHOICES = [
        ('EUR', 'Euro'),
        ('USD', 'US Dollar'),
        ('GBP', 'British Pound'),
        ('CHF', 'Swiss Franc'),
        ('CAD', 'Canadian Dollar'),
        ('AUD', 'Australian Dollar'),
    ]
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='EUR'
    )

    # Display settings
    is_hidden = models.BooleanField(default=False)
    custom_name = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=7, default='#6366f1')

    # Sync information
    last_sync_at = models.DateTimeField(null=True, blank=True)
    balance_updated_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'bank account'
        verbose_name_plural = 'bank accounts'
        ordering = ['name']
        unique_together = ['connection', 'provider_account_id']
        indexes = [
            models.Index(fields=['user', 'account_type']),
            models.Index(fields=['user', 'is_hidden']),
        ]

    def __str__(self):
        display_name = self.custom_name or self.name
        return f"{display_name} ({self.account_type})"

    @property
    def display_name(self):
        """Return custom name if set, otherwise account name."""
        return self.custom_name or self.name

    @property
    def institution_name(self):
        """Return the institution name from the connection."""
        return self.connection.institution_name

    @property
    def provider(self):
        """Return the provider from the connection."""
        return self.connection.provider

    def update_balance(self, balance, available_balance=None):
        """Update account balance."""
        self.balance = balance
        if available_balance is not None:
            self.available_balance = available_balance
        self.balance_updated_at = timezone.now()
        self.last_sync_at = timezone.now()
        self.save(update_fields=[
            'balance', 'available_balance',
            'balance_updated_at', 'last_sync_at', 'updated_at'
        ])


class SyncLog(models.Model):
    """
    Sync log model.

    Tracks synchronization history for auditing and debugging.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        BankConnection,
        on_delete=models.CASCADE,
        related_name='sync_logs'
    )

    # Sync details
    SYNC_TYPE_CHOICES = [
        ('full', 'Full Sync'),
        ('incremental', 'Incremental'),
        ('balance', 'Balance Only'),
    ]
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPE_CHOICES)

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('success', 'Success'),
        ('partial', 'Partial Success'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    # Results
    accounts_synced = models.IntegerField(default=0)
    transactions_synced = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'sync log'
        verbose_name_plural = 'sync logs'
        ordering = ['-started_at']

    def __str__(self):
        return f"Sync {self.sync_type} - {self.status} ({self.started_at})"

    @property
    def duration_seconds(self):
        """Calculate sync duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()
