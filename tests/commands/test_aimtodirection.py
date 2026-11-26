"""Unit tests for AimToDirection."""

from unittest.mock import patch

import pytest
from wpimath import Rotation2d

from lib_6107.commands.drivetrain.aimtodirection import AimToDirection, AimToDirectionConstants
from tests.commands._fakes import FakeDrive


@pytest.fixture(autouse=True)
def no_logger():
    with patch("lib_6107.commands.command.Logger.record_output"):
        yield


def make(drive, heading=90.0, **kw):
    cmd = AimToDirection(drive, heading, **kw)
    cmd.initialize()
    return cmd


def test_heading_none_uses_current_heading():
    drive = FakeDrive(degrees=30)
    cmd = make(drive, None)
    assert cmd._target_direction.degrees() == pytest.approx(30)


def test_callable_heading():
    cmd = make(FakeDrive(), lambda: 45.0)
    assert cmd._target_direction.degrees() == pytest.approx(45)


def test_turn_positive_and_negative():
    drive = FakeDrive(degrees=0)
    cmd = make(drive, 90.0)
    cmd.execute()
    assert drive.arcade_drive.call_args[0][1] > 0
    drive.place(0, 0, 180 - 1)
    drive.arcade_drive.reset_mock()
    cmd.execute()
    assert drive.arcade_drive.call_args[0][1] < 0


def test_angle_wrap_and_min_speed(monkeypatch):
    drive = FakeDrive(degrees=170)
    cmd = make(drive, -170.0)  # 20 degrees remaining via wrap, right turn
    cmd.execute()
    assert drive.arcade_drive.call_args[0][1] > 0
    drive.place(0, 0, -170)
    cmd2 = make(drive, 170.0)
    cmd2.execute()
    assert drive.arcade_drive.call_args[0][1] < 0
    # tiny error -> min turn speed
    drive.place(0, 0, 89.9)
    cmd3 = make(drive, 90.0)
    cmd3.execute()
    assert abs(drive.arcade_drive.call_args[0][1]) == AimToDirectionConstants.MIN_TURN_SPEED


def test_sqrt_control_and_forward(monkeypatch):
    monkeypatch.setattr(AimToDirectionConstants, "USE_SQRT_CONTROL", True)
    drive = FakeDrive()
    cmd = make(drive, 90.0, fwd_speed=0.5)
    cmd.execute()
    fwd, turn = drive.arcade_drive.call_args[0]
    assert fwd == 0.5 and turn > 0


def test_is_finished_branches():
    drive = FakeDrive(degrees=0, turn_rate=0.0)
    assert make(drive, 90.0).is_finished() is False
    assert make(drive, 0.0).is_finished() is True
    drive.gyro.turn_rate_degrees_per_second = 50.0
    assert make(drive, 0.0).is_finished() is False
    assert make(drive, 0.0, fwd_speed=0.5).is_finished() is False


def test_end_stops():
    drive = FakeDrive()
    cmd = make(drive, 0.0)
    cmd.end(True)
    drive.stop.assert_called_once_with()


def test_pathplanner_register():
    assert AimToDirection.pathplanner_register(FakeDrive()) is None
