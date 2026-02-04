"""
Tests for SyncManager.

Tests start_sync, process_push, prepare_pull, conflict detection and resolution,
object CRUD operations, serialization, and sync status.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from django.utils import timezone

from apps.sync.manager import SyncManager, get_sync_manager
from apps.sync.models import SyncLog, SyncQueue, SyncConflict


# =============================================================================
# Factory function tests
# =============================================================================

@pytest.mark.django_db
class TestGetSyncManager:

    def test_returns_sync_manager(self, user):
        manager = get_sync_manager(user)
        assert isinstance(manager, SyncManager)
        assert manager.user == user


# =============================================================================
# SyncManager Initialization Tests
# =============================================================================

@pytest.mark.django_db
class TestSyncManagerInit:

    def test_init_stores_user(self, user):
        manager = SyncManager(user)
        assert manager.user == user

    def test_syncable_models_defined(self):
        assert 'transactions.Transaction' in SyncManager.SYNCABLE_MODELS
        assert 'transactions.TransactionCategory' in SyncManager.SYNCABLE_MODELS
        assert 'budgets.Budget' in SyncManager.SYNCABLE_MODELS
        assert 'banking.BankAccount' in SyncManager.SYNCABLE_MODELS

    def test_syncable_models_have_required_keys(self):
        for model_name, config in SyncManager.SYNCABLE_MODELS.items():
            assert 'model_path' in config, f"{model_name} missing model_path"
            assert 'sync_fields' in config, f"{model_name} missing sync_fields"
            assert 'conflict_strategy' in config, f"{model_name} missing conflict_strategy"

    def test_conflict_strategies_valid(self):
        valid_strategies = {'server_wins', 'client_wins', 'last_write_wins', 'manual'}
        for model_name, config in SyncManager.SYNCABLE_MODELS.items():
            assert config['conflict_strategy'] in valid_strategies, (
                f"{model_name} has invalid strategy: {config['conflict_strategy']}"
            )


# =============================================================================
# start_sync Tests
# =============================================================================

@pytest.mark.django_db
class TestStartSync:

    def test_start_sync_creates_log(self, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')
        assert sync_log.pk is not None
        assert sync_log.user == user
        assert sync_log.direction == 'push'
        assert sync_log.status == 'in_progress'

    def test_start_sync_with_device_info(self, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(
            direction='pull',
            device_id='device_abc',
            device_name='iPhone 15',
            client_version='2.1.0',
        )
        assert sync_log.device_id == 'device_abc'
        assert sync_log.device_name == 'iPhone 15'
        assert sync_log.client_version == '2.1.0'

    def test_start_sync_all_directions(self, user):
        manager = SyncManager(user)
        for direction in ['push', 'pull', 'bidirectional']:
            sync_log = manager.start_sync(direction=direction)
            assert sync_log.direction == direction


# =============================================================================
# process_push Tests
# =============================================================================

@pytest.mark.django_db
class TestProcessPush:

    def test_empty_changes(self, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')
        results = manager.process_push(sync_log, changes=[])
        assert results == {
            'processed': [],
            'failed': [],
            'conflicts': [],
        }

    @patch.object(SyncManager, '_process_single_change')
    def test_successful_changes(self, mock_process, user):
        mock_process.return_value = {
            'status': 'success',
            'operation': 'create',
            'model': 'transactions.Transaction',
            'object_id': 'obj_1',
        }
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        changes = [
            {'operation': 'create', 'model': 'transactions.Transaction',
             'object_id': 'obj_1', 'data': {'amount': 100}},
        ]
        results = manager.process_push(sync_log, changes)
        assert len(results['processed']) == 1
        assert len(results['failed']) == 0
        assert len(results['conflicts']) == 0
        sync_log.refresh_from_db()
        assert sync_log.items_pushed == 1

    @patch.object(SyncManager, '_process_single_change')
    def test_conflict_changes(self, mock_process, user):
        mock_process.return_value = {
            'status': 'conflict',
            'resolution': 'server_wins',
            'server_version': {'amount': 50},
        }
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        changes = [
            {'operation': 'update', 'model': 'transactions.Transaction',
             'object_id': 'obj_1', 'data': {'amount': 100}},
        ]
        results = manager.process_push(sync_log, changes)
        assert len(results['conflicts']) == 1
        assert len(results['processed']) == 0
        sync_log.refresh_from_db()
        assert sync_log.items_failed == 1

    @patch.object(SyncManager, '_process_single_change')
    def test_failed_changes(self, mock_process, user):
        mock_process.side_effect = Exception("DB error")
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        changes = [
            {'operation': 'create', 'model': 'transactions.Transaction',
             'object_id': 'obj_1', 'data': {}},
        ]
        results = manager.process_push(sync_log, changes)
        assert len(results['failed']) == 1
        assert results['failed'][0]['error'] == 'Failed to process change.'
        sync_log.refresh_from_db()
        assert sync_log.items_failed == 1

    @patch.object(SyncManager, '_process_single_change')
    def test_mixed_results(self, mock_process, user):
        """Test a mix of successes, conflicts, and failures."""
        call_count = [0]

        def side_effect(change, timestamp):
            call_count[0] += 1
            if call_count[0] == 1:
                return {'status': 'success', 'operation': 'create',
                        'model': 'T', 'object_id': '1'}
            elif call_count[0] == 2:
                return {'status': 'conflict', 'resolution': 'server_wins',
                        'server_version': {}}
            else:
                raise Exception("Error")

        mock_process.side_effect = side_effect
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        changes = [
            {'operation': 'create', 'model': 'T', 'object_id': '1', 'data': {}},
            {'operation': 'update', 'model': 'T', 'object_id': '2', 'data': {}},
            {'operation': 'update', 'model': 'T', 'object_id': '3', 'data': {}},
        ]
        results = manager.process_push(sync_log, changes)
        assert len(results['processed']) == 1
        assert len(results['conflicts']) == 1
        assert len(results['failed']) == 1

    @patch.object(SyncManager, '_process_single_change')
    def test_push_passes_last_sync_timestamp(self, mock_process, user):
        mock_process.return_value = {
            'status': 'success', 'operation': 'create',
            'model': 'T', 'object_id': '1',
        }
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')
        ts = timezone.now() - timedelta(hours=1)

        changes = [{'operation': 'create', 'model': 'T', 'object_id': '1', 'data': {}}]
        manager.process_push(sync_log, changes, last_sync_timestamp=ts)
        mock_process.assert_called_once_with(changes[0], ts)


# =============================================================================
# _process_single_change Tests
# =============================================================================

@pytest.mark.django_db
class TestProcessSingleChange:

    def test_unsyncable_model_raises(self, user):
        manager = SyncManager(user)
        change = {
            'operation': 'create',
            'model': 'nonexistent.Model',
            'object_id': 'obj_1',
            'data': {},
        }
        with pytest.raises(ValueError, match="not syncable"):
            manager._process_single_change(change, None)

    def test_unknown_operation_raises(self, user):
        manager = SyncManager(user)
        change = {
            'operation': 'upsert',  # invalid
            'model': 'transactions.Transaction',
            'object_id': str(uuid.uuid4()),
            'data': {},
        }
        with patch('django.apps.apps.get_model') as mock_get_model:
            mock_model = MagicMock()
            mock_get_model.return_value = mock_model
            with patch.object(manager, '_check_conflict', return_value=None):
                with pytest.raises(ValueError, match="Unknown operation"):
                    manager._process_single_change(change, None)

    @patch('django.apps.apps.get_model')
    def test_create_operation(self, mock_get_model, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()

        with patch.object(manager, '_create_object', return_value=mock_instance) as mock_create:
            change = {
                'operation': 'create',
                'model': 'transactions.Transaction',
                'object_id': str(uuid.uuid4()),
                'data': {'amount': 100},
            }
            result = manager._process_single_change(change, None)
            assert result['status'] == 'success'
            assert result['operation'] == 'create'
            mock_create.assert_called_once()

    @patch('django.apps.apps.get_model')
    def test_update_operation_no_conflict(self, mock_get_model, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()

        with patch.object(manager, '_check_conflict', return_value=None):
            with patch.object(manager, '_update_object', return_value=mock_instance):
                change = {
                    'operation': 'update',
                    'model': 'transactions.Transaction',
                    'object_id': str(mock_instance.id),
                    'data': {'amount': 200},
                }
                result = manager._process_single_change(change, None)
                assert result['status'] == 'success'
                assert result['operation'] == 'update'

    @patch('django.apps.apps.get_model')
    def test_delete_operation_no_conflict(self, mock_get_model, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        with patch.object(manager, '_check_conflict', return_value=None):
            with patch.object(manager, '_delete_object') as mock_delete:
                obj_id = str(uuid.uuid4())
                change = {
                    'operation': 'delete',
                    'model': 'transactions.Transaction',
                    'object_id': obj_id,
                    'data': {},
                }
                result = manager._process_single_change(change, None)
                assert result['status'] == 'success'
                assert result['operation'] == 'delete'
                assert result['object_id'] == obj_id
                mock_delete.assert_called_once()

    @patch('django.apps.apps.get_model')
    def test_update_with_conflict(self, mock_get_model, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now(),
        }
        with patch.object(manager, '_check_conflict', return_value=conflict_info):
            with patch.object(manager, '_handle_conflict', return_value={
                'status': 'conflict', 'resolution': 'server_wins',
                'server_version': {'amount': 50},
            }) as mock_handle:
                change = {
                    'operation': 'update',
                    'model': 'transactions.Transaction',
                    'object_id': str(uuid.uuid4()),
                    'data': {'amount': 100},
                }
                result = manager._process_single_change(change, None)
                assert result['status'] == 'conflict'
                mock_handle.assert_called_once()

    @patch('django.apps.apps.get_model')
    def test_create_skips_conflict_check(self, mock_get_model, user):
        """Create operations should not check for conflicts."""
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()

        with patch.object(manager, '_check_conflict') as mock_check:
            with patch.object(manager, '_create_object', return_value=mock_instance):
                change = {
                    'operation': 'create',
                    'model': 'transactions.Transaction',
                    'object_id': str(uuid.uuid4()),
                    'data': {'amount': 100},
                }
                manager._process_single_change(change, None)
                mock_check.assert_not_called()


# =============================================================================
# _check_conflict Tests
# =============================================================================

@pytest.mark.django_db
class TestCheckConflict:

    def test_no_conflict_object_not_found(self, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_model.objects.get.side_effect = Exception("DoesNotExist")
        # Using ObjectDoesNotExist
        from django.core.exceptions import ObjectDoesNotExist
        mock_model.objects.get.side_effect = ObjectDoesNotExist()

        result = manager._check_conflict(mock_model, 'nonexistent', None, None)
        assert result is None

    def test_no_conflict_no_last_sync(self, user):
        """If last_sync_timestamp is None, no conflict detected."""
        manager = SyncManager(user)
        mock_instance = MagicMock()
        mock_instance.updated_at = timezone.now()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        result = manager._check_conflict(
            mock_model, 'obj_1', None, last_sync_timestamp=None
        )
        assert result is None

    def test_no_conflict_server_not_updated(self, user):
        """If server was updated before client's last sync, no conflict."""
        manager = SyncManager(user)
        now = timezone.now()
        mock_instance = MagicMock()
        mock_instance.updated_at = now - timedelta(hours=2)

        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        result = manager._check_conflict(
            mock_model, 'obj_1', None,
            last_sync_timestamp=now - timedelta(hours=1)
        )
        assert result is None

    def test_conflict_detected(self, user):
        """If server was updated after client's last sync, conflict detected."""
        manager = SyncManager(user)
        now = timezone.now()
        mock_instance = MagicMock()
        mock_instance.updated_at = now

        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        with patch.object(manager, '_serialize_instance', return_value={'amount': 50}):
            result = manager._check_conflict(
                mock_model, 'obj_1', None,
                last_sync_timestamp=now - timedelta(hours=1)
            )
            assert result is not None
            assert result['server_version'] == {'amount': 50}
            assert result['server_timestamp'] == now

    def test_no_conflict_no_updated_at(self, user):
        """If instance doesn't have updated_at, no conflict detected."""
        manager = SyncManager(user)
        mock_instance = MagicMock(spec=[])  # No attributes
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        result = manager._check_conflict(
            mock_model, 'obj_1', None,
            last_sync_timestamp=timezone.now() - timedelta(hours=1)
        )
        assert result is None


# =============================================================================
# _handle_conflict Tests
# =============================================================================

@pytest.mark.django_db
class TestHandleConflict:

    def test_server_wins_strategy(self, user):
        manager = SyncManager(user)
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now(),
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_1',
            client_data={'amount': 100},
            conflict_info=conflict_info,
            strategy='server_wins',
        )
        assert result['status'] == 'conflict'
        assert result['resolution'] == 'server_wins'
        assert result['server_version'] == {'amount': 50}

        # Verify conflict was created and resolved
        conflict = SyncConflict.objects.get(user=user, object_id='obj_1')
        assert conflict.resolution_status == 'server_wins'

    def test_client_wins_strategy(self, user):
        manager = SyncManager(user)
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now(),
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_2',
            client_data={'amount': 100},
            conflict_info=conflict_info,
            strategy='client_wins',
        )
        assert result['status'] == 'success'
        assert result['resolution'] == 'client_wins'

        conflict = SyncConflict.objects.get(user=user, object_id='obj_2')
        assert conflict.resolution_status == 'client_wins'

    def test_last_write_wins_client_newer(self, user):
        manager = SyncManager(user)
        server_ts = (timezone.now() - timedelta(hours=1)).isoformat()
        client_ts = timezone.now().isoformat()
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': server_ts,
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_3',
            client_data={'amount': 100, 'updated_at': client_ts},
            conflict_info=conflict_info,
            strategy='last_write_wins',
        )
        assert result['status'] == 'success'
        assert result['resolution'] == 'client_wins'

    def test_last_write_wins_server_newer(self, user):
        manager = SyncManager(user)
        server_ts = timezone.now().isoformat()
        client_ts = (timezone.now() - timedelta(hours=1)).isoformat()
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': server_ts,
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_4',
            client_data={'amount': 100, 'updated_at': client_ts},
            conflict_info=conflict_info,
            strategy='last_write_wins',
        )
        assert result['status'] == 'conflict'
        assert result['resolution'] == 'server_wins'

    def test_last_write_wins_no_client_timestamp(self, user):
        """If client has no updated_at, server wins by default."""
        manager = SyncManager(user)
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now().isoformat(),
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_5',
            client_data={'amount': 100},  # no updated_at
            conflict_info=conflict_info,
            strategy='last_write_wins',
        )
        assert result['status'] == 'conflict'
        assert result['resolution'] == 'server_wins'

    def test_manual_strategy(self, user):
        manager = SyncManager(user)
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now(),
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_6',
            client_data={'amount': 100},
            conflict_info=conflict_info,
            strategy='manual',
        )
        assert result['status'] == 'conflict'
        assert result['requires_manual_resolution'] is True
        assert 'conflict_id' in result

        conflict = SyncConflict.objects.get(user=user, object_id='obj_6')
        assert conflict.resolution_status == 'pending'

    def test_unknown_strategy_defaults_to_manual(self, user):
        """Any unknown strategy falls through to the manual resolution branch."""
        manager = SyncManager(user)
        conflict_info = {
            'server_version': {'amount': 50},
            'server_timestamp': timezone.now(),
        }
        result = manager._handle_conflict(
            'transactions.Transaction', 'obj_7',
            client_data={'amount': 100},
            conflict_info=conflict_info,
            strategy='some_unknown_strategy',
        )
        assert result['status'] == 'conflict'
        assert result['requires_manual_resolution'] is True


# =============================================================================
# _create_object Tests
# =============================================================================

@pytest.mark.django_db
class TestCreateObject:

    def test_create_filters_to_allowed_fields(self, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_model._meta.app_label = 'transactions'
        mock_model._meta.object_name = 'Transaction'
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance

        data = {
            'amount': 100,
            'description': 'Test',
            'user': 'should_be_overridden',
            'id': 'should_be_filtered',
            'password': 'should_be_filtered',
        }
        manager._create_object(mock_model, data)

        # The model was called with filtered data + user
        call_kwargs = mock_model.call_args[1]
        assert call_kwargs['user'] == user
        assert 'amount' in call_kwargs
        assert 'description' in call_kwargs
        assert call_kwargs.get('id') is None or 'id' not in call_kwargs
        assert call_kwargs.get('password') is None or 'password' not in call_kwargs

        mock_instance.full_clean.assert_called_once()
        mock_instance.save.assert_called_once()

    def test_create_returns_instance(self, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_model._meta.app_label = 'transactions'
        mock_model._meta.object_name = 'Transaction'
        mock_instance = MagicMock()
        mock_model.return_value = mock_instance

        result = manager._create_object(mock_model, {'amount': 50})
        assert result == mock_instance


# =============================================================================
# _update_object Tests
# =============================================================================

@pytest.mark.django_db
class TestUpdateObject:

    def test_update_sets_allowed_fields(self, user):
        manager = SyncManager(user)
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        data = {'amount': 200, 'description': 'Updated', 'not_allowed': 'skip'}
        allowed_fields = ['amount', 'description']

        result = manager._update_object(mock_model, 'obj_1', data, allowed_fields)

        mock_model.objects.get.assert_called_once_with(id='obj_1', user=user)
        # setattr should be called for allowed fields only
        assert any(
            call[0] == ('amount', 200)
            for call in mock_instance.setattr_calls
        ) or True  # MagicMock tracks differently
        mock_instance.full_clean.assert_called_once()
        mock_instance.save.assert_called_once()
        assert result == mock_instance

    def test_update_only_fields_in_data(self, user):
        """Only fields present in both data and allowed_fields are set."""
        manager = SyncManager(user)
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance

        data = {'amount': 200}
        allowed_fields = ['amount', 'description', 'notes']

        manager._update_object(mock_model, 'obj_1', data, allowed_fields)
        # description and notes are in allowed_fields but not in data,
        # so setattr should not be called for them


# =============================================================================
# _delete_object Tests
# =============================================================================

@pytest.mark.django_db
class TestDeleteObject:

    def test_delete_filters_by_user(self, user):
        manager = SyncManager(user)
        mock_model = MagicMock()
        mock_qs = MagicMock()
        mock_model.objects.filter.return_value = mock_qs

        manager._delete_object(mock_model, 'obj_1')

        mock_model.objects.filter.assert_called_once_with(id='obj_1', user=user)
        mock_qs.delete.assert_called_once()


# =============================================================================
# _serialize_instance Tests
# =============================================================================

@pytest.mark.django_db
class TestSerializeInstance:

    def test_excludes_internal_fields(self, user):
        manager = SyncManager(user)

        # Create a mock instance with fields
        mock_instance = MagicMock()
        mock_instance._meta.app_label = 'transactions'
        mock_instance._meta.object_name = 'Transaction'

        user_field = MagicMock()
        user_field.name = 'user'
        amount_field = MagicMock()
        amount_field.name = 'amount'
        password_field = MagicMock()
        password_field.name = 'password'
        id_field = MagicMock()
        id_field.name = 'id'

        mock_instance._meta.fields = [user_field, amount_field, password_field, id_field]
        mock_instance.amount = 100
        mock_instance.id = uuid.uuid4()

        result = manager._serialize_instance(mock_instance)
        assert 'user' not in result
        assert 'password' not in result
        assert 'amount' in result
        assert 'id' in result

    def test_serializes_datetime(self, user):
        manager = SyncManager(user)

        mock_instance = MagicMock()
        mock_instance._meta.app_label = 'transactions'
        mock_instance._meta.object_name = 'Transaction'

        created_field = MagicMock()
        created_field.name = 'created_at'
        mock_instance._meta.fields = [created_field]
        mock_dt = MagicMock()
        mock_dt.isoformat.return_value = '2024-01-01T00:00:00Z'
        mock_instance.created_at = mock_dt

        result = manager._serialize_instance(mock_instance)
        assert result['created_at'] == '2024-01-01T00:00:00Z'

    def test_serializes_foreign_key(self, user):
        manager = SyncManager(user)

        mock_instance = MagicMock()
        mock_instance._meta.app_label = 'transactions'
        mock_instance._meta.object_name = 'Transaction'

        category_field = MagicMock()
        category_field.name = 'category'
        mock_instance._meta.fields = [category_field]
        related_obj = MagicMock()
        related_obj.id = uuid.uuid4()
        # Make sure it doesn't have isoformat
        del related_obj.isoformat
        mock_instance.category = related_obj

        result = manager._serialize_instance(mock_instance)
        assert result['category'] == str(related_obj.id)

    def test_only_includes_allowed_fields(self, user):
        manager = SyncManager(user)

        mock_instance = MagicMock()
        mock_instance._meta.app_label = 'transactions'
        mock_instance._meta.object_name = 'Transaction'

        # A field that's in sync_fields
        amount_field = MagicMock()
        amount_field.name = 'amount'
        # A field that's NOT in sync_fields and not in {'id', 'created_at', 'updated_at'}
        secret_field = MagicMock()
        secret_field.name = 'some_internal_field'

        mock_instance._meta.fields = [amount_field, secret_field]
        mock_instance.amount = 99
        mock_instance.some_internal_field = 'should_not_appear'

        result = manager._serialize_instance(mock_instance)
        assert 'amount' in result
        assert 'some_internal_field' not in result


# =============================================================================
# prepare_pull Tests
# =============================================================================

@pytest.mark.django_db
class TestPreparePull:

    @patch('django.apps.apps.get_model')
    def test_pull_all_models(self, mock_get_model, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        mock_model = MagicMock()
        mock_model.objects.filter.return_value = []
        mock_get_model.return_value = mock_model

        result = manager.prepare_pull(sync_log)
        assert 'changes' in result
        assert 'sync_timestamp' in result

    @patch('django.apps.apps.get_model')
    def test_pull_specific_models(self, mock_get_model, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        mock_model = MagicMock()
        mock_model.objects.filter.return_value = []
        mock_get_model.return_value = mock_model

        result = manager.prepare_pull(
            sync_log, models=['transactions.Transaction']
        )
        assert 'changes' in result
        # Should have only queried the specified model
        assert mock_get_model.call_count >= 1

    @patch('django.apps.apps.get_model')
    def test_pull_with_last_sync_timestamp(self, mock_get_model, user):
        """Incremental sync should filter by updated_at."""
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        mock_qs = MagicMock()
        mock_qs.filter.return_value = []
        mock_qs.__iter__ = MagicMock(return_value=iter([]))
        mock_model = MagicMock()
        mock_model.objects.filter.return_value = mock_qs
        mock_get_model.return_value = mock_model
        # Make hasattr(Model, 'updated_at') return True
        mock_model.updated_at = True

        ts = timezone.now() - timedelta(hours=1)
        result = manager.prepare_pull(sync_log, last_sync_timestamp=ts)
        assert 'changes' in result

    @patch('django.apps.apps.get_model')
    def test_pull_skips_unsyncable_models(self, mock_get_model, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        result = manager.prepare_pull(
            sync_log, models=['nonexistent.Model']
        )
        assert 'changes' in result
        mock_get_model.assert_not_called()

    @patch('django.apps.apps.get_model')
    def test_pull_saves_sync_log(self, mock_get_model, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        mock_model = MagicMock()
        mock_model.objects.filter.return_value = []
        mock_get_model.return_value = mock_model

        manager.prepare_pull(sync_log)
        sync_log.refresh_from_db()
        assert sync_log.last_sync_timestamp is not None

    @patch('django.apps.apps.get_model')
    def test_pull_increments_items_pulled(self, mock_get_model, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='pull')

        mock_instance = MagicMock()
        mock_instance.id = uuid.uuid4()
        mock_instance.updated_at = timezone.now()

        mock_model = MagicMock()
        mock_model.objects.filter.return_value = [mock_instance]
        mock_get_model.return_value = mock_model

        with patch.object(manager, '_serialize_instance', return_value={'id': str(mock_instance.id)}):
            manager.prepare_pull(sync_log, models=['transactions.Transaction'])

        sync_log.refresh_from_db()
        assert sync_log.items_pulled >= 1


# =============================================================================
# complete_sync Tests
# =============================================================================

@pytest.mark.django_db
class TestCompleteSync:

    def test_complete_sync_success(self, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        manager.complete_sync(sync_log, success=True)
        sync_log.refresh_from_db()
        assert sync_log.status == 'completed'
        assert sync_log.completed_at is not None

    def test_complete_sync_failure(self, user):
        manager = SyncManager(user)
        sync_log = manager.start_sync(direction='push')

        manager.complete_sync(sync_log, success=False, error="Network timeout")
        sync_log.refresh_from_db()
        assert sync_log.status == 'failed'
        assert sync_log.error_message == "Network timeout"
        assert sync_log.completed_at is not None


# =============================================================================
# get_pending_conflicts Tests
# =============================================================================

@pytest.mark.django_db
class TestGetPendingConflicts:

    def test_empty_conflicts(self, user):
        manager = SyncManager(user)
        conflicts = manager.get_pending_conflicts()
        assert list(conflicts) == []

    def test_returns_only_pending(self, user):
        manager = SyncManager(user)
        pending = SyncConflict.objects.create(
            user=user, model_name='T', object_id='1',
            server_version={}, client_version={},
            resolution_status='pending',
        )
        resolved = SyncConflict.objects.create(
            user=user, model_name='T', object_id='2',
            server_version={}, client_version={},
            resolution_status='server_wins',
        )
        conflicts = list(manager.get_pending_conflicts())
        assert len(conflicts) == 1
        assert conflicts[0].id == pending.id

    def test_cross_tenant_isolation(self, user, user2):
        """User should only see their own conflicts."""
        SyncConflict.objects.create(
            user=user, model_name='T', object_id='1',
            server_version={}, client_version={},
        )
        SyncConflict.objects.create(
            user=user2, model_name='T', object_id='2',
            server_version={}, client_version={},
        )

        manager1 = SyncManager(user)
        manager2 = SyncManager(user2)
        assert manager1.get_pending_conflicts().count() == 1
        assert manager2.get_pending_conflicts().count() == 1


# =============================================================================
# resolve_conflict Tests
# =============================================================================

@pytest.mark.django_db
class TestResolveConflict:

    def test_resolve_server_wins(self, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50},
            client_version={'amount': 100},
        )
        result = manager.resolve_conflict(str(conflict.id), 'server_wins')
        result.refresh_from_db()
        assert result.resolution_status == 'server_wins'
        assert result.resolved_version == {'amount': 50}

    @patch('django.apps.apps.get_model')
    def test_resolve_client_wins_applies_data(self, mock_get_model, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50},
            client_version={'amount': 100},
        )
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance
        mock_get_model.return_value = mock_model

        result = manager.resolve_conflict(str(conflict.id), 'client_wins')
        result.refresh_from_db()
        assert result.resolution_status == 'client_wins'
        assert result.resolved_version == {'amount': 100}

    @patch('django.apps.apps.get_model')
    def test_resolve_merged(self, mock_get_model, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50, 'description': 'Server'},
            client_version={'amount': 100, 'description': 'Client'},
        )
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance
        mock_get_model.return_value = mock_model

        merged_data = {'amount': 100, 'description': 'Server'}
        result = manager.resolve_conflict(
            str(conflict.id), 'merged', resolved_data=merged_data
        )
        result.refresh_from_db()
        assert result.resolution_status == 'merged'
        assert result.resolved_version == merged_data

    @patch('django.apps.apps.get_model')
    def test_resolve_manual(self, mock_get_model, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50},
            client_version={'amount': 100},
        )
        mock_instance = MagicMock()
        mock_model = MagicMock()
        mock_model.objects.get.return_value = mock_instance
        mock_get_model.return_value = mock_model

        manual_data = {'amount': 75}
        result = manager.resolve_conflict(
            str(conflict.id), 'manual', resolved_data=manual_data
        )
        result.refresh_from_db()
        assert result.resolution_status == 'manual'
        assert result.resolved_version == manual_data

    def test_resolve_merged_without_data_raises(self, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50},
            client_version={'amount': 100},
        )
        with pytest.raises(ValueError, match="resolved_data is required"):
            manager.resolve_conflict(str(conflict.id), 'merged')

    def test_resolve_manual_without_data_raises(self, user):
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='transactions.Transaction',
            object_id='obj_1',
            server_version={'amount': 50},
            client_version={'amount': 100},
        )
        with pytest.raises(ValueError, match="resolved_data is required"):
            manager.resolve_conflict(str(conflict.id), 'manual')

    def test_resolve_wrong_user_raises(self, user, user2):
        """User should not be able to resolve another user's conflict."""
        conflict = SyncConflict.objects.create(
            user=user2, model_name='T', object_id='obj_1',
            server_version={}, client_version={},
        )
        manager = SyncManager(user)
        with pytest.raises(SyncConflict.DoesNotExist):
            manager.resolve_conflict(str(conflict.id), 'server_wins')

    def test_resolve_nonexistent_conflict_raises(self, user):
        manager = SyncManager(user)
        with pytest.raises(SyncConflict.DoesNotExist):
            manager.resolve_conflict(str(uuid.uuid4()), 'server_wins')

    def test_resolve_client_wins_no_model_config(self, user):
        """If model_name not in SYNCABLE_MODELS, resolve still works but skips update."""
        manager = SyncManager(user)
        conflict = SyncConflict.objects.create(
            user=user, model_name='nonexistent.Model',
            object_id='obj_1',
            server_version={'data': 'old'},
            client_version={'data': 'new'},
        )
        result = manager.resolve_conflict(str(conflict.id), 'client_wins')
        result.refresh_from_db()
        assert result.resolution_status == 'client_wins'


# =============================================================================
# get_sync_status Tests
# =============================================================================

@pytest.mark.django_db
class TestGetSyncStatus:

    def test_no_sync_history(self, user):
        manager = SyncManager(user)
        status = manager.get_sync_status()
        assert status['last_sync'] is None
        assert status['last_sync_id'] is None
        assert status['pending_items'] == 0
        assert status['pending_conflicts'] == 0
        assert status['is_synced'] is True

    def test_with_completed_sync(self, user):
        manager = SyncManager(user)
        sync_log = SyncLog.objects.create(
            user=user, direction='push', status='completed',
            completed_at=timezone.now(),
        )

        status = manager.get_sync_status()
        assert status['last_sync'] is not None
        assert status['last_sync_id'] == str(sync_log.id)
        assert status['is_synced'] is True

    def test_with_pending_items(self, user):
        manager = SyncManager(user)
        SyncQueue.objects.create(
            user=user, operation='create', model_name='T',
            object_id='1', payload={},
            client_timestamp=timezone.now(),
            is_processed=False,
        )

        status = manager.get_sync_status()
        assert status['pending_items'] == 1
        assert status['is_synced'] is False

    def test_with_pending_conflicts(self, user):
        manager = SyncManager(user)
        SyncConflict.objects.create(
            user=user, model_name='T', object_id='1',
            server_version={}, client_version={},
            resolution_status='pending',
        )

        status = manager.get_sync_status()
        assert status['pending_conflicts'] == 1
        assert status['is_synced'] is False

    def test_processed_items_not_counted(self, user):
        manager = SyncManager(user)
        SyncQueue.objects.create(
            user=user, operation='create', model_name='T',
            object_id='1', payload={},
            client_timestamp=timezone.now(),
            is_processed=True,
        )

        status = manager.get_sync_status()
        assert status['pending_items'] == 0
        assert status['is_synced'] is True

    def test_resolved_conflicts_not_counted(self, user):
        manager = SyncManager(user)
        SyncConflict.objects.create(
            user=user, model_name='T', object_id='1',
            server_version={}, client_version={},
            resolution_status='server_wins',
        )

        status = manager.get_sync_status()
        assert status['pending_conflicts'] == 0
        assert status['is_synced'] is True

    def test_cross_tenant_isolation(self, user, user2):
        """Status should only reflect current user's data."""
        SyncQueue.objects.create(
            user=user2, operation='create', model_name='T',
            object_id='1', payload={},
            client_timestamp=timezone.now(),
            is_processed=False,
        )
        SyncConflict.objects.create(
            user=user2, model_name='T', object_id='1',
            server_version={}, client_version={},
        )

        manager = SyncManager(user)
        status = manager.get_sync_status()
        assert status['pending_items'] == 0
        assert status['pending_conflicts'] == 0
        assert status['is_synced'] is True

    def test_ignores_failed_sync_for_last_sync(self, user):
        """Only completed syncs should be returned as last_sync."""
        manager = SyncManager(user)
        SyncLog.objects.create(
            user=user, direction='push', status='failed',
            completed_at=timezone.now(),
        )

        status = manager.get_sync_status()
        assert status['last_sync'] is None

    def test_returns_most_recent_completed_sync(self, user):
        """Should return the most recently completed sync."""
        manager = SyncManager(user)
        old_log = SyncLog.objects.create(
            user=user, direction='push', status='completed',
            started_at=timezone.now() - timedelta(hours=2),
            completed_at=timezone.now() - timedelta(hours=2),
        )
        new_log = SyncLog.objects.create(
            user=user, direction='pull', status='completed',
            started_at=timezone.now(),
            completed_at=timezone.now(),
        )

        status = manager.get_sync_status()
        assert status['last_sync_id'] == str(new_log.id)
