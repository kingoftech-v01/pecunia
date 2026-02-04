"""
Sync Manager.

Handles offline data synchronization logic between clients and server.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from django.db import transaction
from django.apps import apps
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .models import SyncLog, SyncQueue, SyncConflict

logger = logging.getLogger(__name__)


class SyncManager:
    """
    Manager class for handling offline data synchronization.

    Provides methods for:
    - Processing incoming sync requests from clients
    - Preparing sync responses for clients
    - Handling conflict resolution
    - Managing sync queue
    """

    # Models that support synchronization
    SYNCABLE_MODELS = {
        'transactions.Transaction': {
            'model_path': 'apps.transactions.models.Transaction',
            'sync_fields': [
                'amount', 'description', 'transaction_date', 'type',
                'category', 'merchant', 'notes', 'is_recurring'
            ],
            'conflict_strategy': 'last_write_wins',
        },
        'transactions.TransactionCategory': {
            'model_path': 'apps.transactions.models.TransactionCategory',
            'sync_fields': ['name', 'color', 'icon', 'parent'],
            'conflict_strategy': 'last_write_wins',
        },
        'budgets.Budget': {
            'model_path': 'apps.budgets.models.Budget',
            'sync_fields': [
                'name', 'amount', 'period', 'start_date', 'end_date',
                'category', 'is_active'
            ],
            'conflict_strategy': 'server_wins',
        },
        'banking.BankAccount': {
            'model_path': 'apps.banking.models.BankAccount',
            'sync_fields': ['name', 'account_type', 'balance', 'currency', 'is_active'],
            'conflict_strategy': 'server_wins',
        },
    }

    def __init__(self, user):
        """Initialize sync manager for a specific user."""
        self.user = user

    def start_sync(
        self,
        direction: str,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        client_version: Optional[str] = None
    ) -> SyncLog:
        """
        Start a new sync operation and return the sync log.

        Args:
            direction: 'push', 'pull', or 'bidirectional'
            device_id: Unique identifier for the client device
            device_name: Human-readable device name
            client_version: Version of the client app

        Returns:
            SyncLog instance for tracking this sync
        """
        sync_log = SyncLog.objects.create(
            user=self.user,
            direction=direction,
            status='in_progress',
            device_id=device_id,
            device_name=device_name,
            client_version=client_version,
        )
        logger.info(f"Started sync {sync_log.id} for user {self.user.email}")
        return sync_log

    def process_push(
        self,
        sync_log: SyncLog,
        changes: List[Dict[str, Any]],
        last_sync_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process changes pushed from a client.

        Args:
            sync_log: The sync log for this operation
            changes: List of changes from the client
            last_sync_timestamp: When the client last synced

        Returns:
            Dict with results of the push operation
        """
        results = {
            'processed': [],
            'failed': [],
            'conflicts': [],
        }

        for change in changes:
            try:
                result = self._process_single_change(change, last_sync_timestamp)
                if result['status'] == 'conflict':
                    results['conflicts'].append(result)
                    sync_log.items_failed += 1
                else:
                    results['processed'].append(result)
                    sync_log.items_pushed += 1
            except Exception as e:
                logger.error(f"Error processing change: {e}")
                results['failed'].append({
                    'change': change,
                    'error': str(e),
                })
                sync_log.items_failed += 1

        sync_log.save()
        return results

    def _process_single_change(
        self,
        change: Dict[str, Any],
        last_sync_timestamp: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Process a single change from a client.

        Args:
            change: Change data containing operation, model, object_id, data
            last_sync_timestamp: When the client last synced

        Returns:
            Dict with result of processing
        """
        operation = change.get('operation')
        model_name = change.get('model')
        object_id = change.get('object_id')
        data = change.get('data', {})
        client_timestamp = change.get('timestamp')

        if model_name not in self.SYNCABLE_MODELS:
            raise ValueError(f"Model {model_name} is not syncable")

        model_config = self.SYNCABLE_MODELS[model_name]
        Model = apps.get_model(model_config['model_path'])

        # Check for conflicts
        if operation in ['update', 'delete']:
            conflict = self._check_conflict(
                Model, object_id, client_timestamp, last_sync_timestamp
            )
            if conflict:
                return self._handle_conflict(
                    model_name, object_id, data, conflict,
                    model_config['conflict_strategy']
                )

        # Apply the change
        with transaction.atomic():
            if operation == 'create':
                instance = self._create_object(Model, data)
            elif operation == 'update':
                instance = self._update_object(
                    Model, object_id, data, model_config['sync_fields']
                )
            elif operation == 'delete':
                self._delete_object(Model, object_id)
                instance = None
            else:
                raise ValueError(f"Unknown operation: {operation}")

        return {
            'status': 'success',
            'operation': operation,
            'model': model_name,
            'object_id': str(instance.id) if instance else object_id,
        }

    def _check_conflict(
        self,
        Model,
        object_id: str,
        client_timestamp: Optional[str],
        last_sync_timestamp: Optional[datetime]
    ) -> Optional[Dict[str, Any]]:
        """Check if there's a conflict with server data."""
        try:
            instance = Model.objects.get(id=object_id, user=self.user)

            # Check if server version was modified after client's last sync
            if hasattr(instance, 'updated_at') and last_sync_timestamp:
                if instance.updated_at > last_sync_timestamp:
                    return {
                        'server_version': self._serialize_instance(instance),
                        'server_timestamp': instance.updated_at,
                    }
        except ObjectDoesNotExist:
            return None

        return None

    def _handle_conflict(
        self,
        model_name: str,
        object_id: str,
        client_data: Dict[str, Any],
        conflict_info: Dict[str, Any],
        strategy: str
    ) -> Dict[str, Any]:
        """Handle a sync conflict based on the configured strategy."""

        # Record the conflict
        conflict = SyncConflict.objects.create(
            user=self.user,
            model_name=model_name,
            object_id=object_id,
            server_version=conflict_info['server_version'],
            client_version=client_data,
        )

        if strategy == 'server_wins':
            conflict.resolve('server_wins', conflict_info['server_version'])
            return {
                'status': 'conflict',
                'resolution': 'server_wins',
                'server_version': conflict_info['server_version'],
            }
        elif strategy == 'client_wins':
            conflict.resolve('client_wins', client_data)
            return {
                'status': 'success',
                'resolution': 'client_wins',
            }
        elif strategy == 'last_write_wins':
            # Compare timestamps
            client_ts = client_data.get('updated_at')
            server_ts = conflict_info['server_timestamp']
            if client_ts and client_ts > server_ts:
                conflict.resolve('client_wins', client_data)
                return {
                    'status': 'success',
                    'resolution': 'client_wins',
                }
            else:
                conflict.resolve('server_wins', conflict_info['server_version'])
                return {
                    'status': 'conflict',
                    'resolution': 'server_wins',
                    'server_version': conflict_info['server_version'],
                }
        else:
            # Manual resolution required
            return {
                'status': 'conflict',
                'conflict_id': str(conflict.id),
                'requires_manual_resolution': True,
            }

    def _create_object(self, Model, data: Dict[str, Any]):
        """Create a new object from sync data."""
        data['user'] = self.user
        return Model.objects.create(**data)

    def _update_object(
        self,
        Model,
        object_id: str,
        data: Dict[str, Any],
        allowed_fields: List[str]
    ):
        """Update an existing object with sync data."""
        instance = Model.objects.get(id=object_id, user=self.user)

        for field in allowed_fields:
            if field in data:
                setattr(instance, field, data[field])

        instance.save()
        return instance

    def _delete_object(self, Model, object_id: str):
        """Delete an object."""
        Model.objects.filter(id=object_id, user=self.user).delete()

    def _serialize_instance(self, instance) -> Dict[str, Any]:
        """Serialize a model instance to a dictionary."""
        data = {}
        for field in instance._meta.fields:
            value = getattr(instance, field.name)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            elif hasattr(value, 'id'):
                value = str(value.id)
            data[field.name] = value
        return data

    def prepare_pull(
        self,
        sync_log: SyncLog,
        last_sync_timestamp: Optional[datetime] = None,
        models: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Prepare data to be pulled by a client.

        Args:
            sync_log: The sync log for this operation
            last_sync_timestamp: When the client last synced
            models: List of models to sync (None for all)

        Returns:
            Dict with changes for the client
        """
        changes = {}
        sync_models = models or list(self.SYNCABLE_MODELS.keys())

        for model_name in sync_models:
            if model_name not in self.SYNCABLE_MODELS:
                continue

            model_config = self.SYNCABLE_MODELS[model_name]
            Model = apps.get_model(model_config['model_path'])

            queryset = Model.objects.filter(user=self.user)

            # Filter by last sync timestamp for incremental sync
            if last_sync_timestamp and hasattr(Model, 'updated_at'):
                queryset = queryset.filter(updated_at__gt=last_sync_timestamp)

            model_changes = []
            for instance in queryset:
                model_changes.append({
                    'operation': 'update',
                    'object_id': str(instance.id),
                    'data': self._serialize_instance(instance),
                    'timestamp': instance.updated_at.isoformat() if hasattr(
                        instance, 'updated_at'
                    ) else None,
                })
                sync_log.items_pulled += 1

            changes[model_name] = model_changes

        sync_log.last_sync_timestamp = timezone.now()
        sync_log.save()

        return {
            'changes': changes,
            'sync_timestamp': timezone.now().isoformat(),
        }

    def complete_sync(self, sync_log: SyncLog, success: bool = True, error: str = None):
        """
        Complete a sync operation.

        Args:
            sync_log: The sync log to complete
            success: Whether the sync was successful
            error: Error message if sync failed
        """
        if success:
            sync_log.mark_completed()
            logger.info(f"Completed sync {sync_log.id} successfully")
        else:
            sync_log.mark_failed(error)
            logger.error(f"Sync {sync_log.id} failed: {error}")

    def get_pending_conflicts(self) -> List[SyncConflict]:
        """Get all pending conflicts for the user."""
        return SyncConflict.objects.filter(
            user=self.user,
            resolution_status='pending'
        )

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        resolved_data: Optional[Dict[str, Any]] = None
    ) -> SyncConflict:
        """
        Resolve a sync conflict.

        Args:
            conflict_id: ID of the conflict to resolve
            resolution: Resolution strategy ('server_wins', 'client_wins', 'merged', 'manual')
            resolved_data: The final resolved data (required for 'merged' and 'manual')

        Returns:
            Updated SyncConflict instance
        """
        conflict = SyncConflict.objects.get(id=conflict_id, user=self.user)

        if resolution == 'server_wins':
            conflict.resolve('server_wins', conflict.server_version)
        elif resolution == 'client_wins':
            conflict.resolve('client_wins', conflict.client_version)
            # Apply client version to server
            model_config = self.SYNCABLE_MODELS.get(conflict.model_name)
            if model_config:
                Model = apps.get_model(model_config['model_path'])
                self._update_object(
                    Model,
                    conflict.object_id,
                    conflict.client_version,
                    model_config['sync_fields']
                )
        elif resolution in ['merged', 'manual']:
            if not resolved_data:
                raise ValueError("resolved_data is required for merged/manual resolution")
            conflict.resolve(resolution, resolved_data)
            # Apply resolved version
            model_config = self.SYNCABLE_MODELS.get(conflict.model_name)
            if model_config:
                Model = apps.get_model(model_config['model_path'])
                self._update_object(
                    Model,
                    conflict.object_id,
                    resolved_data,
                    model_config['sync_fields']
                )

        return conflict

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get the current sync status for the user.

        Returns:
            Dict with sync status information
        """
        last_sync = SyncLog.objects.filter(
            user=self.user,
            status='completed'
        ).first()

        pending_items = SyncQueue.objects.filter(
            user=self.user,
            is_processed=False
        ).count()

        pending_conflicts = SyncConflict.objects.filter(
            user=self.user,
            resolution_status='pending'
        ).count()

        return {
            'last_sync': last_sync.completed_at.isoformat() if last_sync else None,
            'last_sync_id': str(last_sync.id) if last_sync else None,
            'pending_items': pending_items,
            'pending_conflicts': pending_conflicts,
            'is_synced': pending_items == 0 and pending_conflicts == 0,
        }


def get_sync_manager(user) -> SyncManager:
    """Factory function to get a SyncManager instance for a user."""
    return SyncManager(user)
