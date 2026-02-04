# Pecunia Web - Django REST API

Personal finance management API built with Django REST Framework.

## Overview

Pecunia Web serves as the **source of truth** for the multi-platform finance application. It provides:

- RESTful API endpoints for transactions, budgets, and banking
- JWT-based authentication
- Real-time sync endpoints for offline-first clients
- Bank integration via Plaid/TrueLayer
- Background task processing with Celery

## Architecture

```
pecunia-web/
├── apps/                    # Django applications
│   ├── accounts/           # User authentication & profiles
│   ├── transactions/       # Transaction management
│   ├── budgets/            # Budget tracking
│   ├── banking/            # Bank integrations
│   ├── sync/               # Sync endpoints
│   └── core/               # Shared utilities
├── config/                 # Django configuration
│   └── settings/           # Environment-specific settings
├── docker/                 # Docker configuration
└── templates/              # HTML templates (HTMX)
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for frontend assets)

### Installation

```bash
# Clone and navigate
cd pecunia-web

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Running with Docker

```bash
cd docker
docker-compose -f docker-compose.dev.yml up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | `False` |
| `DATABASE_URL` | PostgreSQL connection | Required |
| `REDIS_URL` | Redis connection | Required |
| `FIELD_ENCRYPTION_KEY` | Fernet key for encryption | Required |

### Settings Files

- `config/settings/base.py` - Shared settings
- `config/settings/development.py` - Development overrides
- `config/settings/production.py` - Production settings

## API Documentation

### Authentication

```bash
# Login
POST /api/v1/accounts/login/
{
  "email": "user@example.com",
  "password": "password123"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": "...", "email": "..." }
}

# Use token in requests
Authorization: Bearer <access_token>
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/accounts/login/` | POST | User login |
| `/api/v1/accounts/register/` | POST | User registration |
| `/api/v1/accounts/users/me/` | GET/PATCH | Current user |
| `/api/v1/transactions/` | GET/POST | Transactions list/create |
| `/api/v1/transactions/{id}/` | GET/PATCH/DELETE | Transaction detail |
| `/api/v1/budgets/` | GET/POST | Budgets list/create |
| `/api/v1/sync/push/` | POST | Push local changes |
| `/api/v1/sync/pull/` | GET | Pull remote changes |

## Background Tasks

### Celery Configuration

```bash
# Start Celery worker
celery -A config worker -l info

# Start Celery beat (scheduler)
celery -A config beat -l info
```

### Scheduled Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `process_recurring` | Daily 00:00 | Create recurring transactions |
| `sync_bank_accounts` | Every 15 min | Sync bank data |
| `cleanup_sessions` | Daily 02:00 | Remove expired sessions |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps/transactions/tests/
```

## Conventions

See [WEB_CONVENTIONS.md](./WEB_CONVENTIONS.md) for Django-specific patterns.

## Related Documentation

- [MASTER_CONVENTIONS.md](../MASTER_CONVENTIONS.md) - Cross-platform conventions
- [SECURITY_GUIDELINES.md](../SECURITY_GUIDELINES.md) - Security requirements
- [SCALABILITY_GUIDELINES.md](../SCALABILITY_GUIDELINES.md) - Performance patterns
- [URL_AND_VIEW_CONVENTIONS.md](../URL_AND_VIEW_CONVENTIONS.md) - URL patterns

## License

Proprietary - All rights reserved
