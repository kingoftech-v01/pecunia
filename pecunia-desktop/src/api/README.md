# API Module

Async HTTP client for server communication.

## Overview

The API module provides:

- Async HTTP client with connection pooling
- Authentication and token management
- Domain-specific API clients
- Error handling and retry logic

## Architecture

```
api/
├── __init__.py
├── client.py          # Base HTTP client
├── auth.py            # Authentication service
├── transactions.py    # Transaction API
├── budgets.py         # Budget API
└── banking.py         # Banking API
```

## Base Client

The `APIClient` class handles all HTTP communication:

```python
from api.client import APIClient

client = APIClient(base_url="https://api.pecunia.com")
await client.connect()

# Set token provider
client.set_token_provider(lambda: auth_service.get_access_token())

# Make requests
response = await client.get("/api/v1/transactions/")
if response.is_ok:
    transactions = response.data['data']

await client.close()
```

### Features

- **Connection pooling**: 100 total, 20 per host
- **Automatic retry**: 3 retries with exponential backoff
- **Timeout handling**: 30 seconds default
- **Token injection**: Via callback function

## Authentication Service

```python
from api.auth import AuthService

auth = AuthService(client)

# Login
tokens = await auth.login("user@example.com", "password")

# Refresh token
new_tokens = await auth.refresh_token()

# Logout
await auth.logout()
```

### Token Storage

Tokens are stored securely:

1. **System keyring** (preferred) - OS-level encryption
2. **Encrypted file** (fallback) - Fernet encryption

Never stores tokens in plain text.

## Domain APIs

### TransactionsAPI

```python
from api.transactions import TransactionsAPI

api = TransactionsAPI(client)

# List transactions
response = await api.list(page=1, page_size=20)

# Create transaction
response = await api.create({
    'amount': 100.00,
    'type': 'expense',
    'description': 'Groceries'
})

# Get statistics
response = await api.stats(date_from=date(2026, 1, 1))
```

### BudgetsAPI

```python
from api.budgets import BudgetsAPI

api = BudgetsAPI(client)

# List budgets
response = await api.list()

# Check budget impact
response = await api.check_impact(budget_id, amount=50.00)
```

### BankingAPI

```python
from api.banking import BankingAPI

api = BankingAPI(client)

# Get Plaid link token
response = await api.create_link_token()

# Sync accounts
response = await api.sync_accounts()
```

## Error Handling

```python
from exceptions import APIError, NetworkError, AuthenticationError

try:
    response = await client.get("/api/v1/transactions/")
except NetworkError:
    # No network connection
    show_offline_message()
except AuthenticationError:
    # Token expired, need re-login
    redirect_to_login()
except APIError as e:
    # Server returned error
    show_error(e.message)
```

## Response Format

```python
@dataclass
class APIResponse:
    status_code: int      # HTTP status
    data: Any            # Response body (dict or list)
    is_ok: bool          # True if 2xx status

    @property
    def error_message(self) -> str | None:
        # Extract error from response
```

## Testing

```python
# tests/test_api/test_transactions.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.get.return_value = APIResponse(200, {'data': []}, True)
    return client

async def test_list_transactions(mock_client):
    api = TransactionsAPI(mock_client)
    response = await api.list()
    assert response.is_ok
```

## Related

- [DESKTOP_CONVENTIONS.md](../../DESKTOP_CONVENTIONS.md) - API patterns
- [SECURITY_GUIDELINES.md](../../../SECURITY_GUIDELINES.md) - Token storage
