"""Unit tests for CtreDriveSubsystem state caching, Drive/State inputs and vision-measurement guards."""

from unittest.mock import MagicMock, patch

import pytest
from wpimath import Pose2d, Pose3d, Rotation2d

from lib_6107.pykit.logtable import LogTable
from lib_6107.subsystems.drivetrain.ctre_drivesubsystem import CtreDriveSubsystem
from lib_6107.subsystems.pykit.drive_state_io import DriveStateIO

NOW = 100.0


def _state(x=1.0, y=2.0, heading=0.5):
    state = MagicMock()
    state.pose = Pose2d(x, y, Rotation2d(heading))
    state.velocity.vx, state.velocity.vy, state.velocity.omega = 1.0, 0.5, 0.25
    state.raw_heading = Rotation2d(0.4)
    state.timestamp = 99.9
    state.odometry_period = 0.004
    state.successful_daqs, state.failed_daqs = 250, 3
    return state


@pytest.fixture
def drive():
    # Bypass the heavy constructor; only the attributes under test are needed
    sub = object.__new__(CtreDriveSubsystem)
    sub._tuner_x_subsystem = MagicMock()
    sub._tuner_x_subsystem.get_state.return_value = _state()
    sub._state = None
    sub._state_inputs = DriveStateIO.DriveStateIOInputs()
    sub._vision_accepted = sub._vision_rejected = sub._vision_this_cycle = 0
    return sub


@pytest.fixture(autouse=True)
def fixed_clock():
    with (
        patch("lib_6107.subsystems.drivetrain.ctre_drivesubsystem.utils.get_current_time_seconds", return_value=NOW),
        patch("lib_6107.subsystems.drivetrain.ctre_drivesubsystem.Logger"),
    ):
        yield


def test_refresh_state_makes_one_native_call_and_accessors_use_cache(drive):
    drive.refresh_state()
    for _ in range(5):
        drive.get_state()
        _ = drive.get_pose()
    drive._tuner_x_subsystem.get_state.assert_called_once()


def test_get_state_before_first_periodic_reads_once(drive):
    drive.get_state()
    drive.get_state()
    drive._tuner_x_subsystem.get_state.assert_called_once()


def test_reset_pose_invalidates_cache(drive):
    drive.refresh_state()
    drive.reset_pose(Pose2d())
    drive._tuner_x_subsystem.reset_pose.assert_called_once()
    drive.get_state()
    assert drive._tuner_x_subsystem.get_state.call_count == 2


def test_periodic_refreshes_then_calls_base(drive):
    drive._initialized = True
    with (
        patch.object(CtreDriveSubsystem, "is_initialized", True),
        patch("lib_6107.subsystems.drivetrain.drivesubsystem.DriveSubsystem.periodic") as base,
    ):
        drive.periodic()
    drive._tuner_x_subsystem.get_state.assert_called_once()
    base.assert_called_once()


def test_periodic_skips_until_initialized(drive):
    with (
        patch.object(CtreDriveSubsystem, "is_initialized", False),
        patch("lib_6107.subsystems.drivetrain.drivesubsystem.DriveSubsystem.periodic") as base,
    ):
        drive.periodic()
    drive._tuner_x_subsystem.get_state.assert_not_called()
    base.assert_not_called()


def test_drive_state_inputs_copied_from_state(drive):
    drive.refresh_state()
    i = drive._state_inputs
    assert (i.pose_x, i.pose_y, i.pose_heading) == (1.0, 2.0, pytest.approx(0.5))
    assert (i.velocity_x, i.velocity_y, i.velocity_omega) == (1.0, 0.5, 0.25)
    assert i.raw_heading == pytest.approx(0.4)
    assert (i.odometry_period, i.successful_daqs, i.failed_daqs) == (0.004, 250, 3)


def test_drive_state_inputs_round_trip(drive):
    drive.refresh_state()
    table = LogTable(0)
    drive._state_inputs.to_log(table, "Drive/State")
    restored = DriveStateIO.DriveStateIOInputs()
    restored.from_log(table, "Drive/State")
    assert restored == drive._state_inputs


def test_valid_vision_measurement_forwarded_with_std_devs(drive):
    assert drive.add_vision_measurement(Pose2d(1, 1, Rotation2d(0)), NOW - 0.05, (0.1, 0.1, 0.2)) is True
    drive._tuner_x_subsystem.add_vision_measurement.assert_called_once_with(
        Pose2d(1, 1, Rotation2d(0)), NOW - 0.05, (0.1, 0.1, 0.2)
    )


def test_pose3d_converted_to_pose2d(drive):
    pose3d = Pose3d()
    drive.add_vision_measurement(pose3d, NOW - 0.01)
    sent = drive._tuner_x_subsystem.add_vision_measurement.call_args.args[0]
    assert isinstance(sent, Pose2d)


@pytest.mark.parametrize(
    "timestamp, reason",
    [(NOW + 1.0, "future_timestamp"), (NOW - 5.0, "stale_timestamp")],
)
def test_bad_timestamps_rejected(drive, timestamp, reason):
    assert drive._vision_reject_reason(timestamp) == reason
    assert drive.add_vision_measurement(Pose2d(), timestamp) is False
    drive._tuner_x_subsystem.add_vision_measurement.assert_not_called()
    assert drive._vision_rejected == 1


def test_per_cycle_cap_and_reset_on_refresh(drive):
    for _ in range(CtreDriveSubsystem.VISION_MAX_PER_CYCLE):
        assert drive.add_vision_measurement(Pose2d(), NOW - 0.01)
    assert drive.add_vision_measurement(Pose2d(), NOW - 0.01) is False
    assert drive._vision_reject_reason(NOW - 0.01) == "per_cycle_cap"
    drive.refresh_state()
    assert drive.add_vision_measurement(Pose2d(), NOW - 0.01) is True


def test_sim_thread_not_duplicated_when_tuner_has_one(drive):
    drive._tuner_x_subsystem._sim_notifier = object()
    with patch("lib_6107.subsystems.drivetrain.drivesubsystem.DriveSubsystem._start_sim_thread") as base:
        drive._start_sim_thread()
    base.assert_not_called()


def test_sim_thread_started_when_tuner_has_none(drive):
    drive._tuner_x_subsystem._sim_notifier = None
    with patch("lib_6107.subsystems.drivetrain.drivesubsystem.DriveSubsystem._start_sim_thread") as base:
        drive._start_sim_thread()
    base.assert_called_once()


def test_sysid_state_keys_are_distinct_per_routine():
    import inspect

    from lib_6107.subsystems.drivetrain.drivesubsystem import DriveSubsystem

    source = inspect.getsource(DriveSubsystem.__init__)
    assert '"SysIdRotation_State"' in source
    assert source.count('"SysIdSteer_State"') == 1


def test_many_cycles_with_vision_use_one_native_state_read_per_cycle(drive):
    cycles = 50
    for _ in range(cycles):
        drive.refresh_state()
        for _ in range(3):
            drive.get_state()
            drive.get_pose()
        drive.add_vision_measurement(Pose2d(1, 1, Rotation2d()), 100.0, (0.1, 0.1, 0.1))
    assert drive._tuner_x_subsystem.get_state.call_count == cycles
    assert drive._tuner_x_subsystem.add_vision_measurement.call_count == cycles
