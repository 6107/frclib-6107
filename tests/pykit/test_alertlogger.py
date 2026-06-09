"""Unit tests for alertlogger module using pytest framework."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.alertlogger import AlertLogger
from lib_6107.pykit.logtable import LogTable


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_network_table_instance():
    """Create a mock NetworkTableInstance."""
    with patch('lib_6107.pykit.alertlogger.NetworkTableInstance') as mock_nt:
        yield mock_nt


@pytest.fixture
def mock_string_array_subscriber():
    """Create a mock StringArraySubscriber."""
    subscriber = MagicMock()
    subscriber.get.return_value = []
    return subscriber


@pytest.fixture
def mock_log_table():
    """Create a mock LogTable."""
    return MagicMock(spec=LogTable)


@pytest.fixture
def reset_alert_logger():
    """Reset AlertLogger class state before and after each test."""
    AlertLogger.groups = []
    AlertLogger.error_subscribers = {}
    AlertLogger.warning_subscribers = {}
    AlertLogger.info_subscribers = {}
    yield
    AlertLogger.groups = []
    AlertLogger.error_subscribers = {}
    AlertLogger.warning_subscribers = {}
    AlertLogger.info_subscribers = {}


# ============================================================================
# Group Registration Tests
# ============================================================================

class TestAlertLoggerGroupRegistration:
    """Test AlertLogger group registration functionality."""

    def test_registers_single_group(self, reset_alert_logger):
        """Verify a single group can be registered."""
        AlertLogger.register_group("Drivetrain")

        assert "Drivetrain" in AlertLogger.groups

    def test_registers_multiple_groups(self, reset_alert_logger):
        """Verify multiple groups can be registered."""
        AlertLogger.register_group("Drivetrain")
        AlertLogger.register_group("Shooter")
        AlertLogger.register_group("Intake")

        assert len(AlertLogger.groups) == 3
        assert "Drivetrain" in AlertLogger.groups
        assert "Shooter" in AlertLogger.groups
        assert "Intake" in AlertLogger.groups

    def test_does_not_register_duplicate_group(self, reset_alert_logger):
        """Verify duplicate group registration is ignored."""
        AlertLogger.register_group("Drivetrain")
        AlertLogger.register_group("Drivetrain")

        assert AlertLogger.groups.count("Drivetrain") == 1

    def test_preserves_group_registration_order(self, reset_alert_logger):
        """Verify groups are registered in order."""
        AlertLogger.register_group("First")
        AlertLogger.register_group("Second")
        AlertLogger.register_group("Third")

        assert AlertLogger.groups == ["First", "Second", "Third"]

    @pytest.mark.parametrize("group_name", [
        "Drivetrain",
        "Shooter",
        "Intake",
        "Elevator",
        "Climber",
    ])
    def test_registers_various_group_names(self, reset_alert_logger, group_name):
        """Verify various group names can be registered."""
        AlertLogger.register_group(group_name)

        assert group_name in AlertLogger.groups


# ============================================================================
# Subscriber Creation Tests
# ============================================================================

class TestAlertLoggerSubscriberCreation:
    """Test AlertLogger subscriber creation."""

    def test_creates_error_subscriber_on_first_periodic(self, reset_alert_logger, mock_network_table_instance,
                                                        mock_log_table, mock_string_array_subscriber):
        """Verify error subscriber is created on first periodic call."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        assert "Drivetrain" in AlertLogger.error_subscribers

    def test_creates_warning_subscriber_on_first_periodic(self, reset_alert_logger, mock_network_table_instance,
                                                          mock_log_table, mock_string_array_subscriber):
        """Verify warning subscriber is created on first periodic call."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        assert "Drivetrain" in AlertLogger.warning_subscribers

    def test_creates_info_subscriber_on_first_periodic(self, reset_alert_logger, mock_network_table_instance,
                                                       mock_log_table, mock_string_array_subscriber):
        """Verify info subscriber is created on first periodic call."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        assert "Drivetrain" in AlertLogger.info_subscribers

    def test_creates_subscribers_for_multiple_groups(self, reset_alert_logger, mock_network_table_instance,
                                                     mock_log_table, mock_string_array_subscriber):
        """Verify subscribers are created for multiple groups."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.register_group("Shooter")
        AlertLogger.periodic(mock_log_table)

        assert len(AlertLogger.error_subscribers) == 2
        assert len(AlertLogger.warning_subscribers) == 2
        assert len(AlertLogger.info_subscribers) == 2

    def test_uses_correct_topic_paths_for_subscribers(self, reset_alert_logger, mock_network_table_instance,
                                                      mock_log_table, mock_string_array_subscriber):
        """Verify correct NetworkTables topic paths are used for subscribers."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        calls = [call[0][0] for call in mock_instance.getStringArrayTopic.call_args_list]
        assert "/SmartDashboard/Drivetrain/errors" in calls
        assert "/SmartDashboard/Drivetrain/warnings" in calls
        assert "/SmartDashboard/Drivetrain/info" in calls


# ============================================================================
# Subscriber Reuse Tests
# ============================================================================

class TestAlertLoggerSubscriberReuse:
    """Test AlertLogger subscriber reuse across periodic calls."""

    def test_reuses_error_subscriber_on_subsequent_periodic(self, reset_alert_logger, mock_network_table_instance,
                                                            mock_log_table, mock_string_array_subscriber):
        """Verify error subscriber is reused on subsequent periodic calls."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)
        first_subscriber = AlertLogger.error_subscribers["Drivetrain"]

        AlertLogger.periodic(mock_log_table)
        second_subscriber = AlertLogger.error_subscribers["Drivetrain"]

        assert first_subscriber is second_subscriber

    def test_reuses_all_subscribers_on_subsequent_calls(self, reset_alert_logger, mock_network_table_instance,
                                                        mock_log_table, mock_string_array_subscriber):
        """Verify all subscriber types are reused on subsequent periodic calls."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        first_error = AlertLogger.error_subscribers["Drivetrain"]
        first_warning = AlertLogger.warning_subscribers["Drivetrain"]
        first_info = AlertLogger.info_subscribers["Drivetrain"]

        AlertLogger.periodic(mock_log_table)

        assert AlertLogger.error_subscribers["Drivetrain"] is first_error
        assert AlertLogger.warning_subscribers["Drivetrain"] is first_warning
        assert AlertLogger.info_subscribers["Drivetrain"] is first_info


# ============================================================================
# Alert Logging Tests
# ============================================================================

class TestAlertLoggerAlertLogging:
    """Test AlertLogger alert logging functionality."""

    def test_logs_type_metadata(self, reset_alert_logger, mock_network_table_instance, mock_log_table,
                                mock_string_array_subscriber):
        """Verify type metadata is logged for each group."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Drivetrain/.type", "Alerts")

    def test_logs_empty_error_alerts(self, reset_alert_logger, mock_network_table_instance, mock_log_table,
                                     mock_string_array_subscriber):
        """Verify empty error alerts are logged."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Drivetrain/errors", [])

    def test_logs_single_error_alert(self, reset_alert_logger, mock_network_table_instance, mock_log_table,
                                     mock_string_array_subscriber):
        """Verify single error alert is logged."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.return_value = ["Motor fault detected"]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Drivetrain/errors", ["Motor fault detected"])

    def test_logs_multiple_error_alerts(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify multiple error alerts are logged."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.return_value = ["Motor fault", "Encoder error", "CAN bus failure"]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Drivetrain/errors", ["Motor fault", "Encoder error", "CAN bus failure"])

    def test_logs_warning_alerts(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify warning alerts are logged."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.return_value = ["Temperature high", "Voltage low"]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Shooter")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Shooter/warnings", ["Temperature high", "Voltage low"])

    def test_logs_info_alerts(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify info alerts are logged."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.return_value = ["System started", "Configuration loaded"]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Intake")
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_any_call("Intake/info", ["System started", "Configuration loaded"])

    def test_logs_alerts_for_multiple_groups(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify alerts are logged for multiple groups."""
        mock_instance = MagicMock()

        error_topic = MagicMock()
        error_subscriber = MagicMock()
        error_subscriber.get.return_value = ["Error 1"]
        error_topic.subscribe.return_value = error_subscriber

        warning_topic = MagicMock()
        warning_subscriber = MagicMock()
        warning_subscriber.get.return_value = ["Warning 1"]
        warning_topic.subscribe.return_value = warning_subscriber

        info_topic = MagicMock()
        info_subscriber = MagicMock()
        info_subscriber.get.return_value = ["Info 1"]
        info_topic.subscribe.return_value = info_subscriber

        def getStringArrayTopic_side_effect(path):
            if "errors" in path:
                return error_topic
            elif "warnings" in path:
                return warning_topic
            else:
                return info_topic

        mock_instance.getStringArrayTopic.side_effect = getStringArrayTopic_side_effect
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.register_group("Shooter")
        AlertLogger.periodic(mock_log_table)

        assert mock_log_table.put.call_count >= 8


# ============================================================================
# Periodic Method with No Groups Tests
# ============================================================================

class TestAlertLoggerPeriodicNoGroups:
    """Test AlertLogger periodic method with no registered groups."""

    def test_handles_periodic_with_no_registered_groups(self, reset_alert_logger, mock_log_table):
        """Verify periodic handles the case of no registered groups."""
        AlertLogger.periodic(mock_log_table)

        mock_log_table.put.assert_not_called()

    def test_handles_periodic_with_empty_groups_list(self, reset_alert_logger, mock_log_table):
        """Verify periodic handles empty groups list without error."""
        AlertLogger.groups = []
        AlertLogger.periodic(mock_log_table)

        assert True


# ============================================================================
# Periodic Method Update Frequency Tests
# ============================================================================

class TestAlertLoggerPeriodicFrequency:
    """Test AlertLogger periodic call frequency and alert retrieval."""

    def test_retrieves_alerts_on_each_periodic_call(self, reset_alert_logger, mock_network_table_instance,
                                                    mock_log_table):
        """Verify alerts are retrieved on each periodic call."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.return_value = ["Alert"]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")

        AlertLogger.periodic(mock_log_table)
        call_count_after_first = mock_subscriber.get.call_count

        AlertLogger.periodic(mock_log_table)
        call_count_after_second = mock_subscriber.get.call_count

        assert call_count_after_second > call_count_after_first

    def test_updates_alerts_on_periodic_call(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify alerts are updated on each periodic call."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_subscriber = MagicMock()
        mock_subscriber.get.side_effect = [
            ["Alert 1"],
            ["Alert 1"],
            ["Alert 1"],
            ["Alert 1", "Alert 2"],
            ["Alert 1", "Alert 2"],
            ["Alert 1", "Alert 2"],
        ]
        mock_topic.subscribe.return_value = mock_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")

        AlertLogger.periodic(mock_log_table)
        AlertLogger.periodic(mock_log_table)

        calls = [call[0][1] for call in mock_log_table.put.call_args_list if "errors" in str(call[0][0])]
        assert ["Alert 1"] in calls
        assert ["Alert 1", "Alert 2"] in calls


# ============================================================================
# Initial Subscriber Configuration Tests
# ============================================================================

class TestAlertLoggerInitialSubscriberConfiguration:
    """Test AlertLogger subscriber initialization with empty default."""

    def test_subscribes_with_empty_default(self, reset_alert_logger, mock_network_table_instance, mock_log_table,
                                           mock_string_array_subscriber):
        """Verify subscribers are created with empty default."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_topic.subscribe.assert_called()
        call_args_list = [call[0][0] for call in mock_topic.subscribe.call_args_list]
        assert all(arg == [] for arg in call_args_list)


# ============================================================================
# Alert Group Scope Tests
# ============================================================================

class TestAlertLoggerGroupScoping:
    """Test AlertLogger alert group isolation."""

    def test_maintains_separate_alerts_per_group(self, reset_alert_logger, mock_network_table_instance, mock_log_table):
        """Verify alerts are maintained separately for each group."""
        mock_instance = MagicMock()

        def create_subscriber_with_value(value):
            subscriber = MagicMock()
            subscriber.get.return_value = value
            return subscriber

        drivetrain_subscriber = create_subscriber_with_value(["DT Error"])
        shooter_subscriber = create_subscriber_with_value(["Shooter Error"])

        topic_side_effects = {}

        def getStringArrayTopic_side_effect(path):
            topic = MagicMock()
            if "Drivetrain" in path:
                topic.subscribe.return_value = drivetrain_subscriber
            elif "Shooter" in path:
                topic.subscribe.return_value = shooter_subscriber
            return topic

        mock_instance.getStringArrayTopic.side_effect = getStringArrayTopic_side_effect
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.register_group("Shooter")
        AlertLogger.periodic(mock_log_table)

        drivetrain_calls = [call for call in mock_log_table.put.call_args_list if "Drivetrain" in str(call)]
        shooter_calls = [call for call in mock_log_table.put.call_args_list if "Shooter" in str(call)]

        assert len(drivetrain_calls) >= 3
        assert len(shooter_calls) >= 3


# ============================================================================
# NetworkTables Instance Access Tests
# ============================================================================

class TestAlertLoggerNetworkTablesAccess:
    """Test AlertLogger NetworkTables instance access."""

    def test_uses_default_network_table_instance(self, reset_alert_logger, mock_network_table_instance, mock_log_table,
                                                 mock_string_array_subscriber):
        """Verify getDefault is called to access NetworkTableInstance."""
        mock_instance = MagicMock()
        mock_topic = MagicMock()
        mock_topic.subscribe.return_value = mock_string_array_subscriber
        mock_instance.getStringArrayTopic.return_value = mock_topic
        mock_network_table_instance.getDefault.return_value = mock_instance

        AlertLogger.register_group("Drivetrain")
        AlertLogger.periodic(mock_log_table)

        mock_network_table_instance.getDefault.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
