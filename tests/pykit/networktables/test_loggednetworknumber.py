"""Unit tests for loggednetworknumber module using pytest framework."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.networktables.loggednetworknumber import LoggedNetworkNumber


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_network_table_instance():
    """Create a mock NetworkTableInstance."""
    with patch('lib_6107.pykit.networktables.loggednetworknumber.NetworkTableInstance') as mock_nt:
        yield mock_nt


@pytest.fixture
def mock_double_entry():
    """Create a mock DoubleEntry."""
    return MagicMock()


@pytest.fixture
def mock_double_topic(mock_double_entry):
    """Create a mock DoubleTopic that returns mock_double_entry."""
    mock_topic = MagicMock()
    mock_topic.getEntry.return_value = mock_double_entry
    return mock_topic


@pytest.fixture
def mock_logger():
    """Create a mock Logger."""
    with patch('lib_6107.pykit.networktables.loggednetworkvalue.Logger') as logger:
        yield logger


@pytest.fixture
def setup_network_table_instance(mock_network_table_instance, mock_double_topic):
    """Setup the mock NetworkTableInstance chain for LoggedNetworkNumber initialization."""
    mock_instance = MagicMock()
    mock_instance.getDoubleTopic.return_value = mock_double_topic
    mock_network_table_instance.getDefault.return_value = mock_instance
    return mock_network_table_instance


@pytest.fixture
def logged_number_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkNumber with default parameters."""
    return LoggedNetworkNumber("TestKey", default=5.0)


@pytest.fixture
def logged_number_zero_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkNumber with zero default."""
    return LoggedNetworkNumber("TestKey", default=0.0)


@pytest.fixture
def logged_number_integer_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkNumber with integer default."""
    return LoggedNetworkNumber("TestKey", default=42)


# ============================================================================
# Initialization Tests
# ============================================================================

class TestLoggedNetworkNumberInitialization:
    """Test LoggedNetworkNumber initialization behavior."""

    def test_creates_double_entry_via_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify __init__ creates a DoubleEntry through NetworkTableInstance chain."""
        key = "Drive/MaxSpeed"
        default = 3.5

        number = LoggedNetworkNumber(key, default)

        setup_network_table_instance.getDefault.assert_called_once()

    def test_retrieves_double_topic_with_correct_key(self, setup_network_table_instance, mock_logger):
        """Verify __init__ retrieves DoubleTopic with the provided key."""
        key = "Drive/MaxSpeed"
        default = 3.5
        mock_instance = setup_network_table_instance.getDefault.return_value

        number = LoggedNetworkNumber(key, default)

        mock_instance.getDoubleTopic.assert_called_once_with(key)

    def test_calls_get_entry_with_default_value(self, setup_network_table_instance, mock_logger):
        """Verify __init__ calls getEntry with default value."""
        key = "Drive/MaxSpeed"
        default = 3.5
        mock_topic = setup_network_table_instance.getDefault.return_value.getDoubleTopic.return_value

        number = LoggedNetworkNumber(key, default)

        mock_topic.getEntry.assert_called_once_with(default)

    def test_stores_entry_reference(self, setup_network_table_instance, mock_logger, mock_double_entry):
        """Verify __init__ stores the DoubleEntry reference."""
        number = LoggedNetworkNumber("TestKey", 5.0)

        assert number._entry == mock_double_entry

    def test_initializes_with_float_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization with float default value."""
        number = LoggedNetworkNumber("speed", 3.14)

        assert number._default == 3.14

    def test_initializes_with_integer_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization with integer default value."""
        number = LoggedNetworkNumber("count", 42)

        assert number._default == 42

    def test_accepts_zero_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts zero as default."""
        number = LoggedNetworkNumber("neutral", 0.0)

        assert number._default == 0.0

    def test_accepts_negative_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts negative default values."""
        number = LoggedNetworkNumber("angle", -45.5)

        assert number._default == -45.5

    def test_accepts_very_large_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts very large default values."""
        large_value = 1e10
        number = LoggedNetworkNumber("large", large_value)

        assert number._default == large_value

    def test_accepts_very_small_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts very small default values."""
        small_value = 1e-10
        number = LoggedNetworkNumber("small", small_value)

        assert number._default == small_value

    def test_uses_zero_default_when_not_specified(self, setup_network_table_instance, mock_logger):
        """Verify initialization uses 0.0 as default when not provided."""
        number = LoggedNetworkNumber("TestKey")

        assert number._default == 0.0

    @pytest.mark.parametrize("key", [
        "SimpleKey",
        "/SmartDashboard/Drive/MaxSpeed",
        "Subsystem/Parameter",
        "Test/Deep/Nested/Key",
        "Sensor/Calibration/Offset",
    ])
    def test_handles_various_key_formats(self, setup_network_table_instance, mock_logger, key):
        """Verify initialization handles various key formats."""
        number = LoggedNetworkNumber(key, 1.0)

        assert number._key == key

    @pytest.mark.parametrize("key,default", [
        ("speed", 5.0),
        ("voltage", 12.0),
        ("pid_kp", 0.1),
        ("rpm", 3000),
        ("distance", 0.0),
    ])
    def test_initialization_with_different_values(self, setup_network_table_instance, mock_logger, key, default):
        """Verify initialization with various key and default combinations."""
        number = LoggedNetworkNumber(key, default)

        assert number._key == key
        assert number._default == default


# ============================================================================
# Entry Type Tests
# ============================================================================

class TestLoggedNetworkNumberEntryType:
    """Test that LoggedNetworkNumber creates correct entry types."""

    def test_creates_double_entry_not_other_types(self, setup_network_table_instance, mock_logger):
        """Verify the entry type is specifically DoubleEntry."""
        number = LoggedNetworkNumber("TestKey", 5.0)

        setup_network_table_instance.getDefault.return_value.getDoubleTopic.assert_called_once()
        setup_network_table_instance.getDefault.return_value.getIntegerTopic.assert_not_called()

    def test_double_entry_created_for_float_values(self, setup_network_table_instance, mock_logger):
        """Verify DoubleEntry created even when default is integer."""
        number = LoggedNetworkNumber("TestKey", 42)

        assert setup_network_table_instance.getDefault.return_value.getDoubleTopic.called


# ============================================================================
# Parent Class Integration Tests
# ============================================================================

class TestLoggedNetworkNumberParentIntegration:
    """Test LoggedNetworkNumber integration with LoggedNetworkValue parent class."""

    def test_inherits_value_property_from_parent(self, logged_number_default):
        """Verify value property is inherited from parent class."""
        logged_number_default._value = 10.0

        assert logged_number_default.value == 10.0

    def test_inherits_value_property_setter(self, logged_number_default):
        """Verify value property setter is inherited from parent class."""
        logged_number_default.value = 15.0

        assert logged_number_default._value == 15.0

    def test_inherits_callable_interface(self, logged_number_default):
        """Verify callable interface is inherited from parent class."""
        logged_number_default._value = 20.0

        result = logged_number_default()

        assert result == 20.0

    def test_inherits_to_log_method(self, logged_number_default):
        """Verify to_log method is inherited from parent class."""
        assert hasattr(logged_number_default, 'to_log')
        assert callable(logged_number_default.to_log)

    def test_inherits_from_log_method(self, logged_number_default):
        """Verify from_log method is inherited from parent class."""
        assert hasattr(logged_number_default, 'from_log')
        assert callable(logged_number_default.from_log)

    def test_inherits_periodic_method(self, logged_number_default):
        """Verify periodic method is inherited from parent class."""
        assert hasattr(logged_number_default, 'periodic')
        assert callable(logged_number_default.periodic)

    def test_inherits_set_default_method(self, logged_number_default):
        """Verify set_default method is inherited from parent class."""
        assert hasattr(logged_number_default, 'set_default')
        assert callable(logged_number_default.set_default)


# ============================================================================
# Type Safety Tests
# ============================================================================

class TestLoggedNetworkNumberTypes:
    """Test LoggedNetworkNumber type handling."""

    def test_stores_float_values(self, logged_number_default):
        """Verify float values are stored correctly."""
        logged_number_default.value = 3.14159

        assert logged_number_default.value == 3.14159

    def test_stores_integer_values(self, logged_number_default):
        """Verify integer values are stored correctly."""
        logged_number_default.value = 42

        assert logged_number_default.value == 42

    def test_stores_negative_values(self, logged_number_default):
        """Verify negative values are stored correctly."""
        logged_number_default.value = -99.5

        assert logged_number_default.value == -99.5

    def test_allows_type_coercion_int_to_float(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts int and uses as default."""
        number = LoggedNetworkNumber("voltage", 12)

        assert number._default == 12


# ============================================================================
# Edge Cases
# ============================================================================

class TestLoggedNetworkNumberEdgeCases:
    """Test LoggedNetworkNumber edge cases."""

    def test_handles_zero_value(self, logged_number_zero_default):
        """Verify handling of zero value."""
        assert logged_number_zero_default._default == 0.0

    def test_handles_very_large_values(self, logged_number_default):
        """Verify handling of very large floating point values."""
        large_value = 1.7976931348623157e+308
        logged_number_default.value = large_value

        assert logged_number_default.value == large_value

    def test_handles_very_small_values(self, logged_number_default):
        """Verify handling of very small floating point values."""
        small_value = 2.2204460492503131e-16
        logged_number_default.value = small_value

        assert logged_number_default.value == small_value

    def test_handles_many_decimal_places(self, logged_number_default):
        """Verify handling of values with many decimal places."""
        precise_value = 3.141592653589793
        logged_number_default.value = precise_value

        assert logged_number_default.value == precise_value

    def test_handles_scientific_notation(self, logged_number_default):
        """Verify handling of scientific notation values."""
        logged_number_default.value = 1.23e-4

        assert logged_number_default.value == 1.23e-4

    def test_multiple_numbers_independent(self, setup_network_table_instance, mock_logger):
        """Verify multiple LoggedNetworkNumber instances are independent."""
        number1 = LoggedNetworkNumber("key1", 10.0)
        number2 = LoggedNetworkNumber("key2", 20.0)

        number1.value = 15.0

        assert number1.value == 15.0
        assert number2.value == 20.0

    def test_repeated_initialization_different_keys(self, setup_network_table_instance, mock_logger):
        """Verify multiple numbers with different keys work independently."""
        mock_instance = setup_network_table_instance.getDefault.return_value

        number1 = LoggedNetworkNumber("FirstKey", 1.0)
        number2 = LoggedNetworkNumber("SecondKey", 2.0)

        assert mock_instance.getDoubleTopic.call_count == 2


# ============================================================================
# Key Format Tests
# ============================================================================

class TestLoggedNetworkNumberKeyFormats:
    """Test LoggedNetworkNumber with various key formats."""

    def test_simple_key_without_slashes(self, setup_network_table_instance, mock_logger):
        """Verify simple key without slashes."""
        number = LoggedNetworkNumber("MaxSpeed", 5.0)

        assert number._key == "MaxSpeed"

    def test_key_with_leading_slash(self, setup_network_table_instance, mock_logger):
        """Verify key with leading slash."""
        number = LoggedNetworkNumber("/SmartDashboard/MaxSpeed", 5.0)

        assert number._key == "/SmartDashboard/MaxSpeed"

    def test_hierarchical_key_multiple_levels(self, setup_network_table_instance, mock_logger):
        """Verify hierarchical key with multiple levels."""
        key = "Subsystems/Drive/Velocity"
        number = LoggedNetworkNumber(key, 5.0)

        assert number._key == key

    def test_key_stored_in_parent_class(self, logged_number_default):
        """Verify key is stored in parent class."""
        assert logged_number_default._key == "TestKey"

    def test_key_passed_to_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify key is passed to NetworkTables during initialization."""
        key = "CustomKey/SubLevel"
        LoggedNetworkNumber(key, 5.0)

        mock_instance = setup_network_table_instance.getDefault.return_value
        mock_instance.getDoubleTopic.assert_called_with(key)


# ============================================================================
# Default Value Tests
# ============================================================================

class TestLoggedNetworkNumberDefaults:
    """Test LoggedNetworkNumber default value handling."""

    def test_default_zero_is_valid(self, setup_network_table_instance, mock_logger):
        """Verify zero is a valid default value."""
        number = LoggedNetworkNumber("key", 0.0)

        assert number._default == 0.0

    def test_default_affects_initialization(self, setup_network_table_instance, mock_logger):
        """Verify default value is passed to getEntry."""
        default_value = 7.25
        mock_topic = setup_network_table_instance.getDefault.return_value.getDoubleTopic.return_value

        LoggedNetworkNumber("key", default_value)

        mock_topic.getEntry.assert_called_once_with(default_value)

    def test_explicit_default_overrides_zero(self, setup_network_table_instance, mock_logger):
        """Verify explicit default overrides implicit zero."""
        number = LoggedNetworkNumber("key", 100.0)

        assert number._default == 100.0

    def test_default_used_for_parent_initialization(self, logged_number_default):
        """Verify default is stored for parent class fallback."""
        assert logged_number_default._default == 5.0

    def test_different_defaults_for_different_instances(self, setup_network_table_instance, mock_logger):
        """Verify different instances can have different defaults."""
        number1 = LoggedNetworkNumber("key1", 10.0)
        number2 = LoggedNetworkNumber("key2", 20.0)

        assert number1._default == 10.0
        assert number2._default == 20.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
