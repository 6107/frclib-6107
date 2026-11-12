"""Unit tests for BaseCommand."""

from unittest.mock import MagicMock, patch

import pytest
from commands2 import Subsystem

from lib_6107.commands.command import BaseCommand

LOGGER = "lib_6107.commands.command.Logger.record_output"


class MyCommand(BaseCommand):
    pass


def _container():
    container = MagicMock()
    container.get_elapsed_time.return_value = 1.234
    return container


def test_name_is_the_class_name():
    cmd = MyCommand(_container())
    assert cmd.name == "MyCommand"
    assert cmd.get_name() == "MyCommand"
    assert MyCommand.get_class_name() == "MyCommand"


def test_container_target_resolves_drivetrain():
    container = _container()
    cmd = MyCommand(container)
    assert cmd._container is container
    assert cmd._drivetrain is container.robot_drive


def test_drivetrain_target_resolves_container_and_requirement():
    class FakeDrive(Subsystem):
        container = _container()

    drive = FakeDrive()
    cmd = MyCommand(drive)
    assert cmd._drivetrain is drive
    assert cmd._container is FakeDrive.container
    assert drive in cmd.get_requirements()


def test_initialize_re_resolves_late_bound_drivetrain():
    container = _container()
    container.robot_drive = None
    cmd = MyCommand(container)
    assert cmd._drivetrain is None

    container.robot_drive = MagicMock()
    with patch(LOGGER):
        cmd.initialize()
    assert cmd._drivetrain is container.robot_drive


def test_initialize_records_start_time_and_state():
    cmd = MyCommand(_container())
    with patch(LOGGER) as record:
        cmd.initialize()
    assert cmd._start_time == 1.23
    record.assert_called_once_with("Commands/MyCommand/State", "running")


@pytest.mark.parametrize("interrupted, state", [(True, "interrupted"), (False, "ended")])
def test_end_records_final_state(interrupted, state):
    cmd = MyCommand(_container())
    with patch(LOGGER) as record:
        cmd.end(interrupted)
    record.assert_called_once_with("Commands/MyCommand/State", state)
