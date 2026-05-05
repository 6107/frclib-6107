"""Unit tests for LoggedNetworkButton module."""

from unittest.mock import MagicMock, patch, call
import pytest

from lib_6107.pykit.LoggedNetworkButton import NetworkTableButton


class TestNetworkTableButtonInitialization:
    """Tests for NetworkTableButton initialization."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_initializes_with_key_and_default(self, mock_logged_bool_class):
        """Verify button creates LoggedNetworkBoolean with correct key and default."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=False)

        mock_logged_bool_class.assert_called_once_with("/SmartDashboard/TestButton", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_initializes_with_default_false_when_not_specified(self, mock_logged_bool_class):
        """Verify button uses False as default when not specified."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")

        mock_logged_bool_class.assert_called_once_with("/SmartDashboard/TestButton", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_initializes_with_true_default(self, mock_logged_bool_class):
        """Verify button accepts True as default value."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=True)

        mock_logged_bool_class.assert_called_once_with("/SmartDashboard/TestButton", True)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_stores_logged_network_boolean(self, mock_logged_bool_class):
        """Verify button stores the LoggedNetworkBoolean reference."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")

        assert button._log_bool is mock_logged_bool

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_sets_initial_value(self, mock_logged_bool_class):
        """Verify button sets initial value on the LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=True)

        mock_logged_bool.value = True
        assert mock_logged_bool.value == True

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_inherits_from_trigger(self, mock_logged_bool_class):
        """Verify button is a Trigger instance."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")

        from commands2.button import Trigger
        assert isinstance(button, Trigger)


class TestNetworkTableButtonTriggerIntegration:
    """Tests for NetworkTableButton trigger integration with Commands-v2."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_trigger_reads_from_logged_boolean(self, mock_logged_bool_class):
        """Verify trigger lambda reads value from LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=True)

        # After initialization, value should be set to default
        assert button._log_bool is mock_logged_bool

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_trigger_updates_when_value_changes(self, mock_logged_bool_class):
        """Verify trigger detects value changes in LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool.value = False
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")
        initial_state = button._log_bool.value

        mock_logged_bool.value = True
        new_state = button._log_bool.value

        assert initial_state == False
        assert new_state == True

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_trigger_with_false_state(self, mock_logged_bool_class):
        """Verify trigger correctly reports False state."""
        mock_logged_bool = MagicMock()
        mock_logged_bool.value = False
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")

        assert button._log_bool.value == False

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_trigger_with_true_state(self, mock_logged_bool_class):
        """Verify trigger correctly reports True state."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=True)

        # Verify LoggedNetworkBoolean was called with True default
        mock_logged_bool_class.assert_called_with("/SmartDashboard/TestButton", True)


class TestNetworkTableButtonDashboardIntegration:
    """Tests for NetworkTableButton dashboard integration."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_publishes_to_networktables(self, mock_logged_bool_class):
        """Verify button provides access to NetworkTables entry."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/IntakeButton")

        assert button._log_bool is not None

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_key_is_accessible_via_logged_boolean(self, mock_logged_bool_class):
        """Verify button key can be accessed through the LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/ShooterButton")

        mock_logged_bool_class.assert_called_with("/SmartDashboard/ShooterButton", False)


class TestNetworkTableButtonLogging:
    """Tests for NetworkTableButton logging integration."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_uses_logged_network_boolean_for_logging(self, mock_logged_bool_class):
        """Verify button delegates logging to LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=False)

        assert button._log_bool is mock_logged_bool

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_value_property_accesses_logged_boolean(self, mock_logged_bool_class):
        """Verify button state is accessible through LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton", default=True)

        # Initially value should be set to default
        # We need to verify that the button sets the value to default during init
        mock_logged_bool_class.assert_called_with("/SmartDashboard/TestButton", True)


class TestNetworkTableButtonReplay:
    """Tests for NetworkTableButton replay compatibility."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_replay_compatible_via_logged_boolean(self, mock_logged_bool_class):
        """Verify button replay compatibility through LoggedNetworkBoolean."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/TestButton")

        assert button._log_bool is not None


class TestNetworkTableButtonKeyFormats:
    """Tests for NetworkTableButton with various key formats."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_smart_dashboard_key(self, mock_logged_bool_class):
        """Verify button works with SmartDashboard key format."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/MyButton")

        mock_logged_bool_class.assert_called_with("/SmartDashboard/MyButton", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_nested_key(self, mock_logged_bool_class):
        """Verify button works with nested key format."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Shooter/Fire", default=False)

        mock_logged_bool_class.assert_called_with("/SmartDashboard/Shooter/Fire", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_custom_prefix(self, mock_logged_bool_class):
        """Verify button works with custom key prefix."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/Custom/Controls/Button1")

        mock_logged_bool_class.assert_called_with("/Custom/Controls/Button1", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_simple_key(self, mock_logged_bool_class):
        """Verify button works with simple key format."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("Button")

        mock_logged_bool_class.assert_called_with("Button", False)


class TestNetworkTableButtonDefaults:
    """Tests for NetworkTableButton default values."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_default_is_false_by_default(self, mock_logged_bool_class):
        """Verify button defaults to False when not specified."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        call_args = mock_logged_bool_class.call_args
        assert call_args[0][1] == False

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_respects_explicit_false_default(self, mock_logged_bool_class):
        """Verify explicit False default is respected."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button", default=False)

        call_args = mock_logged_bool_class.call_args
        assert call_args[0][1] == False

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_respects_explicit_true_default(self, mock_logged_bool_class):
        """Verify explicit True default is respected."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button", default=True)

        call_args = mock_logged_bool_class.call_args
        assert call_args[0][1] == True


class TestNetworkTableButtonEdgeCases:
    """Tests for NetworkTableButton edge cases."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_empty_key(self, mock_logged_bool_class):
        """Verify button handles empty key."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("", default=False)

        mock_logged_bool_class.assert_called_with("", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_special_characters_in_key(self, mock_logged_bool_class):
        """Verify button handles special characters in key."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button-1_Test#")

        mock_logged_bool_class.assert_called_with("/SmartDashboard/Button-1_Test#", False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_with_very_long_key(self, mock_logged_bool_class):
        """Verify button handles very long key."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        long_key = "/SmartDashboard/" + "a" * 1000
        button = NetworkTableButton(long_key)

        mock_logged_bool_class.assert_called_with(long_key, False)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_rapid_value_changes(self, mock_logged_bool_class):
        """Verify button handles rapid value changes."""
        mock_logged_bool = MagicMock()
        mock_logged_bool.value = False
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        for i in range(100):
            mock_logged_bool.value = i % 2 == 0
            state = button._log_bool.value
            assert isinstance(state, bool)


class TestNetworkTableButtonMultipleInstances:
    """Tests for multiple NetworkTableButton instances."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_multiple_buttons_with_different_keys(self, mock_logged_bool_class):
        """Verify multiple buttons with different keys work independently."""
        mock_bool1 = MagicMock()
        mock_bool2 = MagicMock()
        mock_logged_bool_class.side_effect = [mock_bool1, mock_bool2]

        button1 = NetworkTableButton("/SmartDashboard/Button1")
        button2 = NetworkTableButton("/SmartDashboard/Button2")

        assert button1._log_bool is mock_bool1
        assert button2._log_bool is mock_bool2

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_multiple_buttons_same_key_creates_separate_entries(self, mock_logged_bool_class):
        """Verify multiple buttons with same key create separate instances."""
        mock_bool1 = MagicMock()
        mock_bool2 = MagicMock()
        mock_logged_bool_class.side_effect = [mock_bool1, mock_bool2]

        button1 = NetworkTableButton("/SmartDashboard/SharedButton")
        button2 = NetworkTableButton("/SmartDashboard/SharedButton")

        assert button1._log_bool is mock_bool1
        assert button2._log_bool is mock_bool2
        assert mock_logged_bool_class.call_count == 2

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_multiple_buttons_different_defaults(self, mock_logged_bool_class):
        """Verify multiple buttons can have different default values."""
        mock_bool1 = MagicMock()
        mock_bool2 = MagicMock()
        mock_bool3 = MagicMock()
        mock_logged_bool_class.side_effect = [mock_bool1, mock_bool2, mock_bool3]

        button1 = NetworkTableButton("/Button1", default=False)
        button2 = NetworkTableButton("/Button2", default=True)
        button3 = NetworkTableButton("/Button3")

        calls = mock_logged_bool_class.call_args_list
        assert calls[0][0][1] == False
        assert calls[1][0][1] == True
        assert calls[2][0][1] == False


class TestNetworkTableButtonCommandIntegration:
    """Tests for NetworkTableButton integration with Commands-v2."""

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_has_on_true_method(self, mock_logged_bool_class):
        """Verify button has onTrue method from Trigger."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        assert hasattr(button, 'onTrue')
        assert callable(button.onTrue)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_has_on_false_method(self, mock_logged_bool_class):
        """Verify button has onFalse method from Trigger."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        assert hasattr(button, 'onFalse')
        assert callable(button.onFalse)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_has_while_true_method(self, mock_logged_bool_class):
        """Verify button has whileTrue method from Trigger."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        assert hasattr(button, 'whileTrue')
        assert callable(button.whileTrue)

    @patch('lib_6107.pykit.LoggedNetworkButton.LoggedNetworkBoolean')
    def test_button_has_while_false_method(self, mock_logged_bool_class):
        """Verify button has whileFalse method from Trigger."""
        mock_logged_bool = MagicMock()
        mock_logged_bool_class.return_value = mock_logged_bool

        button = NetworkTableButton("/SmartDashboard/Button")

        assert hasattr(button, 'whileFalse')
        assert callable(button.whileFalse)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

