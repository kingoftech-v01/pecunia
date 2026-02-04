# Sync Module

Offline-first synchronization engine.

## Overview

The sync module handles bidirectional data synchronization:

- Queue local changes for sync
- Push changes to server when online
- Pull remote changes
- Resolve conflicts
- Track sync status

## Architecture

```
sync/
├── __init__.py
├── manager.py           # Sync orchestration
├── queue.py            # Operation queue
└── conflict_resolver.py # Conflict resolution
```

## Sync Strategy

### Offline-First Flow

1. **Local Write**: All changes go to local database first
2. **Queue**: Changes queued for sync
3. **Push**: When online, push queued changes
4. **Pull**: Fetch remote changes
5. **Merge**: Apply remote changes, resolve conflicts

```
User Action
    ↓
Local Database (immediate)
    ↓
Sync Queue (background)
    ↓
Server API (when online)
    ↓
Conflict Resolution (if needed)
    ↓
Local Database Update
```

## Components

### SyncManager

Main orchestrator for sync operations:

```python
from sync.manager import SyncManager

manager = SyncManager(
    transactions_api=transactions_api,
    conflict_resolver=ConflictResolver()
)

# Queue a change
manager.queue_operation(QueuedOperation(
    entity_type='transaction',
    entity_id='123',
    operation='create'
))

# Run sync
result = await manager.sync_all()
print(f"Pushed: {result.pushed}, Pulled: {result.pulled}")
```

### SyncQueue

Thread-safe queue for pending operations:

```python
from sync.queue import SyncQueue, QueuedOperation

queue = SyncQueue()

# Add operation
queue.enqueue(QueuedOperation(
    entity_type='transaction',
    entity_id='123',
    operation='update',
    priority=5
))

# Get batch for processing
batch = queue.get_batch(size=50)

# Operations are deduped by entity_type + entity_id
```

### ConflictResolver

Handles sync conflicts:

```python
from sync.conflict_resolver import ConflictResolver, ConflictResolution

resolver = ConflictResolver()

resolution = resolver.resolve(
    local_data={'amount': 100, 'updated_at': '2026-01-28T14:00:00Z'},
    remote_data={'amount': 150, 'updated_at': '2026-01-28T14:30:00Z'}
)

# resolution = ConflictResolution.KEEP_REMOTE
```

#### Resolution Strategies

| Strategy | Description |
|----------|-------------|
| `KEEP_LOCAL` | Local changes win |
| `KEEP_REMOTE` | Server changes win |
| `KEEP_NEWEST` | Most recent wins (default) |
| `MERGE` | Merge fields (complex) |
| `MANUAL` | User decides |

## Data Structures

### QueuedOperation

```python
@dataclass
class QueuedOperation:
    entity_type: str      # 'transaction', 'budget'
    entity_id: str        # Local ID
    operation: str        # 'create', 'update', 'delete'
    payload: str | None   # JSON payload (optional)
    priority: int = 5     # 1 (high) to 10 (low)
    created_at: datetime
```

### SyncResult

```python
@dataclass
class SyncResult:
    status: SyncStatus    # idle, syncing, success, error
    pushed: int          # Records pushed
    pulled: int          # Records pulled
    conflicts: int       # Conflicts encountered
    errors: list[str]    # Error messages
```

## Usage Example

```python
# Initialize sync manager
sync_manager = SyncManager(
    transactions_api=TransactionsAPI(api_client),
    budgets_api=BudgetsAPI(api_client)
)

# When user creates a transaction
async def create_transaction(data):
    # 1. Save locally
    with get_session() as session:
        tx = Transaction(**data, is_synced=False)
        session.add(tx)
        session.commit()

    # 2. Queue for sync
    sync_manager.queue_operation(QueuedOperation(
        entity_type='transaction',
        entity_id=str(tx.id),
        operation='create'
    ))

    # 3. Try immediate sync (non-blocking)
    asyncio.create_task(sync_manager.try_sync())

# Periodic sync (every 15 minutes)
async def periodic_sync():
    while True:
        await sync_manager.sync_all()
        await asyncio.sleep(900)  # 15 minutes
```

## Sync Status Tracking

Each entity has sync status fields:

```python
class Transaction(BaseModel):
    is_synced: bool           # Quick check
    sync_status: str          # 'pending', 'syncing', 'synced', 'error'
    server_id: str | None     # Server-assigned UUID
    local_version: int        # Incremented on change
    server_version: int | None # From server
```

## Error Handling

```python
try:
    result = await sync_manager.sync_all()

    if result.status == SyncStatus.SUCCESS:
        logger.info("Sync completed successfully")

    elif result.status == SyncStatus.CONFLICT:
        # Some conflicts need resolution
        for conflict in result.conflicts:
            await show_conflict_dialog(conflict)

    elif result.status == SyncStatus.ERROR:
        logger.error(f"Sync failed: {result.errors}")
        # Will retry on next sync cycle

except NetworkError:
    # Offline, sync will retry later
    logger.info("Offline, sync deferred")
```

## Testing

```python
# tests/test_sync/test_manager.py
import pytest
from sync.manager import SyncManager
from sync.queue import QueuedOperation

@pytest.fixture
def sync_manager(mock_api):
    return SyncManager(
        transactions_api=mock_api,
        conflict_resolver=ConflictResolver()
    )

async def test_sync_pushes_queued_operations(sync_manager, mock_api):
    # Arrange
    sync_manager.queue_operation(QueuedOperation(
        entity_type='transaction',
        entity_id='1',
        operation='create'
    ))

    # Act
    result = await sync_manager.sync_all()

    # Assert
    assert result.pushed == 1
    mock_api.create.assert_called_once()
```

## Related

- [DESKTOP_CONVENTIONS.md](../../DESKTOP_CONVENTIONS.md) - Sync patterns
- [MASTER_CONVENTIONS.md](../../../MASTER_CONVENTIONS.md) - Sync status fields
- [SCALABILITY_GUIDELINES.md](../../../SCALABILITY_GUIDELINES.md) - Batch processing
