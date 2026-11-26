"""Unit tests for GoToPoint."""

from unittest.mock import patch

import pytest
from wpimath import Rotation2d

from lib_6107.commands.drivetrain.gotopoint import GoToPoint, GoToPointConstants, _optimize
from lib_6107.commands.drivetrain.aimtodirection import AimToDirectionConstants
from tests.commands._fakes import FakeDrive


@pytest.fixture(autouse=True)
def no_logger():
    with patch("lib_6107.commands.command.Logger.record_output"), patch(
        "lib_6107.commands.drivetrain.gotopoint.Logger.record_output"
    ):
        yield


def make(drive, x=5.0, y=0.0, **kw):
    cmd = GoToPoint(drive, x, y, **kw)
    cmd.initialize()
    return cmd


def test_optimize():
    assert _optimize(350) == -10
    assert _optimize(-350) == 10
    assert _optimize(20) == 20


def test_pathplanner_register():
    assert GoToPoint.pathplanner_register(FakeDrive()) is None


def test_init_reverse_finish_direction():
    cmd = GoToPoint(FakeDrive(), 1, 1, speed=0.5, finish_direction=Rotation2d.from_degrees(10))
    assert cmd._finish_direction.degrees() == pytest.approx(10)


def test_initialize_finish_direction_and_reverse():
    cmd = make(FakeDrive(), finish_direction=Rotation2d.from_degrees(20))
    assert cmd._desired_end_direction.degrees() == pytest.approx(20)
    cmd = make(FakeDrive())
    assert cmd._desired_end_direction.degrees() == pytest.approx(0)
    cmd._speed = -1.0
    cmd.initialize()
    assert abs(cmd._desired_end_direction.degrees()) == pytest.approx(180)


def test_execute_rotates_in_place_when_misaligned():
    drive = FakeDrive(degrees=-90)  # target is 90 deg to the left of heading
    cmd = make(drive)
    cmd.execute()
    assert drive.arcade_drive.call_args[0][0] == 0.0 and drive.arcade_drive.call_args[0][1] >= 0
    drive.place(0, 0, 90)
    cmd.execute()
    fwd, rot = drive.arcade_drive.call_args[0]
    assert fwd == 0.0 and rot <= 0


def test_execute_drives_forward_with_oversteer():
    drive = FakeDrive(x=0, y=0.5, degrees=0)
    cmd = make(drive, x=10, y=0)
    cmd.execute()
    fwd, rot = drive.arcade_drive.call_args[0]
    assert fwd > 0 and rot < 0
    assert cmd._pointing_in_good_direction

    drive.place(0, -0.5, 0)
    cmd.execute()
    assert drive.arcade_drive.call_args[0][1] > 0


def test_execute_near_target_uses_end_direction_and_sqrt(monkeypatch):
    monkeypatch.setattr(GoToPointConstants, "USE_SQRT_CONTROL", True)
    monkeypatch.setattr(AimToDirectionConstants, "USE_SQRT_CONTROL", True)
    drive = FakeDrive(x=4.9, y=0, degrees=0)
    cmd = make(drive, finish_direction=Rotation2d.from_degrees(30))
    drive.place(4.9, 0, 0)
    cmd.execute()
    assert drive.arcade_drive.call_args[0][1] > 0


def test_execute_no_oversteer_and_reverse(monkeypatch):
    monkeypatch.setattr(GoToPointConstants, "OVERSTEER_ADJUSTMENT", 0)
    drive = FakeDrive(x=0, y=0, degrees=180)
    cmd = GoToPoint(drive, 5, 0, speed=0.5, slow_down_at_finish=False)
    cmd._speed = -0.5  # reverse driving
    cmd.initialize()
    cmd.execute()
    fwd, _ = drive.arcade_drive.call_args[0]
    assert fwd < 0


def test_is_finished_branches():
    drive = FakeDrive()
    cmd = make(drive, slow_down_at_finish=False)
    assert cmd.is_finished() is False
    drive.place(4.9, 0)
    assert cmd.is_finished() is True  # close enough

    drive = FakeDrive()
    cmd = make(drive)
    assert cmd.is_finished() is False
    drive.place(6, 0)
    assert cmd.is_finished() is True  # overshot
    drive.place(4.99999, 0)
    cmd._initial_distance = 100.0
    cmd._target_position = cmd._target_position.__class__(4.99999, 0)
    assert cmd.is_finished() is True  # too slow


def test_end_stops():
    drive = FakeDrive()
    cmd = make(drive)
    cmd.end(False)
    drive.stop.assert_called_once_with()
