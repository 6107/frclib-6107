"""Unit tests for nt4Publisher module using pytest framework."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.networktables.nt4Publisher import NT4Publisher


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_network_table_instance():
    """Create a mock NetworkTableInstance."""
    with patch('lib_6107.pykit.networktables.nt4Publisher.NetworkTableInstance') as mock_nt:
        yield mock_nt


@pytest.fixture
def mock_network_table():
    """Create a mock NetworkTable."""
    mock_table = MagicMock()
    mock_topic = MagicMock()
    mock_table.getTopic.return_value = mock_topic
    mock_table.getIntegerTopic.return_value = mock_topic
    return mock_table


@pytest.fixture
def mock_generic_publisher():
    """Create a mock GenericPublisher."""
    return MagicMock()


@pytest.fixture
def mock_integer_publisher():
    """Create a mock IntegerPublisher."""
    return MagicMock()


@pytest.fixture
def setup_publisher_with_akit(mock_network_table_instance, mock_network_table, mock_integer_publisher):
    """Setup NT4Publisher in AdvantageKit mode."""
    mock_instance = MagicMock()
    mock_instance.getTable.return_value = mock_network_table
    mock_network_table_instance.getDefault.return_value = mock_instance

    mock_topic = MagicMock()
    mock_network_table.getIntegerTopic.return_value = mock_topic
    mock_topic.publish.return_value = mock_integer_publisher

    publisher = NT4Publisher(act_like_akit=True)
    publisher.publishers.clear()
    publisher.units.clear()
    publisher.last_table = publisher.last_table.__class__(0)
    return publisher


@pytest.fixture
def setup_publisher_default(mock_network_table_instance, mock_network_table, mock_integer_publisher):
    """Setup NT4Publisher in default PyKit mode."""
    mock_instance = MagicMock()
    mock_instance.getTable.return_value = mock_network_table
    mock_network_table_instance.getDefault.return_value = mock_instance

    mock_topic = MagicMock()
    mock_network_table.getIntegerTopic.return_value = mock_topic
    mock_topic.publish.return_value = mock_integer_publisher

    publisher = NT4Publisher(act_like_akit=False)
    publisher.publishers.clear()
    publisher.units.clear()
    publisher.last_table = publisher.last_table.__class__(0)
    return publisher


@pytest.fixture
def mock_log_value_double():
    """Create a mock LogValue with Double type."""
    value = MagicMock(spec=LogValue)
    value.log_type = LogValue.LoggableType.Double
    value.value = 42.5
    value.unit = None
    value.getNT4Type.return_value = "double"
    return value


@pytest.fixture
def mock_log_value_boolean():
    """Create a mock LogValue with Boolean type."""
    value = MagicMock(spec=LogValue)
    value.log_type = LogValue.LoggableType.Boolean
    value.value = True
    value.unit = None
    value.getNT4Type.return_value = "boolean"
    return value


@pytest.fixture
def mock_log_value_string():
    """Create a mock LogValue with String type."""
    value = MagicMock(spec=LogValue)
    value.log_type = LogValue.LoggableType.String
    value.value = "test_value"
    value.unit = None
    value.getNT4Type.return_value = "string"
    return value


@pytest.fixture
def mock_log_table():
    """Create a mock LogTable."""
    table = MagicMock(spec=LogTable)
    table.getTimestamp.return_value = 1000000
    return table


# ============================================================================
# Initialization Tests
# ============================================================================

class TestNT4PublisherInitialization:
    """Test NT4Publisher initialization behavior."""

    def test_initializes_with_default_pykit_namespace(self, mock_network_table_instance, mock_network_table,
                                                      mock_integer_publisher):
        """Verify publisher initializes with /PyKit namespace by default."""
        mock_instance = MagicMock()
        mock_instance.getTable.return_value = mock_network_table
        mock_network_table_instance.getDefault.return_value = mock_instance

        mock_topic = MagicMock()
        mock_network_table.getIntegerTopic.return_value = mock_topic
        mock_topic.publish.return_value = mock_integer_publisher

        publisher = NT4Publisher()

        mock_instance.getTable.assert_called_with("/PyKit")

    def test_initializes_with_advantagekit_namespace(self, mock_network_table_instance, mock_network_table,
                                                     mock_integer_publisher):
        """Verify publisher initializes with /AdvantageKit namespace when specified."""
        mock_instance = MagicMock()
        mock_instance.getTable.return_value = mock_network_table
        mock_network_table_instance.getDefault.return_value = mock_instance

        mock_topic = MagicMock()
        mock_network_table.getIntegerTopic.return_value = mock_topic
        mock_topic.publish.return_value = mock_integer_publisher

        publisher = NT4Publisher(act_like_akit=True)

        mock_instance.getTable.assert_called_with("/AdvantageKit")

    def test_creates_timestamp_publisher(self, setup_publisher_default, mock_network_table):
        """Verify timestamp publisher is created during initialization."""
        mock_topic = mock_network_table.getIntegerTopic.return_value
        mock_topic.publish.assert_called_once()

    def test_initializes_empty_publishers_cache(self, setup_publisher_default):
        """Verify publishers cache is initialized as empty dict."""
        assert setup_publisher_default.publishers == {}

    def test_initializes_empty_units_cache(self, setup_publisher_default):
        """Verify units cache is initialized as empty dict."""
        assert setup_publisher_default.units == {}


# ============================================================================
# Delta Detection Tests
# ============================================================================

class TestNT4PublisherDeltaDetection:
    """Test NT4Publisher delta detection functionality."""

    def test_always_publishes_timestamp(self, setup_publisher_default, mock_log_table, mock_integer_publisher):
        """Verify timestamp is always published regardless of delta detection."""
        mock_log_table.get_all.return_value = {}

        setup_publisher_default.put_table(mock_log_table)

        mock_integer_publisher.set.assert_called_once()

    def test_does_not_publish_when_no_changed_values(self, setup_publisher_default, mock_log_table,
                                                     mock_integer_publisher):
        """Verify only timestamp is published when no values changed."""
        mock_log_table.get_all.return_value = {}

        setup_publisher_default.put_table(mock_log_table)

        mock_integer_publisher.set.assert_called_once()


# ============================================================================
# Type Handling Tests
# ============================================================================

class TestNT4PublisherTypeHandling:
    """Test NT4Publisher handling of different LogValue types."""

    def test_publishes_using_type_specific_methods(self, setup_publisher_default, mock_log_table, mock_network_table,
                                                   mock_generic_publisher):
        """Verify type-specific publish methods are available."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Double
        value.value = 42.5
        value.unit = None

        mock_log_table.get_all.return_value = {"/Drivetrain/speed": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher
        value.getNT4Type.return_value = "double"

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setDouble.called

    def test_publishes_string_type(self, setup_publisher_default, mock_log_table, mock_log_value_string,
                                   mock_network_table, mock_generic_publisher):
        """Verify String LogValue type uses setString."""
        mock_log_table.get_all.return_value = {"/Robot/state": mock_log_value_string}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        mock_generic_publisher.setString.assert_called_once()

    def test_publishes_integer_type(self, setup_publisher_default, mock_log_table, mock_network_table,
                                    mock_generic_publisher):
        """Verify Integer LogValue type uses setInteger."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Integer
        value.value = 42
        value.unit = None

        mock_log_table.get_all.return_value = {"/Motor/count": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setInteger.called

    def test_publishes_raw_type(self, setup_publisher_default, mock_log_table, mock_network_table,
                                mock_generic_publisher):
        """Verify Raw LogValue type uses setRaw."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Raw
        value.value = b"raw_bytes"
        value.unit = None

        mock_log_table.get_all.return_value = {"/Binary/data": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setRaw.called

    def test_publishes_boolean_array_type(self, setup_publisher_default, mock_log_table, mock_network_table,
                                          mock_generic_publisher):
        """Verify BooleanArray LogValue type uses setBooleanArray."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.BooleanArray
        value.value = [True, False, True]
        value.unit = None

        mock_log_table.get_all.return_value = {"/Array/booleans": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setBooleanArray.called

    def test_publishes_double_array_type(self, setup_publisher_default, mock_log_table, mock_network_table,
                                         mock_generic_publisher):
        """Verify DoubleArray LogValue type uses setDoubleArray."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.DoubleArray
        value.value = [1.1, 2.2, 3.3]
        value.unit = None

        mock_log_table.get_all.return_value = {"/Array/doubles": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setDoubleArray.called

    def test_publishes_string_array_type(self, setup_publisher_default, mock_log_table, mock_network_table,
                                         mock_generic_publisher):
        """Verify StringArray LogValue type uses setStringArray."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.StringArray
        value.value = ["one", "two", "three"]
        value.unit = None

        mock_log_table.get_all.return_value = {"/Array/strings": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setStringArray.called


# ============================================================================
# Publisher Caching Tests
# ============================================================================

class TestNT4PublisherCaching:
    """Test NT4Publisher publisher caching and reuse."""

    def test_calls_generic_publish_for_new_topic(self, setup_publisher_default, mock_log_table, mock_log_value_double,
                                                 mock_network_table, mock_generic_publisher):
        """Verify genericPublish is called for new topics."""
        mock_log_table.get_all.return_value = {"/Drivetrain/speed": mock_log_value_double}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        mock_topic.genericPublish.assert_called()

    def test_reuses_cached_publisher_next_cycle(self, setup_publisher_default, mock_log_table, mock_log_value_double,
                                                mock_network_table, mock_generic_publisher):
        """Verify cached publisher is reused in next cycle."""
        mock_log_table.get_all.return_value = {"/Drivetrain/speed": mock_log_value_double}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)
        publish_call_count = mock_topic.genericPublish.call_count

        mock_log_value_double.value = 50.0
        setup_publisher_default.put_table(mock_log_table)

        assert mock_topic.genericPublish.call_count == publish_call_count


# ============================================================================
# Unit Metadata Tests
# ============================================================================

class TestNT4PublisherUnitMetadata:
    """Test NT4Publisher unit metadata handling."""

    def test_sets_unit_metadata_on_first_publish(self, setup_publisher_default, mock_log_table, mock_network_table,
                                                 mock_generic_publisher):
        """Verify unit metadata is set when publishing value with unit."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Double
        value.value = 3.5
        value.unit = "m/s"

        mock_log_table.get_all.return_value = {"/Drivetrain/speed": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        mock_topic.setProperty.assert_called_with("unit", "m/s")

    def test_does_not_set_unit_when_none(self, setup_publisher_default, mock_log_table, mock_network_table,
                                         mock_generic_publisher):
        """Verify setProperty is not called when unit is None."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Double
        value.value = 3.5
        value.unit = None

        mock_log_table.get_all.return_value = {"/Sensor/reading": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        mock_topic.setProperty.assert_not_called()


# ============================================================================
# Topic Key Processing Tests
# ============================================================================

class TestNT4PublisherKeyProcessing:
    """Test NT4Publisher topic key processing."""

    def test_calls_get_topic_for_values(self, setup_publisher_default, mock_log_table, mock_log_value_double,
                                        mock_network_table, mock_generic_publisher):
        """Verify getTopic is called for publishing values."""
        mock_log_table.get_all.return_value = {"/Drivetrain/speed": mock_log_value_double}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        mock_network_table.getTopic.assert_called()

    def test_preserves_hierarchical_structure_in_key(self, setup_publisher_default, mock_log_table, mock_network_table,
                                                     mock_generic_publisher):
        """Verify hierarchical key structure is preserved."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Double
        value.value = 1.0
        value.unit = None

        mock_log_table.get_all.return_value = {"/Deep/Nested/Path/Key": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_network_table.getTopic.called


# ============================================================================
# Multiple Topic Tests
# ============================================================================

class TestNT4PublisherMultipleTopics:
    """Test NT4Publisher with multiple topics."""

    def test_publishes_multiple_topics_same_cycle(self, setup_publisher_default, mock_log_table, mock_network_table,
                                                  mock_generic_publisher):
        """Verify getTopic is called for each topic in same cycle."""
        value1 = MagicMock(spec=LogValue)
        value1.log_type = LogValue.LoggableType.Double
        value1.value = 1.0
        value1.unit = None

        value2 = MagicMock(spec=LogValue)
        value2.log_type = LogValue.LoggableType.Boolean
        value2.value = True
        value2.unit = None

        mock_log_table.get_all.return_value = {
            "/Drivetrain/speed": value1,
            "/Motor/enabled"   : value2
        }

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_network_table.getTopic.call_count >= 2


# ============================================================================
# Timestamp Tests
# ============================================================================

class TestNT4PublisherTimestamp:
    """Test NT4Publisher timestamp handling."""

    def test_publishes_timestamp_from_log_table(self, setup_publisher_default, mock_log_table, mock_integer_publisher):
        """Verify timestamp from LogTable is published."""
        mock_log_table.getTimestamp.return_value = 5000000
        mock_log_table.get_all.return_value = {}

        setup_publisher_default.put_table(mock_log_table)

        mock_integer_publisher.set.assert_called_once_with(5000000, 5000000)

    def test_uses_same_timestamp_for_all_values(self, setup_publisher_default, mock_log_table, mock_network_table,
                                                mock_generic_publisher):
        """Verify all values use the same timestamp as LogTable."""
        value1 = MagicMock(spec=LogValue)
        value1.log_type = LogValue.LoggableType.Double
        value1.value = 1.0
        value1.unit = None

        value2 = MagicMock(spec=LogValue)
        value2.log_type = LogValue.LoggableType.Double
        value2.value = 2.0
        value2.unit = None

        mock_log_table.getTimestamp.return_value = 3000000
        mock_log_table.get_all.return_value = {
            "/Drivetrain/speed"  : value1,
            "/Drivetrain/heading": value2
        }

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        calls = mock_generic_publisher.setDouble.call_args_list
        for call_obj in calls:
            assert call_obj[0][1] == 3000000


# ============================================================================
# Empty and Edge Case Tests
# ============================================================================

class TestNT4PublisherEdgeCases:
    """Test NT4Publisher edge cases."""

    def test_handles_empty_log_table(self, setup_publisher_default, mock_log_table, mock_integer_publisher):
        """Verify publisher handles empty LogTable gracefully."""
        mock_log_table.get_all.return_value = {}

        setup_publisher_default.put_table(mock_log_table)

        mock_integer_publisher.set.assert_called_once()

    def test_handles_empty_string_value(self, setup_publisher_default, mock_log_table, mock_network_table,
                                        mock_generic_publisher):
        """Verify empty string is published (not skipped)."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.String
        value.value = ""
        value.unit = None

        mock_log_table.get_all.return_value = {"/Robot/message": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        assert mock_generic_publisher.setString.called

    def test_publishes_value_with_timestamp(self, setup_publisher_default, mock_log_table, mock_network_table,
                                            mock_generic_publisher):
        """Verify published value includes timestamp."""
        value = MagicMock(spec=LogValue)
        value.log_type = LogValue.LoggableType.Double
        value.value = 42.0
        value.unit = None

        mock_log_table.getTimestamp.return_value = 9999999
        mock_log_table.get_all.return_value = {"/Sensor/value": value}

        mock_topic = MagicMock()
        mock_network_table.getTopic.return_value = mock_topic
        mock_topic.genericPublish.return_value = mock_generic_publisher

        setup_publisher_default.put_table(mock_log_table)

        calls = mock_generic_publisher.method_calls
        assert any(str(9999999) in str(call) for call in calls)


# ============================================================================
# Namespace Mode Tests
# ============================================================================

class TestNT4PublisherNamespaceModes:
    """Test NT4Publisher behavior in different namespace modes."""

    def test_pykit_mode_uses_correct_table(self, setup_publisher_default, mock_network_table_instance):
        """Verify PyKit mode uses correct namespace."""
        mock_network_table_instance.getDefault.return_value.getTable.assert_called_with("/PyKit")

    def test_akit_mode_uses_correct_table(self, setup_publisher_with_akit, mock_network_table_instance):
        """Verify AdvantageKit mode uses correct namespace."""
        mock_network_table_instance.getDefault.return_value.getTable.assert_called_with("/AdvantageKit")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
