"""Unit tests for loggedddashboardchooser module."""

from unittest.mock import MagicMock, patch, call
from enum import Enum
import unittest

from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser
from lib_6107.pykit.logtable import LogTable


class TestAutoMode(Enum):
    """Test enum for type-safe chooser tests."""
    NONE = 0
    SCORE = 1
    CROSS = 2


class LoggedDashboardChooserStringTests(unittest.TestCase):
    """Tests for LoggedDashboardChooser with string values."""

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def chooser_initializes_with_key(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify chooser stores the key and publishes to SmartDashboard."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser

        chooser = LoggedDashboardChooser[str]("TestKey")

        assert chooser.key == "TestKey"
        mock_dashboard.putData.assert_called_once_with("TestKey", mock_chooser)
        mock_logger.registerDashboardInput.assert_called_once_with(chooser)

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def add_option_stores_value_mapping(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify addOption stores the key-value mapping."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")

        chooser.addOption("Drive", "drive_mode")

        assert chooser.options["Drive"] == "drive_mode"
        mock_chooser.addOption.assert_called_with("Drive", "Drive")

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def set_default_option_stores_mapping(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify setDefaultOption stores the key-value mapping."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")

        chooser.setDefaultOption("None", "none_mode")

        assert chooser.options["None"] == "none_mode"
        mock_chooser.setDefaultOption.assert_called_with("None", "None")

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def get_selected_returns_value_for_key(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify get_selected returns the value for the current selection key."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.addOption("Drive", "drive_value")
        chooser.selected_value = "Drive"

        result = chooser.get_selected()

        assert result == "drive_value"

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def get_selected_returns_none_when_key_not_in_options(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify get_selected returns None when selection key not found."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.selected_value = "NonExistent"

        result = chooser.get_selected()

        assert result is None

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def get_selected_raises_when_selected_value_is_none(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify get_selected raises ValueError when selected_value is None."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.selected_value = None

        with self.assertRaises(ValueError):
            chooser.get_selected()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_reads_from_sendable_chooser_in_normal_mode(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic reads from SmartDashboard when not in replay mode."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "NewSelection"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.selected_value = ""

        chooser.periodic()

        mock_chooser.getSelected.assert_called()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_normalizes_none_to_empty_string(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic converts None selected_value to empty string."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = None
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")

        chooser.periodic()

        assert chooser.selected_value == ""

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_calls_logger_process_inputs(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic calls Logger.processInputs for logging integration."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "selected"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")

        chooser.periodic()

        mock_logger.processInputs.assert_called()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_invokes_callback_when_selection_changes(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic invokes callback when selection changes."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "NewSelection"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.addOption("NewSelection", "new_value")
        chooser.selected_value = "OldSelection"
        callback = MagicMock()
        chooser.listener = callback

        chooser.periodic()

        callback.assert_called_once()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_does_not_invoke_callback_when_selection_unchanged(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic does not invoke callback when selection stays same."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "SameSelection"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.addOption("SameSelection", "value")
        chooser.selected_value = "SameSelection"
        chooser.previous_value = "SameSelection"
        callback = MagicMock()
        chooser.listener = callback

        chooser.periodic()

        callback.assert_not_called()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_does_not_invoke_callback_when_no_listener_registered(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic does not fail when no callback registered."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "NewSelection"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.addOption("NewSelection", "value")
        chooser.listener = None

        chooser.periodic()  # Should not raise

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_updates_previous_value_after_cycle(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic updates previous_value for next cycle comparison."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "NewSelection"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.addOption("NewSelection", "value")

        chooser.periodic()

        assert chooser.previous_value == "NewSelection"

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def on_change_registers_callback(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify onChange stores the callback."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")
        callback = MagicMock()

        chooser.onChange(callback)

        assert chooser.listener is callback

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def on_change_replaces_previous_callback(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify onChange replaces any previously registered callback."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("Test")
        old_callback = MagicMock()
        new_callback = MagicMock()
        chooser.listener = old_callback

        chooser.onChange(new_callback)

        assert chooser.listener is new_callback

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def to_log_writes_selection_to_table(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify to_log writes the selected_value to the log table."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("MyChooser")
        chooser.selected_value = "MySelection"
        mock_table = MagicMock()

        chooser.to_log(mock_table, "/SmartDashboard")

        mock_table.put.assert_called_with("/SmartDashboard/MyChooser", "MySelection")

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def from_log_reads_selection_from_table(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify from_log reads selected_value from the log table."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("MyChooser")
        chooser.selected_value = "OldSelection"
        mock_table = MagicMock()
        mock_table.get.return_value = "LoggedSelection"

        chooser.from_log(mock_table, "/SmartDashboard")

        assert chooser.selected_value == "LoggedSelection"

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def from_log_uses_fallback_when_key_missing(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify from_log falls back to current value when log entry missing."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[str]("MyChooser")
        chooser.selected_value = "CurrentValue"
        mock_table = MagicMock()
        mock_table.get.side_effect = lambda key, default: default

        chooser.from_log(mock_table, "/SmartDashboard")

        assert chooser.selected_value == "CurrentValue"


class LoggedDashboardChooserEnumTests(unittest.TestCase):
    """Tests for LoggedDashboardChooser with enum values."""

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def add_option_with_enum_value(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify addOption works with enum values."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[TestAutoMode]("Auto")

        chooser.addOption("Score", TestAutoMode.SCORE)

        assert chooser.options["Score"] == TestAutoMode.SCORE

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def get_selected_returns_enum_value(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify get_selected returns the typed enum value."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        chooser = LoggedDashboardChooser[TestAutoMode]("Auto")
        chooser.addOption("Score", TestAutoMode.SCORE)
        chooser.selected_value = "Score"

        result = chooser.get_selected()

        assert result == TestAutoMode.SCORE

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def callback_receives_enum_value(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify callback receives the typed enum value."""
        mock_chooser = MagicMock()
        mock_chooser.getSelected.return_value = "Score"
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = False
        chooser = LoggedDashboardChooser[TestAutoMode]("Auto")
        chooser.addOption("Score", TestAutoMode.SCORE)
        chooser.selected_value = "None"
        callback = MagicMock()
        chooser.listener = callback

        chooser.periodic()

        callback.assert_called_once_with(TestAutoMode.SCORE)


class LoggedDashboardChooserReplayModeTests(unittest.TestCase):
    """Tests for LoggedDashboardChooser in replay mode."""

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_does_not_read_sendable_chooser_in_replay_mode(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic skips SmartDashboard read when in replay mode."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = True
        chooser = LoggedDashboardChooser[str]("Test")
        chooser.selected_value = "PreviousSelection"

        chooser.periodic()

        mock_chooser.getSelected.assert_not_called()

    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.Logger')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SmartDashboard')
    @patch('lib_6107.pykit.networktables.loggeddashboardchooser.SendableChooser')
    def periodic_processes_inputs_in_replay_mode(self, mock_chooser_class, mock_dashboard, mock_logger):
        """Verify periodic still calls processInputs in replay mode."""
        mock_chooser = MagicMock()
        mock_chooser_class.return_value = mock_chooser
        mock_logger.isReplay.return_value = True
        chooser = LoggedDashboardChooser[str]("Test")

        chooser.periodic()

        mock_logger.processInputs.assert_called()


if __name__ == '__main__':
    unittest.main()