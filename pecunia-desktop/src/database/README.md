# Database Module

SQLAlchemy ORM with SQLite for local storage.

## Overview

The database module provides:

- SQLAlchemy engine and session management
- ORM models with sync tracking
- Connection pooling and optimization
- Optional SQLCipher encryption

## Architecture

```
database/
├── __init__.py
├── connection.py      # Engine and session factory
└── models/
    ├── __init__.py
    ├── base.py        # Base model class
    ├── user.py        # User model
    ├── transaction.py # Transaction model
    └── budget.py      # Budget model
```

## Connection Management

```python
from database.connection import get_session, init_database

# Initialize database
init_database()

# Use session context manager
with get_session() as session:
    transactions = session.query(Transaction).filter(
        Transaction.user_id == user_id
    ).all()
```

### Configuration

```python
# SQLite optimizations applied automatically:
# - WAL journal mode (concurrent reads)
# - Synchronous NORMAL (performance)
# - 64MB cache size
# - Foreign keys enabled
```

## Base Model

All models inherit from `BaseModel`:

```python
class BaseModel(Base):
    __abstract__ = True

    # Local primary key
    id: Mapped[int]

    # Server sync fields
    server_id: Mapped[str | None]   # UUID from server
    is_synced: Mapped[bool]         # Sync status
    sync_status: Mapped[str]        # pending, syncing, synced

    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Version for optimistic locking
    version: Mapped[int]

    # Methods
    def mark_synced(self, server_id: str)
    def mark_dirty(self)
    def to_dict(self) -> dict
```

## Models

### Transaction

```python
class Transaction(BaseModel):
    __tablename__ = 'transactions'

    user_id: Mapped[int]
    category_id: Mapped[int | None]
    bank_account_id: Mapped[int | None]

    amount: Mapped[Decimal]
    type: Mapped[TransactionType]
    description: Mapped[str]
    transaction_date: Mapped[date]

    is_recurring: Mapped[bool]
    is_pending: Mapped[bool]
    is_deleted: Mapped[bool]

    tags: Mapped[str]  # Comma-separated

    # Relationships
    category: Mapped['Category']

    # Properties
    @property
    def signed_amount(self) -> Decimal
    @property
    def tag_list(self) -> list[str]

    # Methods
    def to_api_payload(self) -> dict
    @classmethod
    def from_api_response(cls, data: dict) -> 'Transaction'
```

### Budget

```python
class Budget(BaseModel):
    __tablename__ = 'budgets'

    user_id: Mapped[int]
    category_id: Mapped[int | None]

    name: Mapped[str]
    amount: Mapped[Decimal]
    spent: Mapped[Decimal]

    period_type: Mapped[str]  # monthly, weekly, custom
    period_start: Mapped[date]
    period_end: Mapped[date]

    alert_threshold: Mapped[float]  # 0.8 = 80%
    is_active: Mapped[bool]

    @property
    def remaining(self) -> Decimal
    @property
    def percentage_used(self) -> float
    @property
    def is_over_budget(self) -> bool
```

## Indexes

Performance-critical indexes:

```python
__table_args__ = (
    Index('ix_trans_user_date', 'user_id', 'transaction_date'),
    Index('ix_trans_user_type', 'user_id', 'type'),
    Index('ix_trans_unsynced', 'is_synced'),
)
```

## Encryption

Optional SQLCipher encryption:

```python
from database.connection import create_encrypted_engine

# Encryption key from keyring
key = keyring.get_password('pecunia', 'db_key')

engine = create_encrypted_engine(db_path, key)
```

## Migrations

Using Alembic for schema migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add new field"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Testing

```python
# tests/test_database/test_models.py
import pytest
from database.connection import create_test_engine
from database.models import Transaction

@pytest.fixture
def db_session():
    engine = create_test_engine()  # In-memory SQLite
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_transaction(db_session):
    tx = Transaction(
        user_id=1,
        amount=Decimal('100.00'),
        type=TransactionType.EXPENSE
    )
    db_session.add(tx)
    db_session.commit()

    assert tx.id is not None
    assert not tx.is_synced
```

## Related

- [DESKTOP_CONVENTIONS.md](../../DESKTOP_CONVENTIONS.md) - Model conventions
- [SCALABILITY_GUIDELINES.md](../../../SCALABILITY_GUIDELINES.md) - Query optimization
