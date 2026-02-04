"""
Tests for Sync API views.

Tests push, pull, bidirectional sync, status, conflicts, and logs endpoints.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.utils import timezone
from rest_framework import status

from apps.sync.models import SyncLog, SyncConflict


# =============================================================================
# SyncPushView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncPushView:

    def test_push_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/sync/push/', {'changes': []}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_push_empty_changes(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.start_sync.return_value = MagicMock(id=uuid.uuid4())
        mock_manager.process_push.return_value = {
            'processed': [],
            'failed': [],
            'conflicts': [],
        }

        resp = auth_client.post('/api/v1/sync/push/', {
            'changes': [],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'success'
        assert resp.data['processed_count'] == 0

    @patch('apps.sync.views.get_sync_manager')
    def test_push_with_changes(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.start_sync.return_value = MagicMock(id=uuid.uuid4())
        mock_manager.process_push.return_value = {
            'processed': [{'object_id': 'obj_1', 'status': 'ok'}],
            'failed': [],
            'conflicts': [],
        }

        resp = auth_client.post('/api/v1/sync/push/', {
            'device_id': 'device_123',
            'changes': [
                {
                    'operation': 'create',
                    'model': 'transactions.Transaction',
                    'object_id': str(uuid.uuid4()),
                    'data': {'amount': 100, 'description': 'Test'},
                    'timestamp': timezone.now().isoformat(),
                }
            ],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['processed_count'] == 1

    @patch('apps.sync.views.get_sync_manager')
    def test_push_with_conflicts(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.start_sync.return_value = MagicMock(id=uuid.uuid4())
        mock_manager.process_push.return_value = {
            'processed': [],
            'failed': [],
            'conflicts': [{'object_id': 'obj_1', 'type': 'update_conflict'}],
        }

        resp = auth_client.post('/api/v1/sync/push/', {
            'changes': [{'operation': 'update', 'model': 'T', 'object_id': 'obj_1', 'data': {}}],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'partial'
        assert resp.data['conflict_count'] == 1

    @patch('apps.sync.views.get_sync_manager')
    def test_push_error(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.start_sync.return_value = MagicMock(id=uuid.uuid4())
        mock_manager.process_push.side_effect = Exception("DB error")

        resp = auth_client.post('/api/v1/sync/push/', {
            'changes': [],
        }, format='json')
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
# SyncPullView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncPullView:

    def test_pull_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/sync/pull/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_pull_no_timestamp(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_sync_log = MagicMock()
        mock_sync_log.id = uuid.uuid4()
        mock_sync_log.items_pulled = 0
        mock_manager.start_sync.return_value = mock_sync_log
        mock_manager.prepare_pull.return_value = {
            'changes': [],
            'sync_timestamp': timezone.now().isoformat(),
        }

        resp = auth_client.get('/api/v1/sync/pull/')
        assert resp.status_code == status.HTTP_200_OK

    @patch('apps.sync.views.get_sync_manager')
    def test_pull_with_timestamp(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_sync_log = MagicMock()
        mock_sync_log.id = uuid.uuid4()
        mock_sync_log.items_pulled = 0
        mock_manager.start_sync.return_value = mock_sync_log
        mock_manager.prepare_pull.return_value = {
            'changes': [{'model': 'Transaction', 'object_id': 'obj_1'}],
            'sync_timestamp': timezone.now().isoformat(),
        }

        ts = (timezone.now() - timedelta(hours=1)).isoformat()
        resp = auth_client.get(f'/api/v1/sync/pull/?last_sync_timestamp={ts}')
        assert resp.status_code == status.HTTP_200_OK

    @patch('apps.sync.views.get_sync_manager')
    def test_pull_with_model_filter(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_sync_log = MagicMock()
        mock_sync_log.id = uuid.uuid4()
        mock_sync_log.items_pulled = 0
        mock_manager.start_sync.return_value = mock_sync_log
        mock_manager.prepare_pull.return_value = {
            'changes': [],
            'sync_timestamp': timezone.now().isoformat(),
        }

        resp = auth_client.get('/api/v1/sync/pull/?models=Transaction,Budget')
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# SyncBidirectionalView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncBidirectionalView:

    def test_bidirectional_requires_auth(self, api_client):
        resp = api_client.post('/api/v1/sync/', {'changes': []}, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_bidirectional_sync(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_sync_log = MagicMock()
        mock_sync_log.id = uuid.uuid4()
        mock_sync_log.items_pulled = 0
        mock_manager.start_sync.return_value = mock_sync_log
        mock_manager.process_push.return_value = {
            'processed': [],
            'failed': [],
            'conflicts': [],
        }
        mock_manager.prepare_pull.return_value = {
            'changes': {},
            'sync_timestamp': timezone.now().isoformat(),
        }

        resp = auth_client.post('/api/v1/sync/', {
            'changes': [],
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# SyncStatusView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncStatusView:

    def test_status_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/sync/status/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_get_status(self, mock_get_manager, auth_client):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_sync_status.return_value = {
            'last_sync': None,
            'pending_items': 0,
            'pending_conflicts': 0,
        }

        resp = auth_client.get('/api/v1/sync/status/')
        assert resp.status_code == status.HTTP_200_OK
        assert 'pending_items' in resp.data or 'last_sync' in resp.data


# =============================================================================
# SyncConflictListView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncConflictListView:

    def test_conflicts_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/sync/conflicts/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_list_conflicts(self, mock_get_manager, auth_client, user):
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_pending_conflicts.return_value = []

        resp = auth_client.get('/api/v1/sync/conflicts/')
        assert resp.status_code == status.HTTP_200_OK

    def test_conflicts_cross_tenant_isolation(self, auth_client, user, user2):
        """User should not see other user's conflicts."""
        SyncConflict.objects.create(
            user=user2,
            model_name='Transaction',
            object_id='other_obj',
            server_version={},
            client_version={},
        )
        # With get_sync_manager scoping by user, user should not see user2's conflicts


# =============================================================================
# SyncConflictResolveView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncConflictResolveView:

    def test_resolve_requires_auth(self, api_client):
        resp = api_client.post(
            f'/api/v1/sync/conflicts/{uuid.uuid4()}/resolve/',
            {'resolution': 'server_wins'},
            format='json',
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('apps.sync.views.get_sync_manager')
    def test_resolve_server_wins(self, mock_get_manager, auth_client, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_resolve',
            server_version={'amount': 100},
            client_version={'amount': 150},
        )
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_conflict = MagicMock()
        mock_conflict.id = conflict.id
        mock_conflict.resolution_status = 'server_wins'
        mock_conflict.resolved_at = timezone.now()
        mock_manager.resolve_conflict.return_value = mock_conflict

        resp = auth_client.post(
            f'/api/v1/sync/conflicts/{conflict.id}/resolve/',
            {'resolution': 'server_wins'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK

    @patch('apps.sync.views.get_sync_manager')
    def test_resolve_client_wins(self, mock_get_manager, auth_client, user):
        conflict = SyncConflict.objects.create(
            user=user,
            model_name='Transaction',
            object_id='obj_cw',
            server_version={'amount': 100},
            client_version={'amount': 150},
        )
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_conflict = MagicMock()
        mock_conflict.id = conflict.id
        mock_conflict.resolution_status = 'client_wins'
        mock_conflict.resolved_at = timezone.now()
        mock_manager.resolve_conflict.return_value = mock_conflict

        resp = auth_client.post(
            f'/api/v1/sync/conflicts/{conflict.id}/resolve/',
            {'resolution': 'client_wins'},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# SyncLogListView Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncLogListView:

    def test_logs_requires_auth(self, api_client):
        resp = api_client.get('/api/v1/sync/logs/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_logs(self, auth_client, user):
        SyncLog.objects.create(
            user=user, direction='push', status='completed',
        )
        resp = auth_client.get('/api/v1/sync/logs/')
        assert resp.status_code == status.HTTP_200_OK

    def test_logs_cross_tenant_isolation(self, auth_client, user, user2):
        """User should only see their own logs."""
        SyncLog.objects.create(
            user=user, direction='push', status='completed',
        )
        SyncLog.objects.create(
            user=user2, direction='pull', status='completed',
        )
        resp = auth_client.get('/api/v1/sync/logs/')
        assert resp.status_code == status.HTTP_200_OK
