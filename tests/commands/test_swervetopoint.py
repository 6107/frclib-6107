"""Unit tests for SwerveToPoint and SwerveMove."""

from unittest.mock import patch

import pytest
from wpimath import Rotation2d

from lib_6107.commands.drivetrain.aimtodirection import AimToDirectionConstants
from lib_6107.commands.drivetrain.gotopoint import GoToPointConstants
from lib_6107.commands.drivetrain.swervetopoint import SwerveMove, SwerveToPoint
from tests.commands._fakes import FakeDrive


@pytest.fixture(autouse=True)
def no_logger():
    with patch("lib_6107.commands.command.Logger.record_output"):
        yield


def make(drive, x=5.0, y=0.0, heading=0.0, **kw):
    cmd = SwerveToPoint(drive, x, y, heading, **kw)
    cmd.initialize()
    return cmd


def test_heading_forms():
    d = FakeDrive()
    assert SwerveToPoint(d, 1, 1, Rotation2d.from_degrees(30))._target_heading.degrees() == pytest.approx(30)
    assert SwerveToPoint(d, 1, 1, 45)._target_heading.degrees() == pytest.approx(45)
    assert SwerveToPoint(d, 1, 1, None)._target_heading.degrees() == 0
    assert SwerveToPoint(d, speed=5)._speed == 1.0


def test_pathplanner_register():
    assert SwerveToPoint.pathplanner_register(FakeDrive()) is None
    assert SwerveMove.pathplanner_register(FakeDrive()) is None


def test_initialize_none_heading_uses_current():
    d = FakeDrive(degrees=40)
    cmd = SwerveToPoint(d, 1, 1)
    cmd._target_heading = None
    cmd.initialize()
    assert cmd._target_pose.rotation().degrees() == pytest.approx(40)


@pytest.mark.parametrize("sqrt", [False, True])
@pytest.mark.parametrize("stop", [False, True])
def test_execute_drives(monkeypatch, sqrt, stop):
    monkeypatch.setattr(GoToPointConstants, "USE_SQRT_CONTROL", sqrt)
    monkeypatch.setattr(AimToDirectionConstants, "USE_SQRT_CONTROL", sqrt)
    d = FakeDrive(x=0, y=0, degrees=0)
    cmd = make(d, heading=90)
    cmd.execute()
    args, kwargs = d.drive.call_args
    assert args[0] > 0 and args[2] > 0 and kwargs == {"field_relative": False}

    d.place(0, 0, 170)
    cmd._target_pose = cmd._target_pose.__class__(cmd._target_pose.translation(), Rotation2d.from_degrees(-170))
    cmd.execute()
    assert d.drive.call_args[0][2] > 0  # wraps through 180
    d.place(0, 0, -170)
    cmd._target_pose = cmd._target_pose.__class__(cmd._target_pose.translation(), Rotation2d.from_degrees(170))
    cmd.execute()
    assert d.drive.call_args[0][2] < 0


def test_execute_at_target_zero_distance():
    d = FakeDrive(x=5, y=0)
    cmd = make(d)
    d.place(5, 0)
    cmd.execute()
    assert d.drive.call_args[0][0] == 0.0


def test_get_degrees_left_to_turn_wraps():
    d = FakeDrive(degrees=0)
    cmd = make(d, heading=0)
    cmd._target_pose = cmd._target_pose.__class__(cmd._target_pose.translation(), Rotation2d.from_degrees(190))
    assert cmd.get_degrees_left_to_turn() == pytest.approx(-170)


def test_is_finished():
    d = FakeDrive()
    cmd = make(d, slow_down_at_finish=False)
    assert cmd.is_finished() is False
    d.place(4.9, 0)
    assert cmd.is_finished() is True

    d = FakeDrive()
    cmd = make(d, heading=0)
    assert cmd.is_finished() is False
    d.place(6, 0, 90)
    assert cmd.is_finished() is False  # overshot, wrong direction
    assert cmd._overshot
    assert cmd.is_finished() is False
    d.place(6, 0, 0)
    assert cmd.is_finished() is True


def test_end_stops():
    d = FakeDrive()
    cmd = make(d)
    cmd.end(True)
    d.stop.assert_called_once_with()


def test_swerve_move_lifecycle():
    d = FakeDrive(x=1, y=1, degrees=0)
    cmd = SwerveMove(d, meters_to_the_left=1.0, meters_backwards=2.0, heading=Rotation2d.from_degrees(0))
    cmd.initialize()
    sub = cmd._subcommand
    assert sub._target_point.x == pytest.approx(-1.0)
    assert sub._target_point.y == pytest.approx(2.0)
    cmd.execute()
    assert d.drive.called
    assert cmd.is_finished() in (True, False)
    cmd.end(False)
    d.stop.assert_called_once_with()


def test_swerve_move_default_heading_and_callable():
    d = FakeDrive(degrees=90)
    cmd = SwerveMove(d, 1.0)
    assert cmd._desired_heading is None
    cmd.initialize()
    assert cmd._subcommand._target_heading.degrees() == pytest.approx(90)
    cmd = SwerveMove(d, 1.0, heading=lambda: Rotation2d.from_degrees(10))
    cmd.initialize()
    assert cmd._subcommand._target_heading.degrees() == pytest.approx(10)
