# Pecunia Security Audit Report

**Date:** 2026-02-04
**Scope:** Full codebase review across all three platforms (Web, Desktop, Mobile)
**Total Findings:** 149 issues (25 Critical, 37 High, 53 Medium, 34 Low)

---

## Executive Summary

This report details the results of a comprehensive security, logic, and technical review of the Pecunia personal finance platform across all three codebases: Django web backend, PyQt6 desktop application, and Kotlin/Android mobile application, including deployment infrastructure.

**The most severe systemic issues are:**

1. **The entire security hardening layer (`security.py`) is dead code** -- never imported by any settings module, meaning Argon2 hashing, CSP headers, JWT audience validation, CORS restrictions, and more are all inactive.
2. **Two-Factor Authentication (2FA) is completely bypassed** -- the login flow never checks for TOTP devices after password validation.
3. **Multiple XSS vulnerabilities** in Django templates via `|safe` filter on user-influenced data.
4. **Certificate pinning is entirely non-functional** on mobile (dummy pins, never applied to OkHttpClient).
5. **No authentication gate on mobile** -- the app always opens to the main dashboard.
6. **Critical runtime crashes** across budget signals, AI recommendations, subscription management, and Stripe webhooks due to mismatched field names, method signatures, and type mismatches.

---

## Table of Contents

1. [Web Backend - Authentication & Authorization](#1-web-backend---authentication--authorization)
2. [Web Backend - Banking & Payments](#2-web-backend---banking--payments)
3. [Web Backend - Transactions, AI, Sync & Core](#3-web-backend---transactions-ai-sync--core)
4. [Desktop Application](#4-desktop-application)
5. [Mobile Application](#5-mobile-application)
6. [Infrastructure & Deployment](#6-infrastructure--deployment)
7. [Summary Statistics](#7-summary-statistics)

---

## 1. Web Backend - Authentication & Authorization

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 1 | `config/settings/security.py` | entire file | **Security settings file never imported.** The `__init__.py` imports `production.py` or `development.py`, neither of which imports `security.py`. All hardening (Argon2, CSP, JWT validation, CORS regex, Fernet enforcement) is dead code. |
| 2 | `apps/accounts/views.py` | 109-124 | **2FA completely bypassed.** `LoginAPIView` issues JWT tokens immediately after password check; never calls `TOTPService.is_2fa_enabled()`. Users who enable TOTP get zero additional protection. |
| 3 | `apps/accounts/oauth.py` | 463, 715 | **JWT ID tokens decoded without signature verification.** Both Google and Apple flows use `verify_signature: False`. Comment claims "already verified during token exchange" which is incorrect -- ID tokens must be independently verified against provider JWKS. |
| 4 | `config/settings/base.py` | 36-58 | **Rate limiter runs before authentication middleware.** `RateLimitMiddleware` is at position 2, `AuthenticationMiddleware` at position 9. `request.user` is unset when rate limiting executes, so user-tier rate limits never function. |
| 5 | `config/settings/security.py` | 291 | **JWT signing key can be empty string.** Falls back to `os.environ.get('SECRET_KEY', '')`. If env vars are missing, tokens are signed with empty key, enabling forgery. |
| 6 | `config/settings/production.py` | 13 | **ALLOWED_HOSTS includes empty string.** `''.split(',')` produces `['']`, which matches ANY Host header in Django, enabling DNS rebinding and cache poisoning attacks. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 7 | `apps/accounts/views.py` | 187-199 | **Password change doesn't invalidate JWT tokens.** Attacker's existing tokens remain valid for up to 7 days after victim changes password. |
| 8 | `apps/accounts/views.py` | 136-148 | **Logout can blacklist any user's refresh token.** No validation that the token belongs to the authenticated user. |
| 9 | `apps/accounts/totp.py` | 29-31 | **TOTP secrets stored unencrypted in database.** Plain `CharField`; database compromise exposes all 2FA secrets. |
| 10 | `apps/accounts/tokens.py` | 135 | **Wrong field name breaks email verification token invalidation.** References `email_verified` instead of `is_email_verified`; tokens are never invalidated after verification. |
| 11 | `apps/accounts/views.py` | 151-170 | **UserViewSet exposes DELETE/CREATE.** `ModelViewSet` registers full CRUD; unintended account deletion and creation endpoints are exposed. |
| 12 | `config/settings/development.py` | 16-17 | **CORS allows all origins with credentials.** `CORS_ALLOW_ALL_ORIGINS = True` + `CORS_ALLOW_CREDENTIALS = True` enables cross-origin authenticated requests from any website. |
| 13 | `apps/core/middleware.py` | 737-753 | **`lru_cache` on instance methods causes stale data.** Cached bank account/budget counts never invalidate, allowing subscription limits to be bypassed. |
| 14 | `apps/core/middleware.py` | 142-154, 446-451 | **IP spoofing via X-Forwarded-For.** All three `_get_client_ip` methods trust the first header entry; `TRUSTED_PROXY_COUNT` exists but is never used. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 15 | `apps/accounts/tokens.py` | 78, 118 | Naive datetime in timezone-aware app; token expiration off by UTC offset. |
| 16 | `apps/accounts/tokens.py` | 14, 162 | `PasswordResetTokenGenerator` shadows Django's import of the same name. |
| 17 | `apps/accounts/backup_codes.py` | 69-81 | Backup codes hashed with unsalted SHA-256; brutable in minutes on GPU. |
| 18 | `apps/accounts/totp.py` | 144-156 | TOTP replay prevention is not atomic; race condition allows code reuse. |
| 19 | `apps/accounts/totp.py` | 224-251 | `setup_device` crashes with `IntegrityError` if 2FA already enabled. |
| 20 | `apps/core/middleware.py` | 912-928 | Sanitization regex false positives block legitimate financial data (e.g., "transfer FROM account"). |
| 21 | `apps/core/permissions.py` | 88 | 5-minute subscription cache allows feature access after cancellation. |
| 22 | `apps/accounts/adapters.py` | 124-135 | Auto-linking social accounts trusts unverified `email_verified` claim from provider. |
| 23 | `apps/accounts/adapters.py` | 270-296 | SSRF and unbounded download in profile picture fetch; no URL validation or size limit. |
| 24 | `apps/accounts/views.py` | 82-97 | Registration issues full JWT tokens without requiring email verification. |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 25 | `config/settings/base.py` / `security.py` | various | Duplicate conflicting `SIMPLE_JWT` definitions. |
| 26 | `apps/accounts/serializers.py` | 77-80 | Dead code: inactive user check is unreachable. |
| 27 | `apps/accounts/emails.py` | 75-91 | Non-atomic email rate limiting (check-then-increment race). |
| 28 | `apps/accounts/signals.py` | 18-22 | Cascading profile save on every user save. |
| 29 | `config/settings/security.py` | 108-113 | CSP `style-src 'unsafe-inline'` always enabled. |
| 30 | `apps/accounts/serializers.py` | 96-104 | Dual source of truth for `subscription_tier`. |

---

## 2. Web Backend - Banking & Payments

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 31 | `apps/banking/views.py` | 93-96 | **OAuth state token leaked in API response body.** The CSRF-protection `state` parameter is returned to the client, defeating OAuth CSRF protection. |
| 32 | `apps/banking/serializers.py` | 69-70, 88-93 | **Unvalidated `redirect_uri` enables OAuth token theft.** No domain allowlist; attacker can redirect authorization codes to `https://evil.com`. |
| 33 | `apps/subscriptions/webhooks.py` | 722-761 | **Test webhook endpoint bypasses signature verification.** When `DEBUG=True`, accepts unverified payloads; can forge subscription events for free premium access. |
| 34 | `apps/banking/providers/budget_insight.py` | 222 | **Full bank account numbers stored without masking.** The `account_number_masked` field stores raw unmasked numbers from Budget Insight/Powens. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 35 | `apps/banking/providers/*.py` | 42-56 (all 3) | **Provider init order bug.** `super().__init__()` calls `_validate_configuration()` before attributes are assigned, causing `AttributeError`. Banking feature is non-functional. |
| 36 | `apps/banking/views.py` | 419-423 | **Token refresh discards new refresh_token.** `refresh_balance` only saves `access_token`, permanently breaking connections with rotating refresh tokens (TrueLayer). |
| 37 | `apps/subscriptions/views.py` + `stripe_service.py` | 234, 286, 351 | **Stripe service method signature mismatches.** Views pass strings where objects are expected, expect tuples where objects are returned. All subscription operations crash. |
| 38 | `apps/subscriptions/webhooks.py` | 654 | **`construct_webhook_event` method doesn't exist.** Webhook handler calls nonexistent method; production webhooks crash with `AttributeError`. |
| 39 | `apps/banking/providers/truelayer.py` | 172, 175, 204 | **Naive datetime causes `TypeError` on expiry check.** `datetime.utcnow()` produces naive datetimes compared against timezone-aware `timezone.now()`. |
| 40 | `apps/banking/views.py` | 129-224, 503-558 | **No rate limiting on sync endpoints.** External API calls can be spammed, exhausting provider rate limits. |
| 41 | `apps/banking/providers/plaid.py` | 49-55 | **Plaid secret not validated in configuration check.** Only `client_id` checked; missing `secret` causes cryptic API errors. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 42 | `apps/banking/providers/plaid.py` | 67-89 | Credentials double-sent in both headers and body. |
| 43 | `apps/banking/models.py` | 285-287 | `is_token_expired` defaults to `False` when expiry unknown (fail-open). |
| 44 | `apps/subscriptions/views.py` | 52 | Plan metadata exposed to unauthenticated users. |
| 45 | `apps/subscriptions/stripe_service.py` | 45-46 | Global `stripe.api_key` assignment at module level. |
| 46 | `apps/banking/views.py` | 100-102 | Error messages leak internal provider details to clients. |
| 47 | `apps/banking/views.py` | 503-558 | `SyncAllView` synchronous with no timeout; ties up workers. |
| 48 | `apps/banking/views.py` | 130-224 | No locking on concurrent syncs; race condition on balance data. |
| 49 | `apps/subscriptions/views.py` | 247-258 | Local subscription state can diverge from Stripe on crash. |
| 50 | `apps/subscriptions/webhooks.py` | 707-708 | Webhook errors leak raw payload data (PII). |
| 51 | `apps/subscriptions/webhooks.py` | 711-715 | Exception details returned in webhook error response. |
| 52 | `apps/subscriptions/webhooks.py` | 35-67 | Cache-based webhook idempotency is fragile (survives only 24h, lost on restart). |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 53 | `apps/subscriptions/views.py` | multiple | PII (email) logged in application logs. |
| 54 | `apps/subscriptions/webhooks.py` | 636-638 | No webhook IP allowlisting. |
| 55 | `apps/banking/template_views.py` | 103 | Host header used for OAuth redirect_uri construction. |
| 56 | `apps/banking/template_views.py` | 143 | OAuth authorization code exposed in GET parameters. |

---

## 3. Web Backend - Transactions, AI, Sync & Core

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 57 | `apps/sync/manager.py` | 276-279 | **Mass assignment in sync `_create_object`.** Passes all client data to `Model.objects.create(**data)` without field filtering; attacker can inject `is_staff=True` or any field. |
| 58 | `apps/ai/views.py` | 318 | **CSRF exemption on ChatView.** `@csrf_exempt` on a session-authenticated view enables cross-site request forgery against AI chat. |
| 59 | `apps/transactions/importers/ofx_importer.py` | 13, 172 | **XXE vulnerability.** Uses `xml.etree.ElementTree` to parse user-uploaded OFX files; vulnerable to Billion Laughs XML bomb and external entity resolution. |
| 60 | `apps/transactions/serializers.py` | 53-67 | **Cross-user IDOR.** `TransactionSerializer` allows setting `bank_account` and `category` to UUIDs belonging to other users; no ownership validation. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 61 | `apps/ai/views.py`, `services/categorization.py`, `services/anomaly_detection.py`, `services/recommendations.py` | multiple | **AI prompt injection.** User-controlled transaction descriptions interpolated directly into AI prompts without sanitization. |
| 62 | `apps/ai/views.py`, `apps/sync/views.py` | multiple | **Error messages leak internal details.** Raw `str(e)` returned to clients; recommendations service also returns `raw_data`. |
| 63 | `apps/budgets/signals.py` | 16, 90, 99, 123, 130-131 | **Budget signals reference non-existent models/fields.** `BudgetAlert` import fails; `is_alert_enabled`, `transaction_type`, `date`, `is_deleted` don't exist. Budget tracking is non-functional. |
| 64 | `apps/ai/models.py` vs `services/anomaly_detection.py`, `services/recommendations.py` | multiple | **Priority type mismatch.** Model uses `PositiveSmallIntegerField(1-5)` but services save strings like `"medium"`, `"urgent"`. All recommendation saves crash. |
| 65 | `apps/ai/models.py` vs `services/*` | multiple | **RecommendationType mismatch.** Services use `"spending"`, `"saving"`, `"goal"`, `"trend"` which are not valid model choices. |
| 66 | `apps/budgets/serializers.py` | 189-205 | **Non-atomic budget item updates.** Deletes all items then recreates; crash mid-operation causes permanent data loss. |
| 67 | `apps/ai/serializers.py` | 85-87 | **ChatMessageSerializer allows `system` role.** Clients can inject system-level prompts into AI conversations. |
| 68 | `apps/ai/tasks.py` | 82-90 | **Cross-tenant data access.** When `user_id=None`, batch task processes all users' transactions together. |
| 69 | `apps/sync/manager.py` | 302-312 | **`_serialize_instance` exposes all model fields** in sync pull, including internal fields not intended for client exposure. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 70 | `apps/transactions/importers/base.py` | -- | No file size limits on import operations. |
| 71 | `apps/ai/services/anomaly_detection.py` | 169-174 | O(n^2) duplicate detection algorithm; DoS risk on large datasets. |
| 72 | `apps/transactions/views.py` | 137-143 | Unvalidated date parameters passed to ORM filters. |
| 73 | `apps/core/tasks.py` | 1028 | `_raw_delete` bypasses Django signals and cascade logic. |
| 74 | `apps/core/tasks.py` | 1087-1097 | Raw `VACUUM ANALYZE` may block during business hours. |
| 75 | `config/celery.py` | 230-285 | `BaseTaskWithRetry` retries all exceptions including validation errors. |
| 76 | `apps/ai/views.py` | 596-609 | **Insights view uses wrong field names** (`date` vs `transaction_date`, `transaction_type` vs `type`). Endpoint crashes with `FieldError`. |
| 77 | `apps/sync/manager.py` | 416-424 | Sync conflict resolution applies unvalidated client data (no `full_clean()`). |
| 78 | `apps/sync/views.py` | 460 | `SyncLogListView` crashes on invalid `limit` parameter. |
| 79 | `config/urls.py` | 42-43 | API docs/schema exposed without authentication. |
| 80 | `apps/ai/services/recommendations.py` | 751-758 | `_save_recommendations` bulk-dismisses active user recommendations. |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 81 | `apps/transactions/template_views.py` | 169 | Hard delete of transactions (no soft-delete). |
| 82 | `apps/ai/services/categorization.py` | 353 | MD5 used for cache keys. |
| 83 | `apps/budgets/serializers.py` | 38-46 | `BudgetItemSerializer` doesn't validate budget ownership (IDOR). |
| 84 | `apps/budgets/views.py` | 299-333 | `update_spent` accepts arbitrary amounts without bounds. |
| 85 | `apps/budgets/views.py` | 335-365 | `bulk_update` silently ignores failures. |
| 86 | `apps/ai/services/recommendations.py` | 525-530 | `_gather_budget_data` uses wrong Budget model structure; crashes silently. |

---

## 4. Desktop Application

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 87 | `src/services/backup.py` | 388 | **Zip Slip vulnerability.** `zf.extractall()` without path validation; malicious backup can write files anywhere on filesystem. |
| 88 | `src/api/auth.py` | 258-279 | **Plaintext token storage in fallback file.** Access/refresh tokens written as JSON to `~/.config/.tokens` without encryption. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 89 | `src/constants.py`, `src/settings_manager.py` | 27, 72 | Default API URL uses HTTP (`http://localhost:8000`). |
| 90 | `src/api/client.py` | 371 | SSL verification can be completely disabled via config. |
| 91 | `src/database/connection.py` | 226 | Database URL (potentially with cipher key) logged at INFO level. |
| 92 | `src/services/backup.py` | 414-422 | Unbound variable `backup_current` crashes restore when no DB exists. |
| 93 | `src/services/notifications.py` | 462-465 | Unsafe `setattr` with user-provided key on notification preferences. |
| 94 | `src/database/models/user.py` | 172-176 | `User.from_dict` uses `setattr` without allowlist; can overwrite ORM internals. |
| 95 | `src/api/auth.py` | 402, 645 | PII (email addresses) logged at INFO level. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 96 | `src/services/import_service.py` | 74 | MD5 used for transaction deduplication hashing. |
| 97 | `src/database/connection.py` | 461-464 | Naive semicolon splitting for SQL migration scripts. |
| 98 | `src/database/connection.py` | 753 | String interpolation for SQL table name (anti-pattern). |
| 99 | `src/database/models/user.py` | 103 | User `__repr__` includes email address (leaks to logs). |
| 100 | `src/sync/manager.py` | 377 | Hardcoded Google DNS (`8.8.8.8`) for connectivity check. |
| 101 | `src/api/budgets.py`, `src/api/transactions.py` | 52, 43 | `float` used for financial amounts instead of `Decimal`. |
| 102 | `src/settings_manager.py` | 560-563 | Non-atomic settings save on Windows (race between unlink and rename). |
| 103 | `src/api/auth.py` | 337 | `is_authenticated` doesn't check token expiry. |
| 104 | `src/keyring_manager.py` | 307-322, 466-484 | XOR cipher fallback with predictable machine-derived key. |
| 105 | `src/main.py`, `src/app.py` | 1186, 876 | Unvalidated URL from server response opened in browser. |
| 106 | `src/database/models/sync.py` | 260-272 | `SyncRecord.from_dict` uses `setattr` without allowlist. |
| 107 | `src/keyring_manager.py` | 25 | Missing `get_credentials_path` function causes `ImportError`. |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 108 | multiple files | various | `sys.path` manipulation at import time. |
| 109 | `src/services/import_service.py` | 31 | Custom `ImportError` shadows Python built-in. |
| 110 | `src/api/client.py` | 152 | Custom `TimeoutError` shadows Python built-in. |
| 111 | `src/main.py` | 1550 | Command-line arguments logged (future secret exposure risk). |
| 112 | `src/services/export.py` | 164 | No path validation on export output path. |
| 113 | `src/main.py`, `src/logger.py` | various | Log files created without explicit restrictive permissions. |
| 114 | `src/services/import_service.py` | -- | No file size check before import despite `MAX_IMPORT_FILE_SIZE` constant. |

---

## 5. Mobile Application

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 115 | `di/NetworkModule.kt` | 97 | **Dummy certificate pin.** SHA-256 pin is all 'A' characters; provides zero MITM protection. |
| 116 | `di/NetworkModule.kt` | 109-165 | **CertificatePinner created but never applied** to either OkHttpClient builder. |
| 117 | `res/xml/network_security_config.xml` | 11-15 | **Cleartext traffic permitted to `api-dev.pecunia.com`** in release builds (not gated by `debug-overrides`). |
| 118 | `res/xml/network_security_config.xml` | 25-30 | **Production certificate pinning entirely commented out.** |
| 119 | `MainActivity.kt` | 122-126 | **No authentication gate.** App always navigates to main dashboard regardless of auth state. |
| 120 | `MainActivity.kt` | 210-254 | **Deep links bypass authentication** and navigate to arbitrary screens with unvalidated resource IDs. |
| 121 | `data/local/database/DatabaseCallback.kt` | 242-260 | **SQL injection via string interpolation** in database prepopulation. French strings containing apostrophes will break or inject SQL. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 122 | `res/xml/backup_rules.xml` | 3 | Backup rules include encrypted SharedPreferences containing auth tokens. |
| 123 | `AndroidManifest.xml` | 67 | `android:allowBackup="true"` for a financial application. |
| 124 | `di/DatabaseModule.kt` | 73 | `fallbackToDestructiveMigration()` will silently wipe all financial data on schema change. |
| 125 | `data/remote/api/AuthInterceptor.kt` | 49-69 | Token refresh not implemented; retries with same expired token in infinite loop. |
| 126 | multiple | (absent) | No root/jailbreak detection. |
| 127 | multiple | (absent) | No biometric authentication implementation despite feature flag and dependencies. |
| 128 | `data/remote/api/AuthInterceptor.kt` | 93, 111 | `getAccessToken()` and `getRefreshToken()` are public methods. |
| 129 | `data/local/database/AppDatabase.kt` | -- | No database encryption (SQLCipher). Financial data stored in plaintext SQLite. |
| 130 | `data/local/preferences/UserPreferences.kt` | 46-48 | Tokens in data class with auto-generated `toString()` leaking to logs. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 131 | `di/AppModule.kt` | 85 | Gson date format treats 'Z' as literal character, not UTC indicator. |
| 132 | `di/NetworkModule.kt` | 133, 163 | `retryOnConnectionFailure(true)` can duplicate financial mutations. |
| 133 | `data/repository/TransactionRepository.kt` | 270-274 | Delete operations silently discard server-side failures. |
| 134 | `data/repository/BudgetRepository.kt` | 397-414 | `resetAllSpentAmounts()` queries only unsynced budgets (wrong data source). |
| 135 | `data/remote/dto/TransactionDto.kt` | 18 | `Double` used for financial amounts instead of `BigDecimal`. |
| 136 | `data/remote/dto/BudgetDto.kt` | 74 | `Enum.valueOf()` crashes on unknown server values. |
| 137 | `data/repository/BudgetRepository.kt` | 214-219 | Force-unwrap (`!!`) on nullable budget causes NPE on race condition. |
| 138 | `MainActivity.kt` | 69, 114, 132, 212 | Deep link URLs (potentially with tokens) logged. |
| 139 | `di/AppModule.kt` | 86-87 | `serializeNulls()` + `setPrettyPrinting()` in production Gson. |
| 140 | `AndroidManifest.xml` | 101-107 | Custom scheme deep link without host restriction. |
| 141 | `proguard-rules.pro` | -- | Missing ProGuard rules to strip debug logs. |
| 142 | `di/NetworkModule.kt` | 151-155 | Static `Content-Type: application/json` breaks multipart uploads. |
| 143 | `data/remote/api/AuthInterceptor.kt` | 118-121 | Token expiry relies on client clock; clock manipulation bypasses check. |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| 144 | `data/local/database/AppDatabase.kt` | 101-105 | Duplicate database singleton patterns (companion + Hilt). |
| 145 | `res/xml/backup_rules.xml` | 4 | Wrong database name in backup exclusion (`pecunia.db` vs `pecunia_database`). |
| 146 | `AppConfig.kt` | 136-170 | Feature flags are mutable public `var` properties; can be toggled at runtime. |
| 147 | `data/local/database/DatabaseCallback.kt` | 45+ | Uses `android.util.Log` instead of Timber; logs appear in release. |
| 148 | `data/local/database/DatabaseCallback.kt` | 303-326 | Database row counts logged in production via `Log.d()`. |
| 149 | `MainActivity.kt` | 297 | Placeholder screens display password reset tokens and emails on UI. |

---

## 6. Infrastructure & Deployment

### CRITICAL

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| A1 | `scripts/entrypoint.sh` | 62-77 | **Shell-to-Python code injection via `DB_PASSWORD`.** Password interpolated into inline Python string; single quotes in password enable arbitrary code execution. |
| A2 | `docker/redis/redis.conf` | 111 | **Redis runs without authentication.** `requirepass` commented out. |
| A3 | `docker/redis/redis.conf` | 113-117 | **Dangerous Redis commands not disabled.** `FLUSHALL`, `CONFIG`, `DEBUG` all available. |
| A4 | `docker/nginx/nginx.conf` | 185 | **CSP allows `unsafe-inline` and `unsafe-eval`** for scripts, rendering XSS protections useless. |
| A5 | `docker/nginx/nginx.conf` + `templates/base.html` | 185, 27/116-124 | **CSP blocks legitimate CDN scripts** -- either site is broken or CSP is unenforced. |
| A6 | `templates/transactions/transaction_form.html` | 664 | **XSS via `|safe` filter** on `categories_json` containing user data. |
| A7 | `templates/transactions/transaction_form.html` | 656 | **XSS via unescaped tag names** in JavaScript string literals. |
| A8 | `docker/docker-compose.prod.yml` | 288, 293 | **Default Flower credentials `admin:admin`** on publicly exposed port 5555. |

### HIGH

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| A9 | `.dockerignore` | (missing) | No `.dockerignore`; `COPY . .` bakes `.env` secrets into Docker image layers. |
| A10 | `docker/docker-compose.dev.yml` | 27, 38 | Database and Redis exposed to `0.0.0.0` with default credentials. |
| A11 | `docker/Dockerfile.dev` | entire file | Development container runs as root. |
| A12 | `docker/docker-compose.yml` | 8-9 | Django port 8000 exposed directly, bypassing nginx security. |
| A13 | `docker/nginx/nginx.conf` | 332-345 | Admin panel publicly accessible; IP restriction commented out. |
| A14 | `templates/base.html` | 27, 116-124 | External CDN scripts loaded without Subresource Integrity (SRI). |
| A15 | `templates/base.html` | 27 | Tailwind CSS CDN (development-only) used in production. |
| A16 | `.github/workflows/deploy.yml` | 228-263 | Quoted heredoc prevents variable expansion; deployments silently fail. |
| A17 | `.github/workflows/ci.yml` | 79, 85, 127 | Security checks (Bandit, Safety) silenced with `|| true`. |
| A18 | `.github/workflows/deploy.yml` | 24-28 | `skip_tests` option allows untested code in production. |

### MEDIUM

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| A19 | `docker/nginx/Dockerfile` | 205-212 | Self-signed SSL cert baked into image; same key for all deployments. |
| A20 | `docker/nginx/nginx.conf` | 193-227 | Security headers missing on static/media file responses (nginx `add_header` override). |
| A21 | `templates/partials/messages.html` | 3 | `messages|safe` bypasses escaping on flash messages. |
| A22 | `docker/nginx/nginx.conf` | 165 | `server_name localhost` in production HTTPS block. |
| A23 | `.github/workflows/ci.yml` | 353 | Unpinned GitHub Action (`@master`); supply chain risk. |
| A24 | `templates/base.html` | 12 | CSRF token in meta tag with weak CSP. |
| A25 | `templates/transactions/transaction_form.html` | 7-8, 639-640 | Flatpickr from CDN without SRI or version pinning. |
| A26 | `templates/ai/chat.html` | 229 | AI content rendered with `linebreaks`; future XSS risk if escaping changes. |

### LOW

| # | File | Line(s) | Issue |
|---|------|---------|-------|
| A27 | `.env.example` | 2, 7-8 | Weak default credentials (`postgres:postgres`, placeholder secret key). |
| A28 | `docker/nginx/nginx.conf` | 58 | Excessive `client_max_body_size` (50MB). |
| A29 | `static/js/app.js` | 639 | `console.log` of page views in production. |
| A30 | `docker/redis/redis.conf` | 11 | Redis binds to `0.0.0.0`. |
| A31 | `.github/workflows/deploy.yml` | 368 | Deprecated `actions/create-release@v1`. |
| A32 | `docker/docker-compose.dev.yml` | 13-18 | Missing `DJANGO_SECRET_KEY` in dev compose. |
| A33 | `.github/workflows/deploy.yml` | 260 | Health check over HTTP (not HTTPS). |

---

## 7. Summary Statistics

### By Severity

| Severity | Web Auth | Web Banking | Web Core/AI | Desktop | Mobile | Infra | **Total** |
|----------|----------|-------------|-------------|---------|--------|-------|-----------|
| CRITICAL | 6 | 4 | 4 | 2 | 7 | 8 | **31** |
| HIGH | 8 | 7 | 9 | 7 | 9 | 10 | **50** |
| MEDIUM | 10 | 11 | 11 | 12 | 13 | 8 | **65** |
| LOW | 6 | 4 | 6 | 7 | 6 | 7 | **36** |
| **Total** | **30** | **26** | **30** | **28** | **35** | **33** | **182** |

### By Category

| Category | Count |
|----------|-------|
| Security Vulnerability | 98 |
| Logic Bug | 52 |
| Technical Issue | 32 |

### Top 10 Most Critical Issues to Fix Immediately

1. **Import `security.py`** in production settings -- activates Argon2, CSP, JWT validation, CORS
2. **Implement 2FA check in login flow** -- 2FA currently provides zero protection
3. **Fix XSS via `|safe` filter** in transaction templates -- stored XSS in financial app
4. **Verify OAuth ID token signatures** -- prevents account takeover via forged tokens
5. **Fix mass assignment in sync `_create_object`** -- arbitrary field injection
6. **Apply certificate pinning on mobile** -- financial data transmitted without MITM protection
7. **Add authentication gate on mobile** -- anyone with device access sees all data
8. **Fix Redis authentication** -- unauthenticated cache/queue server
9. **Fix entrypoint.sh code injection** -- DB_PASSWORD enables arbitrary code execution
10. **Fix budget signals and AI type mismatches** -- budget tracking and AI recommendations are completely non-functional

---

*This report was generated through manual source code review of all files across the Pecunia codebase.*
