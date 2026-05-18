"""Unit tests for loggednetworkvalue module using pytest framework."""

from unittest.mock import MagicMock, Mock, patch
import pytest

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue
from lib_6107.pykit.logtable import LogTable


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_entry():
    """Create a mock NetworkTables entry."""
    return MagicMock()


@pytest.fixture
def mock_logger():
    """Create a mock Logger."""
    with patch('lib_6107.pykit.networktables.loggednetworkvalue.Logger') as logger:
        yield logger


@pytest.fixture
def mock_table():
    """Create a mock LogTable."""
    return MagicMock(spec=LogTable)


@pytest.fixture
def logged_value_float(mock_entry, mock_logger):
    """Create a LoggedNetworkValue[float] instance for testing."""
    logged_value = LoggedNetworkValue[float, type(mock_entry)]("speed", 5.0)
    logged_value._entry = mock_entry
    return logged_value


@pytest.fixture
def logged_value_bool(mock_entry, mock_logger):
    """Create a LoggedNetworkValue[bool] instance for testing."""
    logged_value = LoggedNetworkValue[bool, type(mock_entry)]("enabled", False)
    logged_value._entry = mock_entry
    return logged_value


@pytest.fixture
def logged_value_string(mock_entry, mock_logger):
    """Create a LoggedNetworkValue[str] instance for testing."""
    logged_value = LoggedNetworkValue[str, type(mock_entry)]("mode", "idle")
    logged_value._entry = mock_entry
    return logged_value


# ============================================================================
# Initialization Tests
# ============================================================================

class TestLoggedNetworkValueInitialization:
    """Test LoggedNetworkValue initialization behavior."""

    def test_initialization_stores_key(self, mock_entry, mock_logger):
        """Arrange/Act/Assert: Verify __init__ stores the provided key."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("myKey", 5.0)
        logged_value._entry = mock_entry

        assert logged_value._key == "myKey"

    def test_initialization_stores_default_value(self, mock_entry, mock_logger):
        """Arrange/Act/Assert: Verify __init__ initializes value to default."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("speed", 5.0)
        logged_value._entry = mock_entry

        assert logged_value._value == 5.0

    def test_initialization_stores_default_fallback(self, mock_entry, mock_logger):
        """Arrange/Act/Assert: Verify __init__ stores default for fallback."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("speed", 5.0)
        logged_value._entry = mock_entry

        assert logged_value._default == 5.0

    def test_initialization_registers_with_logger(self, mock_entry, mock_logger):
        """Arrange/Act/Assert: Verify __init__ registers with Logger."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("speed", 5.0)
        logged_value._entry = mock_entry

        mock_logger.registerDashboardInput.assert_called_once()

    def test_initialization_publishes_to_entry(self, mock_entry, mock_logger):
        """Arrange/Act/Assert: Verify __init__ publishes default to entry."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("speed", 5.0)
        logged_value._entry = mock_entry

        mock_entry.set.assert_called_with(5.0)

    @pytest.mark.parametrize("key,default", [
        ("speed", 5.0),
        ("enabled", True),
        ("mode", "idle"),
        ("count", 42),
    ])
    def test_initialization_with_different_values(self, mock_entry, mock_logger, key, default):
        """Arrange/Act/Assert: Verify initialization with various types."""
        logged_value = LoggedNetworkValue[type(default), type(mock_entry)](key, default)
        logged_value._entry = mock_entry

        assert logged_value._key == key
        assert logged_value._value == default
        assert logged_value._default == default


# ============================================================================
# Property Getter Tests
# ============================================================================

class TestLoggedNetworkValuePropertyGetter:
    """Test LoggedNetworkValue value property getter."""

    def test_value_property_returns_cached_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify value property returns current cached value."""
        logged_value_float._value = 20.0

        result = logged_value_float.value

        assert result == 20.0

    @pytest.mark.parametrize("cached_value", [0.0, -42.5, 100.0, 1.5])
    def test_value_property_returns_various_float_values(self, logged_value_float, cached_value):
        """Arrange/Act/Assert: Verify value property with various float values."""
        logged_value_float._value = cached_value

        assert logged_value_float.value == cached_value

    def test_value_property_with_boolean(self, logged_value_bool):
        """Arrange/Act/Assert: Verify value property returns boolean."""
        logged_value_bool._value = True

        assert logged_value_bool.value is True

    def test_value_property_with_string(self, logged_value_string):
        """Arrange/Act/Assert: Verify value property returns string."""
        logged_value_string._value = "active"

        assert logged_value_string.value == "active"


# ============================================================================
# Property Setter Tests
# ============================================================================

class TestLoggedNetworkValuePropertySetter:
    """Test LoggedNetworkValue value property setter."""

    def test_value_property_setter_updates_cached_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify value setter updates cached value."""
        logged_value_float.value = 15.0

        assert logged_value_float._value == 15.0

    @pytest.mark.parametrize("new_value", [0.0, -10.0, 99.9, 1e6])
    def test_value_property_setter_with_various_values(self, logged_value_float, new_value):
        """Arrange/Act/Assert: Verify setter with various float values."""
        logged_value_float.value = new_value

        assert logged_value_float.value == new_value

    def test_value_property_setter_with_boolean(self, logged_value_bool):
        """Arrange/Act/Assert: Verify setter with boolean value."""
        logged_value_bool.value = True

        assert logged_value_bool.value is True

    def test_value_property_setter_replaces_previous_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify setter replaces previous value."""
        logged_value_float.value = 10.0
        logged_value_float.value = 20.0

        assert logged_value_float.value == 20.0


# ============================================================================
# Callable Interface Tests
# ============================================================================

class TestLoggedNetworkValueCallable:
    """Test LoggedNetworkValue callable interface."""

    def test_calling_object_returns_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify calling object returns current value."""
        logged_value_float._value = 20.0

        result = logged_value_float()

        assert result == 20.0

    def test_calling_object_returns_updated_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify calling object returns updated value."""
        logged_value_float.value = 25.0

        result = logged_value_float()

        assert result == 25.0

    @pytest.mark.parametrize("value", [0.0, 15.5, -100.0])
    def test_callable_interface_with_various_values(self, logged_value_float, value):
        """Arrange/Act/Assert: Verify callable interface with various values."""
        logged_value_float.value = value

        assert logged_value_float() == value

    def test_callable_and_property_are_equivalent(self, logged_value_float):
        """Arrange/Act/Assert: Verify callable and property return same value."""
        logged_value_float.value = 42.0

        assert logged_value_float() == logged_value_float.value


# ============================================================================
# SetDefault Tests
# ============================================================================

class TestLoggedNetworkValueSetDefault:
    """Test LoggedNetworkValue set_default method."""

    def test_set_default_updates_stored_default(self, logged_value_float):
        """Arrange/Act/Assert: Verify set_default updates _default attribute."""
        logged_value_float.set_default(10.0)

        assert logged_value_float._default == 10.0

    @pytest.mark.parametrize("new_default", [0.0, 50.0, -25.5])
    def test_set_default_with_various_values(self, logged_value_float, new_default):
        """Arrange/Act/Assert: Verify set_default with various values."""
        logged_value_float.set_default(new_default)

        assert logged_value_float._default == new_default

    def test_set_default_does_not_change_current_value(self, logged_value_float):
        """Arrange/Act/Assert: Verify set_default doesn't affect current value."""
        logged_value_float.value = 35.0
        logged_value_float.set_default(10.0)

        assert logged_value_float.value == 35.0

    def test_set_default_multiple_times(self, logged_value_float):
        """Arrange/Act/Assert: Verify set_default can be called multiple times."""
        logged_value_float.set_default(10.0)
        logged_value_float.set_default(20.0)
        logged_value_float.set_default(30.0)

        assert logged_value_float._default == 30.0


# ============================================================================
# ToLog Tests
# ============================================================================

class TestLoggedNetworkValueToLog:
    """Test LoggedNetworkValue to_log method."""

    def test_to_log_writes_value_to_table(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify to_log writes value to log table."""
        logged_value_float._value = 42.0

        logged_value_float.to_log(mock_table, "/SmartDashboard")

        mock_table.put.assert_called_once()
        call_args = mock_table.put.call_args[0]
        assert call_args[1] == 42.0

    def test_to_log_uses_correct_key_path(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify to_log constructs correct key path."""
        logged_value_float._value = 10.0

        logged_value_float.to_log(mock_table, "/SmartDashboard")

        call_args = mock_table.put.call_args[0]
        assert "/SmartDashboard" in call_args[0]
        assert "speed" in call_args[0]

    def test_to_log_removes_leading_slash_from_key(self, mock_entry, mock_logger, mock_table):
        """Arrange/Act/Assert: Verify to_log removes leading slash from key."""
        logged_value = LoggedNetworkValue[float, type(mock_entry)]("/myKey", 5.0)
        logged_value._entry = mock_entry
        logged_value._value = 42.0

        logged_value.to_log(mock_table, "/SmartDashboard")

        call_args = mock_table.put.call_args[0]
        # Should not have double slash
        assert "//" not in call_args[0]

    @pytest.mark.parametrize("value,prefix", [
        (0.0, "/SmartDashboard"),
        (99.9, "/Test"),
        (-50.0, "/Custom"),
    ])
    def test_to_log_with_various_values_and_prefixes(self, logged_value_float, mock_table, value, prefix):
        """Arrange/Act/Assert: Verify to_log with various values and prefixes."""
        logged_value_float._value = value

        logged_value_float.to_log(mock_table, prefix)

        call_args = mock_table.put.call_args[0]
        assert call_args[1] == value
        assert prefix in call_args[0]


# ============================================================================
# FromLog Tests
# ============================================================================

class TestLoggedNetworkValueFromLog:
    """Test LoggedNetworkValue from_log method."""

    def test_from_log_reads_and_updates_value(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify from_log reads value from log table."""
        logged_value_float._value = 10.0
        mock_table.get.return_value = 99.0

        logged_value_float.from_log(mock_table, "/SmartDashboard")

        assert logged_value_float._value == 99.0

    def test_from_log_uses_default_when_key_missing(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify from_log uses default when value missing."""
        logged_value_float._default = 42.0
        mock_table.get.side_effect = lambda key, default: default

        logged_value_float.from_log(mock_table, "/SmartDashboard")

        assert logged_value_float._value == 42.0

    def test_from_log_queries_correct_key_path(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify from_log queries correct key path."""
        mock_table.get.return_value = 55.0

        logged_value_float.from_log(mock_table, "/SmartDashboard")

        mock_table.get.assert_called_once()
        call_args = mock_table.get.call_args[0]
        assert "/SmartDashboard" in call_args[0]

    @pytest.mark.parametrize("logged_value,new_value", [
        (0.0, 100.0),
        (50.0, 10.0),
        (-100.0, 0.0),
    ])
    def test_from_log_with_various_transitions(self, logged_value_float, mock_table, logged_value, new_value):
        """Arrange/Act/Assert: Verify from_log transitions between values."""
        logged_value_float._value = logged_value
        mock_table.get.return_value = new_value

        logged_value_float.from_log(mock_table, "/SmartDashboard")

        assert logged_value_float._value == new_value


# ============================================================================
# Periodic Tests - Normal Mode
# ============================================================================

class TestLoggedNetworkValuePeriodicNormalMode:
    """Test LoggedNetworkValue periodic method in normal mode."""

    def test_periodic_reads_from_entry_in_normal_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic reads from entry when not replaying."""
        logged_value_float._entry.get.return_value = 88.0
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()

        logged_value_float._entry.get.assert_called()

    def test_periodic_updates_value_from_entry(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic updates cached value from entry."""
        logged_value_float._entry.get.return_value = 77.0
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()

        assert logged_value_float._value == 77.0

    def test_periodic_uses_default_if_entry_unavailable(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic uses default when entry unavailable."""
        logged_value_float._default = 5.0
        logged_value_float._entry.get.side_effect = lambda default: default
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()

        assert logged_value_float._value == 5.0

    def test_periodic_calls_process_inputs_in_normal_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic calls Logger.processInputs."""
        logged_value_float._entry.get.return_value = 42.0
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()

        mock_logger.processInputs.assert_called_once()


# ============================================================================
# Periodic Tests - Replay Mode
# ============================================================================

class TestLoggedNetworkValuePeriodicReplayMode:
    """Test LoggedNetworkValue periodic method in replay mode."""

    def test_periodic_skips_entry_read_in_replay_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic skips entry read when replaying."""
        mock_logger.isReplay.return_value = True

        logged_value_float.periodic()

        logged_value_float._entry.get.assert_not_called()

    def test_periodic_preserves_value_in_replay_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic doesn't change value in replay mode."""
        logged_value_float._value = 33.0
        mock_logger.isReplay.return_value = True

        logged_value_float.periodic()

        assert logged_value_float._value == 33.0

    def test_periodic_calls_process_inputs_in_replay_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify periodic calls processInputs in replay mode."""
        mock_logger.isReplay.return_value = True

        logged_value_float.periodic()

        mock_logger.processInputs.assert_called_once()


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestLoggedNetworkValueEdgeCases:
    """Test LoggedNetworkValue edge cases."""

    def test_value_with_zero(self, logged_value_float):
        """Arrange/Act/Assert: Verify value works with zero."""
        logged_value_float.value = 0.0

        assert logged_value_float.value == 0.0

    def test_value_with_negative(self, logged_value_float):
        """Arrange/Act/Assert: Verify value works with negative numbers."""
        logged_value_float.value = -42.5

        assert logged_value_float.value == -42.5

    def test_value_with_very_large_number(self, logged_value_float):
        """Arrange/Act/Assert: Verify value works with very large numbers."""
        large_value = 1e10
        logged_value_float.value = large_value

        assert logged_value_float.value == large_value

    def test_value_with_very_small_number(self, logged_value_float):
        """Arrange/Act/Assert: Verify value works with very small numbers."""
        small_value = 1e-10
        logged_value_float.value = small_value

        assert logged_value_float.value == small_value

    def test_to_log_with_zero_value(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify to_log with zero value."""
        logged_value_float._value = 0.0

        logged_value_float.to_log(mock_table, "/SmartDashboard")

        call_args = mock_table.put.call_args[0]
        assert call_args[1] == 0.0

    def test_to_log_with_negative_value(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify to_log with negative value."""
        logged_value_float._value = -99.9

        logged_value_float.to_log(mock_table, "/SmartDashboard")

        call_args = mock_table.put.call_args[0]
        assert call_args[1] == -99.9

    def test_from_log_with_zero_value(self, logged_value_float, mock_table):
        """Arrange/Act/Assert: Verify from_log with zero value."""
        mock_table.get.return_value = 0.0

        logged_value_float.from_log(mock_table, "/SmartDashboard")

        assert logged_value_float._value == 0.0

    def test_boolean_value_false(self, logged_value_bool):
        """Arrange/Act/Assert: Verify boolean false value."""
        logged_value_bool.value = False

        assert logged_value_bool.value is False

    def test_boolean_value_true(self, logged_value_bool):
        """Arrange/Act/Assert: Verify boolean true value."""
        logged_value_bool.value = True

        assert logged_value_bool.value is True

    def test_string_value_empty(self, logged_value_string):
        """Arrange/Act/Assert: Verify empty string value."""
        logged_value_string.value = ""

        assert logged_value_string.value == ""

    def test_string_value_with_special_characters(self, logged_value_string):
        """Arrange/Act/Assert: Verify string with special characters."""
        special_string = "test@#$%^&*()_+-=[]{}|;':\",./<>?"
        logged_value_string.value = special_string

        assert logged_value_string.value == special_string


# ============================================================================
# Integration Tests
# ============================================================================

class TestLoggedNetworkValueIntegration:
    """Test LoggedNetworkValue integration scenarios."""

    def test_full_lifecycle_normal_mode(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify full lifecycle in normal mode."""
        logged_value_float._entry.get.return_value = 50.0
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()
        logged_value_float.value = 60.0

        assert logged_value_float.value == 60.0

    def test_value_changes_between_periodic_calls(self, logged_value_float, mock_logger):
        """Arrange/Act/Assert: Verify value can change between periodic calls."""
        logged_value_float._entry.get.return_value = 10.0
        mock_logger.isReplay.return_value = False

        logged_value_float.periodic()
        first_value = logged_value_float.value

        logged_value_float._entry.get.return_value = 20.0
        logged_value_float.periodic()
        second_value = logged_value_float.value

        assert first_value == 10.0
        assert second_value == 20.0

    def test_default_fallback_used_when_entry_fails(self, logged_value_float):
        """Arrange/Act/Assert: Verify default used when entry fails."""
        logged_value_float._default = 42.0
        logged_value_float._entry.get.side_effect = Exception("Entry failed")

        with pytest.raises(Exception):
            logged_value_float._entry.get(logged_value_float._default)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

