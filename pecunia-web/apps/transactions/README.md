# Transactions App

Transaction management and categorization.

## Overview

The transactions app handles financial transaction management:

- CRUD operations for transactions
- Category management
- Recurring transactions
- Transaction statistics and summaries
- Filtering, search, and pagination

## Models

### Transaction

```python
class Transaction(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)
    bank_account = ForeignKey(BankAccount, SET_NULL, null=True)
    category = ForeignKey(TransactionCategory, SET_NULL, null=True)

    amount = DecimalField(max_digits=15, decimal_places=2)
    type = CharField(choices=['income', 'expense', 'transfer'])
    description = TextField(blank=True)
    transaction_date = DateField()

    is_recurring = BooleanField(default=False)
    tags = JSONField(default=list)

    # AI categorization
    ai_category_suggestion = ForeignKey(TransactionCategory, null=True)
    ai_confidence = FloatField(null=True)

    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### TransactionCategory

```python
class TransactionCategory(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)
    name = CharField(max_length=100)
    color = CharField(max_length=7, default='#6366f1')
    icon = CharField(max_length=50, blank=True)
    is_default = BooleanField(default=False)
```

### RecurringTransaction

```python
class RecurringTransaction(Model):
    user = ForeignKey(User, CASCADE)
    amount = DecimalField()
    type = CharField()
    category = ForeignKey(TransactionCategory, null=True)
    description = CharField()

    frequency = CharField()  # daily, weekly, monthly, yearly
    next_occurrence = DateField()
    end_date = DateField(null=True)
    is_active = BooleanField(default=True)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transactions/` | GET | List with filters |
| `/api/v1/transactions/` | POST | Create transaction |
| `/api/v1/transactions/{id}/` | GET | Get details |
| `/api/v1/transactions/{id}/` | PATCH | Update |
| `/api/v1/transactions/{id}/` | DELETE | Delete |
| `/api/v1/transactions/stats/` | GET | Statistics |
| `/api/v1/transactions/by_category/` | GET | Grouped by category |
| `/api/v1/transactions/categories/` | GET/POST | Categories CRUD |
| `/api/v1/transactions/recurring/` | GET/POST | Recurring transactions |

## Filtering

```
GET /api/v1/transactions/?type=expense&category=food&date_from=2026-01-01
```

| Parameter | Description |
|-----------|-------------|
| `type` | income, expense, transfer |
| `category` | Category ID |
| `date_from` | Start date (YYYY-MM-DD) |
| `date_to` | End date (YYYY-MM-DD) |
| `amount_min` | Minimum amount |
| `amount_max` | Maximum amount |
| `search` | Search description |

## Statistics Endpoint

```json
GET /api/v1/transactions/stats/
{
  "total_income": 5000.00,
  "total_expenses": 3500.00,
  "net_amount": 1500.00,
  "transaction_count": 45,
  "by_category": [
    {"category": "Food", "total": 800.00, "count": 15},
    {"category": "Transport", "total": 200.00, "count": 8}
  ]
}
```

## Celery Tasks

- `process_recurring_transactions` - Daily, creates recurring entries
- `categorize_transactions` - AI-powered categorization

## Testing

```bash
pytest apps/transactions/tests/ -v
```

## Related

- [WEB_CONVENTIONS.md](../../WEB_CONVENTIONS.md) - Django patterns
- [SCALABILITY_GUIDELINES.md](../../../SCALABILITY_GUIDELINES.md) - Query optimization
