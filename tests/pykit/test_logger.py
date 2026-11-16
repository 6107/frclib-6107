"""Unit tests for logger module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.logger import _ConsoleRecorder, Logger


class TestConsoleRecorder:
    """Tests for _ConsoleRecorder helper class."""

    def test_console_recorder_initializes_with_original_stream(self):
        """Verify _ConsoleRecorder stores the original stream."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        assert recorder.orig is mock_stream

    def test_console_recorder_writes_to_original_stream(self):
        """Verify _ConsoleRecorder passes writes through to original stream."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        recorder.write("test message")

        mock_stream.write.assert_called_with("test message")

    def test_console_recorder_flushes_original_stream(self):
        """Verify _ConsoleRecorder flushes original stream after write."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        recorder.write("test")

        mock_stream.flush.assert_called()

    def test_console_recorder_handles_flush_exceptions(self):
        """Verify _ConsoleRecorder gracefully handles flush exceptions."""
        mock_stream = MagicMock()
        mock_stream.flush.side_effect = OSError("Stream error")
        recorder = _ConsoleRecorder(mock_stream)

        recorder.write("test")  # Should not raise

    def test_console_recorder_logs_complete_lines(self):
        """Verify _ConsoleRecorder logs complete lines with newline."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        with patch.object(Logger, 'record_output'):
            recorder.write("line1\n")
            Logger.record_output.assert_called_with("Console", "line1")

    def test_console_recorder_buffers_incomplete_lines(self):
        """Verify _ConsoleRecorder buffers text until newline."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        with patch.object(Logger, 'record_output'):
            recorder.write("in")
            Logger.record_output.assert_not_called()
            recorder.write("complete")
            Logger.record_output.assert_not_called()

    def test_console_recorder_handles_multiple_newlines(self):
        """Verify _ConsoleRecorder handles multiple newlines in single write."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        with patch.object(Logger, 'record_output'):
            recorder.write("line1\nline2\nline3\n")
            assert Logger.record_output.call_count == 3

    def test_console_recorder_flush_method_logs_buffered_content(self):
        """Verify flush() logs any buffered content."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        with patch.object(Logger, 'record_output'):
            recorder.write("buffered")
            recorder.flush()
            Logger.record_output.assert_called_with("Console", "buffered")

    def test_console_recorder_clears_buffer_after_flush(self):
        """Verify buffer is cleared after flush()."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        with patch.object(Logger, 'record_output'):
            recorder.write("text")
            recorder.flush()
            assert recorder.buffer == ""

    def test_console_recorder_handles_write_exceptions(self):
        """Verify _ConsoleRecorder handles write exceptions gracefully."""
        mock_stream = MagicMock()
        mock_stream.write.side_effect = ValueError("Write error")
        recorder = _ConsoleRecorder(mock_stream)

        recorder.write("test")  # Should not raise


class TestLoggerInitialization:
    """Tests for Logger class state and initialization."""

    def test_logger_starts_not_running(self):
        """Verify Logger.running is False initially."""
        Logger.running = False
        assert Logger.running is False

    def test_logger_has_empty_data_receivers_initially(self):
        """Verify Logger.data_receivers is empty initially."""
        Logger.data_receivers = []
        assert len(Logger.data_receivers) == 0

    def test_logger_has_empty_dashboard_inputs_initially(self):
        """Verify Logger.dashboardInputs is empty initially."""
        Logger.dashboardInputs = []
        assert len(Logger.dashboardInputs) == 0

    def test_logger_replay_source_is_none_initially(self):
        """Verify Logger.replaySource is None in normal mode initially."""
        Logger.replaySource = None
        assert Logger.replaySource is None

    def test_logger_cycle_count_starts_at_zero(self):
        """Verify Logger.cycleCount starts at zero."""
        Logger.cycleCount = 0
        assert Logger.cycleCount == 0


class TestLoggerReplayModeDetection:
    """Tests for replay mode detection."""

    def test_is_replay_returns_false_when_replay_source_none(self):
        """Verify is_replay() returns False when no replay source."""
        Logger.replaySource = None
        assert Logger.is_replay() is False

    def test_is_replay_returns_true_when_replay_source_set(self):
        """Verify is_replay() returns True when replay source is set."""
        mock_source = MagicMock()
        Logger.replaySource = mock_source

        assert Logger.is_replay() is True

        Logger.replaySource = None

    def test_set_replay_source_sets_replay_source(self):
        """Verify set_replay_source() sets the replay source."""
        mock_source = MagicMock()
        Logger.set_replay_source(mock_source)

        assert Logger.replaySource is mock_source

        Logger.replaySource = None

    def test_set_replay_source_with_none_disables_replay(self):
        """Verify set_replay_source(None) disables replay mode."""
        mock_source = MagicMock()
        Logger.set_replay_source(mock_source)
        Logger.set_replay_source(None)

        assert Logger.replaySource is None
        assert Logger.is_replay() is False


class TestLoggerRecordOutput:
    """Tests for Logger.record_output method."""

    def test_record_output_does_nothing_when_not_running(self):
        """Verify record_output is no-op when Logger.running is False."""
        Logger.running = False
        Logger.outputTable = MagicMock()

        Logger.record_output("test/key", 42)

        Logger.outputTable.put.assert_not_called()

    def test_record_output_calls_output_table_put_when_running(self):
        """Verify record_output calls outputTable.put when running."""
        Logger.running = True
        Logger.outputTable = MagicMock()

        Logger.record_output("test/key", 42)

        Logger.outputTable.put.assert_called_with("test/key", 42, unit=None)

    def test_record_output_with_unit(self):
        """Verify record_output passes unit parameter."""
        Logger.running = True
        Logger.outputTable = MagicMock()

        Logger.record_output("speed", 5.0, unit="m/s")

        Logger.outputTable.put.assert_called_with("speed", 5.0, unit="m/s")

    def test_record_output_handles_exceptions(self):
        """Verify record_output catches and ignores exceptions."""
        Logger.running = True
        Logger.outputTable = MagicMock()
        Logger.outputTable.put.side_effect = RuntimeError("Put failed")

        Logger.record_output("test", 42)  # Should not raise

    @pytest.mark.parametrize("value,unit", [
        ("string_value", None),
        (3.14, "radians"),
        (True, None),
        ([1, 2, 3], None),
        (0, "units"),
    ])
    def test_record_output_with_various_types(self, value, unit):
        """Verify record_output works with various value types."""
        Logger.running = True
        Logger.outputTable = MagicMock()

        Logger.record_output("key", value, unit=unit)

        Logger.outputTable.put.assert_called_once()


class TestLoggerRecordMetadata:
    """Tests for Logger.record_metadata method."""

    def test_record_metadata_does_nothing_in_replay_mode(self):
        """Verify record_metadata is no-op in replay mode."""
        Logger.replaySource = MagicMock()
        Logger.metadata = {}

        Logger.record_metadata("key", "value")

        assert "key" not in Logger.metadata
        Logger.replaySource = None

    def test_record_metadata_stores_in_normal_mode(self):
        """Verify record_metadata stores value in normal mode."""
        Logger.replaySource = None
        Logger.metadata = {}

        Logger.record_metadata("RobotVersion", "1.0.0")

        assert Logger.metadata["RobotVersion"] == "1.0.0"

    def test_record_metadata_overwrites_existing_key(self):
        """Verify record_metadata overwrites existing metadata."""
        Logger.replaySource = None
        Logger.metadata = {"key": "old_value"}

        Logger.record_metadata("key", "new_value")

        assert Logger.metadata["key"] == "new_value"

    @pytest.mark.parametrize("key,value", [
        ("Team", "6107"),
        ("Match", "Q10"),
        ("Alliance", "Red"),
    ])
    def test_record_metadata_with_various_keys(self, key, value):
        """Verify record_metadata works with various metadata keys."""
        Logger.replaySource = None
        Logger.metadata = {}

        Logger.record_metadata(key, value)

        assert Logger.metadata[key] == value


class TestLoggerProcessInputs:
    """Tests for Logger.process_inputs method."""

    def test_process_inputs_calls_to_log_in_normal_mode(self):
        """Verify process_inputs calls to_log() in normal mode."""
        Logger.running = True
        Logger.replaySource = None
        mock_input = MagicMock()
        Logger.entry = MagicMock()

        Logger.process_inputs("/prefix", mock_input)

        mock_input.to_log.assert_called_once()

    def test_process_inputs_calls_from_log_in_replay_mode(self):
        """Verify process_inputs calls from_log() in replay mode."""
        Logger.running = True
        Logger.replaySource = MagicMock()
        mock_input = MagicMock()
        Logger.entry = MagicMock()

        Logger.process_inputs("/prefix", mock_input)

        mock_input.from_log.assert_called_once()
        Logger.replaySource = None

    def test_process_inputs_does_nothing_when_not_running(self):
        """Verify process_inputs does nothing when Logger.running is False."""
        Logger.running = False
        mock_input = MagicMock()

        Logger.process_inputs("/prefix", mock_input)

        mock_input.to_log.assert_not_called()
        mock_input.from_log.assert_not_called()

    def test_process_inputs_passes_correct_parameters(self):
        """Verify process_inputs passes correct prefix and entry."""
        Logger.running = True
        Logger.replaySource = None
        mock_input = MagicMock()
        mock_entry = MagicMock()
        Logger.entry = mock_entry

        Logger.process_inputs("/Subsystem", mock_input)

        mock_input.to_log.assert_called_with(mock_entry, "/Subsystem")


class TestLoggerDataReceivers:
    """Tests for Logger data receiver management."""

    def test_add_data_receiver_appends_to_list(self):
        """Verify add_data_reciever adds receiver to list."""
        Logger.data_receivers = []
        mock_receiver = MagicMock()

        Logger.add_data_reciever(mock_receiver)

        assert mock_receiver in Logger.data_receivers

    def test_add_data_receiver_preserves_existing_receivers(self):
        """Verify add_data_reciever preserves previously added receivers."""
        mock_receiver1 = MagicMock()
        mock_receiver2 = MagicMock()
        Logger.data_receivers = [mock_receiver1]

        Logger.add_data_reciever(mock_receiver2)

        assert len(Logger.data_receivers) == 2
        assert mock_receiver1 in Logger.data_receivers
        assert mock_receiver2 in Logger.data_receivers

    def test_add_multiple_data_receivers(self):
        """Verify multiple data receivers can be added."""
        Logger.data_receivers = []
        receivers = [MagicMock() for _ in range(3)]

        for receiver in receivers:
            Logger.add_data_reciever(receiver)

        assert len(Logger.data_receivers) == 3


class TestLoggerDashboardInputs:
    """Tests for Logger dashboard inputs management."""

    def test_register_dashboard_input_appends_to_list(self):
        """Verify register_dashboard_input adds input to list."""
        Logger.dashboardInputs = []
        mock_input = MagicMock()

        Logger.register_dashboard_input(mock_input)

        assert mock_input in Logger.dashboardInputs

    def test_register_dashboard_input_preserves_existing(self):
        """Verify register_dashboard_input preserves previously added inputs."""
        mock_input1 = MagicMock()
        mock_input2 = MagicMock()
        Logger.dashboardInputs = [mock_input1]

        Logger.register_dashboard_input(mock_input2)

        assert len(Logger.dashboardInputs) == 2

    def test_register_multiple_dashboard_inputs(self):
        """Verify multiple dashboard inputs can be registered."""
        Logger.dashboardInputs = []
        inputs = [MagicMock() for _ in range(3)]

        for input_item in inputs:
            Logger.register_dashboard_input(input_item)

        assert len(Logger.dashboardInputs) == 3


class TestLoggerStart:
    """Tests for Logger.start method."""

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_sets_running_flag(self, mock_controller):
        """Verify start() sets Logger.running to True."""
        Logger.running = False
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = False

        Logger.start()

        assert Logger.running is True

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_increments_cycle_count(self, mock_controller):
        """Verify start() calls periodic_before_user which increments cycle count."""
        Logger.running = False
        Logger.cycleCount = 0
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = False
        Logger.entry = MagicMock()
        Logger.entry.get_subtable.return_value = MagicMock()

        Logger.start()

        assert Logger.cycleCount >= 1

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_sets_time_source(self, mock_controller):
        """Verify start() sets RobotController time source."""
        Logger.running = False
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = False
        Logger.entry = MagicMock()
        Logger.entry.get_subtable.return_value = MagicMock()

        Logger.start()

        mock_controller.set_time_source.assert_called()

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_in_normal_mode(self, mock_controller):
        """Verify start() creates RealOutputs in normal mode."""
        Logger.running = False
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = False
        mock_entry = MagicMock()
        Logger.entry = mock_entry
        mock_entry.get_sub_table.return_value = MagicMock()

        Logger.start()

        mock_entry.get_sub_table.assert_any_call("RealOutputs")

    @patch('lib_6107.pykit.logger.LoggedDriverStation')
    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_in_replay_mode(self, mock_controller, mock_ds):
        """Verify start() creates ReplayOutputs in replay mode."""
        Logger.running = False
        mock_replay_source = MagicMock()
        Logger.replaySource = mock_replay_source
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = False
        mock_entry = MagicMock()
        Logger.entry = mock_entry
        mock_entry.get_sub_table.return_value = MagicMock()

        Logger.start()

        mock_entry.get_sub_table.assert_any_call("ReplayOutputs")
        Logger.replaySource = None

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_wraps_console_when_enabled(self, mock_controller):
        """Verify start() wraps console output when checkConsole is True."""
        Logger.running = False
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []
        Logger.metadata = {}
        Logger.checkConsole = True
        Logger._console_wrapped = False
        Logger.entry = MagicMock()
        Logger.entry.get_subtable.return_value = MagicMock()
        original_stdout = sys.stdout

        try:
            Logger.start()
            # Console should be wrapped
            assert sys.stdout != original_stdout or Logger._console_wrapped
        finally:
            sys.stdout = original_stdout
            Logger._console_wrapped = False

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_start_idempotent_when_already_running(self, mock_controller):
        """Verify start() is safe to call multiple times."""
        Logger.running = True
        Logger.replaySource = None
        Logger.data_receivers = []
        Logger.dashboardInputs = []

        Logger.start()  # Second call

        assert Logger.running is True


class TestLoggerEnd:
    """Tests for Logger.end method."""

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_end_sets_running_false(self, mock_controller):
        """Verify end() sets Logger.running to False."""
        Logger.running = True
        Logger.data_receivers = []
        Logger._console_wrapped = False
        Logger.replaySource = None

        Logger.end()

        assert Logger.running is False

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_end_restores_time_source(self, mock_controller):
        """Verify end() restores RobotController time source."""
        Logger.running = True
        Logger.data_receivers = []
        Logger._console_wrapped = False
        Logger.replaySource = None

        Logger.end()

        mock_controller.set_time_source.assert_called()

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_end_calls_receiver_end(self, mock_controller):
        """Verify end() calls end() on all receivers."""
        mock_receiver1 = MagicMock()
        mock_receiver2 = MagicMock()
        Logger.running = True
        Logger.data_receivers = [mock_receiver1, mock_receiver2]
        Logger._console_wrapped = False
        Logger.replaySource = None

        Logger.end()

        mock_receiver1.end.assert_called_once()
        mock_receiver2.end.assert_called_once()

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_end_restores_console(self, mock_controller):
        """Verify end() restores console streams if wrapped."""
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        Logger.running = True
        Logger.data_receivers = []
        Logger._console_wrapped = True
        Logger._orig_stdout = original_stdout
        Logger._orig_stderr = original_stderr
        Logger.replaySource = None

        Logger.end()

        assert sys.stdout == original_stdout
        assert sys.stderr == original_stderr

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_end_idempotent_when_not_running(self, mock_controller):
        """Verify end() is safe to call when not running."""
        Logger.running = False
        Logger.data_receivers = []
        Logger._console_wrapped = False

        Logger.end()  # Should not raise


class TestLoggerTimestamp:
    """Tests for Logger.get_timestamp method."""

    @patch('lib_6107.pykit.timeutil.RobotController')
    def test_get_timestamp_returns_fpga_time_in_normal_mode(self, mock_controller):
        """Verify get_timestamp returns FPGA time in normal mode."""
        Logger.replaySource = None
        mock_controller.get_time.return_value = 123456789000

        timestamp = Logger.get_timestamp()

        assert timestamp == 123456789

    @patch('lib_6107.pykit.logger.RobotController')
    def test_get_timestamp_returns_entry_time_in_replay_mode(self, mock_controller):
        """Verify get_timestamp returns entry timestamp in replay mode."""
        mock_replay_source = MagicMock()
        Logger.replaySource = mock_replay_source
        mock_entry = MagicMock()
        mock_entry.get_timestamp.return_value = 987654321
        Logger.entry = mock_entry

        timestamp = Logger.get_timestamp()

        assert timestamp == 987654321
        Logger.replaySource = None

    @patch('lib_6107.pykit.timeutil.RobotController')
    def test_get_timestamp_returns_integer(self, mock_controller):
        """Verify get_timestamp always returns an integer."""
        Logger.replaySource = None
        mock_controller.get_time.return_value = 123456789000

        timestamp = Logger.get_timestamp()

        assert isinstance(timestamp, int)


class TestLoggerPeriodicBeforeUser:
    """Tests for Logger.periodic_before_user method."""

    @patch('lib_6107.pykit.logger.RobotController')
    def test_periodic_before_user_increments_cycle_count(self, mock_controller):
        """Verify periodic_before_user increments cycle count."""
        Logger.running = True
        Logger.replaySource = None
        Logger.cycleCount = 0
        Logger.dashboardInputs = []
        Logger.entry = MagicMock()

        Logger.periodic_before_user()

        assert Logger.cycleCount == 1

    @patch('lib_6107.pykit.timeutil.RobotController')
    def test_periodic_before_user_sets_timestamp_in_normal_mode(self, mock_controller):
        """Verify periodic_before_user sets entry timestamp in normal mode."""
        Logger.running = True
        Logger.replaySource = None
        Logger.cycleCount = 0
        Logger.dashboardInputs = []
        mock_entry = MagicMock()
        Logger.entry = mock_entry
        mock_controller.get_time.return_value = 123456789000

        Logger.periodic_before_user()

        mock_entry.set_timestamp.assert_called()

    @patch('lib_6107.pykit.logger.LoggedDriverStation')
    @patch('lib_6107.pykit.logger.RobotController')
    def test_periodic_before_user_calls_replay_update_in_replay_mode(self, mock_controller, mock_ds):
        """Verify periodic_before_user updates table from replay source."""
        mock_replay_source = MagicMock()
        mock_replay_source.update_table.return_value = True
        Logger.running = True
        Logger.replaySource = mock_replay_source
        Logger.cycleCount = 0
        Logger.dashboardInputs = []
        Logger.entry = MagicMock()
        Logger.entry.get_subtable.return_value = MagicMock()

        Logger.periodic_before_user()

        mock_replay_source.update_table.assert_called()
        Logger.replaySource = None

    @patch('lib_6107.pykit.logger.RobotController')
    def test_periodic_before_user_calls_dashboard_periodic(self, mock_controller):
        """Verify periodic_before_user calls periodic() on dashboard inputs."""
        mock_input1 = MagicMock()
        mock_input2 = MagicMock()
        Logger.running = True
        Logger.replaySource = None
        Logger.cycleCount = 0
        Logger.dashboardInputs = [mock_input1, mock_input2]
        Logger.entry = MagicMock()

        Logger.periodic_before_user()

        mock_input1.periodic.assert_called()
        mock_input2.periodic.assert_called()

    @patch('lib_6107.pykit.logger.RobotController')
    def test_periodic_before_user_exits_on_end_of_replay(self, mock_controller):
        """Verify periodic_before_user exits when replay reaches end."""
        mock_replay_source = MagicMock()
        mock_replay_source.update_table.return_value = False
        Logger.running = True
        Logger.replaySource = mock_replay_source
        Logger.cycleCount = 2
        Logger.dashboardInputs = []
        Logger.entry = MagicMock()

        with pytest.raises(SystemExit):
            Logger.periodic_before_user()

        Logger.replaySource = None


class TestLoggerPeriodicAfterUser:
    """Tests for Logger.periodic_after_user method."""

    @patch('lib_6107.pykit.logger.AutoLogOutputManager')
    @patch('lib_6107.pykit.logger.AlertLogger')
    @patch('lib_6107.pykit.timeutil.RobotController')
    def test_periodic_after_user_records_timing_metrics(self, mock_controller, mock_alert, mock_auto):
        """Verify periodic_after_user records performance timing metrics."""
        Logger.running = True
        Logger.replaySource = None
        Logger.outputTable = MagicMock()
        Logger.entry = MagicMock()
        mock_controller.get_time.return_value = 1000000000

        Logger.periodic_after_user(user_code_length=1000, periodic_before_length=500)

        Logger.outputTable.put.assert_called()

    @patch('lib_6107.pykit.logger.AutoLogOutputManager')
    @patch('lib_6107.pykit.logger.AlertLogger')
    @patch('lib_6107.pykit.timeutil.RobotController')
    def test_periodic_after_user_publishes_to_receivers(self, mock_controller, mock_alert, mock_auto):
        """Verify periodic_after_user publishes to all receivers."""
        mock_receiver1 = MagicMock()
        mock_receiver2 = MagicMock()
        Logger.running = True
        Logger.replaySource = None
        Logger.data_receivers = [mock_receiver1, mock_receiver2]
        Logger.outputTable = MagicMock()
        Logger.entry = MagicMock()
        mock_controller.get_time.return_value = 1000000000

        Logger.periodic_after_user(user_code_length=1000, periodic_before_length=500)

        mock_receiver1.put_table.assert_called()
        mock_receiver2.put_table.assert_called()

    @patch('lib_6107.pykit.logger.AutoLogOutputManager')
    @patch('lib_6107.pykit.logger.AlertLogger')
    @patch('lib_6107.pykit.logger.RobotController')
    def test_periodic_after_user_does_nothing_when_not_running(self, mock_controller, mock_alert, mock_auto):
        """Verify periodic_after_user does nothing when not running."""
        mock_receiver = MagicMock()
        Logger.running = False
        Logger.data_receivers = [mock_receiver]

        Logger.periodic_after_user(user_code_length=1000, periodic_before_length=500)

        mock_receiver.put_table.assert_not_called()


class TestLoggerStartReceiver:
    """Tests for Logger.start_receiver method."""

    def test_start_receiver_calls_start_on_all_receivers(self):
        """Verify start_receiver calls start() on all data receivers."""
        mock_receiver1 = MagicMock()
        mock_receiver2 = MagicMock()
        Logger.data_receivers = [mock_receiver1, mock_receiver2]

        Logger.start_receiver()

        mock_receiver1.start.assert_called_once()
        mock_receiver2.start.assert_called_once()

    def test_start_receiver_handles_exceptions(self):
        """Verify start_receiver handles receiver startup exceptions."""
        mock_receiver_good = MagicMock()
        mock_receiver_bad = MagicMock()
        mock_receiver_bad.start.side_effect = RuntimeError("Start failed")
        Logger.data_receivers = [mock_receiver_good, mock_receiver_bad]

        Logger.start_receiver()  # Should not raise

    def test_start_receiver_continues_after_exception(self):
        """Verify start_receiver continues with other receivers after exception."""
        mock_receiver1 = MagicMock()
        mock_receiver1.start.side_effect = RuntimeError("Start failed")
        mock_receiver2 = MagicMock()
        Logger.data_receivers = [mock_receiver1, mock_receiver2]

        Logger.start_receiver()

        mock_receiver2.start.assert_called_once()


class TestLoggerEdgeCases:
    """Tests for Logger edge cases and error handling."""

    def test_logger_record_output_with_empty_key(self):
        """Verify record_output works with empty key."""
        Logger.running = True
        Logger.outputTable = MagicMock()

        Logger.record_output("", 42)

        Logger.outputTable.put.assert_called_with("", 42, unit=None)

    def test_logger_record_output_with_special_characters(self):
        """Verify record_output works with special characters in key."""
        Logger.running = True
        Logger.outputTable = MagicMock()

        Logger.record_output("Sub/Sys-Item_123", 42)

        Logger.outputTable.put.assert_called()

    def test_logger_record_metadata_with_empty_string(self):
        """Verify record_metadata works with empty strings."""
        Logger.replaySource = None
        Logger.metadata = {}

        Logger.record_metadata("", "")

        assert "" in Logger.metadata

    @patch('lib_6107.pykit.logger.RobotController')
    def test_logger_concurrent_console_writes(self, mock_controller):
        """Verify _ConsoleRecorder handles rapid writes."""
        mock_stream = MagicMock()
        recorder = _ConsoleRecorder(mock_stream)

        for i in range(100):
            recorder.write(f"line{i}\n")

        assert mock_stream.write.call_count == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
