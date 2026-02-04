# Banking App

Bank account connections and transaction synchronization.

## Overview

The banking app handles integration with bank APIs:

- Bank connection management (Plaid, TrueLayer)
- Account synchronization
- Encrypted credential storage
- Transaction import from banks

## Models

### BankConnection

```python
class BankConnection(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)

    provider = CharField(choices=['plaid', 'truelayer', 'budget_insight'])
    institution_id = CharField()
    institution_name = CharField()

    # Encrypted tokens
    _access_token_encrypted = TextField()
    _refresh_token_encrypted = TextField()
    token_expires_at = DateTimeField(null=True)

    status = CharField(choices=['active', 'pending', 'expired', 'error'])

    last_sync_at = DateTimeField(null=True)
    error_message = TextField(blank=True)
```

### BankAccount

```python
class BankAccount(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)
    connection = ForeignKey(BankConnection, CASCADE)

    external_id = CharField()
    name = CharField()
    account_type = CharField()  # checking, savings, credit

    balance = DecimalField()
    currency = CharField(default='EUR')

    is_active = BooleanField(default=True)
    last_sync_at = DateTimeField(null=True)
```

## Security

### Token Encryption

Bank API tokens are encrypted using Fernet (AES-128-CBC):

```python
# Access tokens are encrypted at rest
connection.access_token = "plain_token"  # Auto-encrypts
token = connection.access_token  # Auto-decrypts
```

**NEVER** store unencrypted bank credentials.

### Environment Variables

```bash
FIELD_ENCRYPTION_KEY=<fernet-key>
PLAID_CLIENT_ID=<plaid-client-id>
PLAID_SECRET=<plaid-secret>
PLAID_ENV=sandbox  # or development, production
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/banking/connections/` | GET | List connections |
| `/api/v1/banking/connections/` | POST | Create connection |
| `/api/v1/banking/connections/{id}/` | DELETE | Remove connection |
| `/api/v1/banking/connections/{id}/sync/` | POST | Trigger sync |
| `/api/v1/banking/accounts/` | GET | List accounts |
| `/api/v1/banking/accounts/{id}/` | PATCH | Update account |
| `/api/v1/banking/link-token/` | POST | Get Plaid link token |

## Sync Flow

```
1. User connects bank via Plaid Link
2. Exchange public_token for access_token
3. Store encrypted access_token
4. Fetch accounts and store
5. Periodic sync (every 15 min) fetches new transactions
6. Transactions imported to local database
```

## Celery Tasks

- `sync_bank_account` - Sync single account
- `sync_all_bank_accounts` - Sync all active accounts
- `refresh_expired_tokens` - Refresh expiring tokens

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `active` | Working normally | Continue syncing |
| `pending` | Awaiting user action | Show reconnect prompt |
| `expired` | Token expired | Refresh or reconnect |
| `error` | Sync failed | Show error, retry later |

## Testing

```bash
# Use Plaid sandbox for testing
PLAID_ENV=sandbox pytest apps/banking/tests/ -v
```

## Related

- [SECURITY_GUIDELINES.md](../../../SECURITY_GUIDELINES.md) - Encryption requirements
- [WEB_CONVENTIONS.md](../../WEB_CONVENTIONS.md) - Django patterns
