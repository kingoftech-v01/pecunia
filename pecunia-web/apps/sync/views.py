"""
Sync API Views.

DRF Views for data synchronization operations between clients and server.

This module implements the sync protocol for offline-first applications:

Sync Architecture:
------------------
1. Push Sync (Client → Server):
   - Client sends local changes since last_sync_timestamp
   - Server processes changes, detects conflicts, returns results
   - Changes include: create, update, delete operations

2. Pull Sync (Server → Client):
   - Client requests changes since last_sync_timestamp
   - Server returns all modified records for requested models
   - Client applies changes to local database

3. Bidirectional Sync:
   - Combines push and pull in single request
   - More efficient for full sync operations

Conflict Resolution Strategy:
----------------------------
When the same record is modified on both client and server:

| Strategy      | Description                           |
|---------------|---------------------------------------|
| server_wins   | Server version overwrites client      |
| client_wins   | Client version overwrites server      |
| merged        | Merge fields (requires resolved_data) |
| manual        | User decides via conflict UI          |

Default: Last-Write-Wins based on updated_at timestamp.

API Endpoints:
--------------
- POST /api/v1/sync/push/              - Push local changes
- GET  /api/v1/sync/pull/              - Pull server changes
- POST /api/v1/sync/                   - Bidirectional sync
- GET  /api/v1/sync/status/            - Get sync status
- GET  /api/v1/sync/conflicts/         - List pending conflicts
- POST /api/v1/sync/conflicts/{id}/resolve/  - Resolve a conflict
- GET  /api/v1/sync/logs/              - List sync history

Related Documentation:
- See SCALABILITY_GUIDELINES.md for batch processing limits
- See SECURITY_GUIDELINES.md for rate limiting configuration
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.utils.dateparse import parse_datetime

from .models import SyncLog, SyncQueue, SyncConflict
from .manager import get_sync_manager


class SyncPushView(APIView):
    """
    Handle push sync from clients.

    POST /api/v1/sync/push/
    Push local changes to the server.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Process pushed changes from client.

        Request body:
        {
            "device_id": "optional-device-id",
            "device_name": "optional-device-name",
            "client_version": "1.0.0",
            "last_sync_timestamp": "2024-01-01T00:00:00Z",
            "changes": [
                {
                    "operation": "create|update|delete",
                    "model": "transactions.Transaction",
                    "object_id": "uuid",
                    "data": {...},
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
        }
        """
        manager = get_sync_manager(request.user)

        # Extract request data
        device_id = request.data.get('device_id')
        device_name = request.data.get('device_name')
        client_version = request.data.get('client_version')
        changes = request.data.get('changes', [])

        last_sync_str = request.data.get('last_sync_timestamp')
        last_sync_timestamp = parse_datetime(last_sync_str) if last_sync_str else None

        # Start sync
        sync_log = manager.start_sync(
            direction='push',
            device_id=device_id,
            device_name=device_name,
            client_version=client_version,
        )

        try:
            # Process the push
            results = manager.process_push(sync_log, changes, last_sync_timestamp)

            # Complete sync
            has_errors = len(results['failed']) > 0 or len(results['conflicts']) > 0
            manager.complete_sync(sync_log, success=not has_errors)

            return Response({
                'sync_id': str(sync_log.id),
                'status': 'partial' if has_errors else 'success',
                'processed_count': len(results['processed']),
                'failed_count': len(results['failed']),
                'conflict_count': len(results['conflicts']),
                'processed': results['processed'],
                'failed': results['failed'],
                'conflicts': results['conflicts'],
            }, status=status.HTTP_200_OK)

        except Exception as e:
            manager.complete_sync(sync_log, success=False, error=str(e))
            return Response({
                'sync_id': str(sync_log.id),
                'status': 'error',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncPullView(APIView):
    """
    Handle pull sync for clients.

    GET /api/v1/sync/pull/
    Pull server changes to the client.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get changes since last sync.

        Query params:
        - last_sync_timestamp: ISO timestamp of last sync
        - models: Comma-separated list of models to sync (optional)
        - device_id: Device identifier (optional)
        """
        manager = get_sync_manager(request.user)

        # Extract query params
        device_id = request.query_params.get('device_id')
        last_sync_str = request.query_params.get('last_sync_timestamp')
        last_sync_timestamp = parse_datetime(last_sync_str) if last_sync_str else None

        models_str = request.query_params.get('models')
        models = models_str.split(',') if models_str else None

        # Start sync
        sync_log = manager.start_sync(
            direction='pull',
            device_id=device_id,
        )

        try:
            # Prepare pull data
            data = manager.prepare_pull(sync_log, last_sync_timestamp, models)

            # Complete sync
            manager.complete_sync(sync_log, success=True)

            return Response({
                'sync_id': str(sync_log.id),
                'status': 'success',
                'sync_timestamp': data['sync_timestamp'],
                'changes': data['changes'],
                'items_count': sync_log.items_pulled,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            manager.complete_sync(sync_log, success=False, error=str(e))
            return Response({
                'sync_id': str(sync_log.id),
                'status': 'error',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncBidirectionalView(APIView):
    """
    Handle bidirectional sync (push + pull in single request).

    POST /api/v1/sync/

    This is the primary sync endpoint for mobile/desktop clients.
    It combines push and pull operations for efficiency, reducing
    the number of HTTP round-trips required for a full sync.

    Sync Flow:
    ----------
    1. Client sends local changes with last_sync_timestamp
    2. Server processes push (creates/updates/deletes)
    3. Server detects conflicts (same record modified both sides)
    4. Server prepares pull data (all changes since timestamp)
    5. Server returns combined results

    Conflict Detection:
    ------------------
    A conflict occurs when:
    - Same object_id modified on both client and server
    - Client's timestamp < server's updated_at for that record

    Response Status:
    ---------------
    - 'success': All operations completed without issues
    - 'partial': Some conflicts or failures occurred
    - 'error': Critical error prevented sync completion

    Performance Notes:
    -----------------
    - Batch size limited to 100 changes per request (configurable)
    - Large syncs should use pagination via last_sync_timestamp
    - Consider using push/pull separately for initial bulk sync
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Perform bidirectional sync.

        Request Body:
        -------------
        {
            "device_id": "uuid",           // Device identifier for multi-device sync
            "device_name": "iPhone 15",    // Human-readable device name
            "client_version": "1.0.0",     // App version for compatibility checks
            "last_sync_timestamp": "ISO",  // Last successful sync time
            "changes": [                   // Local changes to push
                {
                    "operation": "create|update|delete",
                    "model": "transactions.Transaction",
                    "object_id": "uuid",
                    "data": {...},
                    "timestamp": "ISO"
                }
            ],
            "models": ["transactions.Transaction", ...]  // Models to pull
        }

        Response:
        ---------
        {
            "sync_id": "uuid",
            "status": "success|partial|error",
            "sync_timestamp": "ISO",       // Use as next last_sync_timestamp
            "push": {
                "processed_count": 5,
                "failed_count": 0,
                "conflict_count": 1,
                "processed": [...],
                "failed": [...],
                "conflicts": [...]
            },
            "pull": {
                "items_count": 10,
                "changes": [...]
            }
        }
        """
        manager = get_sync_manager(request.user)

        # Extract request data
        device_id = request.data.get('device_id')
        device_name = request.data.get('device_name')
        client_version = request.data.get('client_version')
        changes = request.data.get('changes', [])
        models = request.data.get('models')

        last_sync_str = request.data.get('last_sync_timestamp')
        last_sync_timestamp = parse_datetime(last_sync_str) if last_sync_str else None

        # Start sync
        sync_log = manager.start_sync(
            direction='bidirectional',
            device_id=device_id,
            device_name=device_name,
            client_version=client_version,
        )

        try:
            # Process push
            push_results = manager.process_push(sync_log, changes, last_sync_timestamp)

            # Prepare pull
            pull_data = manager.prepare_pull(sync_log, last_sync_timestamp, models)

            # Determine overall status
            has_errors = (
                len(push_results['failed']) > 0 or
                len(push_results['conflicts']) > 0
            )
            manager.complete_sync(sync_log, success=not has_errors)

            return Response({
                'sync_id': str(sync_log.id),
                'status': 'partial' if has_errors else 'success',
                'sync_timestamp': pull_data['sync_timestamp'],
                'push': {
                    'processed_count': len(push_results['processed']),
                    'failed_count': len(push_results['failed']),
                    'conflict_count': len(push_results['conflicts']),
                    'processed': push_results['processed'],
                    'failed': push_results['failed'],
                    'conflicts': push_results['conflicts'],
                },
                'pull': {
                    'items_count': sync_log.items_pulled,
                    'changes': pull_data['changes'],
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            manager.complete_sync(sync_log, success=False, error=str(e))
            return Response({
                'sync_id': str(sync_log.id),
                'status': 'error',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncStatusView(APIView):
    """
    Get sync status for the current user.

    GET /api/v1/sync/status/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current sync status."""
        manager = get_sync_manager(request.user)
        status_data = manager.get_sync_status()

        return Response({
            'status': 'success',
            **status_data,
        }, status=status.HTTP_200_OK)


class SyncConflictListView(APIView):
    """
    List and resolve sync conflicts.

    GET /api/v1/sync/conflicts/
    POST /api/v1/sync/conflicts/{id}/resolve/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all pending conflicts for the user."""
        conflicts = SyncConflict.objects.filter(
            user=request.user,
            resolution_status='pending'
        )

        conflicts_data = [
            {
                'id': str(c.id),
                'model_name': c.model_name,
                'object_id': c.object_id,
                'server_version': c.server_version,
                'client_version': c.client_version,
                'detected_at': c.detected_at.isoformat(),
            }
            for c in conflicts
        ]

        return Response({
            'status': 'success',
            'count': len(conflicts_data),
            'conflicts': conflicts_data,
        }, status=status.HTTP_200_OK)


class SyncConflictResolveView(APIView):
    """
    Resolve a specific sync conflict.

    POST /api/v1/sync/conflicts/{id}/resolve/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, conflict_id):
        """
        Resolve a conflict.

        Request body:
        {
            "resolution": "server_wins|client_wins|merged|manual",
            "resolved_data": {...}  // Required for merged/manual
        }
        """
        manager = get_sync_manager(request.user)

        resolution = request.data.get('resolution')
        resolved_data = request.data.get('resolved_data')

        if not resolution:
            return Response({
                'status': 'error',
                'error': 'resolution is required',
            }, status=status.HTTP_400_BAD_REQUEST)

        if resolution in ['merged', 'manual'] and not resolved_data:
            return Response({
                'status': 'error',
                'error': 'resolved_data is required for merged/manual resolution',
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            conflict = manager.resolve_conflict(conflict_id, resolution, resolved_data)

            return Response({
                'status': 'success',
                'conflict_id': str(conflict.id),
                'resolution': conflict.resolution_status,
                'resolved_at': conflict.resolved_at.isoformat(),
            }, status=status.HTTP_200_OK)

        except SyncConflict.DoesNotExist:
            return Response({
                'status': 'error',
                'error': 'Conflict not found',
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'error': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncLogListView(APIView):
    """
    List sync logs for the current user.

    GET /api/v1/sync/logs/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get recent sync logs."""
        limit = int(request.query_params.get('limit', 10))
        device_id = request.query_params.get('device_id')

        queryset = SyncLog.objects.filter(user=request.user)

        if device_id:
            queryset = queryset.filter(device_id=device_id)

        logs = queryset[:limit]

        logs_data = [
            {
                'id': str(log.id),
                'direction': log.direction,
                'status': log.status,
                'device_id': log.device_id,
                'device_name': log.device_name,
                'items_pushed': log.items_pushed,
                'items_pulled': log.items_pulled,
                'items_failed': log.items_failed,
                'started_at': log.started_at.isoformat(),
                'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                'duration': log.duration,
                'error_message': log.error_message,
            }
            for log in logs
        ]

        return Response({
            'status': 'success',
            'count': len(logs_data),
            'logs': logs_data,
        }, status=status.HTTP_200_OK)
