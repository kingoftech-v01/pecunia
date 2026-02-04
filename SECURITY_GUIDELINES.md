# Security Guidelines - FinanceApp

**Version**: 1.0
**Last Updated**: 2026-01-28
**Classification**: INTERNAL - CONFIDENTIAL
**Status**: MANDATORY - All platforms MUST follow these guidelines

---

## Table of Contents

1. [Security Principles](#1-security-principles)
2. [Authentication](#2-authentication)
3. [Token Management](#3-token-management)
4. [Data Encryption](#4-data-encryption)
5. [Input Validation](#5-input-validation)
6. [OWASP Top 10 Compliance](#6-owasp-top-10-compliance)
7. [Rate Limiting](#7-rate-limiting)
8. [Secret Management](#8-secret-management)
9. [Logging Security](#9-logging-security)
10. [API Security Headers](#10-api-security-headers)
11. [Platform-Specific Security](#11-platform-specific-security)
12. [Security Checklist](#12-security-checklist)
13. [Incident Response](#13-incident-response)

---

## 1. Security Principles

### Defense in Depth

Apply multiple layers of security controls:

```
                    +------------------+
                    |   Rate Limiting  |  ← Layer 1: Traffic Control
                    +--------+---------+
                             |
                    +--------v---------+
                    |   API Gateway    |  ← Layer 2: Entry Point
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Authentication  |  ← Layer 3: Identity
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Authorization   |  ← Layer 4: Permissions
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Input Validation|  ← Layer 5: Data Integrity
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Business Logic  |  ← Layer 6: Application
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Data Encryption |  ← Layer 7: Data Protection
                    +------------------+
```

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Least Privilege** | Grant minimum permissions required |
| **Defense in Depth** | Multiple security layers |
| **Fail Secure** | Default to deny on errors |
| **Zero Trust** | Verify every request |
| **Separation of Duties** | No single point of compromise |

### Security Requirements by Data Type

| Data Type | Storage | Transit | Access |
|-----------|---------|---------|--------|
| Passwords | Argon2 hash | TLS 1.3 | Never exposed |
| Access Tokens | Encrypted | TLS 1.3 | User only |
| Bank Credentials | AES-256 | TLS 1.3 + Pin | System only |
| Transactions | At-rest encryption | TLS 1.3 | Owner + Admin |
| Personal Info | At-rest encryption | TLS 1.3 | Owner + Admin |

---

## 2. Authentication

### JWT Configuration

**Django SimpleJWT Settings** (MANDATORY):

```python
# config/settings/base.py
from datetime import timedelta

SIMPLE_JWT = {
    # Token Lifetimes
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Token Rotation (CRITICAL for security)
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # Algorithm and Signing
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,  # Use dedicated JWT secret in production
    'VERIFYING_KEY': None,

    # Token Type
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',

    # Token Claims
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    # Token Validation
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # Additional Security
    'JTI_CLAIM': 'jti',  # Unique token identifier
    'AUDIENCE': 'financeapp-api',
    'ISSUER': 'financeapp',

    # Sliding tokens (optional)
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=60),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=7),
}
```

### Password Security

**Hashing Configuration**:

```python
# config/settings/base.py
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Primary
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # Fallback
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 12},  # Minimum 12 characters
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

**Password Requirements**:
| Requirement | Value |
|-------------|-------|
| Minimum Length | 12 characters |
| Complexity | 1 uppercase, 1 lowercase, 1 number, 1 special |
| History | Cannot reuse last 5 passwords |
| Expiry | 90 days (optional, consider security vs usability) |

### Account Lockout

```python
# apps/accounts/security.py
from django.core.cache import cache
from django.conf import settings

class AccountLockout:
    """
    Implement account lockout after failed login attempts.

    Configuration:
        MAX_ATTEMPTS: Maximum failed attempts before lockout
        LOCKOUT_DURATION: Lockout duration in seconds
        ATTEMPT_WINDOW: Window for counting attempts in seconds
    """
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    ATTEMPT_WINDOW = 300    # 5 minutes

    @classmethod
    def get_cache_key(cls, email: str) -> str:
        """Generate cache key for login attempts."""
        return f"login_attempts:{email.lower()}"

    @classmethod
    def record_failed_attempt(cls, email: str) -> int:
        """Record a failed login attempt. Returns current count."""
        key = cls.get_cache_key(email)
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, cls.ATTEMPT_WINDOW)

        if attempts >= cls.MAX_ATTEMPTS:
            # Lock the account
            cache.set(f"locked:{email.lower()}", True, cls.LOCKOUT_DURATION)

        return attempts

    @classmethod
    def is_locked(cls, email: str) -> bool:
        """Check if account is locked."""
        return cache.get(f"locked:{email.lower()}", False)

    @classmethod
    def clear_attempts(cls, email: str) -> None:
        """Clear failed attempts after successful login."""
        cache.delete(cls.get_cache_key(email))
        cache.delete(f"locked:{email.lower()}")
```

### Multi-Factor Authentication (MFA)

**TOTP Implementation** (Recommended):

```python
# apps/accounts/mfa.py
import pyotp
from django.conf import settings

class TOTPManager:
    """
    TOTP-based two-factor authentication.

    Uses RFC 6238 compliant TOTP with:
    - 30-second time step
    - SHA-1 algorithm
    - 6-digit codes
    """

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret for user."""
        return pyotp.random_base32()

    @staticmethod
    def get_provisioning_uri(secret: str, email: str) -> str:
        """Generate QR code URI for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name="FinanceApp"
        )

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """
        Verify TOTP code with 1-step tolerance.

        Allows codes from previous and next 30-second window
        to account for clock drift.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)
```

---

## 3. Token Management

### Token Storage Requirements

| Platform | Access Token | Refresh Token | NEVER Store In |
|----------|--------------|---------------|----------------|
| **Web** | HTTP-only cookie | HTTP-only cookie | LocalStorage, SessionStorage |
| **Desktop** | System keyring | System keyring | Plain text files, Environment |
| **Mobile** | EncryptedSharedPreferences | EncryptedSharedPreferences | SharedPreferences, SQLite |

### Desktop Token Storage (Python)

**CORRECT Implementation**:

```python
# financeapp-desktop/src/api/token_storage.py
"""
Secure token storage using system keyring.

Security Features:
- Uses OS-level credential storage (Keychain, Credential Manager)
- Encrypted at rest by operating system
- Requires user authentication for access
- Fallback to encrypted file storage if keyring unavailable
"""
import keyring
from cryptography.fernet import Fernet
import json
from pathlib import Path
import os

SERVICE_NAME = "financeapp"
KEYRING_ACCESS_TOKEN = "access_token"
KEYRING_REFRESH_TOKEN = "refresh_token"


class TokenStorage:
    """
    Secure token storage with keyring and encrypted fallback.

    Priority:
    1. System keyring (most secure)
    2. Encrypted file (fallback)

    Never stores tokens in plain text.
    """

    def __init__(self):
        self._use_keyring = self._test_keyring()
        if not self._use_keyring:
            self._init_fallback()

    def _test_keyring(self) -> bool:
        """Test if system keyring is available."""
        try:
            keyring.get_password(SERVICE_NAME, "test")
            return True
        except Exception:
            return False

    def _init_fallback(self):
        """Initialize encrypted file fallback."""
        self._fallback_dir = Path.home() / '.financeapp' / 'secure'
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions (Unix only)
        try:
            os.chmod(self._fallback_dir, 0o700)
        except Exception:
            pass

        self._key_file = self._fallback_dir / '.key'
        self._token_file = self._fallback_dir / '.tokens'

        if not self._key_file.exists():
            key = Fernet.generate_key()
            self._key_file.write_bytes(key)
            try:
                os.chmod(self._key_file, 0o600)
            except Exception:
                pass

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher for fallback encryption."""
        return Fernet(self._key_file.read_bytes())

    def save_tokens(self, access_token: str, refresh_token: str) -> None:
        """
        Save tokens securely.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
        """
        if self._use_keyring:
            keyring.set_password(SERVICE_NAME, KEYRING_ACCESS_TOKEN, access_token)
            keyring.set_password(SERVICE_NAME, KEYRING_REFRESH_TOKEN, refresh_token)
        else:
            # Encrypted fallback
            cipher = self._get_cipher()
            data = json.dumps({
                'access_token': access_token,
                'refresh_token': refresh_token
            }).encode()
            encrypted = cipher.encrypt(data)
            self._token_file.write_bytes(encrypted)

    def get_access_token(self) -> str | None:
        """Retrieve access token."""
        if self._use_keyring:
            return keyring.get_password(SERVICE_NAME, KEYRING_ACCESS_TOKEN)
        else:
            return self._get_fallback_token('access_token')

    def get_refresh_token(self) -> str | None:
        """Retrieve refresh token."""
        if self._use_keyring:
            return keyring.get_password(SERVICE_NAME, KEYRING_REFRESH_TOKEN)
        else:
            return self._get_fallback_token('refresh_token')

    def _get_fallback_token(self, token_type: str) -> str | None:
        """Get token from encrypted fallback storage."""
        if not self._token_file.exists():
            return None
        try:
            cipher = self._get_cipher()
            encrypted = self._token_file.read_bytes()
            data = json.loads(cipher.decrypt(encrypted))
            return data.get(token_type)
        except Exception:
            return None

    def clear_tokens(self) -> None:
        """Remove all stored tokens."""
        if self._use_keyring:
            try:
                keyring.delete_password(SERVICE_NAME, KEYRING_ACCESS_TOKEN)
                keyring.delete_password(SERVICE_NAME, KEYRING_REFRESH_TOKEN)
            except keyring.errors.PasswordDeleteError:
                pass
        else:
            if self._token_file.exists():
                self._token_file.unlink()
```

### Mobile Token Storage (Kotlin)

**CORRECT Implementation**:

```kotlin
// financeapp-mobile/data/local/TokenStorage.kt
package com.financeapp.data.local

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Secure token storage using Android EncryptedSharedPreferences.
 *
 * Security Features:
 * - AES-256-GCM encryption for values
 * - AES-256-SIV encryption for keys
 * - Hardware-backed keystore (when available)
 * - Automatic key rotation support
 */
@Singleton
class TokenStorage @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val encryptedPrefs = EncryptedSharedPreferences.create(
        context,
        "secure_tokens",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    companion object {
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_TOKEN_EXPIRY = "token_expiry"
    }

    /**
     * Save authentication tokens.
     *
     * @param accessToken JWT access token
     * @param refreshToken JWT refresh token
     * @param expiryTimestamp Token expiry as Unix timestamp (milliseconds)
     */
    fun saveTokens(
        accessToken: String,
        refreshToken: String,
        expiryTimestamp: Long
    ) {
        encryptedPrefs.edit().apply {
            putString(KEY_ACCESS_TOKEN, accessToken)
            putString(KEY_REFRESH_TOKEN, refreshToken)
            putLong(KEY_TOKEN_EXPIRY, expiryTimestamp)
            apply()
        }
    }

    /**
     * Get access token if not expired.
     *
     * @return Access token or null if expired/missing
     */
    fun getAccessToken(): String? {
        val expiry = encryptedPrefs.getLong(KEY_TOKEN_EXPIRY, 0)
        val bufferMs = 60_000L // 1 minute buffer

        return if (System.currentTimeMillis() < expiry - bufferMs) {
            encryptedPrefs.getString(KEY_ACCESS_TOKEN, null)
        } else {
            null // Token expired
        }
    }

    /**
     * Get refresh token.
     */
    fun getRefreshToken(): String? {
        return encryptedPrefs.getString(KEY_REFRESH_TOKEN, null)
    }

    /**
     * Check if tokens are valid and not expired.
     */
    fun hasValidTokens(): Boolean {
        val expiry = encryptedPrefs.getLong(KEY_TOKEN_EXPIRY, 0)
        return System.currentTimeMillis() < expiry &&
               encryptedPrefs.getString(KEY_ACCESS_TOKEN, null) != null
    }

    /**
     * Clear all stored tokens (logout).
     */
    fun clearTokens() {
        encryptedPrefs.edit().clear().apply()
    }
}
```

### Token Refresh Flow

```
+--------+                               +--------+                               +--------+
| Client |                               |  API   |                               |  Auth  |
+---+----+                               +---+----+                               +---+----+
    |                                        |                                        |
    |  1. Request with expired token         |                                        |
    |--------------------------------------->|                                        |
    |                                        |                                        |
    |  2. 401 Unauthorized                   |                                        |
    |<---------------------------------------|                                        |
    |                                        |                                        |
    |  3. Refresh token request              |                                        |
    |------------------------------------------------------------------------------->|
    |                                        |                                        |
    |  4. Validate refresh token             |                                        |
    |                                        |<---------------------------------------|
    |                                        |                                        |
    |  5. Issue new access + refresh tokens  |                                        |
    |<-------------------------------------------------------------------------------|
    |                                        |                                        |
    |  6. Blacklist old refresh token        |                                        |
    |                                        |--------------------------------------->|
    |                                        |                                        |
    |  7. Retry original request             |                                        |
    |--------------------------------------->|                                        |
    |                                        |                                        |
    |  8. Success response                   |                                        |
    |<---------------------------------------|                                        |
```

---

## 4. Data Encryption

### Encryption at Rest

#### Database Encryption

| Platform | Database | Encryption Method |
|----------|----------|-------------------|
| **Web** | PostgreSQL | TDE or pgcrypto extension |
| **Desktop** | SQLite | SQLCipher (AES-256) |
| **Mobile** | Room | SQLCipher Android |

**Desktop SQLCipher Implementation**:

```python
# financeapp-desktop/src/database/connection.py
"""
Encrypted SQLite database connection using SQLCipher.

Security Features:
- AES-256 encryption
- Secure key derivation (PBKDF2)
- Memory protection for key material
"""
from sqlcipher3 import dbapi2 as sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os


def create_encrypted_engine(db_path: str, encryption_key: str):
    """
    Create SQLAlchemy engine with SQLCipher encryption.

    Args:
        db_path: Path to database file
        encryption_key: Encryption passphrase (min 32 chars recommended)

    Returns:
        Configured SQLAlchemy engine
    """
    # Use in-memory URI to enable SQLCipher
    engine = create_engine(
        f"sqlite+pysqlcipher://:{encryption_key}@/{db_path}",
        echo=False,
        pool_pre_ping=True,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # SQLCipher configuration
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.execute("PRAGMA kdf_iter = 256000")  # Key derivation iterations
        cursor.execute("PRAGMA cipher_memory_security = ON")
        cursor.close()

    return engine


def get_encryption_key() -> str:
    """
    Retrieve database encryption key from secure storage.

    NEVER hardcode this key. Use:
    1. System keyring
    2. Environment variable (development only)
    3. Hardware security module (production)
    """
    import keyring
    key = keyring.get_password("financeapp", "db_encryption_key")
    if not key:
        # Generate and store new key
        key = os.urandom(32).hex()
        keyring.set_password("financeapp", "db_encryption_key", key)
    return key
```

**Mobile SQLCipher Implementation**:

```kotlin
// financeapp-mobile/data/local/database/AppDatabase.kt
package com.financeapp.data.local.database

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import net.sqlcipher.database.SQLiteDatabase
import net.sqlcipher.database.SupportFactory

@Database(
    entities = [TransactionEntity::class, BudgetEntity::class],
    version = 1,
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun transactionDao(): TransactionDao
    abstract fun budgetDao(): BudgetDao

    companion object {
        private const val DATABASE_NAME = "financeapp.db"

        /**
         * Create encrypted Room database.
         *
         * Uses SQLCipher for AES-256 encryption of all database files.
         *
         * @param context Application context
         * @param passphrase Database encryption passphrase
         */
        fun create(context: Context, passphrase: CharArray): AppDatabase {
            val passphraseBytes = SQLiteDatabase.getBytes(passphrase)
            val factory = SupportFactory(passphraseBytes)

            return Room.databaseBuilder(
                context.applicationContext,
                AppDatabase::class.java,
                DATABASE_NAME
            )
                .openHelperFactory(factory)
                .build()
        }
    }
}
```

#### Sensitive Field Encryption

For individual field encryption (bank tokens, etc.):

```python
# financeapp-web/apps/banking/encryption.py
"""
Field-level encryption for sensitive banking data.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
Encryption key MUST be stored in secure secrets management.
"""
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
import base64
import os


class FieldEncryption:
    """
    Encrypt/decrypt individual database fields.

    Usage:
        encrypted = FieldEncryption.encrypt("secret_value")
        decrypted = FieldEncryption.decrypt(encrypted)
    """

    _cipher: Fernet | None = None

    @classmethod
    def _get_cipher(cls) -> Fernet:
        """Get or create Fernet cipher."""
        if cls._cipher is None:
            key = settings.FIELD_ENCRYPTION_KEY
            if not key:
                raise ValueError(
                    "FIELD_ENCRYPTION_KEY must be set in environment. "
                    "Generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            cls._cipher = Fernet(key.encode())
        return cls._cipher

    @classmethod
    def encrypt(cls, value: str) -> str:
        """
        Encrypt a string value.

        Args:
            value: Plain text to encrypt

        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return ""
        cipher = cls._get_cipher()
        encrypted = cipher.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    @classmethod
    def decrypt(cls, encrypted_value: str) -> str:
        """
        Decrypt an encrypted value.

        Args:
            encrypted_value: Base64-encoded encrypted string

        Returns:
            Decrypted plain text

        Raises:
            InvalidToken: If decryption fails (wrong key or corrupted data)
        """
        if not encrypted_value:
            return ""
        cipher = cls._get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
        return cipher.decrypt(encrypted_bytes).decode()
```

### Encryption in Transit

**TLS Requirements**:

| Requirement | Value |
|-------------|-------|
| Minimum Version | TLS 1.2 (prefer 1.3) |
| Cipher Suites | ECDHE + AES-GCM only |
| Certificate | Valid CA-signed certificate |
| HSTS | Enabled with preload |

**Certificate Pinning (Mobile)**:

```kotlin
// financeapp-mobile/data/remote/NetworkModule.kt
package com.financeapp.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import okhttp3.CertificatePinner
import okhttp3.OkHttpClient
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    /**
     * Configure OkHttp with certificate pinning.
     *
     * CRITICAL: Update pins when server certificates are rotated.
     * Include backup pins to prevent lockout during rotation.
     */
    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        val certificatePinner = CertificatePinner.Builder()
            // Primary certificate pin
            .add(
                "api.financeapp.com",
                "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
            )
            // Backup pin (intermediate CA)
            .add(
                "api.financeapp.com",
                "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="
            )
            .build()

        return OkHttpClient.Builder()
            .certificatePinner(certificatePinner)
            .build()
    }
}
```

---

## 5. Input Validation

### Validation Rules

**ALWAYS validate**:
- All user input
- All API request parameters
- All file uploads
- All URL parameters

**Validation Order**:
1. Type checking
2. Length limits
3. Format validation (regex)
4. Business rules
5. Authorization check

### Django Serializer Validation

```python
# financeapp-web/apps/transactions/serializers.py
"""
Transaction serializers with comprehensive validation.
"""
from rest_framework import serializers
from decimal import Decimal
import bleach
from .models import Transaction


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating transactions.

    Validation:
    - Amount: Positive, max 999,999,999.99
    - Description: Max 500 chars, HTML sanitized
    - Type: Must be valid enum value
    - Date: Not in future
    """

    class Meta:
        model = Transaction
        fields = ['amount', 'type', 'category_id', 'description', 'transaction_date']

    def validate_amount(self, value: Decimal) -> Decimal:
        """
        Validate transaction amount.

        - Must be positive
        - Maximum 999,999,999.99
        - Exactly 2 decimal places
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")

        if value > Decimal('999999999.99'):
            raise serializers.ValidationError("Amount exceeds maximum allowed")

        # Ensure exactly 2 decimal places
        if value.as_tuple().exponent < -2:
            raise serializers.ValidationError("Amount cannot have more than 2 decimal places")

        return value

    def validate_description(self, value: str) -> str:
        """
        Sanitize and validate description.

        - Strip HTML tags
        - Max 500 characters
        - Strip leading/trailing whitespace
        """
        if not value:
            return ""

        # Remove all HTML tags
        sanitized = bleach.clean(value, tags=[], strip=True)

        # Strip whitespace
        sanitized = sanitized.strip()

        if len(sanitized) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters")

        return sanitized

    def validate_transaction_date(self, value):
        """Validate transaction date is not in future."""
        from django.utils import timezone

        if value > timezone.now().date():
            raise serializers.ValidationError("Transaction date cannot be in the future")

        return value

    def validate(self, attrs):
        """Cross-field validation."""
        # Example: Transfers must have destination account
        if attrs.get('type') == 'transfer' and not attrs.get('destination_account_id'):
            raise serializers.ValidationError({
                'destination_account_id': 'Required for transfer transactions'
            })

        return attrs
```

### SQL Injection Prevention

**ALWAYS use parameterized queries**:

```python
# CORRECT - Parameterized query
from django.db import connection

def get_user_transactions(user_id: str, min_amount: Decimal):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT * FROM transactions
            WHERE user_id = %s AND amount >= %s
            ORDER BY transaction_date DESC
            """,
            [user_id, min_amount]
        )
        return cursor.fetchall()

# CORRECT - ORM (safe by default)
Transaction.objects.filter(user_id=user_id, amount__gte=min_amount)

# WRONG - String interpolation (VULNERABLE!)
cursor.execute(f"SELECT * FROM transactions WHERE user_id = '{user_id}'")

# WRONG - String concatenation (VULNERABLE!)
query = "SELECT * FROM transactions WHERE user_id = '" + user_id + "'"
```

### XSS Prevention

```python
# Django templates - Auto-escaped by default
# SAFE:
{{ user_input }}

# If you MUST render HTML (use sparingly):
{{ user_input|safe }}  # Only after sanitization

# Manual sanitization with bleach:
import bleach

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'li']
ALLOWED_ATTRIBUTES = {}

def sanitize_html(html_content: str) -> str:
    """Sanitize HTML to prevent XSS attacks."""
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
```

---

## 6. OWASP Top 10 Compliance

### A01:2021 - Broken Access Control

**Requirements**:
- Every endpoint MUST check user ownership
- Use Django's `get_object_or_404` with user filter
- Implement proper permission classes

```python
# financeapp-web/apps/transactions/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet with mandatory user-based access control.

    Security:
    - All queries filtered by authenticated user
    - Object-level permission check on retrieve/update/delete
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter all queries to user's own data."""
        # CRITICAL: Never return unfiltered queryset
        return Transaction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Ensure user is set on create."""
        serializer.save(user=self.request.user)
```

### A02:2021 - Cryptographic Failures

**Checklist**:
- [ ] Use strong algorithms (AES-256, SHA-256+, Argon2)
- [ ] Never roll your own crypto
- [ ] Rotate secrets periodically
- [ ] Use TLS 1.3 for all communications
- [ ] Encrypt sensitive data at rest

### A03:2021 - Injection

**Prevention**:
- ORM for all database access
- Parameterized queries when raw SQL needed
- Input validation and sanitization
- Content Security Policy headers

### A04:2021 - Insecure Design

**Requirements**:
- Threat modeling during design
- Security requirements in user stories
- Security-focused code reviews
- Rate limiting on all endpoints

### A05:2021 - Security Misconfiguration

**Production Settings** (MANDATORY):

```python
# config/settings/production.py
DEBUG = False

ALLOWED_HOSTS = ['api.financeapp.com', 'www.financeapp.com']

# HTTPS enforcement
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

# Content security
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### A06:2021 - Vulnerable Components

**Requirements**:
- Regular dependency updates (weekly)
- Automated vulnerability scanning (Dependabot, Snyk)
- Pin versions in requirements
- Monitor security advisories

### A07:2021 - Authentication Failures

**Covered in Section 2: Authentication**

### A08:2021 - Software and Data Integrity Failures

**Requirements**:
- Code signing for releases
- Checksum verification for dependencies
- Secure CI/CD pipeline
- Signed commits (recommended)

### A09:2021 - Security Logging and Monitoring

**Covered in Section 9: Logging Security**

### A10:2021 - Server-Side Request Forgery (SSRF)

**Prevention**:
- Validate and sanitize all URLs
- Allowlist external services
- Block internal IP ranges
- No user-controlled URLs to internal resources

---

## 7. Rate Limiting

### Rate Limit Configuration

| Endpoint Category | Limit | Window | Reason |
|-------------------|-------|--------|--------|
| Login | 5 | 1 minute | Brute force prevention |
| Register | 3 | 1 hour | Abuse prevention |
| Password Reset | 3 | 1 hour | Email bombing prevention |
| Standard API | 100 | 1 minute | Fair usage |
| Bulk Operations | 10 | 1 minute | Resource protection |
| Bank Sync | 5 | 5 minutes | External API limits |

### Django REST Framework Configuration

```python
# config/settings/base.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '100/minute',
        'auth': '5/minute',
        'password_reset': '3/hour',
        'register': '3/hour',
        'bank_sync': '5/5m',
    }
}
```

```python
# financeapp-web/apps/accounts/throttles.py
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """Rate limit for authentication endpoints."""
    scope = 'auth'


class PasswordResetRateThrottle(AnonRateThrottle):
    """Rate limit for password reset."""
    scope = 'password_reset'


class BankSyncRateThrottle(UserRateThrottle):
    """Rate limit for bank synchronization."""
    scope = 'bank_sync'
```

### Response Headers

```python
# Custom middleware to add rate limit headers
class RateLimitHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add rate limit info to headers
        if hasattr(request, 'throttle_info'):
            response['X-RateLimit-Limit'] = request.throttle_info['limit']
            response['X-RateLimit-Remaining'] = request.throttle_info['remaining']
            response['X-RateLimit-Reset'] = request.throttle_info['reset']

        return response
```

---

## 8. Secret Management

### Environment Variables

**Required Environment Variables**:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Random 50+ chars |
| `DATABASE_URL` | Database connection | `postgres://...` |
| `REDIS_URL` | Redis connection | `redis://...` |
| `FIELD_ENCRYPTION_KEY` | Fernet key for field encryption | Fernet.generate_key() |
| `JWT_SIGNING_KEY` | JWT signing secret | Random 64+ chars |
| `PLAID_CLIENT_ID` | Plaid API client ID | `xxx` |
| `PLAID_SECRET` | Plaid API secret | `xxx` |
| `STRIPE_SECRET_KEY` | Stripe API key | `sk_live_xxx` |

### .gitignore (MANDATORY)

```gitignore
# Environment files
.env
.env.local
.env.*.local
.env.production
.env.staging

# Secret files
*.pem
*.key
*.p12
secrets/
credentials/

# IDE secrets
.idea/secrets/
.vscode/secrets/

# Local database with sensitive data
*.sqlite3
*.db

# Log files (may contain sensitive data)
*.log
logs/
```

### .env.example Template

```bash
# FinanceApp Environment Configuration
# Copy this file to .env and fill in values
# NEVER commit .env to version control

# =============================================================================
# DJANGO SETTINGS
# =============================================================================

# SECURITY: Generate with: python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY=your-secret-key-here

# SECURITY: Set to False in production
DEBUG=True

# Production hosts
ALLOWED_HOSTS=localhost,127.0.0.1

# =============================================================================
# DATABASE
# =============================================================================

# Format: postgres://USER:PASSWORD@HOST:PORT/DATABASE
DATABASE_URL=postgres://postgres:password@localhost:5432/financeapp

# =============================================================================
# REDIS
# =============================================================================

REDIS_URL=redis://localhost:6379/0

# =============================================================================
# ENCRYPTION
# =============================================================================

# SECURITY: Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY=your-fernet-key-here

# =============================================================================
# THIRD-PARTY SERVICES
# =============================================================================

# Plaid (banking integration)
PLAID_CLIENT_ID=
PLAID_SECRET=
PLAID_ENV=sandbox

# Stripe (payments)
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=

# =============================================================================
# EMAIL
# =============================================================================

EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

### Secret Rotation Schedule

| Secret Type | Rotation Frequency | Process |
|-------------|-------------------|---------|
| JWT Signing Key | 90 days | Zero-downtime rotation with grace period |
| API Keys (third-party) | 90 days | Coordinated with key deployment |
| Database Passwords | 90 days | Rotate during maintenance window |
| Encryption Keys | 365 days | Re-encrypt data after rotation |
| Service Account Keys | 180 days | Automated rotation where possible |

---

## 9. Logging Security

### Fields to NEVER Log

```python
# financeapp-web/apps/core/logging.py
"""
Logging configuration with security safeguards.

CRITICAL: Never log these fields:
- Passwords (any form)
- Authentication tokens
- API keys/secrets
- Credit card numbers
- SSN/national IDs
- Full bank account numbers
"""

SENSITIVE_FIELDS = [
    'password',
    'new_password',
    'old_password',
    'confirm_password',
    'access_token',
    'refresh_token',
    'token',
    'api_key',
    'secret',
    'secret_key',
    'credit_card',
    'card_number',
    'cvv',
    'cvc',
    'ssn',
    'social_security',
    'bank_account',
    'account_number',
    'routing_number',
    'authorization',
]


def sanitize_log_data(data: dict) -> dict:
    """
    Remove sensitive fields from data before logging.

    Args:
        data: Dictionary that may contain sensitive fields

    Returns:
        Sanitized copy with sensitive values masked
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()

        # Check if key contains any sensitive field name
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_log_data(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value

    return sanitized
```

### Required Audit Events

**MUST log these events**:

| Event | Log Level | Data to Include |
|-------|-----------|-----------------|
| Login success | INFO | user_id, IP, user_agent |
| Login failure | WARNING | email (masked), IP, reason |
| Logout | INFO | user_id |
| Password change | INFO | user_id |
| MFA enabled/disabled | INFO | user_id |
| API key created | INFO | user_id, key_id |
| API key revoked | INFO | user_id, key_id |
| Permission change | WARNING | user_id, old_role, new_role |
| Data export | INFO | user_id, export_type |
| Account deletion | WARNING | user_id |

### Structured Log Format

```json
{
  "timestamp": "2026-01-28T14:30:00.000Z",
  "level": "INFO",
  "logger": "financeapp.accounts",
  "event": "user.login.success",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "ip_address": "192.168.1.100",
  "user_agent": "FinanceApp Desktop/1.0.0",
  "request_id": "abc123-def456",
  "correlation_id": "xyz789",
  "message": "User logged in successfully"
}
```

### Log Configuration

```python
# config/settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(timestamp)s %(level)s %(name)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
        'security': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'formatter': 'json',
        },
    },
    'loggers': {
        'financeapp.security': {
            'handlers': ['console', 'security'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

---

## 10. API Security Headers

### Required Headers

```python
# config/settings/base.py

# Security Headers (Django built-in)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### Custom Security Headers Middleware

```python
# financeapp-web/apps/core/middleware.py
"""
Security headers middleware.

Adds security headers to all responses for protection against:
- XSS attacks
- Clickjacking
- MIME sniffing
- Information disclosure
"""


class SecurityHeadersMiddleware:
    """Add comprehensive security headers to all responses."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(self)'
        )

        # Remove server identification
        if 'Server' in response:
            del response['Server']
        response['X-Powered-By'] = ''

        return response
```

### CORS Configuration

```python
# config/settings/base.py

# CORS settings (django-cors-headers)
CORS_ALLOWED_ORIGINS = [
    "https://app.financeapp.com",
    "https://www.financeapp.com",
]

# For development only - NEVER in production
# CORS_ALLOW_ALL_ORIGINS = True  # DANGEROUS!

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-request-id',
]
```

---

## 11. Platform-Specific Security

### Web (Django)

**Security Checklist**:
- [x] CSRF protection enabled (default)
- [x] Clickjacking protection (X-Frame-Options)
- [x] SQL injection protection (ORM)
- [x] XSS protection (template auto-escaping)
- [ ] Rate limiting on all endpoints
- [ ] Content Security Policy
- [ ] Security headers middleware

### Desktop (Python/PyQt)

**Security Checklist**:
- [ ] No embedded credentials in binary
- [ ] Code signing for distribution
- [ ] Secure update mechanism
- [ ] Token storage in system keyring
- [ ] Database encryption (SQLCipher)
- [ ] Memory protection for secrets
- [ ] Anti-debugging measures (optional)

### Mobile (Android)

**Security Checklist**:
- [ ] ProGuard/R8 obfuscation enabled
- [ ] Network security config with TLS
- [ ] Certificate pinning
- [ ] Encrypted SharedPreferences
- [ ] Root detection (optional)
- [ ] Screenshot prevention on sensitive screens
- [ ] Secure WebView configuration

**Network Security Config**:

```xml
<!-- res/xml/network_security_config.xml -->
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <!-- Block cleartext traffic -->
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>

    <!-- Production API with pinning -->
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">api.financeapp.com</domain>
        <pin-set expiration="2027-01-01">
            <pin digest="SHA-256">AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=</pin>
            <pin digest="SHA-256">BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=</pin>
        </pin-set>
    </domain-config>

    <!-- Debug overrides (debug builds only) -->
    <debug-overrides>
        <trust-anchors>
            <certificates src="user" />
        </trust-anchors>
    </debug-overrides>
</network-security-config>
```

**AndroidManifest.xml Security**:

```xml
<application
    android:allowBackup="false"
    android:networkSecurityConfig="@xml/network_security_config"
    android:usesCleartextTraffic="false">

    <!-- Prevent screenshots on sensitive activities -->
    <activity
        android:name=".ui.auth.LoginActivity"
        android:windowSecureMode="enabled" />

</application>
```

---

## 12. Security Checklist

### Pre-Release Security Review

**Authentication & Authorization**:
- [ ] JWT tokens expire appropriately
- [ ] Refresh tokens are rotated
- [ ] Old tokens are blacklisted
- [ ] Password requirements enforced
- [ ] Account lockout implemented
- [ ] MFA available (if required)

**Data Protection**:
- [ ] Sensitive data encrypted at rest
- [ ] TLS enforced for all connections
- [ ] No secrets in code or logs
- [ ] PII handled according to policy
- [ ] Data retention policy implemented

**Input Validation**:
- [ ] All inputs validated server-side
- [ ] SQL injection prevented (parameterized queries)
- [ ] XSS prevented (output encoding)
- [ ] File upload restrictions in place
- [ ] Rate limiting enabled

**Infrastructure**:
- [ ] Production debug disabled
- [ ] Security headers configured
- [ ] CORS properly restricted
- [ ] Dependencies updated
- [ ] Vulnerability scan passed

**Logging & Monitoring**:
- [ ] Security events logged
- [ ] Sensitive data not logged
- [ ] Log rotation configured
- [ ] Alerting set up

---

## 13. Incident Response

### Security Incident Types

| Level | Description | Response Time |
|-------|-------------|---------------|
| **Critical** | Active breach, data exfiltration | Immediate (< 1 hour) |
| **High** | Exploitable vulnerability discovered | < 4 hours |
| **Medium** | Potential vulnerability, limited impact | < 24 hours |
| **Low** | Best practice violation, minimal risk | < 1 week |

### Incident Response Steps

1. **Identify**: Confirm the security incident
2. **Contain**: Limit damage (revoke tokens, block IPs)
3. **Eradicate**: Remove threat (patch vulnerability)
4. **Recover**: Restore normal operations
5. **Document**: Record incident details
6. **Review**: Update procedures to prevent recurrence

### Contact Information

| Role | Contact |
|------|---------|
| Security Lead | security@financeapp.com |
| On-Call Engineer | oncall@financeapp.com |
| Incident Response | incident@financeapp.com |

---

**This document is MANDATORY for all FinanceApp development.**

*Last security review: 2026-01-28*
*Next scheduled review: 2026-04-28*
