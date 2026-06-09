"""Unit tests for loggednetworkstring module using pytest framework."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.networktables.loggednetworkstring import LoggedNetworkString


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_network_table_instance():
    """Create a mock NetworkTableInstance."""
    with patch('lib_6107.pykit.networktables.loggednetworkstring.NetworkTableInstance') as mock_nt:
        yield mock_nt


@pytest.fixture
def mock_string_entry():
    """Create a mock StringEntry."""
    return MagicMock()


@pytest.fixture
def mock_string_topic(mock_string_entry):
    """Create a mock StringTopic that returns mock_string_entry."""
    mock_topic = MagicMock()
    mock_topic.getEntry.return_value = mock_string_entry
    return mock_topic


@pytest.fixture
def mock_logger():
    """Create a mock Logger."""
    with patch('lib_6107.pykit.networktables.loggednetworkvalue.Logger') as logger:
        yield logger


@pytest.fixture
def setup_network_table_instance(mock_network_table_instance, mock_string_topic):
    """Setup the mock NetworkTableInstance chain for LoggedNetworkString initialization."""
    mock_instance = MagicMock()
    mock_instance.getStringTopic.return_value = mock_string_topic
    mock_network_table_instance.getDefault.return_value = mock_instance
    return mock_network_table_instance


@pytest.fixture
def logged_string_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkString with default parameters."""
    return LoggedNetworkString("TestKey", default="DefaultValue")


@pytest.fixture
def logged_string_empty(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkString with empty string default."""
    return LoggedNetworkString("TestKey", default="")


@pytest.fixture
def logged_string_no_default(setup_network_table_instance, mock_logger):
    """Create a LoggedNetworkString without specifying default."""
    return LoggedNetworkString("TestKey")


# ============================================================================
# Initialization Tests
# ============================================================================

class TestLoggedNetworkStringInitialization:
    """Test LoggedNetworkString initialization behavior."""

    def test_creates_string_entry_via_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify __init__ creates a StringEntry through NetworkTableInstance chain."""
        key = "Robot/State"
        default = "Idle"

        string_value = LoggedNetworkString(key, default)

        setup_network_table_instance.getDefault.assert_called_once()

    def test_retrieves_string_topic_with_correct_key(self, setup_network_table_instance, mock_logger):
        """Verify __init__ retrieves StringTopic with the provided key."""
        key = "Robot/State"
        default = "Idle"
        mock_instance = setup_network_table_instance.getDefault.return_value

        string_value = LoggedNetworkString(key, default)

        mock_instance.getStringTopic.assert_called_once_with(key)

    def test_calls_get_entry_with_default_value(self, setup_network_table_instance, mock_logger):
        """Verify __init__ calls getEntry with default value."""
        key = "Robot/State"
        default = "Ready"
        mock_topic = setup_network_table_instance.getDefault.return_value.getStringTopic.return_value

        string_value = LoggedNetworkString(key, default)

        mock_topic.getEntry.assert_called_once_with(default)

    def test_stores_entry_reference(self, setup_network_table_instance, mock_logger, mock_string_entry):
        """Verify __init__ stores the StringEntry reference."""
        string_value = LoggedNetworkString("TestKey", "value")

        assert string_value._entry == mock_string_entry

    def test_initializes_with_string_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization with string default value."""
        string_value = LoggedNetworkString("status", "Ready")

        assert string_value._default == "Ready"

    def test_accepts_empty_string_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts empty string as default."""
        string_value = LoggedNetworkString("optional", "")

        assert string_value._default == ""

    def test_uses_empty_string_default_when_not_specified(self, setup_network_table_instance, mock_logger):
        """Verify initialization uses empty string as default when not provided."""
        string_value = LoggedNetworkString("TestKey")

        assert string_value._default == ""

    def test_accepts_multiline_string_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts multiline string as default."""
        multiline = "Line1\nLine2\nLine3"
        string_value = LoggedNetworkString("text", multiline)

        assert string_value._default == multiline

    def test_accepts_very_long_string_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts very long string as default."""
        long_string = "x" * 10000
        string_value = LoggedNetworkString("long", long_string)

        assert string_value._default == long_string

    def test_accepts_unicode_string_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts Unicode characters in default."""
        unicode_string = "レボット 机器人 روبوت 🤖"
        string_value = LoggedNetworkString("unicode", unicode_string)

        assert string_value._default == unicode_string

    def test_accepts_special_characters_default(self, setup_network_table_instance, mock_logger):
        """Verify initialization accepts special characters as default."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        string_value = LoggedNetworkString("special", special)

        assert string_value._default == special

    @pytest.mark.parametrize("key", [
        "SimpleKey",
        "/SmartDashboard/Robot/State",
        "Subsystem/Message",
        "Test/Deep/Nested/Key",
        "Diagnostics/Error",
    ])
    def test_handles_various_key_formats(self, setup_network_table_instance, mock_logger, key):
        """Verify initialization handles various key formats."""
        string_value = LoggedNetworkString(key, "value")

        assert string_value._key == key

    @pytest.mark.parametrize("key,default", [
        ("status", "Ready"),
        ("message", "Processing"),
        ("game_data", "RGR"),
        ("error", ""),
        ("version", "2026.1.0"),
    ])
    def test_initialization_with_different_values(self, setup_network_table_instance, mock_logger, key, default):
        """Verify initialization with various key and default combinations."""
        string_value = LoggedNetworkString(key, default)

        assert string_value._key == key
        assert string_value._default == default


# ============================================================================
# Entry Type Tests
# ============================================================================

class TestLoggedNetworkStringEntryType:
    """Test that LoggedNetworkString creates correct entry types."""

    def test_creates_string_entry_not_other_types(self, setup_network_table_instance, mock_logger):
        """Verify the entry type is specifically StringEntry."""
        string_value = LoggedNetworkString("TestKey", "value")

        setup_network_table_instance.getDefault.return_value.getStringTopic.assert_called_once()
        setup_network_table_instance.getDefault.return_value.getDoubleTopic.assert_not_called()

    def test_string_entry_created_regardless_of_content(self, setup_network_table_instance, mock_logger):
        """Verify StringEntry created for any string content."""
        string_value = LoggedNetworkString("TestKey", "")

        assert setup_network_table_instance.getDefault.return_value.getStringTopic.called


# ============================================================================
# Parent Class Integration Tests
# ============================================================================

class TestLoggedNetworkStringParentIntegration:
    """Test LoggedNetworkString integration with LoggedNetworkValue parent class."""

    def test_inherits_value_property_from_parent(self, logged_string_default):
        """Verify value property is inherited from parent class."""
        logged_string_default._value = "TestValue"

        assert logged_string_default.value == "TestValue"

    def test_inherits_value_property_setter(self, logged_string_default):
        """Verify value property setter is inherited from parent class."""
        logged_string_default.value = "NewValue"

        assert logged_string_default._value == "NewValue"

    def test_inherits_callable_interface(self, logged_string_default):
        """Verify callable interface is inherited from parent class."""
        logged_string_default._value = "CallableValue"

        result = logged_string_default()

        assert result == "CallableValue"

    def test_inherits_to_log_method(self, logged_string_default):
        """Verify to_log method is inherited from parent class."""
        assert hasattr(logged_string_default, 'to_log')
        assert callable(logged_string_default.to_log)

    def test_inherits_from_log_method(self, logged_string_default):
        """Verify from_log method is inherited from parent class."""
        assert hasattr(logged_string_default, 'from_log')
        assert callable(logged_string_default.from_log)

    def test_inherits_periodic_method(self, logged_string_default):
        """Verify periodic method is inherited from parent class."""
        assert hasattr(logged_string_default, 'periodic')
        assert callable(logged_string_default.periodic)

    def test_inherits_set_default_method(self, logged_string_default):
        """Verify set_default method is inherited from parent class."""
        assert hasattr(logged_string_default, 'set_default')
        assert callable(logged_string_default.set_default)


# ============================================================================
# String Value Tests
# ============================================================================

class TestLoggedNetworkStringValues:
    """Test LoggedNetworkString string value handling."""

    def test_stores_simple_string_values(self, logged_string_default):
        """Verify simple string values are stored correctly."""
        logged_string_default.value = "SimpleString"

        assert logged_string_default.value == "SimpleString"

    def test_stores_empty_string_values(self, logged_string_default):
        """Verify empty string values are stored correctly."""
        logged_string_default.value = ""

        assert logged_string_default.value == ""

    def test_stores_numeric_string_values(self, logged_string_default):
        """Verify numeric strings are stored as strings, not converted."""
        logged_string_default.value = "12345"

        assert logged_string_default.value == "12345"
        assert isinstance(logged_string_default.value, str)

    def test_stores_whitespace_string_values(self, logged_string_default):
        """Verify whitespace-only strings are stored correctly."""
        logged_string_default.value = "   "

        assert logged_string_default.value == "   "

    def test_stores_multiline_string_values(self, logged_string_default):
        """Verify multiline strings are stored correctly."""
        multiline = "Line1\nLine2\nLine3"
        logged_string_default.value = multiline

        assert logged_string_default.value == multiline

    def test_stores_unicode_string_values(self, logged_string_default):
        """Verify Unicode strings are stored correctly."""
        unicode_string = "レボット 机器人 روبوت 🤖"
        logged_string_default.value = unicode_string

        assert logged_string_default.value == unicode_string

    def test_stores_special_characters_string_values(self, logged_string_default):
        """Verify special character strings are stored correctly."""
        special = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        logged_string_default.value = special

        assert logged_string_default.value == special

    def test_stores_tab_and_escape_sequences(self, logged_string_default):
        """Verify tab and escape sequences are stored correctly."""
        escaped = "Text\twith\ttabs\nand\nnewlines"
        logged_string_default.value = escaped

        assert logged_string_default.value == escaped

    def test_stores_very_long_string_values(self, logged_string_default):
        """Verify very long strings are stored correctly."""
        long_string = "x" * 100000
        logged_string_default.value = long_string

        assert logged_string_default.value == long_string
        assert len(logged_string_default.value) == 100000


# ============================================================================
# Edge Cases
# ============================================================================

class TestLoggedNetworkStringEdgeCases:
    """Test LoggedNetworkString edge cases."""

    def test_empty_string_is_valid_default(self, logged_string_empty):
        """Verify empty string is a valid default value."""
        assert logged_string_empty._default == ""

    def test_empty_string_is_implicit_default(self, logged_string_no_default):
        """Verify empty string is used when no default specified."""
        assert logged_string_no_default._default == ""

    def test_stores_null_like_string_value(self, logged_string_default):
        """Verify string "null" is stored, not converted to None."""
        logged_string_default.value = "null"

        assert logged_string_default.value == "null"
        assert logged_string_default.value is not None

    def test_stores_none_like_string_value(self, logged_string_default):
        """Verify string "None" is stored, not converted to None."""
        logged_string_default.value = "None"

        assert logged_string_default.value == "None"
        assert logged_string_default.value is not None

    def test_stores_false_like_string_value(self, logged_string_default):
        """Verify string "False" is stored as string, not boolean."""
        logged_string_default.value = "False"

        assert logged_string_default.value == "False"
        assert isinstance(logged_string_default.value, str)

    def test_stores_zero_string_value(self, logged_string_default):
        """Verify string "0" is stored as string."""
        logged_string_default.value = "0"

        assert logged_string_default.value == "0"

    def test_string_value_replacement(self, logged_string_default):
        """Verify string values can be replaced multiple times."""
        logged_string_default.value = "First"
        assert logged_string_default.value == "First"

        logged_string_default.value = "Second"
        assert logged_string_default.value == "Second"

        logged_string_default.value = "Third"
        assert logged_string_default.value == "Third"

    def test_multiple_strings_independent(self, setup_network_table_instance, mock_logger):
        """Verify multiple LoggedNetworkString instances are independent."""
        string1 = LoggedNetworkString("key1", "Value1")
        string2 = LoggedNetworkString("key2", "Value2")

        string1.value = "Modified1"

        assert string1.value == "Modified1"
        assert string2.value == "Value2"

    def test_repeated_initialization_different_keys(self, setup_network_table_instance, mock_logger):
        """Verify multiple strings with different keys work independently."""
        mock_instance = setup_network_table_instance.getDefault.return_value

        string1 = LoggedNetworkString("FirstKey", "Val1")
        string2 = LoggedNetworkString("SecondKey", "Val2")

        assert mock_instance.getStringTopic.call_count == 2


# ============================================================================
# Key Format Tests
# ============================================================================

class TestLoggedNetworkStringKeyFormats:
    """Test LoggedNetworkString with various key formats."""

    def test_simple_key_without_slashes(self, setup_network_table_instance, mock_logger):
        """Verify simple key without slashes."""
        string_value = LoggedNetworkString("Status", "Ready")

        assert string_value._key == "Status"

    def test_key_with_leading_slash(self, setup_network_table_instance, mock_logger):
        """Verify key with leading slash."""
        string_value = LoggedNetworkString("/SmartDashboard/Robot/State", "Running")

        assert string_value._key == "/SmartDashboard/Robot/State"

    def test_hierarchical_key_multiple_levels(self, setup_network_table_instance, mock_logger):
        """Verify hierarchical key with multiple levels."""
        key = "Diagnostics/LastError/Message"
        string_value = LoggedNetworkString(key, "OK")

        assert string_value._key == key

    def test_key_stored_in_parent_class(self, logged_string_default):
        """Verify key is stored in parent class."""
        assert logged_string_default._key == "TestKey"

    def test_key_passed_to_network_tables(self, setup_network_table_instance, mock_logger):
        """Verify key is passed to NetworkTables during initialization."""
        key = "Match/GameData"
        LoggedNetworkString(key, "RGR")

        mock_instance = setup_network_table_instance.getDefault.return_value
        mock_instance.getStringTopic.assert_called_with(key)


# ============================================================================
# Default Value Tests
# ============================================================================

class TestLoggedNetworkStringDefaults:
    """Test LoggedNetworkString default value handling."""

    def test_empty_string_is_valid_default(self, setup_network_table_instance, mock_logger):
        """Verify empty string is a valid default value."""
        string_value = LoggedNetworkString("key", "")

        assert string_value._default == ""

    def test_default_affects_initialization(self, setup_network_table_instance, mock_logger):
        """Verify default value is passed to getEntry."""
        default_value = "DefaultStatus"
        mock_topic = setup_network_table_instance.getDefault.return_value.getStringTopic.return_value

        LoggedNetworkString("key", default_value)

        mock_topic.getEntry.assert_called_once_with(default_value)

    def test_explicit_default_overrides_implicit(self, setup_network_table_instance, mock_logger):
        """Verify explicit default is used when specified."""
        string_value = LoggedNetworkString("key", "CustomDefault")

        assert string_value._default == "CustomDefault"

    def test_default_used_for_parent_initialization(self, logged_string_default):
        """Verify default is stored for parent class fallback."""
        assert logged_string_default._default == "DefaultValue"

    def test_different_defaults_for_different_instances(self, setup_network_table_instance, mock_logger):
        """Verify different instances can have different defaults."""
        string1 = LoggedNetworkString("key1", "Default1")
        string2 = LoggedNetworkString("key2", "Default2")

        assert string1._default == "Default1"
        assert string2._default == "Default2"

    def test_unicode_default_values(self, setup_network_table_instance, mock_logger):
        """Verify Unicode default values are stored correctly."""
        unicode_default = "チーム6107"
        string_value = LoggedNetworkString("key", unicode_default)

        assert string_value._default == unicode_default

    def test_whitespace_only_default(self, setup_network_table_instance, mock_logger):
        """Verify whitespace-only default is valid."""
        whitespace_default = "   \t\n"
        string_value = LoggedNetworkString("key", whitespace_default)

        assert string_value._default == whitespace_default


# ============================================================================
# Unicode and International Tests
# ============================================================================

class TestLoggedNetworkStringUnicode:
    """Test LoggedNetworkString Unicode and international character support."""

    def test_stores_chinese_characters(self, logged_string_default):
        """Verify Chinese characters are stored correctly."""
        logged_string_default.value = "机器人编程"

        assert logged_string_default.value == "机器人编程"

    def test_stores_arabic_characters(self, logged_string_default):
        """Verify Arabic characters are stored correctly."""
        logged_string_default.value = "روبوت"

        assert logged_string_default.value == "روبوت"

    def test_stores_japanese_hiragana(self, logged_string_default):
        """Verify Japanese hiragana is stored correctly."""
        logged_string_default.value = "ひらがな"

        assert logged_string_default.value == "ひらがな"

    def test_stores_japanese_katakana(self, logged_string_default):
        """Verify Japanese katakana is stored correctly."""
        logged_string_default.value = "カタカナ"

        assert logged_string_default.value == "カタカナ"

    def test_stores_emoji_characters(self, logged_string_default):
        """Verify emoji characters are stored correctly."""
        logged_string_default.value = "🤖🎮🏆"

        assert logged_string_default.value == "🤖🎮🏆"

    def test_stores_mixed_unicode_languages(self, logged_string_default):
        """Verify mixed Unicode from multiple languages."""
        logged_string_default.value = "Team 6107 チーム 机器人 روبوت 🤖"

        assert logged_string_default.value == "Team 6107 チーム 机器人 روبوت 🤖"

    def test_stores_accented_characters(self, logged_string_default):
        """Verify accented Roman characters are stored correctly."""
        logged_string_default.value = "café naïve résumé"

        assert logged_string_default.value == "café naïve résumé"

    def test_stores_combining_diacritical_marks(self, logged_string_default):
        """Verify combining diacritical marks are stored correctly."""
        logged_string_default.value = "e\u0301"  # e with acute accent

        assert logged_string_default.value == "e\u0301"


# ============================================================================
# FRC Game Data Tests
# ============================================================================

class TestLoggedNetworkStringGameData:
    """Test LoggedNetworkString with typical FRC game data patterns."""

    def test_stores_frc_game_data_format(self, logged_string_default):
        """Verify typical FRC game data format (e.g., 'RGR')."""
        logged_string_default.value = "RGR"

        assert logged_string_default.value == "RGR"

    def test_stores_robot_status_messages(self, logged_string_default):
        """Verify robot status messages."""
        statuses = ["Idle", "Running", "Error: Motor 3", "Searching for Target"]
        for status in statuses:
            logged_string_default.value = status
            assert logged_string_default.value == status

    def test_stores_version_strings(self, logged_string_default):
        """Verify version string format."""
        logged_string_default.value = "2026.1.0.3"

        assert logged_string_default.value == "2026.1.0.3"

    def test_stores_iso_8601_timestamp(self, logged_string_default):
        """Verify ISO 8601 format timestamps."""
        logged_string_default.value = "2026-03-15T14:30:45Z"

        assert logged_string_default.value == "2026-03-15T14:30:45Z"

    def test_stores_strategy_names(self, logged_string_default):
        """Verify autonomous strategy names."""
        strategies = ["Aggressive", "Conservative", "Score", "Avoid"]
        for strategy in strategies:
            logged_string_default.value = strategy
            assert logged_string_default.value == strategy


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
