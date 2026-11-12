"""Unit tests for the ArcadeDrive command."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.commands.drivetrain.arcade_drive import ArcadeDrive


@pytest.fixture
def drivetrain():
    drive = MagicMock()
    drive.container.get_elapsed_time.return_value = 0.0
    del drive.robot_drive  # behave like a drivetrain, not a container
    return drive


def test_execute_uses_callable_speeds(drivetrain):
    cmd = ArcadeDrive(drivetrain, lambda: 1.5, lambda: -0.5, assume_manual_input=True)
    cmd.execute()
    drivetrain.arcade_drive.assert_called_once_with(1.5, -0.5, assume_manual_input=True, field_relative=True)


def test_constant_speeds_are_clamped_to_non_negative(drivetrain):
    cmd = ArcadeDrive(drivetrain, 2.0, -1.0)
    cmd.execute()
    drivetrain.arcade_drive.assert_called_once_with(2.0, 0.0, assume_manual_input=False, field_relative=True)


def test_never_finishes(drivetrain):
    assert ArcadeDrive(drivetrain).is_finished() is False


def test_end_stops_the_drivetrain(drivetrain):
    cmd = ArcadeDrive(drivetrain)
    with patch("lib_6107.commands.command.Logger.record_output"):
        cmd.end(False)
    drivetrain.stop.assert_called_once_with()


def test_pathplanner_register_is_a_noop_for_now(drivetrain):
    assert ArcadeDrive.pathplanner_register(drivetrain) is None
