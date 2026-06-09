"""Unit tests for loggednetworkboolean module using pytest framework."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.networktables.loggednetworkboolean import LoggedNetworkBoolean


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_network_table_instance():
    """Create a mock NetworkTableInstance."""
    with patch('lib_6107.pykit.networktables.loggednetworkboolean.NetworkTableInstance') as mock_nt:
        yield mock_nt


@pytest.fixture
def mock_boolean_entry():
    """Create a mock BooleanEntry."""
    return MagicMock()


@pytest.fixture
def mock_boolean_topic(mock_boolean_entry):
    """Create a mock BooleanTopic that returns mock_boolean_entry."""
    mock_topic = MagicMock()
    mock_topic.getEntry.return_value = mock_boolean_entry
    return mock_topic


@pytest.fixture
def mock_logger():
    """Create a mock Logger."""
    with patch('lib_6107.pykit.networktables.loggednetworkvalue.Logger') as logger:
        yield logger


@pytest.fixture
def setup_network_table_instance(mock_network_table_instance, mock_boolean_topic):
    """Setup the mock NetworkTableInstance chain for LoggedNetworkBoolean initialization."""
    mock_instance = MagicMock()
    mock_instance.getBooleanTopic.return_value = mock_boolean_topic
    mock_network_table_instance.getDefault.return_value = mock_instance
    return mock_network_table_instance


@pytest.fixture
def logged_boolean_true(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkBoolean with True default."""
    return LoggedNetworkBoolean("TestKey", default=True)


@pytest.fixture
def logged_boolean_false(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkBoolean with False default."""
    return LoggedNetworkBoolean("TestKey", default=False)


@pytest.fixture
def logged_boolean_no_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkBoolean without specifying default."""
    return LoggedNetworkBoolean("TestKey")


# ============================================================================
# Initialization Tests
# ============================================================================

class TestLoggedNetworkBooleanInitialization:
    """Test LoggedNetworkBoolean initialization behavior."""

    def test_creates_boolean_entry_via_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify __init__ creates a BooleanEntry through NetworkTableInstance chain."""
        key = "Intake/Enabled"
        default = True

        boolean_value = LoggedNetworkBoolean(key, default)

        setup_network_table_instance.getDefault.assert_called_once()

    def test_retrieves_boolean_topic_with_correct_key(self, setup_network_table_instance, mock_logger):
        """Verify __init__ retrieves BooleanTopic with the provided key."""
        key = "Intake/Enabled"
        default = True
        mock_instance = setup_network_table_instance.getDefault.return_value

        boolean_value = LoggedNetworkBoolean(key, default)

        mock_instance.getBooleanTopic.assert_called_once_with(key)

    def test_calls_get_entry_with_default_value(self, setup_network_table_instance, mock_logger):
        """Verify __init__ calls getEntry with default value."""
        key = "Intake/Enabled"
        default = True
        mock_topic = setup_network_table_instance.getDefault.return_value.getBooleanTopic.return_value

        boolean_value = LoggedNetworkBoolean(key, default)

        mock_topic.getEntry.assert_called_once_with(default)

    def test_stores_entry_reference(self, setup_network_table_instance, mock_logger, mock_boolean_entry):
        """Verify __init__ stores the BooleanEntry reference."""
        boolean_value = LoggedNetworkBoolean("TestKey", True)

        assert boolean_value._entry == mock_boolean_entry

    def test_initializes_with_true_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization with True default value."""
        boolean_value = LoggedNetworkBoolean("enabled", True)

        assert boolean_value._default is True

    def test_initializes_with_false_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization with False default value."""
        boolean_value = LoggedNetworkBoolean("disabled", False)

        assert boolean_value._default is False

    def test_uses_false_default_when_not_specified(self, setup_network_table_instance, mock_logger):
        """Verify initialization uses False as default when not provided."""
        boolean_value = LoggedNetworkBoolean("TestKey")

        assert boolean_value._default is False

    @pytest.mark.parametrize("key", [
        "SimpleKey",
        "/SmartDashboard/Debug/Enabled",
        "Subsystem/Running",
        "Robot/State/HasBall",
        "Config/Vision",
    ])
    def test_handles_various_key_formats(self, setup_network_table_instance, mock_logger, key):
        """Verify initialization handles various key formats."""
        boolean_value = LoggedNetworkBoolean(key, True)

        assert boolean_value._key == key

    @pytest.mark.parametrize("key,default", [
        ("debug_mode", True),
        ("intake_running", False),
        ("has_note", True),
        ("motor_enabled", False),
        ("vision_enabled", True),
    ])
    def test_initialization_with_different_values(self, setup_network_table_instance, mock_logger, key, default):
        """Verify initialization with various key and default combinations."""
        boolean_value = LoggedNetworkBoolean(key, default)

        assert boolean_value._key == key
        assert boolean_value._default is default


# ============================================================================
# Entry Type Tests
# ============================================================================

class TestLoggedNetworkBooleanEntryType:
    """Test that LoggedNetworkBoolean creates correct entry types."""

    def test_creates_boolean_entry_not_other_types(self, setup_network_table_instance, mock_logger):
        """Verify the entry type is specifically BooleanEntry."""
        boolean_value = LoggedNetworkBoolean("TestKey", True)

        setup_network_table_instance.getDefault.return_value.getBooleanTopic.assert_called_once()
        setup_network_table_instance.getDefault.return_value.getDoubleTopic.assert_not_called()

    def test_boolean_entry_created_for_true_default(self, setup_network_table_instance, mock_logger):
        """Verify BooleanEntry created when default is True."""
        boolean_value = LoggedNetworkBoolean("TestKey", True)

        assert setup_network_table_instance.getDefault.return_value.getBooleanTopic.called

    def test_boolean_entry_created_for_false_default(self, setup_network_table_instance, mock_logger):
        """Verify BooleanEntry created when default is False."""
        boolean_value = LoggedNetworkBoolean("TestKey", False)

        assert setup_network_table_instance.getDefault.return_value.getBooleanTopic.called


# ============================================================================
# Parent Class Integration Tests
# ============================================================================

class TestLoggedNetworkBooleanParentIntegration:
    """Test LoggedNetworkBoolean integration with LoggedNetworkValue parent class."""

    def test_inherits_value_property_from_parent(self, logged_boolean_true):
        """Verify value property is inherited from parent class."""
        logged_boolean_true._value = False

        assert logged_boolean_true.value is False

    def test_inherits_value_property_setter(self, logged_boolean_true):
        """Verify value property setter is inherited from parent class."""
        logged_boolean_true.value = False

        assert logged_boolean_true._value is False

    def test_inherits_callable_interface(self, logged_boolean_true):
        """Verify callable interface is inherited from parent class."""
        logged_boolean_true._value = True

        result = logged_boolean_true()

        assert result is True

    def test_inherits_to_log_method(self, logged_boolean_true):
        """Verify to_log method is inherited from parent class."""
        assert hasattr(logged_boolean_true, 'to_log')
        assert callable(logged_boolean_true.to_log)

    def test_inherits_from_log_method(self, logged_boolean_true):
        """Verify from_log method is inherited from parent class."""
        assert hasattr(logged_boolean_true, 'from_log')
        assert callable(logged_boolean_true.from_log)

    def test_inherits_periodic_method(self, logged_boolean_true):
        """Verify periodic method is inherited from parent class."""
        assert hasattr(logged_boolean_true, 'periodic')
        assert callable(logged_boolean_true.periodic)

    def test_inherits_set_default_method(self, logged_boolean_true):
        """Verify set_default method is inherited from parent class."""
        assert hasattr(logged_boolean_true, 'set_default')
        assert callable(logged_boolean_true.set_default)


# ============================================================================
# Boolean Value Tests
# ============================================================================

class TestLoggedNetworkBooleanValues:
    """Test LoggedNetworkBoolean boolean value handling."""

    def test_stores_true_value(self, logged_boolean_false):
        """Verify True value is stored correctly."""
        logged_boolean_false.value = True

        assert logged_boolean_false.value is True

    def test_stores_false_value(self, logged_boolean_true):
        """Verify False value is stored correctly."""
        logged_boolean_true.value = False

        assert logged_boolean_true.value is False

    def test_returns_boolean_type_true(self, logged_boolean_false):
        """Verify returned value is boolean type when True."""
        logged_boolean_false.value = True

        assert isinstance(logged_boolean_false.value, bool)
        assert logged_boolean_false.value is True

    def test_returns_boolean_type_false(self, logged_boolean_true):
        """Verify returned value is boolean type when False."""
        logged_boolean_true.value = False

        assert isinstance(logged_boolean_true.value, bool)
        assert logged_boolean_true.value is False

    def test_boolean_value_not_converted_from_truthy(self, logged_boolean_false):
        """Verify boolean property doesn't accept truthy values."""
        logged_boolean_false.value = True
        assert logged_boolean_false.value is True

        logged_boolean_false.value = False
        assert logged_boolean_false.value is False

    def test_multiple_value_transitions(self, logged_boolean_true):
        """Verify boolean can transition between states multiple times."""
        assert logged_boolean_true.value is True

        logged_boolean_true.value = False
        assert logged_boolean_true.value is False

        logged_boolean_true.value = True
        assert logged_boolean_true.value is True

        logged_boolean_true.value = False
        assert logged_boolean_true.value is False


# ============================================================================
# Edge Cases
# ============================================================================

class TestLoggedNetworkBooleanEdgeCases:
    """Test LoggedNetworkBoolean edge cases."""

    def test_false_is_default_when_not_specified(self, logged_boolean_no_default):
        """Verify False is used as default when not specified."""
        assert logged_boolean_no_default._default is False

    def test_callable_interface_with_true(self, logged_boolean_false):
        """Verify callable interface works with True value."""
        logged_boolean_false.value = True

        assert logged_boolean_false() is True

    def test_callable_interface_with_false(self, logged_boolean_true):
        """Verify callable interface works with False value."""
        logged_boolean_true.value = False

        assert logged_boolean_true() is False

    def test_multiple_booleans_independent(self, setup_network_table_instance, mock_logger):
        """Verify multiple LoggedNetworkBoolean instances are independent."""
        bool1 = LoggedNetworkBoolean("key1", True)
        bool2 = LoggedNetworkBoolean("key2", False)

        bool1.value = False

        assert bool1.value is False
        assert bool2.value is False

    def test_repeated_initialization_different_keys(self, setup_network_table_instance, mock_logger):
        """Verify multiple booleans with different keys work independently."""
        mock_instance = setup_network_table_instance.getDefault.return_value

        bool1 = LoggedNetworkBoolean("FirstKey", True)
        bool2 = LoggedNetworkBoolean("SecondKey", False)

        assert mock_instance.getBooleanTopic.call_count == 2

    def test_value_stays_true_on_repeated_true_assignment(self, logged_boolean_true):
        """Verify assigning True multiple times keeps value as True."""
        logged_boolean_true.value = True
        assert logged_boolean_true.value is True

        logged_boolean_true.value = True
        assert logged_boolean_true.value is True

        logged_boolean_true.value = True
        assert logged_boolean_true.value is True

    def test_value_stays_false_on_repeated_false_assignment(self, logged_boolean_false):
        """Verify assigning False multiple times keeps value as False."""
        logged_boolean_false.value = False
        assert logged_boolean_false.value is False

        logged_boolean_false.value = False
        assert logged_boolean_false.value is False

        logged_boolean_false.value = False
        assert logged_boolean_false.value is False


# ============================================================================
# Key Format Tests
# ============================================================================

class TestLoggedNetworkBooleanKeyFormats:
    """Test LoggedNetworkBoolean with various key formats."""

    def test_simple_key_without_slashes(self, setup_network_table_instance, mock_logger):
        """Verify simple key without slashes."""
        boolean_value = LoggedNetworkBoolean("Enabled", True)

        assert boolean_value._key == "Enabled"

    def test_key_with_leading_slash(self, setup_network_table_instance, mock_logger):
        """Verify key with leading slash."""
        boolean_value = LoggedNetworkBoolean("/SmartDashboard/Debug/Enabled", False)

        assert boolean_value._key == "/SmartDashboard/Debug/Enabled"

    def test_hierarchical_key_multiple_levels(self, setup_network_table_instance, mock_logger):
        """Verify hierarchical key with multiple levels."""
        key = "Subsystem/State/HasBall"
        boolean_value = LoggedNetworkBoolean(key, True)

        assert boolean_value._key == key

    def test_key_stored_in_parent_class(self, logged_boolean_true):
        """Verify key is stored in parent class."""
        assert logged_boolean_true._key == "TestKey"

    def test_key_passed_to_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify key is passed to NetworkTables during initialization."""
        key = "Robot/Intake/Running"
        LoggedNetworkBoolean(key, True)

        mock_instance = setup_network_table_instance.getDefault.return_value
        mock_instance.getBooleanTopic.assert_called_with(key)


# ============================================================================
# Default Value Tests
# ============================================================================

class TestLoggedNetworkBooleanDefaults:
    """Test LoggedNetworkBoolean default value handling."""

    def test_true_is_valid_default(self, setup_network_table_instance, mock_logger):
        """Verify True is a valid default value."""
        boolean_value = LoggedNetworkBoolean("key", True)

        assert boolean_value._default is True

    def test_false_is_valid_default(self, setup_network_table_instance, mock_logger):
        """Verify False is a valid default value."""
        boolean_value = LoggedNetworkBoolean("key", False)

        assert boolean_value._default is False

    def test_default_affects_initialization(self, setup_network_table_instance, mock_logger):
        """Verify default value is passed to getEntry."""
        mock_topic = setup_network_table_instance.getDefault.return_value.getBooleanTopic.return_value

        LoggedNetworkBoolean("key", True)

        mock_topic.getEntry.assert_called_once_with(True)

    def test_default_false_affects_initialization(self, setup_network_table_instance, mock_logger):
        """Verify False default is passed to getEntry."""
        mock_topic = setup_network_table_instance.getDefault.return_value.getBooleanTopic.return_value
        mock_topic.reset_mock()

        LoggedNetworkBoolean("key", False)

        mock_topic.getEntry.assert_called_once_with(False)

    def test_explicit_default_overrides_implicit(self, setup_network_table_instance, mock_logger):
        """Verify explicit default is used when specified."""
        boolean_value = LoggedNetworkBoolean("key", True)

        assert boolean_value._default is True

    def test_default_used_for_parent_initialization(self, logged_boolean_true):
        """Verify default is stored for parent class fallback."""
        assert logged_boolean_true._default is True

    def test_different_defaults_for_different_instances(self, setup_network_table_instance, mock_logger):
        """Verify different instances can have different defaults."""
        bool1 = LoggedNetworkBoolean("key1", True)
        bool2 = LoggedNetworkBoolean("key2", False)

        assert bool1._default is True
        assert bool2._default is False

    def test_implicit_false_default(self, setup_network_table_instance, mock_logger):
        """Verify implicit False default when parameter omitted."""
        boolean_value = LoggedNetworkBoolean("key")

        assert boolean_value._default is False


# ============================================================================
# Use Case Tests
# ============================================================================

class TestLoggedNetworkBooleanUseCases:
    """Test LoggedNetworkBoolean with realistic use cases."""

    def test_subsystem_state_indicator(self, logged_boolean_false):
        """Verify use case: subsystem publishes enabled state."""
        logged_boolean_false.value = True
        assert logged_boolean_false.value is True

        logged_boolean_false.value = False
        assert logged_boolean_false.value is False

    def test_intake_has_game_piece_pattern(self, logged_boolean_false):
        """Verify use case: intake tracks if it has game piece."""
        logged_boolean_false.value = True
        has_piece = logged_boolean_false.value
        assert has_piece is True

        logged_boolean_false.value = False
        has_piece = logged_boolean_false.value
        assert has_piece is False

    def test_debug_mode_toggle(self, logged_boolean_false):
        """Verify use case: debug mode toggle from dashboard."""
        if not logged_boolean_false.value:
            logged_boolean_false.value = True

        assert logged_boolean_false.value is True

    def test_motor_fault_detection(self, logged_boolean_false):
        """Verify use case: motor fault state tracking."""
        has_fault = False
        logged_boolean_false.value = has_fault
        assert logged_boolean_false.value is False

        has_fault = True
        logged_boolean_false.value = has_fault
        assert logged_boolean_false.value is True

    def test_configuration_persistence_true(self, setup_network_table_instance, mock_logger):
        """Verify use case: configuration that persists as True."""
        use_vision = LoggedNetworkBoolean("Config/Vision", default=True)

        assert use_vision.value is True
        use_vision.value = False
        assert use_vision.value is False
        use_vision.value = True
        assert use_vision.value is True

    def test_configuration_persistence_false(self, setup_network_table_instance, mock_logger):
        """Verify use case: configuration that persists as False."""
        use_vision = LoggedNetworkBoolean("Config/Vision", default=False)

        assert use_vision.value is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
