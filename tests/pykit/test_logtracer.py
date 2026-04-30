from unittest.mock import patch, MagicMock, call
from lib_6107.pykit.logtracer import LogTracer


def logtracer_resetouter_sets_prefix():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=1000000):
        LogTracer.resetOuter("TestPrefix")
        assert LogTracer._prefix == "TestPrefix"


def logtracer_resetouter_sets_outer_start_time():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=5000000):
        LogTracer.resetOuter("TestOp")
        assert LogTracer._outer_start == 5000000


def logtracer_resetouter_initializes_inner_start():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=1000000):
        LogTracer.resetOuter("TestOp")
        assert LogTracer._inner_start == 1000000


def logtracer_reset_updates_inner_start():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=2000000):
        LogTracer._outer_start = 1000000
        LogTracer.reset()
        assert LogTracer._inner_start == 2000000
        assert LogTracer._outer_start == 1000000


def logtracer_record_logs_phase_time_in_milliseconds():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 2000000]
        LogTracer.resetOuter("RobotPeriodic")
        mock_time.side_effect = [1000000, 3000000]
        LogTracer.record("DrivetrainUpdate")
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/DrivetrainUpdateMS", 2.0)


def logtracer_record_resets_inner_timer():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput'):
        mock_time.side_effect = [1000000, 2000000, 3000000]
        LogTracer.resetOuter("TestOp")
        LogTracer.record("Phase1")
        assert LogTracer._inner_start == 3000000


def logtracer_record_formats_key_correctly():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 2000000, 3000000]
        LogTracer.resetOuter("MyOperation")
        LogTracer.record("PhaseOne")
        mock_logger.assert_called_once()
        call_args = mock_logger.call_args[0]
        assert call_args[0] == "LogTracer/MyOperation/PhaseOneMS"


def logtracer_recordtotal_logs_total_time_from_outer_start():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 1000000, 6000000]
        LogTracer.resetOuter("RobotPeriodic")
        LogTracer.record("Phase1")
        mock_logger.reset_mock()
        mock_time.return_value = 6000000
        LogTracer.recordTotal()
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/TotalMS", 5.0)


def logtracer_recordtotal_formats_key_with_totalms_suffix():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 1000000, 2000000]
        LogTracer.resetOuter("TestBlock")
        mock_logger.reset_mock()
        mock_time.return_value = 2000000
        LogTracer.recordTotal()
        call_args = mock_logger.call_args[0]
        assert call_args[0] == "LogTracer/TestBlock/TotalMS"


def logtracer_multiple_records_measure_sequential_phases():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 1000000, 2000000, 3000000, 4000000]
        LogTracer.resetOuter("RobotPeriodic")
        LogTracer.record("Phase1")
        LogTracer.record("Phase2")
        LogTracer.record("Phase3")
        calls = mock_logger.call_args_list
        assert calls[0][0] == ("LogTracer/RobotPeriodic/Phase1MS", 1.0)
        assert calls[1][0] == ("LogTracer/RobotPeriodic/Phase2MS", 1.0)
        assert calls[2][0] == ("LogTracer/RobotPeriodic/Phase3MS", 1.0)


def logtracer_converts_microseconds_to_milliseconds():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [0, 0, 500000]
        LogTracer.resetOuter("Test")
        LogTracer.record("Half")
        mock_logger.assert_called_once_with("LogTracer/Test/HalfMS", 500.0)


def logtracer_handles_zero_elapsed_time():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.return_value = 1000000
        LogTracer.resetOuter("Test")
        LogTracer.record("Instant")
        mock_logger.assert_called_once_with("LogTracer/Test/InstantMS", 0.0)


def logtracer_preserves_outer_start_through_multiple_records():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [1000000, 1000000, 2000000, 3000000, 5000000]
        LogTracer.resetOuter("RobotPeriodic")
        outer_time = LogTracer._outer_start
        LogTracer.record("Phase1")
        LogTracer.record("Phase2")
        mock_logger.reset_mock()
        mock_time.return_value = 5000000
        LogTracer.recordTotal()
        assert LogTracer._outer_start == outer_time
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/TotalMS", 4.0)


def logtracer_prefix_changes_on_new_resetouter():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=1000000):
        LogTracer.resetOuter("FirstOp")
        assert LogTracer._prefix == "FirstOp"
        LogTracer.resetOuter("SecondOp")
        assert LogTracer._prefix == "SecondOp"


def logtracer_reset_does_not_change_prefix():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=1000000):
        LogTracer.resetOuter("MyOperation")
        original_prefix = LogTracer._prefix
        LogTracer.reset()
        assert LogTracer._prefix == original_prefix


def logtracer_reset_does_not_change_outer_start():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time:
        mock_time.return_value = 1000000
        LogTracer.resetOuter("Op")
        outer_time = LogTracer._outer_start
        mock_time.return_value = 2000000
        LogTracer.reset()
        assert LogTracer._outer_start == outer_time


def logtracer_full_workflow_correctly_sequences_operations():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.recordOutput') as mock_logger:
        mock_time.side_effect = [0, 0, 1000000, 4000000, 7000000]
        LogTracer.resetOuter("RobotPeriodic")
        LogTracer.record("Subsystem1")
        LogTracer.record("Subsystem2")
        LogTracer.record("Subsystem3")
        calls = [call[0] for call in mock_logger.call_args_list]
        assert len(calls) == 3
        assert calls[0][0] == "LogTracer/RobotPeriodic/Subsystem1MS"
        assert calls[1][0] == "LogTracer/RobotPeriodic/Subsystem2MS"
        assert calls[2][0] == "LogTracer/RobotPeriodic/Subsystem3MS"