# Pecunia - Personal Finance Management Platform

[![GitHub issues](https://img.shields.io/github/issues/kingoftech-v01/pecunia)](https://github.com/kingoftech-v01/pecunia/issues)
[![GitHub stars](https://img.shields.io/github/stars/kingoftech-v01/pecunia)](https://github.com/kingoftech-v01/pecunia/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/kingoftech-v01/pecunia)](https://github.com/kingoftech-v01/pecunia/network)
[![Contributors](https://img.shields.io/github/contributors/kingoftech-v01/pecunia)](https://github.com/kingoftech-v01/pecunia/graphs/contributors)

**Version**: 1.0.0
**Last Updated**: 2026-04-09
**Platforms**: Web API, Desktop (Windows/macOS/Linux), Mobile (Android)

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Technology Stack](#technology-stack)
6. [Getting Started](#getting-started)
7. [Platform-Specific Setup](#platform-specific-setup)
8. [API Documentation](#api-documentation)
9. [Security](#security)
10. [Testing](#testing)
11. [Deployment](#deployment)
12. [Contributing](#contributing)
13. [License](#license)

---

## Overview

### What is Pecunia?

Pecunia is a comprehensive personal finance management platform designed to help users track their income, expenses, budgets, and financial goals across multiple devices. The platform follows an **offline-first architecture**, allowing users to manage their finances even without an internet connection, with automatic synchronization when connectivity is restored.

### Why Pecunia?

Managing personal finances is challenging. Users need:
- **Visibility**: Clear insights into where their money goes
- **Control**: Tools to set and track budgets effectively
- **Security**: Bank-level protection for sensitive financial data
- **Accessibility**: Access from any device, anywhere, even offline
- **Intelligence**: AI-powered categorization and anomaly detection

Pecunia addresses all these needs with a modern, secure, and user-friendly platform.

### Target Users

- **Individuals** tracking personal income and expenses
- **Families** managing shared household budgets
- **Freelancers** separating business and personal finances
- **Small businesses** needing basic financial oversight

---

## Features

### Core Features

| Feature | Description | Platforms |
|---------|-------------|-----------|
| **Transaction Management** | Add, edit, delete, and categorize financial transactions | All |
| **Budget Tracking** | Create monthly/weekly/custom budgets with progress tracking | All |
| **Bank Integration** | Connect bank accounts via Plaid, TrueLayer, or Powens | Web, Mobile |
| **Multi-Currency** | Support for 150+ currencies with automatic conversion | All |
| **Receipt Scanning** | OCR-powered receipt capture and automatic data extraction | Mobile |
| **Reports & Analytics** | Visual charts and detailed spending analysis | All |
| **Data Export** | Export to CSV, PDF, OFX, and QIF formats | All |
| **Recurring Transactions** | Automatic tracking of subscriptions and recurring bills | All |

### AI-Powered Features

| Feature | Description | Subscription |
|---------|-------------|--------------|
| **Smart Categorization** | AI automatically categorizes transactions using Claude API | Premium+ |
| **Anomaly Detection** | Identifies unusual spending patterns and potential fraud | Premium+ |
| **Financial Insights** | Personalized recommendations based on spending habits | Pro+ |
| **Natural Language Queries** | Ask questions about your finances in plain language | Pro+ |

### Security Features

| Feature | Description |
|---------|-------------|
| **Two-Factor Authentication (2FA)** | TOTP-based 2FA with backup codes |
| **End-to-End Encryption** | Banking tokens encrypted with Fernet (AES-256) |
| **Biometric Authentication** | Fingerprint/Face unlock on mobile |
| **Session Management** | Automatic timeout and device management |
| **Audit Logging** | Complete audit trail of all actions |

### Offline Capabilities

| Feature | Desktop | Mobile |
|---------|---------|--------|
| View all data | Yes | Yes |
| Add transactions | Yes | Yes |
| Edit transactions | Yes | Yes |
| View budgets | Yes | Yes |
| Generate reports | Yes | Limited |
| Sync when online | Automatic | Automatic |

---

## Architecture

### System Overview

```
                         +-----------------------+
                         |                       |
                         |    Pecunia Cloud      |
                         |    (Django REST)      |
                         |                       |
                         |  - User Management    |
                         |  - Transaction API    |
                         |  - Budget API         |
                         |  - Banking Integration|
                         |  - AI Services        |
                         |  - Sync Management    |
                         |                       |
                         +----------+------------+
                                    |
                                    | HTTPS/REST API
                                    |
         +--------------------------+---------------------------+
         |                          |                           |
         v                          v                           v
+--------+--------+        +--------+--------+         +--------+--------+
|                 |        |                 |         |                 |
|  Desktop App    |        |   Mobile App    |         |   Web Frontend  |
|  (PyQt6/Python) |        |   (Kotlin)      |         |   (Django)      |
|                 |        |                 |         |                 |
|  - SQLite DB    |        |  - Room DB      |         |  - Session Auth |
|  - Offline Mode |        |  - Offline Mode |         |  - Server-Side  |
|  - Local Sync   |        |  - Local Sync   |         |    Rendering    |
|                 |        |  - Biometrics   |         |                 |
+-----------------+        +-----------------+         +-----------------+
```

### Key Architectural Principles

#### 1. Single Source of Truth
The Web API (Django REST) is the authoritative source for all data. Desktop and mobile clients maintain local copies that sync with the server.

#### 2. Offline-First Design
Desktop and mobile applications store data locally and function fully without network connectivity. Changes are queued and synchronized when connectivity is restored.

#### 3. Conflict Resolution
When offline changes conflict with server data, the system uses:
- **Timestamp comparison**: Most recent change wins
- **Version tracking**: Optimistic locking prevents overwrites
- **Manual resolution**: Users can review and resolve complex conflicts

#### 4. UUID-Based Identities
All entities use UUIDs as primary keys, enabling:
- Offline entity creation without server round-trips
- Guaranteed uniqueness across all clients
- Seamless merging during synchronization

### Data Flow

```
User Action (Create Transaction)
         |
         v
+--------+--------+
|  Local Database |  <-- Immediate storage
|  (SQLite/Room)  |
+--------+--------+
         |
         v
+--------+--------+
|   Sync Queue    |  <-- Queued for sync
|   (pending)     |
+--------+--------+
         |
         | (When online)
         v
+--------+--------+
|   API Client    |  <-- POST /api/v1/transactions/
+--------+--------+
         |
         v
+--------+--------+
|  Server (Django)|  <-- Validates & stores
+--------+--------+
         |
         v
+--------+--------+
|   Response      |  <-- Returns server_id, timestamps
+--------+--------+
         |
         v
+--------+--------+
| Update Local DB |  <-- Mark as synced
| (synced status) |
+--------+--------+
```

---

## Project Structure

```
Account Activity Management/
│
├── pecunia-web/                    # Django REST API (Backend)
│   ├── apps/                       # Django applications
│   │   ├── accounts/               # User authentication & profiles
│   │   │   ├── models.py           # User, Profile models
│   │   │   ├── views.py            # Auth endpoints
│   │   │   ├── serializers.py      # DRF serializers
│   │   │   ├── tokens.py           # JWT token handling
│   │   │   ├── totp.py             # 2FA implementation
│   │   │   └── backup_codes.py     # 2FA backup codes
│   │   │
│   │   ├── transactions/           # Transaction management
│   │   │   ├── models.py           # Transaction, Category models
│   │   │   ├── views.py            # CRUD + statistics endpoints
│   │   │   ├── serializers.py      # Transaction serializers
│   │   │   └── importers/          # CSV, OFX, QIF importers
│   │   │
│   │   ├── budgets/                # Budget management
│   │   │   ├── models.py           # Budget, BudgetItem models
│   │   │   ├── views.py            # Budget CRUD + progress
│   │   │   └── serializers.py      # Budget serializers
│   │   │
│   │   ├── banking/                # Bank account integration
│   │   │   ├── models.py           # BankConnection, BankAccount
│   │   │   ├── views.py            # Connection management
│   │   │   └── providers/          # Plaid, TrueLayer, Powens
│   │   │
│   │   ├── ai/                     # AI-powered features
│   │   │   └── services/           # Categorization, anomaly detection
│   │   │
│   │   ├── subscriptions/          # Subscription & billing
│   │   │   ├── models.py           # Subscription, Plan models
│   │   │   └── stripe_service.py   # Stripe integration
│   │   │
│   │   ├── sync/                   # Multi-device synchronization
│   │   │   ├── models.py           # SyncLog, ConflictLog
│   │   │   └── manager.py          # Sync orchestration
│   │   │
│   │   └── core/                   # Shared utilities
│   │       ├── middleware.py       # Rate limiting, audit logging
│   │       └── permissions.py      # Custom permissions
│   │
│   ├── config/                     # Django configuration
│   │   ├── settings/               # Settings (base, dev, prod)
│   │   ├── urls.py                 # URL routing
│   │   └── wsgi.py                 # WSGI entry point
│   │
│   ├── requirements/               # Python dependencies
│   │   ├── base.txt                # Core dependencies
│   │   ├── dev.txt                 # Development tools
│   │   └── prod.txt                # Production optimizations
│   │
│   └── docker/                     # Container configuration
│       ├── Dockerfile
│       └── docker-compose.yml
│
├── pecunia-desktop/                # Python/PyQt6 Desktop App
│   ├── src/
│   │   ├── api/                    # API client modules
│   │   │   ├── client.py           # Base HTTP client
│   │   │   ├── auth.py             # Authentication endpoints
│   │   │   ├── transactions.py     # Transaction API
│   │   │   ├── budgets.py          # Budget API
│   │   │   └── banking.py          # Banking API
│   │   │
│   │   ├── database/               # Local SQLite database
│   │   │   ├── connection.py       # SQLAlchemy engine/sessions
│   │   │   └── models/             # ORM models
│   │   │
│   │   ├── sync/                   # Offline synchronization
│   │   │   ├── manager.py          # Sync orchestration
│   │   │   ├── queue.py            # Pending changes queue
│   │   │   └── conflict_resolver.py
│   │   │
│   │   ├── ui/                     # PyQt6 user interface
│   │   │   ├── pages/              # Main application pages
│   │   │   ├── widgets/            # Reusable UI components
│   │   │   ├── dialogs/            # Modal dialogs
│   │   │   └── styles/             # QSS stylesheets
│   │   │
│   │   ├── services/               # Business logic services
│   │   │   ├── export.py           # Data export functionality
│   │   │   └── notifications.py    # Desktop notifications
│   │   │
│   │   ├── config.py               # Application configuration
│   │   ├── constants.py            # Application constants
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── main.py                 # Application entry point
│   │
│   ├── resources/                  # Assets (icons, images)
│   ├── installer/                  # Platform installers
│   └── requirements.txt            # Python dependencies
│
├── pecunia-mobile/                 # Kotlin/Android Mobile App
│   ├── app/
│   │   └── src/main/java/com/pecunia/
│   │       ├── di/                 # Hilt dependency injection
│   │       │   ├── AppModule.kt
│   │       │   ├── DatabaseModule.kt
│   │       │   └── NetworkModule.kt
│   │       │
│   │       ├── data/               # Data layer
│   │       │   ├── local/          # Room database
│   │       │   │   ├── database/   # AppDatabase, DAOs
│   │       │   │   ├── entities/   # Room entities
│   │       │   │   └── preferences/# DataStore preferences
│   │       │   │
│   │       │   ├── remote/         # Network layer
│   │       │   │   ├── api/        # Retrofit API interfaces
│   │       │   │   └── dto/        # Data transfer objects
│   │       │   │
│   │       │   └── repository/     # Repository implementations
│   │       │
│   │       ├── domain/             # Domain layer
│   │       │   ├── models/         # Domain models
│   │       │   ├── repository/     # Repository interfaces
│   │       │   └── usecases/       # Use case implementations
│   │       │
│   │       ├── ui/                 # Presentation layer
│   │       │   ├── components/     # Jetpack Compose components
│   │       │   ├── screens/        # Screen composables
│   │       │   ├── navigation/     # Navigation components
│   │       │   └── theme/          # Material 3 theming
│   │       │
│   │       ├── PecuniaApp.kt       # Application class
│   │       └── MainActivity.kt     # Main activity
│   │
│   ├── build.gradle.kts            # Gradle build configuration
│   └── gradle.properties           # Gradle properties
│
├── MASTER_CONVENTIONS.md           # Coding standards & conventions
├── SECURITY_GUIDELINES.md          # Security implementation guide
├── SCALABILITY_GUIDELINES.md       # Performance optimization guide
├── README.md                       # This file
└── TODO.md                         # Project roadmap & tasks
```

---

## Technology Stack

### Backend (pecunia-web)

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Framework** | Django | 5.0+ | Web framework |
| **API** | Django REST Framework | 3.14+ | REST API development |
| **Database** | PostgreSQL | 15+ | Primary database |
| **Cache** | Redis | 7+ | Caching & sessions |
| **Task Queue** | Celery | 5.3+ | Background tasks |
| **Authentication** | djangorestframework-simplejwt | 5.3+ | JWT authentication |
| **Banking** | Plaid, TrueLayer, Powens | - | Bank integrations |
| **AI** | Anthropic Claude API | - | AI categorization |
| **Payments** | Stripe | - | Subscription billing |
| **Email** | SendGrid / SES | - | Transactional emails |

### Desktop (pecunia-desktop)

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Python | 3.11+ | Primary language |
| **UI Framework** | PyQt6 | 6.6+ | Desktop UI |
| **Database** | SQLite + SQLAlchemy | 2.0+ | Local storage |
| **HTTP Client** | httpx | 0.26+ | Async API client |
| **Keyring** | keyring | 24+ | Secure credential storage |
| **Config** | pydantic-settings | 2.1+ | Configuration management |

### Mobile (pecunia-mobile)

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Language** | Kotlin | 1.9+ | Primary language |
| **UI Framework** | Jetpack Compose | 1.5+ | Modern UI toolkit |
| **Architecture** | MVVM + Clean Architecture | - | App architecture |
| **DI** | Hilt | 2.48+ | Dependency injection |
| **Database** | Room | 2.6+ | Local database |
| **Network** | Retrofit + OkHttp | 2.9+ | HTTP client |
| **Async** | Kotlin Coroutines + Flow | 1.7+ | Asynchronous programming |
| **Navigation** | Navigation Compose | 2.7+ | Screen navigation |

---

## Getting Started

### Prerequisites

Before starting, ensure you have:

1. **Git** - Version control
2. **Python 3.11+** - For web and desktop
3. **PostgreSQL 15+** - Database (web)
4. **Redis 7+** - Caching (web)
5. **Android Studio** - For mobile development
6. **JDK 17+** - For Android development

### Quick Start

#### 1. Clone the Repository

```bash
git clone https://github.com/your-org/pecunia.git
cd pecunia
```

#### 2. Set Up the Web API

```bash
cd pecunia-web

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

#### 3. Set Up the Desktop App

```bash
cd pecunia-desktop

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

#### 4. Set Up the Mobile App

```bash
cd pecunia-mobile

# Open in Android Studio
# File -> Open -> Select pecunia-mobile directory

# Sync Gradle and run on emulator/device
```

---

## Platform-Specific Setup

### Web API Configuration

#### Environment Variables

Create a `.env` file with:

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://user:password@localhost:5432/pecunia

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_LIFETIME=15  # minutes
JWT_REFRESH_TOKEN_LIFETIME=7  # days

# Banking Providers
PLAID_CLIENT_ID=your-plaid-client-id
PLAID_SECRET=your-plaid-secret
PLAID_ENV=sandbox  # or development, production

TRUELAYER_CLIENT_ID=your-truelayer-client-id
TRUELAYER_CLIENT_SECRET=your-truelayer-secret

# AI
ANTHROPIC_API_KEY=your-claude-api-key

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret
STRIPE_WEBHOOK_SECRET=your-webhook-secret

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your-sendgrid-api-key
```

### Desktop Configuration

The desktop app uses `config.json` for persistent settings:

```json
{
  "api": {
    "base_url": "https://api.pecunia.com",
    "timeout": 30
  },
  "sync": {
    "enabled": true,
    "interval_minutes": 15
  },
  "ui": {
    "theme": "system",
    "language": "en"
  }
}
```

### Mobile Configuration

Update `app/build.gradle.kts`:

```kotlin
android {
    defaultConfig {
        buildConfigField("String", "API_BASE_URL", "\"https://api.pecunia.com\"")
    }
}
```

---

## API Documentation

### Base URL

- **Development**: `http://localhost:8000/api/v1/`
- **Production**: `https://api.pecunia.com/api/v1/`

### Authentication

All API requests (except login/register) require a JWT token:

```http
Authorization: Bearer <access_token>
```

### Core Endpoints

#### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register/` | Create new account |
| POST | `/auth/login/` | Obtain JWT tokens |
| POST | `/auth/refresh/` | Refresh access token |
| POST | `/auth/logout/` | Invalidate tokens |
| POST | `/auth/password-reset/` | Request password reset |
| POST | `/auth/2fa/enable/` | Enable 2FA |
| POST | `/auth/2fa/verify/` | Verify 2FA code |

#### Transactions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/transactions/` | List transactions (paginated) |
| POST | `/transactions/` | Create transaction |
| GET | `/transactions/{id}/` | Get transaction details |
| PUT | `/transactions/{id}/` | Update transaction |
| DELETE | `/transactions/{id}/` | Delete transaction |
| GET | `/transactions/stats/` | Get statistics |
| GET | `/transactions/categories/` | List categories |

#### Budgets

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/budgets/` | List budgets |
| POST | `/budgets/` | Create budget |
| GET | `/budgets/{id}/` | Get budget details |
| PUT | `/budgets/{id}/` | Update budget |
| DELETE | `/budgets/{id}/` | Delete budget |
| GET | `/budgets/{id}/progress/` | Get budget progress |
| GET | `/budgets/current/` | Get active budgets |

#### Banking

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/banking/connections/` | List bank connections |
| POST | `/banking/connections/` | Initiate bank connection |
| DELETE | `/banking/connections/{id}/` | Remove connection |
| POST | `/banking/connections/{id}/sync/` | Trigger sync |
| GET | `/banking/accounts/` | List bank accounts |
| GET | `/banking/accounts/summary/` | Get balance summary |

### Request/Response Format

**Request Example:**
```json
POST /api/v1/transactions/
Content-Type: application/json
Authorization: Bearer eyJ0eXAiOiJKV1Q...

{
  "amount": 125.50,
  "type": "expense",
  "description": "Grocery shopping",
  "category_id": "550e8400-e29b-41d4-a716-446655440000",
  "transaction_date": "2026-01-29"
}
```

**Response Example:**
```json
HTTP/1.1 201 Created
Content-Type: application/json

{
  "data": {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "amount": "125.50",
    "type": "expense",
    "description": "Grocery shopping",
    "category": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Groceries",
      "color": "#4CAF50"
    },
    "transaction_date": "2026-01-29",
    "created_at": "2026-01-29T14:30:00Z",
    "updated_at": "2026-01-29T14:30:00Z"
  }
}
```

---

## Security

### Authentication & Authorization

- **JWT-based authentication** with short-lived access tokens (15 min)
- **Refresh token rotation** for enhanced security
- **Two-Factor Authentication (2FA)** using TOTP
- **Role-based access control** for subscription tiers

### Data Protection

- **Encryption at rest**: All sensitive data encrypted in database
- **Encryption in transit**: TLS 1.3 for all API communication
- **Banking tokens**: Encrypted with Fernet (AES-256-CBC)
- **Password hashing**: Argon2id algorithm

### Security Headers

All API responses include:
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy`

### Rate Limiting

| Tier | Requests/Minute |
|------|-----------------|
| Anonymous | 60 |
| Free | 120 |
| Premium | 300 |
| Pro | 600 |
| Business | 1200 |

For detailed security guidelines, see [SECURITY_GUIDELINES.md](./SECURITY_GUIDELINES.md).

---

## Testing

### Web API

```bash
cd pecunia-web

# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test file
pytest apps/transactions/tests/test_views.py
```

### Desktop

```bash
cd pecunia-desktop

# Run all tests
pytest tests/

# Run with coverage
pytest --cov=src --cov-report=html
```

### Mobile

```bash
cd pecunia-mobile

# Run unit tests
./gradlew test

# Run instrumented tests
./gradlew connectedAndroidTest
```

---

## Deployment

### Web API (Docker)

```bash
cd pecunia-web

# Build image
docker build -t pecunia-api .

# Run with docker-compose
docker-compose up -d
```

### Desktop (PyInstaller)

```bash
cd pecunia-desktop

# Build executable
pyinstaller --onefile --windowed src/main.py
```

### Mobile (Release)

```bash
cd pecunia-mobile

# Build release APK
./gradlew assembleRelease

# Build release AAB (Play Store)
./gradlew bundleRelease
```

---

## Contributing

We welcome contributions! Please read our contributing guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`feature/web/FA-123-description`)
3. **Follow** the coding conventions in [MASTER_CONVENTIONS.md](./MASTER_CONVENTIONS.md)
4. **Write** tests for new functionality
5. **Submit** a pull request

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **Kotlin**: Follow Kotlin coding conventions
- **All**: Use meaningful commit messages (conventional commits)

---

## Contributing

We welcome contributions! Pecunia is an open-source project and we'd love your help.

- Read our [Contributing Guide](./CONTRIBUTING.md) to get started
- Check the [open issues](https://github.com/kingoftech-v01/pecunia/issues) for tasks
- Look for `good first issue` labels if you're new to the project
- Please follow our [Code of Conduct](./CODE_OF_CONDUCT.md)

### Areas Where We Need Help

| Area | Platform | Difficulty |
|------|----------|------------|
| Offline sync completion | All | Medium-Hard |
| Receipt scanner with OCR | Mobile | Medium |
| Dashboard with charts | Desktop | Medium |
| Budget alerts | Web API | Easy-Medium |
| Dark mode fixes | Mobile | Easy |
| Test coverage improvement | All | Easy-Medium |
| Documentation & API docs | Web API | Easy |

---

## Support

- **Issue Tracker**: [GitHub Issues](https://github.com/kingoftech-v01/pecunia/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kingoftech-v01/pecunia/discussions)

---

*Built with care by the Pecunia community*
