from unittest.mock import patch

from lib_6107.pykit.logtracer import LogTracer
import pytest


@pytest.fixture(autouse=True)
def _clean_tracer():
    LogTracer.clear()
    yield
    LogTracer.clear()


def test_logtracer_resetouter_sets_prefix():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=1000000000):
        LogTracer.reset_outer("TestPrefix")
        assert LogTracer._prefix == "TestPrefix"


def test_logtracer_resetouter_sets_outer_start_time():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=5000000000):
        LogTracer.reset_outer("TestOp")
        assert LogTracer._outer_start == 5000000000


def test_logtracer_resetouter_initializes_inner_start():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=1000000000):
        LogTracer.reset_outer("TestOp")
        assert LogTracer._inner_start == 1000000000


def test_logtracer_reset_updates_inner_start():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=2000000000):
        LogTracer._outer_start = 1000000000
        LogTracer.reset()
        assert LogTracer._inner_start == 2000000000
        assert LogTracer._outer_start == 1000000000


def test_logtracer_record_logs_phase_time_in_milliseconds():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 2000000000]
        LogTracer.reset_outer("RobotPeriodic")
        mock_time.side_effect = [3000000000]
        LogTracer.record("DrivetrainUpdate")
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/DrivetrainUpdateMS", 1000.0)


def test_logtracer_record_resets_inner_timer():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output'):
        mock_time.side_effect = [1000000000, 2000000000, 3000000000]
        LogTracer.reset_outer("TestOp")
        LogTracer.record("Phase1")
        assert LogTracer._inner_start == 3000000000


def test_logtracer_record_formats_key_correctly():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 2000000000, 3000000000]
        LogTracer.reset_outer("MyOperation")
        LogTracer.record("PhaseOne")
        mock_logger.assert_called_once()
        call_args = mock_logger.call_args[0]
        assert call_args[0] == "LogTracer/MyOperation/PhaseOneMS"


def test_logtracer_recordtotal_logs_total_time_from_outer_start():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 1000000000, 1000000000, 6000000000]
        LogTracer.reset_outer("RobotPeriodic")
        LogTracer.record("Phase1")
        mock_logger.reset_mock()
        mock_time.return_value = 6000000000
        LogTracer.record_total()
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/TotalMS", 5000.0)


def test_logtracer_recordtotal_formats_key_with_totalms_suffix():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 1000000000, 2000000000]
        LogTracer.reset_outer("TestBlock")
        mock_logger.reset_mock()
        mock_time.return_value = 2000000000
        LogTracer.record_total()
        call_args = mock_logger.call_args[0]
        assert call_args[0] == "LogTracer/TestBlock/TotalMS"


def test_logtracer_multiple_records_measure_sequential_phases():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 1000000000, 2000000000, 3000000000, 4000000000]
        LogTracer.reset_outer("RobotPeriodic")
        LogTracer.record("Phase1")
        LogTracer.record("Phase2")
        LogTracer.record("Phase3")
        calls = mock_logger.call_args_list
        assert calls[0][0] == ("LogTracer/RobotPeriodic/Phase1MS", 1000.0)
        assert calls[1][0] == ("LogTracer/RobotPeriodic/Phase2MS", 1000.0)
        assert calls[2][0] == ("LogTracer/RobotPeriodic/Phase3MS", 1000.0)


def test_logtracer_converts_nanoseconds_to_milliseconds():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [0, 0, 500000000]
        LogTracer.reset_outer("Test")
        LogTracer.record("Half")
        mock_logger.assert_called_once_with("LogTracer/Test/HalfMS", 500.0)


def test_logtracer_handles_zero_elapsed_time():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.return_value = 1000000000
        LogTracer.reset_outer("Test")
        LogTracer.record("Instant")
        mock_logger.assert_called_once_with("LogTracer/Test/InstantMS", 0.0)


def test_logtracer_preserves_outer_start_through_multiple_records():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [1000000000, 1000000000, 2000000000, 3000000000, 5000000000]
        LogTracer.reset_outer("RobotPeriodic")
        outer_time = LogTracer._outer_start
        LogTracer.record("Phase1")
        LogTracer.record("Phase2")
        mock_logger.reset_mock()
        mock_time.return_value = 5000000000
        LogTracer.record_total()
        assert LogTracer._outer_start == outer_time
        mock_logger.assert_called_once_with("LogTracer/RobotPeriodic/TotalMS", 4000.0)


def test_logtracer_prefix_changes_on_new_resetouter():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=1000000000):
        LogTracer.reset_outer("FirstOp")
        assert LogTracer._prefix == "FirstOp"
        LogTracer.reset_outer("SecondOp")
        assert LogTracer._prefix == "SecondOp"


def test_logtracer_reset_does_not_change_prefix():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time', return_value=1000000000):
        LogTracer.reset_outer("MyOperation")
        original_prefix = LogTracer._prefix
        LogTracer.reset()
        assert LogTracer._prefix == original_prefix


def test_logtracer_reset_does_not_change_outer_start():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time:
        mock_time.return_value = 1000000000
        LogTracer.reset_outer("Op")
        outer_time = LogTracer._outer_start
        mock_time.return_value = 2000000000
        LogTracer.reset()
        assert LogTracer._outer_start == outer_time


def test_logtracer_full_workflow_correctly_sequences_operations():
    with patch('lib_6107.pykit.logtracer.RobotController.get_monotonic_time') as mock_time, \
         patch('lib_6107.pykit.logtracer.Logger.record_output') as mock_logger:
        mock_time.side_effect = [0, 0, 1000000000, 4000000000, 7000000000]
        LogTracer.reset_outer("RobotPeriodic")
        LogTracer.record("Subsystem1")
        LogTracer.record("Subsystem2")
        LogTracer.record("Subsystem3")
        calls = [call[0] for call in mock_logger.call_args_list]
        assert len(calls) == 3
        assert calls[0][0] == "LogTracer/RobotPeriodic/Subsystem1MS"
        assert calls[1][0] == "LogTracer/RobotPeriodic/Subsystem2MS"
        assert calls[2][0] == "LogTracer/RobotPeriodic/Subsystem3MS"

def _times(values):
    return patch("lib_6107.pykit.logtracer.RobotController.get_monotonic_time", side_effect=values)


def test_nested_block_restores_parent_prefix_and_timers():
    # reset_outer reads the clock twice (outer + inner); record/record_total once
    with _times([100, 100, 200, 200, 300, 400, 500]), patch("lib_6107.pykit.logtracer.Logger.record_output") as out:
        LogTracer.reset_outer("Parent")
        LogTracer.reset_outer("Child")
        LogTracer.record_total()
        assert LogTracer._prefix == "Parent"
        assert LogTracer._outer_start == 100
        assert LogTracer._inner_start == 100
        LogTracer.record("AfterChild")
        LogTracer.record_total()
    keys = [c.args[0] for c in out.call_args_list]
    assert keys == [
        "LogTracer/Child/TotalMS",
        "LogTracer/Parent/AfterChildMS",
        "LogTracer/Parent/TotalMS",
    ]
    assert out.call_args_list[0].args[1] == 100 / 1_000_000.0
    assert out.call_args_list[1].args[1] == 300 / 1_000_000.0
    assert out.call_args_list[2].args[1] == 400 / 1_000_000.0


def test_depth_returns_to_zero_when_balanced():
    with patch("lib_6107.pykit.logtracer.Logger.record_output"):
        LogTracer.reset_outer("A")
        LogTracer.reset_outer("B")
        LogTracer.reset_outer("C")
        assert LogTracer._depth == 3
        for _ in range(3):
            LogTracer.record_total()
    assert LogTracer._depth == 0
    assert LogTracer._parents == []


def test_extra_record_total_is_safe():
    with patch("lib_6107.pykit.logtracer.Logger.record_output"):
        LogTracer.reset_outer("A")
        LogTracer.record_total()
        LogTracer.record_total()
    assert LogTracer._depth == 0


def test_clear_discards_leaked_blocks():
    LogTracer.reset_outer("Leaked")
    LogTracer.reset_outer("Leaked2")
    LogTracer.clear()
    assert LogTracer._depth == 0
    assert LogTracer._parents == []


def test_stack_is_bounded():
    for i in range(LogTracer.MAX_DEPTH + 10):
        LogTracer.reset_outer(f"P{i}")
    assert len(LogTracer._parents) <= LogTracer.MAX_DEPTH
