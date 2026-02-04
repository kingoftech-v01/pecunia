"""Tests for src/services/notifications.py — NotificationService and related classes."""

import threading
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from services.notifications import (
    NotificationType, NotificationPriority, NotificationCategory,
    Notification, NotificationPreferences, NotificationService,
    DEFAULT_DURATIONS, NOTIFICATION_COLORS, MAX_NOTIFICATION_HISTORY,
    get_notification_service, notify, notify_info, notify_success,
    notify_warning, notify_error, show_notification, show_system_notification,
)


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_info(self):
        assert NotificationType.INFO.value == "info"

    def test_success(self):
        assert NotificationType.SUCCESS.value == "success"

    def test_warning(self):
        assert NotificationType.WARNING.value == "warning"

    def test_error(self):
        assert NotificationType.ERROR.value == "error"

    def test_is_str_enum(self):
        assert isinstance(NotificationType.INFO, str)


class TestNotificationPriority:
    """Tests for NotificationPriority enum."""

    def test_low(self):
        assert NotificationPriority.LOW == 0

    def test_normal(self):
        assert NotificationPriority.NORMAL == 1

    def test_high(self):
        assert NotificationPriority.HIGH == 2

    def test_urgent(self):
        assert NotificationPriority.URGENT == 3

    def test_ordering(self):
        assert NotificationPriority.LOW < NotificationPriority.URGENT


class TestNotificationCategory:
    """Tests for NotificationCategory enum."""

    def test_general(self):
        assert NotificationCategory.GENERAL.value == "general"

    def test_budget(self):
        assert NotificationCategory.BUDGET.value == "budget"

    def test_transaction(self):
        assert NotificationCategory.TRANSACTION.value == "transaction"

    def test_sync(self):
        assert NotificationCategory.SYNC.value == "sync"

    def test_security(self):
        assert NotificationCategory.SECURITY.value == "security"

    def test_system(self):
        assert NotificationCategory.SYSTEM.value == "system"


class TestDefaultDurations:
    """Tests for default notification durations."""

    def test_info_duration(self):
        assert DEFAULT_DURATIONS[NotificationType.INFO] == 4000

    def test_success_duration(self):
        assert DEFAULT_DURATIONS[NotificationType.SUCCESS] == 3000

    def test_warning_duration(self):
        assert DEFAULT_DURATIONS[NotificationType.WARNING] == 5000

    def test_error_duration(self):
        assert DEFAULT_DURATIONS[NotificationType.ERROR] == 7000


class TestNotificationColors:
    """Tests for notification color configuration."""

    def test_info_colors(self):
        colors = NOTIFICATION_COLORS[NotificationType.INFO]
        assert "background" in colors
        assert "text" in colors
        assert "icon" in colors

    def test_all_types_have_colors(self):
        for nt in NotificationType:
            assert nt in NOTIFICATION_COLORS


class TestNotification:
    """Tests for Notification dataclass."""

    def test_default_creation(self):
        n = Notification(title="Test", message="Hello")
        assert n.title == "Test"
        assert n.message == "Hello"
        assert n.notification_type == NotificationType.INFO
        assert n.category == NotificationCategory.GENERAL
        assert n.priority == NotificationPriority.NORMAL
        assert n.duration_ms is None
        assert n.dismissible is True
        assert n.action_text is None
        assert n.action_callback is None
        assert isinstance(n.timestamp, datetime)
        assert isinstance(n.id, str)
        assert n.data == {}

    def test_custom_creation(self):
        n = Notification(
            title="Alert",
            message="Budget exceeded",
            notification_type=NotificationType.ERROR,
            category=NotificationCategory.BUDGET,
            priority=NotificationPriority.URGENT,
            duration_ms=10000,
            dismissible=False,
            action_text="View",
        )
        assert n.notification_type == NotificationType.ERROR
        assert n.category == NotificationCategory.BUDGET
        assert n.duration_ms == 10000
        assert n.dismissible is False
        assert n.action_text == "View"

    def test_get_duration_custom(self):
        n = Notification(title="T", message="M", duration_ms=5000)
        assert n.get_duration() == 5000

    def test_get_duration_default(self):
        n = Notification(title="T", message="M", notification_type=NotificationType.WARNING)
        assert n.get_duration() == 5000

    def test_get_duration_fallback(self):
        n = Notification(title="T", message="M")
        assert n.get_duration() == DEFAULT_DURATIONS.get(NotificationType.INFO, 4000)


class TestNotificationPreferences:
    """Tests for NotificationPreferences dataclass."""

    def test_default_values(self):
        prefs = NotificationPreferences()
        assert prefs.enabled is True
        assert prefs.system_notifications_enabled is True
        assert prefs.in_app_notifications_enabled is True
        assert prefs.sound_enabled is True
        assert prefs.budget_alerts is True
        assert prefs.transaction_alerts is True
        assert prefs.sync_alerts is False
        assert prefs.security_alerts is True
        assert prefs.budget_warning_threshold == 80
        assert prefs.budget_critical_threshold == 95
        assert prefs.do_not_disturb is False
        assert prefs.dnd_start_hour == 22
        assert prefs.dnd_end_hour == 7
        assert prefs.max_visible_toasts == 3
        assert prefs.toast_position == "top-right"

    def test_custom_values(self):
        prefs = NotificationPreferences(
            enabled=False,
            budget_warning_threshold=75,
            toast_position="bottom-left",
        )
        assert prefs.enabled is False
        assert prefs.budget_warning_threshold == 75
        assert prefs.toast_position == "bottom-left"


class TestNotificationServiceSingleton:
    """Tests for NotificationService singleton pattern."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_singleton_same_instance(self):
        svc1 = NotificationService()
        svc2 = NotificationService()
        assert svc1 is svc2

    def test_singleton_thread_safe(self):
        results = []

        def create():
            results.append(NotificationService())

        threads = [threading.Thread(target=create) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is results[0] for r in results)


class TestNotificationServiceConfig:
    """Tests for NotificationService configuration."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_set_preferences(self):
        svc = NotificationService()
        prefs = NotificationPreferences(enabled=False)
        svc.set_preferences(prefs)
        assert svc.get_preferences().enabled is False

    def test_update_preference_allowed(self):
        svc = NotificationService()
        svc.update_preference("enabled", False)
        assert svc._preferences.enabled is False

    def test_update_preference_rejected(self):
        svc = NotificationService()
        svc.update_preference("nonexistent_key", True)
        # Should not raise but should be rejected

    def test_set_parent_widget(self):
        svc = NotificationService()
        widget = MagicMock()
        svc.set_parent_widget(widget)
        assert svc._parent_widget is widget


class TestNotificationServiceShouldShow:
    """Tests for notification filtering logic."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_disabled_returns_false(self):
        svc = NotificationService(preferences=NotificationPreferences(enabled=False))
        result = svc._should_show_notification(NotificationCategory.GENERAL)
        assert result is False

    def test_enabled_returns_true(self):
        svc = NotificationService(preferences=NotificationPreferences(enabled=True))
        result = svc._should_show_notification(NotificationCategory.GENERAL)
        assert result is True

    def test_budget_disabled(self):
        svc = NotificationService(preferences=NotificationPreferences(budget_alerts=False))
        result = svc._should_show_notification(NotificationCategory.BUDGET)
        assert result is False

    def test_transaction_disabled(self):
        svc = NotificationService(preferences=NotificationPreferences(transaction_alerts=False))
        result = svc._should_show_notification(NotificationCategory.TRANSACTION)
        assert result is False

    def test_sync_disabled_by_default(self):
        svc = NotificationService()
        result = svc._should_show_notification(NotificationCategory.SYNC)
        assert result is False

    def test_dnd_active_spans_midnight(self):
        svc = NotificationService(
            preferences=NotificationPreferences(
                do_not_disturb=True,
                dnd_start_hour=22,
                dnd_end_hour=7,
            )
        )
        with patch("services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 23, 0)
            assert svc._is_dnd_active() is True

    def test_dnd_not_active(self):
        svc = NotificationService(
            preferences=NotificationPreferences(
                do_not_disturb=True,
                dnd_start_hour=22,
                dnd_end_hour=7,
            )
        )
        with patch("services.notifications.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 1, 1, 12, 0)
            assert svc._is_dnd_active() is False


class TestNotificationServiceNotify:
    """Tests for notification sending."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_notify_returns_id(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify("Test", "Message")
        assert result is not None

    def test_notify_disabled_returns_none(self):
        svc = NotificationService(preferences=NotificationPreferences(enabled=False))
        result = svc.notify("Test", "Message")
        assert result is None

    def test_notify_adds_to_history(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        svc.notify("Test", "Message")
        assert len(svc.get_history()) == 1

    def test_notify_calls_callbacks(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        cb = MagicMock()
        svc.on_notification(cb)
        svc.notify("Test", "Message")
        cb.assert_called_once()

    def test_info_convenience(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.info("Title", "Msg")
        assert result is not None

    def test_success_convenience(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.success("Title", "Msg")
        assert result is not None

    def test_warning_convenience(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.warning("Title", "Msg")
        assert result is not None

    def test_error_convenience(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.error("Title", "Msg")
        assert result is not None

    def test_system_only(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        svc.notify("Test", "Message", system_only=True)
        svc._show_system_notification.assert_called_once()
        svc._queue_toast_notification.assert_not_called()

    def test_toast_only(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        svc.notify("Test", "Message", toast_only=True)
        svc._show_system_notification.assert_not_called()
        svc._queue_toast_notification.assert_called_once()


class TestNotificationServiceSpecialized:
    """Tests for specialized notification methods."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_budget_warning(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_budget_warning("Food", 800, 1000)
        assert result is not None

    def test_budget_critical(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_budget_warning("Food", 960, 1000)
        assert result is not None

    def test_budget_warning_below_threshold(self):
        svc = NotificationService()
        result = svc.notify_budget_warning("Food", 100, 1000)
        assert result is None

    def test_budget_warning_disabled(self):
        svc = NotificationService(
            preferences=NotificationPreferences(budget_alerts=False)
        )
        result = svc.notify_budget_warning("Food", 900, 1000)
        assert result is None

    def test_budget_exceeded(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_budget_exceeded("Food", 50)
        assert result is not None

    def test_budget_exceeded_disabled(self):
        svc = NotificationService(
            preferences=NotificationPreferences(budget_alerts=False)
        )
        result = svc.notify_budget_exceeded("Food", 50)
        assert result is None

    def test_sync_started(self):
        svc = NotificationService(
            preferences=NotificationPreferences(sync_alerts=True)
        )
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_sync_started()
        assert result is not None

    def test_sync_started_disabled(self):
        svc = NotificationService()  # sync_alerts=False by default
        result = svc.notify_sync_started()
        assert result is None

    def test_sync_completed_success(self):
        svc = NotificationService(
            preferences=NotificationPreferences(sync_alerts=True)
        )
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_sync_completed(10)
        assert result is not None

    def test_sync_completed_with_failures(self):
        svc = NotificationService(
            preferences=NotificationPreferences(sync_alerts=True)
        )
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_sync_completed(10, failed_count=2, duration_ms=5000)
        assert result is not None

    def test_sync_failed(self):
        svc = NotificationService(
            preferences=NotificationPreferences(sync_alerts=True)
        )
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_sync_failed("Network error")
        assert result is not None

    def test_sync_conflict(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_sync_conflict(3)
        assert result is not None

    def test_new_transaction(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_new_transaction("Coffee", -5.50)
        assert result is not None

    def test_new_transaction_disabled(self):
        svc = NotificationService(
            preferences=NotificationPreferences(transaction_alerts=False)
        )
        result = svc.notify_new_transaction("Coffee", -5.50)
        assert result is None

    def test_security_alert(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        result = svc.notify_security_alert("Login Alert", "New login detected")
        assert result is not None

    def test_security_alert_disabled(self):
        svc = NotificationService(
            preferences=NotificationPreferences(security_alerts=False)
        )
        result = svc.notify_security_alert("Test", "Test")
        assert result is None


class TestNotificationServiceHistory:
    """Tests for notification history management."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_get_history_empty(self):
        svc = NotificationService()
        assert svc.get_history() == []

    def test_get_history_limit(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        for i in range(10):
            svc.notify("Test", f"Message {i}")
        assert len(svc.get_history(limit=5)) == 5

    def test_clear_history(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        svc.notify("Test", "Message")
        svc.clear_history()
        assert len(svc.get_history()) == 0


class TestNotificationServiceCallbacks:
    """Tests for callback management."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_on_notification_callback(self):
        svc = NotificationService()
        svc._show_system_notification = MagicMock()
        svc._queue_toast_notification = MagicMock()
        cb = MagicMock()
        svc.on_notification(cb)
        svc.notify("Test", "Message")
        cb.assert_called_once()
        arg = cb.call_args[0][0]
        assert isinstance(arg, Notification)

    def test_on_action_callback(self):
        svc = NotificationService()
        cb = MagicMock()
        svc.on_action(cb)
        assert cb in svc._on_action

    def test_remove_callback(self):
        svc = NotificationService()
        cb = MagicMock()
        svc.on_notification(cb)
        svc.remove_callback(cb)
        assert cb not in svc._on_notification


class TestNotificationServiceUtility:
    """Tests for utility methods."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        yield
        NotificationService._instance = None

    def test_get_active_count(self):
        svc = NotificationService()
        assert svc.get_active_count() == 0

    def test_get_queue_size(self):
        svc = NotificationService()
        assert svc.get_queue_size() == 0

    def test_dismiss_not_found(self):
        svc = NotificationService()
        assert svc.dismiss("nonexistent") is False

    def test_dismiss_all_empty(self):
        svc = NotificationService()
        svc.dismiss_all()  # Should not raise


class TestModuleLevelFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        NotificationService._instance = None
        import services.notifications as mod
        mod._notification_service = None
        yield
        NotificationService._instance = None
        mod._notification_service = None

    def test_get_notification_service(self):
        svc = get_notification_service()
        assert isinstance(svc, NotificationService)

    def test_get_notification_service_cached(self):
        svc1 = get_notification_service()
        svc2 = get_notification_service()
        assert svc1 is svc2

    def test_notify_function(self):
        with patch.object(NotificationService, 'notify', return_value="id1") as mock:
            result = notify("Title", "Msg")
            mock.assert_called_once()

    def test_notify_info_function(self):
        with patch.object(NotificationService, 'info', return_value="id1") as mock:
            result = notify_info("Title", "Msg")
            mock.assert_called_once()

    def test_notify_success_function(self):
        with patch.object(NotificationService, 'success', return_value="id1") as mock:
            result = notify_success("Title", "Msg")
            mock.assert_called_once()

    def test_notify_warning_function(self):
        with patch.object(NotificationService, 'warning', return_value="id1") as mock:
            result = notify_warning("Title", "Msg")
            mock.assert_called_once()

    def test_notify_error_function(self):
        with patch.object(NotificationService, 'error', return_value="id1") as mock:
            result = notify_error("Title", "Msg")
            mock.assert_called_once()

    def test_show_notification_function(self):
        with patch.object(NotificationService, 'notify', return_value="id1") as mock:
            result = show_notification("Title", "Msg", "warning")
            mock.assert_called_once()

    def test_show_notification_default_type(self):
        with patch.object(NotificationService, 'notify', return_value="id1") as mock:
            show_notification("Title", "Msg")
            call_args = mock.call_args
            assert call_args[0][2] == NotificationType.INFO

    def test_show_system_notification_function(self):
        with patch.object(NotificationService, 'notify', return_value="id1") as mock:
            result = show_system_notification("Title", "Msg")
            mock.assert_called_once()
            assert mock.call_args[1].get("system_only") is True
