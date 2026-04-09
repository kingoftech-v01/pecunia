# Master Conventions - Pecunia Multi-Platform

**Version**: 1.0
**Last Updated**: 2026-01-28
**Status**: MANDATORY - All platforms MUST follow these conventions

---

## Table of Contents

1. [Overview](#1-overview)
2. [Project Architecture](#2-project-architecture)
3. [Universal Naming Conventions](#3-universal-naming-conventions)
4. [Platform-Specific Naming](#4-platform-specific-naming)
5. [Git Workflow](#5-git-workflow)
6. [Code Review Guidelines](#6-code-review-guidelines)
7. [Cross-Platform Consistency](#7-cross-platform-consistency)
8. [Data Model Standards](#8-data-model-standards)
9. [API Contract Standards](#9-api-contract-standards)
10. [Error Handling Standards](#10-error-handling-standards)
11. [Testing Standards](#11-testing-standards)
12. [Documentation Standards](#12-documentation-standards)

---

## 1. Overview

### Purpose

This document establishes the foundational conventions for the Pecunia multi-platform project. All developers MUST adhere to these standards to ensure:

- **Consistency**: Uniform code style across all platforms
- **Security**: Standardized security practices
- **Scalability**: Performance-optimized patterns
- **Maintainability**: Easy onboarding and code reviews

### Scope

These conventions apply to:
- **pecunia-web**: Django REST API (source of truth)
- **pecunia-desktop**: Python/PyQt6 desktop application
- **pecunia-mobile**: Kotlin/Android mobile application

### Related Documents

| Document | Purpose |
|----------|---------|
| [SECURITY_GUIDELINES.md](./SECURITY_GUIDELINES.md) | Authentication, encryption, OWASP compliance |
| [SCALABILITY_GUIDELINES.md](./SCALABILITY_GUIDELINES.md) | Performance, caching, database optimization |
| [URL_AND_VIEW_CONVENTIONS.md](./URL_AND_VIEW_CONVENTIONS.md) | Django URL/View patterns |

---

## 2. Project Architecture

### System Overview

```
                    +-------------------+
                    |   Pecunia API  |
                    |   (Django REST)   |
                    |   Source of Truth |
                    +--------+----------+
                             |
            +----------------+----------------+
            |                |                |
    +-------v------+  +------v-------+  +-----v--------+
    |   Desktop    |  |    Mobile    |  |     Web      |
    |   (PyQt6)    |  |   (Android)  |  |   Frontend   |
    |  SQLite DB   |  |   Room DB    |  |   Templates  |
    +--------------+  +--------------+  +--------------+
           |                |
           +----------------+
                   |
         Offline-First Sync
```

### Core Principles

1. **Single Source of Truth**: Web API defines all data contracts
2. **Offline-First**: Desktop and mobile must work without connectivity
3. **Sync-Conflict Resolution**: Last-write-wins with manual override option
4. **UUID Primary Keys**: Consistent across all platforms
5. **ISO 8601 Dates**: Standard date format in API communication

### Repository Structure

```
Account Activity Management/
├── pecunia-web/              # Django REST API
│   ├── apps/                    # Django applications
│   │   ├── accounts/            # User management
│   │   ├── transactions/        # Transaction management
│   │   ├── banking/             # Bank integrations
│   │   ├── budgets/             # Budget management
│   │   └── sync/                # Sync endpoints
│   ├── config/                  # Django settings
│   ├── docker/                  # Container definitions
│   └── requirements.txt
│
├── pecunia-desktop/          # Python desktop app
│   ├── src/
│   │   ├── api/                 # API client modules
│   │   ├── database/            # SQLAlchemy models
│   │   ├── sync/                # Offline sync logic
│   │   ├── ui/                  # PyQt6 components
│   │   └── main.py
│   └── requirements.txt
│
├── pecunia-mobile/           # Android app
│   ├── app/                     # Application module
│   ├── data/                    # Data layer
│   ├── domain/                  # Domain layer
│   └── ui/                      # Presentation layer
│
├── MASTER_CONVENTIONS.md        # This document
├── SECURITY_GUIDELINES.md       # Security standards
├── SCALABILITY_GUIDELINES.md    # Performance standards
└── URL_AND_VIEW_CONVENTIONS.md  # Django URL conventions
```

---

## 3. Universal Naming Conventions

### Identifiers

| Element | Format | Example |
|---------|--------|---------|
| UUID | Lowercase with hyphens | `550e8400-e29b-41d4-a716-446655440000` |
| API Version | Lowercase v + number | `v1`, `v2` |
| Feature Flags | SCREAMING_SNAKE_CASE | `ENABLE_AI_CATEGORIZATION` |

### Date and Time

**API Communication**: Always use ISO 8601 format

```json
{
  "created_at": "2026-01-28T14:30:00Z",
  "transaction_date": "2026-01-28",
  "expires_at": "2026-01-28T15:30:00+01:00"
}
```

| Format | Usage | Example |
|--------|-------|---------|
| DateTime with timezone | Timestamps | `2026-01-28T14:30:00Z` |
| Date only | Transaction dates | `2026-01-28` |
| Time only | Schedules | `14:30:00` |

**NEVER use**:
- Unix timestamps in API responses
- Locale-specific formats (`01/28/2026`)
- Ambiguous formats (`28-01-26`)

### Currency and Money

| Element | Format | Example |
|---------|--------|---------|
| Currency Code | ISO 4217 uppercase | `EUR`, `USD`, `GBP`, `CHF` |
| Amount | Decimal, 2 places, no separators | `1234.56` |
| Negative amounts | Minus prefix | `-1234.56` |

**NEVER use**:
- Thousand separators in API (`1,234.56`)
- Currency symbols in API (`$100`)
- Floating point for money calculations

```json
{
  "amount": 1234.56,
  "currency": "EUR"
}
```

### Text Content

| Element | Format | Example |
|---------|--------|---------|
| Slugs/URL paths | kebab-case | `monthly-budget-report` |
| Display names | Title Case | `Monthly Budget Report` |
| Enum values | lowercase_snake | `pending_approval` |
| Boolean fields | Positive naming | `is_active`, `has_notifications` |

---

## 4. Platform-Specific Naming

### File Naming

| Platform | Files | Directories |
|----------|-------|-------------|
| **Web (Python)** | snake_case.py | snake_case/ |
| **Desktop (Python)** | snake_case.py | snake_case/ |
| **Mobile (Kotlin)** | PascalCase.kt | lowercase/ |

### Code Elements

| Element | Web (Python) | Desktop (Python) | Mobile (Kotlin) |
|---------|--------------|------------------|-----------------|
| Classes | `PascalCase` | `PascalCase` | `PascalCase` |
| Functions/Methods | `snake_case` | `snake_case` | `camelCase` |
| Variables | `snake_case` | `snake_case` | `camelCase` |
| Constants | `SCREAMING_SNAKE` | `SCREAMING_SNAKE` | `SCREAMING_SNAKE` |
| Private members | `_prefix` | `_prefix` | `_prefix` or private |
| Type parameters | `T`, `K`, `V` | `T`, `K`, `V` | `T`, `K`, `V` |

### Database Naming

| Element | Convention | Example |
|---------|------------|---------|
| Tables | plural_snake_case | `transactions`, `bank_accounts` |
| Columns | snake_case | `created_at`, `user_id` |
| Primary keys | `id` | `id` (UUID) |
| Foreign keys | `<table>_id` | `user_id`, `category_id` |
| Junction tables | `<table1>_<table2>` | `user_permissions` |
| Indexes | `ix_<table>_<columns>` | `ix_transactions_user_date` |

---

## 5. Git Workflow

### Branch Strategy

```
main (protected)
├── develop
│   ├── feature/<platform>/<ticket>-<description>
│   ├── bugfix/<platform>/<ticket>-<description>
│   └── refactor/<platform>/<description>
├── release/<version>
└── hotfix/<version>-<description>
```

### Branch Naming

**Format**: `<type>/<platform>/<ticket-id>-<short-description>`

| Type | Usage |
|------|-------|
| `feature` | New functionality |
| `bugfix` | Bug fixes |
| `hotfix` | Critical production fixes |
| `refactor` | Code improvements |
| `docs` | Documentation only |
| `test` | Test additions/fixes |

**Examples**:
```
feature/web/FA-123-add-recurring-transactions
bugfix/mobile/FA-456-fix-sync-conflict
hotfix/1.2.1-critical-auth-fix
refactor/desktop/improve-database-queries
docs/all/update-api-documentation
```

### Commit Message Format

```
<type>(<platform>): <subject>

[optional body]

[optional footer]
```

**Types**:
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Formatting, no code change |
| `refactor` | Code restructuring |
| `perf` | Performance improvement |
| `test` | Adding/fixing tests |
| `chore` | Maintenance tasks |
| `security` | Security-related changes |

**Subject Rules**:
- Use imperative mood ("Add feature" not "Added feature")
- No period at the end
- Maximum 72 characters
- Reference ticket if applicable

**Examples**:

```
feat(web): add transaction categorization endpoint

Implements POST /api/v1/transactions/{id}/categorize
with AI-powered category suggestion support.

Closes FA-789
```

```
fix(desktop): resolve sync conflict on transaction update

The conflict resolver was not properly comparing timestamps
when both local and remote changes occurred within the same
minute. Added millisecond precision to timestamp comparison.

Fixes FA-456
```

```
security(mobile): add certificate pinning for API calls

Implements SHA-256 certificate pinning to prevent
man-in-the-middle attacks on production API endpoints.

BREAKING CHANGE: Requires new certificate deployment
```

### Pull Request Requirements

**Title Format**: `[<PLATFORM>] <type>: <description>`

**Example**: `[WEB] feat: Add recurring transaction support`

**Required Sections**:
```markdown
## Summary
Brief description of changes

## Changes
- List of specific changes
- Organized by category

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if UI changes)
Before | After

## Checklist
- [ ] Code follows conventions
- [ ] Documentation updated
- [ ] No security vulnerabilities introduced
- [ ] Cross-platform compatibility verified (if applicable)
```

### Protected Branch Rules

| Branch | Requirements |
|--------|--------------|
| `main` | 2 approvals, CI pass, no force push |
| `develop` | 1 approval, CI pass |
| `release/*` | 1 approval, CI pass, QA sign-off |

---

## 6. Code Review Guidelines

### Review Checklist

#### Security (CRITICAL)
- [ ] No hardcoded secrets or credentials
- [ ] Input validation present and complete
- [ ] SQL injection prevention verified
- [ ] Authentication/authorization checks in place
- [ ] Sensitive data not logged
- [ ] CSRF protection maintained

#### Code Quality
- [ ] Follows platform naming conventions
- [ ] Docstrings/KDoc comments for public APIs
- [ ] No code duplication (DRY principle)
- [ ] Single responsibility principle followed
- [ ] Error handling is comprehensive
- [ ] No TODO comments without ticket references

#### Performance
- [ ] Database queries optimized (no N+1)
- [ ] Pagination used for list endpoints
- [ ] Caching considered where appropriate
- [ ] No blocking operations in UI thread

#### Testing
- [ ] Unit tests for new functionality
- [ ] Edge cases covered
- [ ] Test names clearly describe behavior
- [ ] Mocks used appropriately

#### Cross-Platform
- [ ] API contract compatibility verified
- [ ] Data model changes coordinated
- [ ] Sync behavior tested if applicable
- [ ] Error codes consistent

### Review Response Times

| Priority | Response Time |
|----------|---------------|
| Critical (security/hotfix) | < 2 hours |
| High (blocking work) | < 4 hours |
| Normal | < 24 hours |
| Low (docs/refactor) | < 48 hours |

### Approval Requirements

| Change Type | Required Approvals |
|-------------|-------------------|
| Security-related | 2 (including security lead) |
| API contract changes | 2 (all platform leads) |
| Database schema changes | 2 |
| Standard changes | 1 |

---

## 7. Cross-Platform Consistency

### Data Type Mapping

| Concept | Web (Django) | Desktop (SQLAlchemy) | Mobile (Room) |
|---------|--------------|----------------------|---------------|
| Primary Key | `UUIDField` | `String(36)` | `@PrimaryKey String` |
| Money | `DecimalField(15,2)` | `Numeric(15,2)` | `Double` |
| DateTime | `DateTimeField` | `DateTime` | `Long` (epoch ms) |
| Date | `DateField` | `Date` | `Long` (epoch ms) |
| Boolean | `BooleanField` | `Boolean` | `Boolean` |
| JSON | `JSONField` | `Text` (JSON string) | `String` (JSON) |
| Enum | `CharField(choices)` | `Enum` | `enum class` |

### Transaction Types (All Platforms)

```python
# Web (Django)
class TransactionType(models.TextChoices):
    INCOME = 'income', 'Income'
    EXPENSE = 'expense', 'Expense'
    TRANSFER = 'transfer', 'Transfer'
```

```python
# Desktop (Python)
class TransactionType(Enum):
    INCOME = 'income'
    EXPENSE = 'expense'
    TRANSFER = 'transfer'
```

```kotlin
// Mobile (Kotlin)
enum class TransactionType {
    INCOME,
    EXPENSE,
    TRANSFER;

    fun toApiValue(): String = name.lowercase()
}
```

### Category Enum (All Platforms)

Standard categories that MUST be consistent:

| Category | API Value | Display Name |
|----------|-----------|--------------|
| Salary | `salary` | Salary |
| Food & Dining | `food` | Food & Dining |
| Transportation | `transportation` | Transportation |
| Utilities | `utilities` | Utilities |
| Entertainment | `entertainment` | Entertainment |
| Shopping | `shopping` | Shopping |
| Healthcare | `healthcare` | Healthcare |
| Education | `education` | Education |
| Travel | `travel` | Travel |
| Subscriptions | `subscriptions` | Subscriptions |
| Investments | `investments` | Investments |
| Gifts | `gifts` | Gifts |
| Personal Care | `personal_care` | Personal Care |
| Home | `home` | Home |
| Insurance | `insurance` | Insurance |
| Taxes | `taxes` | Taxes |
| Other Income | `other_income` | Other Income |
| Other Expense | `other_expense` | Other Expense |

### Sync Status Fields

Every syncable entity MUST include these fields:

```python
# Web (Django) - Source of Truth
id = models.UUIDField(primary_key=True, default=uuid.uuid4)
created_at = models.DateTimeField(auto_now_add=True)
updated_at = models.DateTimeField(auto_now=True)
version = models.PositiveIntegerField(default=1)  # Optimistic locking
```

```python
# Desktop (SQLAlchemy)
id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Local ID
server_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
is_synced: Mapped[bool] = mapped_column(Boolean, default=False)
sync_status: Mapped[str] = mapped_column(String(20), default='pending')
created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
local_version: Mapped[int] = mapped_column(Integer, default=1)
server_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

```kotlin
// Mobile (Room)
@Entity
data class Transaction(
    @PrimaryKey val id: String,              // Local UUID
    val serverId: String? = null,            // Server UUID
    val isSynced: Boolean = false,
    val syncStatus: SyncStatus = SyncStatus.PENDING,
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis(),
    val localVersion: Int = 1,
    val serverVersion: Int? = null
)

enum class SyncStatus { PENDING, SYNCING, SYNCED, CONFLICT, ERROR }
```

---

## 8. Data Model Standards

### Required Fields (All Models)

Every database model MUST include:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary key |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last modification timestamp |

### Soft Delete Pattern

For entities that should not be permanently deleted:

```python
# Web (Django)
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
```

### Field Ordering Convention

Order fields in this sequence:

1. Primary key (`id`)
2. Foreign keys (`user_id`, `category_id`)
3. Required business fields
4. Optional business fields
5. Status/type fields
6. Metadata fields
7. Timestamps (`created_at`, `updated_at`)

**Example**:
```python
class Transaction(models.Model):
    # 1. Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    # 2. Foreign keys
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    bank_account = models.ForeignKey(BankAccount, on_delete=models.SET_NULL, null=True)

    # 3. Required business fields
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_date = models.DateField()

    # 4. Optional business fields
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    # 5. Status/type fields
    type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default='active')
    is_recurring = models.BooleanField(default=False)

    # 6. Metadata fields
    tags = models.JSONField(default=list)
    metadata = models.JSONField(default=dict)

    # 7. Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 9. API Contract Standards

### Response Format

**Success Response (Single Item)**:
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "amount": 1234.56,
    "type": "expense",
    "created_at": "2026-01-28T14:30:00Z"
  }
}
```

**Success Response (Collection)**:
```json
{
  "data": [
    { "id": "...", "amount": 100.00 },
    { "id": "...", "amount": 200.00 }
  ],
  "pagination": {
    "count": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8,
    "next": "/api/v1/transactions?page=2",
    "previous": null
  }
}
```

**Error Response**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid transaction data",
    "details": {
      "amount": ["Amount must be positive"],
      "category_id": ["Category not found"]
    }
  }
}
```

### HTTP Status Codes

| Code | Usage | When to Use |
|------|-------|-------------|
| `200` | OK | Successful GET, PUT, PATCH |
| `201` | Created | Successful POST creating resource |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Malformed request syntax |
| `401` | Unauthorized | Missing/invalid authentication |
| `403` | Forbidden | Valid auth, insufficient permissions |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Sync conflict, duplicate resource |
| `422` | Unprocessable Entity | Valid syntax, semantic errors |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |

### Error Codes

Standardized error codes for client handling:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400/422 | Input validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | No valid token provided |
| `INVALID_TOKEN` | 401 | Token expired or invalid |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource doesn't exist |
| `CONFLICT` | 409 | Resource conflict (sync, duplicate) |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

### Versioning

- API version in URL path: `/api/v1/`, `/api/v2/`
- Breaking changes require new version
- Old versions supported for minimum 6 months
- Deprecation warnings in response headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | `Bearer <token>` (* except public endpoints) |
| `Content-Type` | Yes | `application/json` |
| `Accept` | No | `application/json` (default) |
| `X-Request-ID` | No | Client-generated UUID for tracing |
| `X-Client-Version` | No | Client app version for compatibility |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Echo of request ID or server-generated |
| `X-RateLimit-Limit` | Rate limit ceiling |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `X-RateLimit-Reset` | Unix timestamp of limit reset |

---

## 10. Error Handling Standards

### Error Hierarchy

```python
# Web/Desktop (Python)
class PecuniaError(Exception):
    """Base exception for all application errors."""
    code: str = "UNKNOWN_ERROR"
    message: str = "An unexpected error occurred"

class ValidationError(PecuniaError):
    code = "VALIDATION_ERROR"

class AuthenticationError(PecuniaError):
    code = "AUTHENTICATION_ERROR"

class PermissionError(PecuniaError):
    code = "PERMISSION_DENIED"

class ResourceNotFoundError(PecuniaError):
    code = "RESOURCE_NOT_FOUND"

class ConflictError(PecuniaError):
    code = "CONFLICT"

class RateLimitError(PecuniaError):
    code = "RATE_LIMITED"
```

```kotlin
// Mobile (Kotlin)
sealed class PecuniaError : Exception() {
    abstract val code: String
    abstract override val message: String

    data class Validation(
        override val message: String,
        val details: Map<String, List<String>> = emptyMap()
    ) : PecuniaError() {
        override val code = "VALIDATION_ERROR"
    }

    data class Authentication(
        override val message: String = "Authentication required"
    ) : PecuniaError() {
        override val code = "AUTHENTICATION_ERROR"
    }

    // ... other error types
}
```

### Error Logging

**DO log**:
- Error code and message
- Request ID for tracing
- User ID (not email/name)
- Endpoint and method
- Stack trace for server errors

**DO NOT log**:
- Passwords or tokens
- Credit card numbers
- Personal identification numbers
- Full request/response bodies

### User-Facing Messages

- Never expose technical details to users
- Use friendly, actionable messages
- Provide error codes for support reference

---

## 11. Testing Standards

### Test File Naming

| Platform | Test Files | Test Classes |
|----------|------------|--------------|
| Web | `test_<module>.py` | `Test<Feature>` |
| Desktop | `test_<module>.py` | `Test<Feature>` |
| Mobile | `<Feature>Test.kt` | `<Feature>Test` |

### Test Method Naming

**Format**: `test_<action>_<condition>_<expected_result>`

**Examples**:
```python
# Python
def test_create_transaction_with_valid_data_returns_201():
def test_create_transaction_without_amount_returns_validation_error():
def test_get_transactions_as_unauthenticated_user_returns_401():
```

```kotlin
// Kotlin
fun `create transaction with valid data returns success`()
fun `create transaction without amount returns validation error`()
fun `get transactions as unauthenticated user returns 401`()
```

### Test Structure (AAA Pattern)

```python
def test_create_transaction_with_valid_data():
    # Arrange
    user = UserFactory.create()
    category = CategoryFactory.create(user=user)
    transaction_data = {
        'amount': 100.00,
        'type': 'expense',
        'category_id': str(category.id)
    }

    # Act
    response = client.post('/api/v1/transactions/', transaction_data)

    # Assert
    assert response.status_code == 201
    assert response.data['data']['amount'] == '100.00'
```

### Coverage Requirements

| Type | Minimum Coverage |
|------|-----------------|
| Unit Tests | 80% |
| Integration Tests | 60% |
| Critical Paths | 100% |

---

## 12. Documentation Standards

### Code Comments

**When to Comment**:
- Complex algorithms
- Non-obvious business logic
- Workarounds with ticket references
- Public API methods

**When NOT to Comment**:
- Self-explanatory code
- Obvious operations
- Redundant with code

### Docstring Format

**Python (Google Style)**:
```python
def calculate_budget_remaining(
    budget: Budget,
    transactions: List[Transaction],
    as_of_date: Optional[date] = None
) -> Decimal:
    """
    Calculate remaining budget amount based on transactions.

    Args:
        budget: The budget to calculate for.
        transactions: List of transactions to consider.
        as_of_date: Calculate as of this date. Defaults to today.

    Returns:
        Remaining budget amount. Can be negative if overspent.

    Raises:
        ValueError: If budget period hasn't started yet.

    Example:
        >>> budget = Budget(amount=1000)
        >>> transactions = [Transaction(amount=250)]
        >>> calculate_budget_remaining(budget, transactions)
        Decimal('750.00')
    """
```

**Kotlin (KDoc)**:
```kotlin
/**
 * Calculates the remaining budget amount based on transactions.
 *
 * @param budget The budget to calculate for.
 * @param transactions List of transactions to consider.
 * @param asOfDate Calculate as of this date. Defaults to today.
 * @return Remaining budget amount. Can be negative if overspent.
 * @throws IllegalArgumentException If budget period hasn't started.
 */
fun calculateBudgetRemaining(
    budget: Budget,
    transactions: List<Transaction>,
    asOfDate: LocalDate = LocalDate.now()
): Double
```

### README Requirements

Every module MUST have a README.md containing:

1. **Overview**: Purpose and scope
2. **Quick Start**: Setup instructions
3. **Architecture**: Key components and design
4. **API Reference**: For libraries/modules
5. **Configuration**: Environment variables
6. **Testing**: How to run tests
7. **Contributing**: Module-specific guidelines

### API Documentation

Use OpenAPI 3.0 specification for all API endpoints.

---

## Summary

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Consistency** | Same patterns across all platforms |
| **Security First** | Security in every decision |
| **Offline-First** | Desktop/mobile work without network |
| **Single Source of Truth** | Web API is authoritative |
| **Documentation** | Code is self-documenting + comments |

### Enforcement

- Pre-commit hooks for linting
- CI/CD pipeline checks
- Mandatory code reviews
- Automated testing

---

**This convention is MANDATORY for all development in Pecunia.**

*Last reviewed: 2026-01-28*
