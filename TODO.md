# Pecunia - Project Roadmap & TODO

**Last Updated**: 2026-04-09
**Status Legend**:
- `[x]` Completed
- `[-]` In Progress
- `[ ]` Not Started
- `[!]` Blocked/Needs Discussion

---

## Table of Contents

1. [Overview](#overview)
2. [Current Sprint](#current-sprint)
3. [Backend (pecunia-web)](#backend-pecunia-web)
4. [Desktop App (pecunia-desktop)](#desktop-app-pecunia-desktop)
5. [Mobile App (pecunia-mobile)](#mobile-app-pecunia-mobile)
6. [Infrastructure & DevOps](#infrastructure--devops)
7. [Documentation](#documentation)
8. [Testing](#testing)
9. [Security Enhancements](#security-enhancements)
10. [Future Features](#future-features)
11. [Technical Debt](#technical-debt)
12. [Known Issues](#known-issues)

---

## Overview

### Project Status Summary

| Platform | Core Features | Authentication | Sync | Banking | AI | Status |
|----------|--------------|----------------|------|---------|-----|--------|
| **Web API** | 90% | 95% | 85% | 80% | 70% | Beta |
| **Desktop** | 75% | 90% | 70% | 60% | 50% | Alpha |
| **Mobile** | 70% | 85% | 65% | 50% | 40% | Alpha |

### Priority Levels

| Priority | Description | Target |
|----------|-------------|--------|
| **P0 - Critical** | Blocking issues, security vulnerabilities | Immediate |
| **P1 - High** | Core features, major bugs | This Sprint |
| **P2 - Medium** | Important features, minor bugs | Next Sprint |
| **P3 - Low** | Nice-to-have, enhancements | Backlog |

---

## How to Contribute

All tasks below are tracked as [GitHub Issues](https://github.com/kingoftech-v01/pecunia/issues). Look for `good first issue` and `help wanted` labels to get started. See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## Current Priorities

**Focus**: Bug fixes, open-source readiness, and community contributions

### Priority Tasks

#### P0 - Critical

- [ ] **[WEB]** Fix token refresh race condition
  - **Description**: When multiple API calls happen simultaneously with an expired token, multiple refresh requests are sent, causing token invalidation
  - **Impact**: Users randomly logged out during heavy API usage
  - **Assignee**: Backend Team
  - **Files**: `pecunia-web/apps/accounts/tokens.py`
  - **Solution**: Implement token refresh locking mechanism with Redis distributed lock

- [ ] **[MOBILE]** Fix crash on budget deletion
  - **Description**: App crashes when deleting a budget that has linked transactions
  - **Impact**: Users cannot delete budgets, app crashes
  - **Assignee**: Mobile Team
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/domain/usecases/DeleteBudgetUseCase.kt`
  - **Solution**: Add cascade deletion handling and confirmation dialog

#### P1 - High

- [-] **[ALL]** Complete offline sync implementation
  - **Description**: Implement reliable offline-first sync across all platforms
  - **Progress**: 70% complete
  - **Remaining**:
    - [ ] Desktop: Conflict resolution UI
    - [ ] Mobile: Background sync worker
    - [ ] Web: Batch sync endpoint optimization
  - **Documentation**: See [Sync Architecture](#sync-architecture-details) below

- [ ] **[WEB]** Implement Plaid production integration
  - **Description**: Move from Plaid sandbox to production environment
  - **Requirements**:
    - [ ] Complete Plaid production application
    - [ ] Implement webhook handling for real-time updates
    - [ ] Add institution logo caching
    - [ ] Implement balance refresh scheduling
  - **Files**: `pecunia-web/apps/banking/providers/plaid.py`

- [ ] **[DESKTOP]** Implement auto-update mechanism
  - **Description**: Desktop app should check for updates and prompt user to install
  - **Requirements**:
    - [ ] Version check endpoint on API
    - [ ] Download and verification logic
    - [ ] Installation prompt UI
    - [ ] Rollback capability
  - **Files**: `pecunia-desktop/src/services/updater.py` (new)

#### P2 - Medium

- [ ] **[WEB]** Add bulk transaction import
  - **Description**: Allow users to import multiple transactions at once via CSV/OFX upload
  - **Requirements**:
    - [ ] File upload endpoint (max 10MB)
    - [ ] Async processing with Celery
    - [ ] Progress tracking via WebSocket or polling
    - [ ] Duplicate detection
    - [ ] Category suggestion for imported transactions
  - **Files**: `pecunia-web/apps/transactions/views.py`, `pecunia-web/apps/transactions/importers/`

- [ ] **[MOBILE]** Implement receipt scanner
  - **Description**: Use camera to scan receipts and auto-fill transaction data
  - **Requirements**:
    - [ ] Camera permission handling
    - [ ] Image capture and cropping
    - [ ] OCR integration (ML Kit or cloud service)
    - [ ] Amount and merchant extraction
    - [ ] Confirmation UI before saving
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/scanner/`

---

## Backend (pecunia-web)

### Authentication & Users

#### Completed
- [x] User registration with email verification
- [x] JWT authentication with refresh tokens
- [x] Password reset functionality
- [x] Two-factor authentication (TOTP)
- [x] Backup codes generation
- [x] Session management

#### In Progress
- [-] OAuth social login (Google, Apple)
  - **Description**: Allow users to sign in with Google or Apple accounts
  - **Progress**: Google OAuth partially implemented, Apple pending
  - **Remaining**:
    - [ ] Complete Google OAuth callback handling
    - [ ] Implement Apple Sign-In
    - [ ] Link social accounts to existing users
    - [ ] Handle account merge conflicts
  - **Files**: `pecunia-web/apps/accounts/oauth.py`, `pecunia-web/apps/accounts/social_views.py`

#### Not Started
- [ ] Passwordless authentication (magic links)
  - **Description**: Allow users to login via email link without password
  - **Rationale**: Improves UX and security for users who prefer not to manage passwords
  - **Implementation**:
    1. Generate secure, time-limited token
    2. Send email with login link
    3. Validate token and create session
    4. Expire token after use or timeout (15 min)
  - **Files**: `pecunia-web/apps/accounts/magic_link.py` (new)

- [ ] Device fingerprinting and trusted devices
  - **Description**: Track user devices and allow marking trusted devices to skip 2FA
  - **Rationale**: Balance security with convenience for returning users
  - **Implementation**:
    1. Collect device fingerprint (browser, OS, IP range)
    2. Store in DeviceTrust model
    3. Allow users to manage trusted devices
    4. Skip 2FA for trusted devices (configurable)
  - **Files**: `pecunia-web/apps/accounts/devices.py` (new)

### Transactions

#### Completed
- [x] CRUD operations for transactions
- [x] Transaction categorization (manual)
- [x] Transaction filtering and search
- [x] Pagination and sorting
- [x] Statistics endpoint
- [x] Category management

#### In Progress
- [-] Recurring transactions
  - **Description**: Support for automatic transaction creation based on schedules
  - **Progress**: Model created, scheduling logic pending
  - **Remaining**:
    - [ ] Celery task for transaction generation
    - [ ] Notification before due date
    - [ ] Skip/pause functionality
    - [ ] Variable amount support
  - **Files**: `pecunia-web/apps/transactions/models.py`, `pecunia-web/apps/transactions/tasks.py`

#### Not Started
- [ ] Transaction attachments
  - **Description**: Allow attaching images/PDFs to transactions (receipts, invoices)
  - **Requirements**:
    - [ ] File upload to S3/CloudFront
    - [ ] Image resizing and optimization
    - [ ] PDF preview generation
    - [ ] Attachment model and relationship
    - [ ] Storage quota per user tier
  - **Storage Estimate**: ~50MB per user average
  - **Files**: `pecunia-web/apps/transactions/attachments.py` (new)

- [ ] Transaction splits
  - **Description**: Split a single transaction into multiple categories
  - **Use Case**: User buys groceries ($80) and household items ($20) in one purchase ($100)
  - **Implementation**:
    1. Parent transaction with total amount
    2. Child split transactions with category assignments
    3. Splits must sum to parent amount
    4. Budget tracking considers splits
  - **Files**: `pecunia-web/apps/transactions/splits.py` (new)

- [ ] Transaction rules/automation
  - **Description**: Auto-categorize transactions based on user-defined rules
  - **Examples**:
    - "If merchant contains 'Starbucks', set category to 'Food & Dining'"
    - "If amount > 1000, add tag 'Large Purchase'"
  - **Implementation**:
    1. Rule model (condition type, value, action)
    2. Rule engine to evaluate on transaction creation
    3. UI for rule management
    4. Rule priority ordering
  - **Files**: `pecunia-web/apps/transactions/rules.py` (new)

### Budgets

#### Completed
- [x] CRUD operations for budgets
- [x] Budget items by category
- [x] Progress tracking
- [x] Period types (weekly, monthly, custom)

#### In Progress
- [-] Budget alerts
  - **Description**: Notify users when approaching or exceeding budget limits
  - **Progress**: Alert threshold field added, notification logic pending
  - **Remaining**:
    - [ ] Celery task for daily budget check
    - [ ] Email notification
    - [ ] Push notification (mobile)
    - [ ] In-app notification
  - **Files**: `pecunia-web/apps/budgets/alerts.py` (new), `pecunia-web/apps/budgets/tasks.py`

#### Not Started
- [ ] Budget templates
  - **Description**: Pre-defined budget templates users can start from
  - **Templates**:
    - 50/30/20 Rule (Needs/Wants/Savings)
    - Zero-Based Budget
    - Envelope System
    - Custom User Templates
  - **Implementation**:
    1. Template model with categories and percentages
    2. Clone template to create budget
    3. Allow users to save their budgets as templates
  - **Files**: `pecunia-web/apps/budgets/templates.py` (new)

- [ ] Rollover budgets
  - **Description**: Carry unused budget to next period (or apply overspend)
  - **Use Case**: User budgets $200/month for entertainment, spends $150, $50 rolls to next month
  - **Implementation**:
    1. Rollover configuration per budget
    2. Calculate rollover on period end
    3. Create adjustment transaction
    4. Cap maximum rollover optionally
  - **Files**: `pecunia-web/apps/budgets/rollover.py` (new)

- [ ] Budget sharing (family accounts)
  - **Description**: Share budgets with family members
  - **Requirements**:
    - [ ] Family group model
    - [ ] Invitation system
    - [ ] Permission levels (view, edit, admin)
    - [ ] Shared budget tracking
    - [ ] Individual vs shared expense categorization
  - **Subscription**: Pro tier required
  - **Files**: `pecunia-web/apps/family/` (new app)

### Banking Integration

#### Completed
- [x] Plaid sandbox integration
- [x] TrueLayer integration
- [x] Powens (Budget Insight) integration
- [x] Bank connection management
- [x] Account balance retrieval
- [x] Transaction import from banks

#### In Progress
- [-] Real-time balance updates
  - **Description**: Webhooks for instant balance updates instead of polling
  - **Progress**: Plaid webhook endpoint created, processing logic pending
  - **Remaining**:
    - [ ] Webhook signature verification
    - [ ] Transaction webhook handling
    - [ ] Balance webhook handling
    - [ ] Error/warning webhook handling
  - **Files**: `pecunia-web/apps/banking/webhooks.py`

#### Not Started
- [ ] Multi-currency accounts
  - **Description**: Support bank accounts in different currencies
  - **Requirements**:
    - [ ] Currency field on BankAccount model
    - [ ] Exchange rate service integration
    - [ ] Automatic conversion for reporting
    - [ ] Historical exchange rates for past transactions
  - **Exchange Rate Source**: European Central Bank or Open Exchange Rates
  - **Files**: `pecunia-web/apps/banking/currency.py` (new)

- [ ] Investment account support
  - **Description**: Track investment portfolios, stocks, crypto
  - **Requirements**:
    - [ ] Investment position model
    - [ ] Market data integration (Yahoo Finance, Alpha Vantage)
    - [ ] Gain/loss calculations
    - [ ] Portfolio performance charts
  - **Complexity**: High - separate feature set
  - **Files**: `pecunia-web/apps/investments/` (new app)

### AI Features

#### Completed
- [x] Claude API client integration
- [x] Transaction categorization service
- [x] Anomaly detection algorithm

#### In Progress
- [-] AI-powered insights
  - **Description**: Generate personalized financial insights and recommendations
  - **Progress**: Insight generation logic 60% complete
  - **Remaining**:
    - [ ] Spending pattern analysis
    - [ ] Savings opportunity detection
    - [ ] Budget adjustment suggestions
    - [ ] Caching for performance
  - **Files**: `pecunia-web/apps/ai/services/recommendations.py`

#### Not Started
- [ ] Natural language transaction search
  - **Description**: "Show me coffee purchases last month" -> filtered results
  - **Implementation**:
    1. Parse natural language query with Claude
    2. Extract filters (category, date range, amount)
    3. Execute database query
    4. Return formatted results
  - **Subscription**: Pro tier required
  - **Files**: `pecunia-web/apps/ai/services/nl_search.py` (new)

- [ ] Fraud detection alerts
  - **Description**: Detect potentially fraudulent transactions using AI
  - **Signals**:
    - Unusual location
    - Abnormal amount
    - Unusual time of day
    - Merchant category mismatch
  - **Implementation**:
    1. Train model on user's normal patterns
    2. Score each transaction
    3. Alert on high-risk scores
    4. Allow user feedback to improve model
  - **Subscription**: Premium tier required
  - **Files**: `pecunia-web/apps/ai/services/fraud_detection.py` (new)

### Subscriptions & Billing

#### Completed
- [x] Stripe integration
- [x] Subscription plans model
- [x] Checkout flow
- [x] Webhook handling

#### Not Started
- [ ] Usage-based billing for API access
  - **Description**: Charge API users based on request volume
  - **Implementation**:
    1. Track API usage per user
    2. Calculate billing based on tier thresholds
    3. Monthly invoice generation
    4. Usage dashboard
  - **Files**: `pecunia-web/apps/subscriptions/metering.py` (new)

- [ ] Gift subscriptions
  - **Description**: Allow users to purchase subscriptions as gifts
  - **Implementation**:
    1. Gift code generation
    2. Redemption flow
    3. Gift notification email
    4. Expiration handling
  - **Files**: `pecunia-web/apps/subscriptions/gifts.py` (new)

---

## Desktop App (pecunia-desktop)

### Core Functionality

#### Completed
- [x] Application framework (PyQt6)
- [x] Local SQLite database with SQLAlchemy
- [x] Configuration management
- [x] Secure credential storage (keyring)
- [x] Basic UI layout and navigation

#### In Progress
- [-] Complete transaction management UI
  - **Description**: Full CRUD interface for transactions
  - **Progress**: List and create done, edit/delete pending
  - **Remaining**:
    - [ ] Edit transaction dialog
    - [ ] Delete confirmation
    - [ ] Bulk operations (select multiple, delete/categorize)
    - [ ] Filter panel improvements
  - **Files**: `pecunia-desktop/src/ui/pages/transactions.py`

- [-] Sync manager implementation
  - **Description**: Reliable offline-first sync with conflict resolution
  - **Progress**: Basic sync working, conflict resolution UI pending
  - **Remaining**:
    - [ ] Conflict detection improvements
    - [ ] Conflict resolution dialog
    - [ ] Sync progress indicator
    - [ ] Retry logic for failed syncs
  - **Files**: `pecunia-desktop/src/sync/manager.py`, `pecunia-desktop/src/sync/conflict_resolver.py`

#### Not Started
- [ ] Dashboard with charts
  - **Description**: Overview page with spending charts and recent transactions
  - **Requirements**:
    - [ ] Spending by category pie chart
    - [ ] Income vs expenses line chart
    - [ ] Budget progress bars
    - [ ] Recent transactions list
    - [ ] Quick add transaction button
  - **Charting Library**: PyQtChart or matplotlib
  - **Files**: `pecunia-desktop/src/ui/pages/dashboard.py`, `pecunia-desktop/src/ui/widgets/charts.py`

- [ ] Data export functionality
  - **Description**: Export transactions to CSV, PDF, OFX, QIF
  - **Requirements**:
    - [ ] Format selection dialog
    - [ ] Date range selection
    - [ ] Category filtering
    - [ ] PDF report generation with charts
  - **Files**: `pecunia-desktop/src/services/export.py`

- [ ] Keyboard shortcuts
  - **Description**: Power-user keyboard shortcuts for common actions
  - **Shortcuts**:
    - `Ctrl+N` - New transaction
    - `Ctrl+S` - Sync now
    - `Ctrl+F` - Search/filter
    - `Ctrl+,` - Settings
    - `Ctrl+Q` - Quit
  - **Files**: `pecunia-desktop/src/ui/shortcuts.py` (new)

- [ ] System tray integration
  - **Description**: Minimize to system tray, show notifications
  - **Requirements**:
    - [ ] Tray icon with menu
    - [ ] Desktop notifications for alerts
    - [ ] Background sync when minimized
    - [ ] Quick actions from tray menu
  - **Files**: `pecunia-desktop/src/ui/tray.py` (new)

### Platform-Specific

- [ ] macOS menu bar integration
  - **Description**: Native macOS menu bar and touch bar support
  - **Files**: `pecunia-desktop/src/ui/macos.py` (new)

- [ ] Windows taskbar progress
  - **Description**: Show sync progress in Windows taskbar
  - **Files**: `pecunia-desktop/src/ui/windows.py` (new)

- [ ] Linux desktop integration
  - **Description**: XDG compliance, .desktop file, notifications
  - **Files**: `pecunia-desktop/installer/linux/`

---

## Mobile App (pecunia-mobile)

### Core Functionality

#### Completed
- [x] Application architecture (MVVM + Clean Architecture)
- [x] Hilt dependency injection
- [x] Room database setup
- [x] Navigation with Jetpack Compose
- [x] Basic theme and styling

#### In Progress
- [-] Transaction list and details
  - **Description**: View, add, edit transactions with Compose UI
  - **Progress**: List screen done, form screen 80% complete
  - **Remaining**:
    - [ ] Transaction detail screen
    - [ ] Category picker improvements
    - [ ] Date picker improvements
    - [ ] Swipe actions (delete, edit)
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/transactions/`

- [-] Budget tracking
  - **Description**: View budgets and track progress
  - **Progress**: List screen done, progress visualization pending
  - **Remaining**:
    - [ ] Budget detail screen
    - [ ] Progress ring visualization
    - [ ] Spending breakdown by category
    - [ ] Budget creation/edit form
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/budgets/`

#### Not Started
- [ ] Receipt scanner with OCR
  - **Description**: Scan receipts to auto-fill transaction data
  - **Implementation**:
    1. Camera integration with CameraX
    2. Image cropping and preprocessing
    3. OCR with ML Kit Text Recognition
    4. Amount and merchant extraction
    5. Confirmation and edit before save
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/scanner/`

- [ ] Biometric authentication
  - **Description**: Fingerprint/face unlock for app access
  - **Implementation**:
    1. BiometricPrompt integration
    2. Fallback to PIN/password
    3. Secure storage of auth state
    4. Timeout configuration
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/auth/BiometricAuthScreen.kt` (new)

- [ ] Push notifications
  - **Description**: Receive budget alerts and transaction notifications
  - **Implementation**:
    1. Firebase Cloud Messaging setup
    2. Notification channels for Android 8+
    3. Token registration with backend
    4. Deep linking from notifications
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/services/PushNotificationService.kt` (new)

- [ ] Widget for home screen
  - **Description**: Show balance summary on home screen
  - **Requirements**:
    - [ ] Balance summary widget
    - [ ] Quick add transaction widget
    - [ ] Recent transactions widget
    - [ ] Glance API implementation
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/widget/` (new)

- [ ] Dark mode support
  - **Description**: Complete dark theme implementation
  - **Progress**: Theme infrastructure done, some screens need adjustment
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/theme/Theme.kt`

---

## Infrastructure & DevOps

### CI/CD

#### Completed
- [x] GitHub Actions for backend tests
- [x] Docker build automation

#### Not Started
- [ ] Complete CI/CD pipeline
  - **Web API**:
    - [ ] Automated testing on PR
    - [ ] Code coverage reporting (Codecov)
    - [ ] Security scanning (Snyk, Bandit)
    - [ ] Docker image build and push
    - [ ] Staging deployment on merge to develop
    - [ ] Production deployment on release tag
  - **Desktop**:
    - [ ] Cross-platform builds (Windows, macOS, Linux)
    - [ ] Code signing
    - [ ] Installer creation
    - [ ] Release asset upload
  - **Mobile**:
    - [ ] Android build and test
    - [ ] APK/AAB artifact generation
    - [ ] Play Store deployment (internal track)

- [ ] Infrastructure as Code
  - **Description**: Terraform/Pulumi for cloud infrastructure
  - **Resources**:
    - [ ] AWS VPC and networking
    - [ ] RDS PostgreSQL
    - [ ] ElastiCache Redis
    - [ ] ECS/EKS for containers
    - [ ] CloudFront CDN
    - [ ] S3 for file storage
    - [ ] Route 53 DNS
  - **Files**: `infrastructure/terraform/` (new)

### Monitoring & Observability

- [ ] Application monitoring
  - **Requirements**:
    - [ ] Sentry for error tracking
    - [ ] Prometheus + Grafana for metrics
    - [ ] Structured logging with ELK stack
    - [ ] Uptime monitoring
    - [ ] APM (Application Performance Monitoring)
  - **Files**: Various configuration files

- [ ] Alerting
  - **Requirements**:
    - [ ] PagerDuty/Opsgenie integration
    - [ ] Alert rules for critical metrics
    - [ ] On-call rotation setup
    - [ ] Incident response runbooks

---

## Documentation

### User Documentation

- [ ] User guide
  - **Sections**:
    - [ ] Getting started
    - [ ] Adding transactions
    - [ ] Creating budgets
    - [ ] Connecting bank accounts
    - [ ] Using reports
    - [ ] Mobile app guide
    - [ ] Desktop app guide
  - **Format**: Hosted documentation (GitBook, Docusaurus)

- [ ] Video tutorials
  - **Topics**:
    - [ ] Platform overview (3 min)
    - [ ] Transaction management (5 min)
    - [ ] Budget setup (5 min)
    - [ ] Bank connection (3 min)
    - [ ] Reports and insights (5 min)

### Developer Documentation

- [x] Code conventions (MASTER_CONVENTIONS.md)
- [x] Security guidelines (SECURITY_GUIDELINES.md)
- [x] Scalability guidelines (SCALABILITY_GUIDELINES.md)
- [ ] API documentation (OpenAPI/Swagger)
  - **Requirements**:
    - [ ] Complete endpoint documentation
    - [ ] Request/response examples
    - [ ] Authentication guide
    - [ ] Error code reference
    - [ ] Rate limiting documentation
  - **Tool**: drf-spectacular or drf-yasg
  - **Files**: `pecunia-web/config/openapi.py` (new)

- [ ] Architecture Decision Records (ADRs)
  - **Decisions to Document**:
    - [ ] Why offline-first architecture
    - [ ] Why UUID primary keys
    - [ ] Why Django REST Framework
    - [ ] Why Room vs SQLDelight (mobile)
    - [ ] Why PyQt6 vs Electron (desktop)
  - **Format**: Markdown files in `docs/adr/`

---

## Testing

### Backend

- [ ] Increase test coverage to 85%
  - **Current Coverage**: ~65%
  - **Priority Areas**:
    - [ ] Banking provider tests
    - [ ] Sync endpoint tests
    - [ ] AI service tests
    - [ ] Subscription workflow tests
  - **Command**: `pytest --cov=apps --cov-report=html`

- [ ] Load testing
  - **Tool**: Locust or k6
  - **Scenarios**:
    - [ ] 1000 concurrent users
    - [ ] Bulk transaction import
    - [ ] Sync storm (many devices syncing)
  - **Files**: `pecunia-web/tests/load/` (new)

### Desktop

- [ ] UI automation tests
  - **Tool**: pytest-qt
  - **Coverage**:
    - [ ] Login flow
    - [ ] Transaction CRUD
    - [ ] Budget management
    - [ ] Sync behavior
  - **Files**: `pecunia-desktop/tests/ui/` (new)

### Mobile

- [ ] UI tests with Compose
  - **Tool**: Compose testing library
  - **Coverage**:
    - [ ] Navigation tests
    - [ ] Transaction form tests
    - [ ] Budget screen tests
  - **Files**: `pecunia-mobile/app/src/androidTest/`

- [ ] End-to-end tests
  - **Tool**: Maestro or Appium
  - **Scenarios**:
    - [ ] Complete onboarding flow
    - [ ] Add transaction and verify sync
    - [ ] Budget creation and tracking

---

## Security Enhancements

### High Priority

- [ ] Implement rate limiting per endpoint
  - **Description**: Different limits for sensitive endpoints
  - **Current**: Global rate limiting only
  - **Needed**:
    - [ ] Login: 5 req/min
    - [ ] Password reset: 3 req/min
    - [ ] Bank connection: 10 req/hour
  - **Files**: `pecunia-web/apps/core/middleware.py`

- [ ] Add CAPTCHA for login after failures
  - **Description**: Require CAPTCHA after 3 failed login attempts
  - **Implementation**: hCaptcha or reCAPTCHA v3
  - **Files**: `pecunia-web/apps/accounts/views.py`

- [ ] Security audit logging
  - **Description**: Log all security-relevant events
  - **Events**:
    - [ ] Login attempts (success/failure)
    - [ ] Password changes
    - [ ] 2FA enable/disable
    - [ ] Bank connection changes
    - [ ] Suspicious activity
  - **Storage**: Separate security log table
  - **Files**: `pecunia-web/apps/core/security_logger.py` (new)

### Medium Priority

- [ ] Implement Content Security Policy
  - **Description**: Strict CSP headers to prevent XSS
  - **Files**: `pecunia-web/apps/core/middleware.py`

- [ ] Add database field encryption
  - **Description**: Encrypt sensitive fields at rest
  - **Fields**:
    - [ ] Bank account numbers
    - [ ] Notes containing potential PII
  - **Library**: django-encrypted-model-fields
  - **Files**: `pecunia-web/apps/banking/models.py`

---

## Future Features

### Version 2.0 (Q3 2026)

- [ ] Multi-user family accounts
  - **Description**: Shared accounts for families with individual spending tracking
  - **Subscription**: Pro tier

- [ ] Investment portfolio tracking
  - **Description**: Track stocks, ETFs, crypto alongside regular finances
  - **Subscription**: Premium tier

- [ ] Bill reminders and calendar
  - **Description**: Calendar view of upcoming bills and due dates
  - **All tiers**

- [ ] Goals and savings targets
  - **Description**: Set financial goals (vacation fund, emergency fund) and track progress
  - **All tiers**

### Version 3.0 (Q1 2027)

- [ ] Business/freelancer features
  - **Description**: Invoicing, expense tracking for business, tax categories
  - **Subscription**: Business tier

- [ ] Open Banking API (PSD2)
  - **Description**: Direct bank integration in Europe without aggregators

- [ ] Machine learning spending predictions
  - **Description**: Predict future spending based on historical patterns

---

## Technical Debt

### High Priority

- [ ] Refactor banking provider code
  - **Issue**: Code duplication across Plaid, TrueLayer, Powens providers
  - **Solution**: Extract common functionality to base class
  - **Files**: `pecunia-web/apps/banking/providers/`

- [ ] Optimize N+1 queries in transaction list
  - **Issue**: Category lookup for each transaction
  - **Solution**: Add select_related/prefetch_related
  - **Files**: `pecunia-web/apps/transactions/views.py`

### Medium Priority

- [ ] Migrate to async views in Django
  - **Issue**: Blocking I/O in API calls
  - **Solution**: Use async views for I/O-bound endpoints
  - **Files**: Various view files

- [ ] Consolidate duplicate code in mobile
  - **Issue**: Similar code in multiple ViewModels
  - **Solution**: Create base ViewModel class
  - **Files**: `pecunia-mobile/app/src/main/java/com/pecunia/ui/screens/*/`

### Low Priority

- [ ] Update deprecated dependencies
  - **Check**: `pip list --outdated`, `./gradlew dependencyUpdates`
  - **Schedule**: Monthly dependency review

---

## Known Issues

### Critical

| ID | Platform | Description | Workaround |
|----|----------|-------------|------------|
| BUG-001 | Web | Token refresh race condition | Refresh manually before heavy operations |
| BUG-002 | Mobile | Budget deletion crash | Don't delete budgets with transactions |

### High

| ID | Platform | Description | Workaround |
|----|----------|-------------|------------|
| BUG-003 | Desktop | Sync conflicts not showing UI | Check sync log in settings |
| BUG-004 | Web | Plaid webhook signature fails intermittently | Manual sync as backup |

### Medium

| ID | Platform | Description | Workaround |
|----|----------|-------------|------------|
| BUG-005 | Mobile | Dark mode colors incorrect on some screens | Use light mode |
| BUG-006 | Desktop | Chart tooltips cut off at edges | Resize window |

---

## Sync Architecture Details

### Overview

The synchronization system ensures data consistency across all user devices while supporting offline operation.

### Sync Flow

```
1. User makes change locally
   |
   v
2. Change saved to local DB with sync_status='pending'
   |
   v
3. Change added to sync queue
   |
   v
4. Sync manager detects connectivity
   |
   v
5. Batch pending changes
   |
   v
6. POST /api/v1/sync/batch/
   |
   v
7. Server processes each change
   |
   +---> Success: Update local sync_status='synced'
   |
   +---> Conflict: Return conflict data
   |            |
   |            v
   |       Show conflict resolution UI
   |            |
   |            v
   |       User resolves (keep local/remote/merge)
   |
   +---> Error: Retry with exponential backoff
```

### Conflict Resolution Strategies

1. **Last Write Wins**: Default - most recent timestamp wins
2. **Server Wins**: Always prefer server version
3. **Client Wins**: Always prefer local version
4. **Manual Merge**: User reviews both versions and chooses

### Implementation Tasks

- [x] Sync queue model (local storage)
- [x] Batch sync endpoint (server)
- [x] Conflict detection logic
- [ ] Conflict resolution UI (desktop)
- [ ] Conflict resolution UI (mobile)
- [ ] Sync progress indicator
- [ ] Background sync service (mobile)
- [ ] Retry with exponential backoff

---

**This document is updated weekly. Last review: 2026-01-29**
