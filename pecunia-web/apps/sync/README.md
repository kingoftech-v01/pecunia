# Sync App

Bidirectional data synchronization for offline-first clients.

## Overview

The sync app provides endpoints for desktop and mobile clients to:

- Push local changes to server
- Pull remote changes
- Detect and resolve conflicts
- Track sync status

## Sync Strategy

### Offline-First Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Desktop   │     │   Mobile    │     │   Server    │
│   (SQLite)  │     │   (Room)    │     │ (PostgreSQL)│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │   Push Changes    │                   │
       ├───────────────────┼──────────────────>│
       │                   │                   │
       │   Pull Changes    │                   │
       │<──────────────────┼───────────────────│
       │                   │                   │
       │   Conflict?       │                   │
       ├───────────────────┼──────────────────>│
       │                   │                   │
       │   Resolution      │                   │
       │<──────────────────┼───────────────────│
```

### Conflict Resolution

Default strategy: **Last-Write-Wins** with manual override option.

| Scenario | Resolution |
|----------|------------|
| Local newer | Keep local, push to server |
| Remote newer | Keep remote, update local |
| Same timestamp | Server wins (configurable) |
| Manual resolution | User chooses |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/sync/push/` | POST | Push local changes |
| `/api/v1/sync/pull/` | GET | Pull remote changes |
| `/api/v1/sync/` | POST | Bidirectional sync |
| `/api/v1/sync/status/` | GET | Sync status |
| `/api/v1/sync/conflicts/` | GET | List unresolved conflicts |
| `/api/v1/sync/conflicts/{id}/resolve/` | POST | Resolve conflict |

## Push Endpoint

```json
POST /api/v1/sync/push/
{
  "transactions": [
    {
      "id": "local-uuid",
      "operation": "create",  // create, update, delete
      "data": {
        "amount": 100.00,
        "type": "expense",
        "description": "Groceries"
      },
      "local_version": 1,
      "updated_at": "2026-01-28T14:30:00Z"
    }
  ],
  "budgets": [...]
}

Response:
{
  "success": true,
  "results": {
    "transactions": {
      "created": 1,
      "updated": 0,
      "conflicts": []
    }
  }
}
```

## Pull Endpoint

```json
GET /api/v1/sync/pull/?since=2026-01-28T00:00:00Z

Response:
{
  "transactions": [
    {
      "id": "server-uuid",
      "amount": 100.00,
      "type": "expense",
      "updated_at": "2026-01-28T14:35:00Z",
      "version": 2
    }
  ],
  "budgets": [...],
  "deleted_ids": {
    "transactions": ["uuid1", "uuid2"]
  },
  "sync_token": "eyJ..."
}
```

## Models

### SyncLog

```python
class SyncLog(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)

    sync_type = CharField()  # push, pull, bidirectional
    status = CharField()  # started, completed, failed

    pushed_count = IntegerField(default=0)
    pulled_count = IntegerField(default=0)
    conflict_count = IntegerField(default=0)

    started_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True)
    error_message = TextField(blank=True)
```

### SyncConflict

```python
class SyncConflict(Model):
    id = UUIDField(primary_key=True)
    user = ForeignKey(User, CASCADE)

    entity_type = CharField()  # transaction, budget
    entity_id = CharField()

    local_data = JSONField()
    remote_data = JSONField()

    status = CharField()  # pending, resolved, ignored
    resolution = CharField(null=True)  # local, remote, merged

    created_at = DateTimeField(auto_now_add=True)
    resolved_at = DateTimeField(null=True)
```

## Versioning

Each syncable entity has a `version` field:

- Incremented on every update
- Used for optimistic locking
- Prevents lost updates

```python
# Server-side version check
if local_version < server_version:
    # Conflict detected
    create_sync_conflict(...)
else:
    # Safe to update
    entity.version += 1
    entity.save()
```

## Client Implementation

### Desktop (Python)

```python
async def sync(self):
    # 1. Push local changes
    local_changes = await self.get_unsynced()
    push_result = await self.api.push(local_changes)

    # 2. Handle push conflicts
    for conflict in push_result.conflicts:
        await self.handle_conflict(conflict)

    # 3. Pull remote changes
    pull_result = await self.api.pull(since=self.last_sync)

    # 4. Apply remote changes
    await self.apply_changes(pull_result)

    # 5. Update last sync timestamp
    self.last_sync = datetime.utcnow()
```

### Mobile (Kotlin)

```kotlin
suspend fun sync() {
    // 1. Push local changes
    val unsynced = dao.getUnsyncedTransactions()
    val pushResult = apiService.pushChanges(unsynced)

    // 2. Mark as synced
    for (item in pushResult.success) {
        dao.markSynced(item.localId, item.serverId)
    }

    // 3. Pull remote changes
    val pullResult = apiService.pullChanges(lastSyncTimestamp)

    // 4. Apply to local database
    for (transaction in pullResult.transactions) {
        dao.upsert(transaction.toEntity())
    }
}
```

## Testing

```bash
pytest apps/sync/tests/ -v

# Test conflict scenarios
pytest apps/sync/tests/test_conflicts.py -v
```

## Related

- [MASTER_CONVENTIONS.md](../../../MASTER_CONVENTIONS.md) - Sync status fields
- [SCALABILITY_GUIDELINES.md](../../../SCALABILITY_GUIDELINES.md) - Batch processing
