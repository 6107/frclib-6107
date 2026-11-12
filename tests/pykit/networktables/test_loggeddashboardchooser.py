"""Unit tests for LoggedDashboardChooser (backed by the 2027 ``tunables.Selectable``)."""

from enum import Enum
from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser

MODULE = "lib_6107.pykit.networktables.loggeddashboardchooser"


class AutoMode(Enum):
    NONE = 0
    SCORE = 1
    CROSS = 2


@pytest.fixture
def logger():
    with patch(f"{MODULE}.Logger") as mock_logger:
        mock_logger.is_replay.return_value = False
        yield mock_logger


def _select(chooser, name):
    chooser.sendable_chooser._selected.set(name)


def test_init_registers_with_logger_and_starts_empty(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    assert chooser.key == "Test"
    assert chooser.options == {}
    assert chooser.selected_value == ""
    logger.register_dashboard_input.assert_called_once_with(chooser)


def test_options_are_not_shared_between_instances(logger):
    a = LoggedDashboardChooser[str]("A")
    b = LoggedDashboardChooser[str]("B")
    a.add_option("x", "1")
    assert b.options == {}


def test_default_option_is_selected_after_periodic(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.set_default_option("None", "none")
    chooser.add_option("Drive", "drive")
    chooser.periodic()
    assert chooser.get_selected() == "none"


def test_selection_changes_return_typed_value(logger):
    chooser = LoggedDashboardChooser[AutoMode]("Auto")
    chooser.set_default_option("None", AutoMode.NONE)
    chooser.add_option("Score", AutoMode.SCORE)
    _select(chooser, "Score")
    chooser.periodic()
    assert chooser.get_selected() is AutoMode.SCORE


def test_get_selected_is_none_for_unknown_key(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.selected_value = "missing"
    assert chooser.get_selected() is None


def test_get_selected_raises_when_selected_value_is_none(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.selected_value = None
    with pytest.raises(ValueError):
        chooser.get_selected()


def test_periodic_processes_inputs_through_logger(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    logger.process_inputs.reset_mock()
    chooser.periodic()
    logger.process_inputs.assert_called_once_with(chooser.prefix + "/SmartDashboard", chooser)


def test_listener_fires_once_per_change(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.set_default_option("None", "none")
    chooser.add_option("Drive", "drive")
    chooser.periodic()
    seen = []
    chooser.on_change(seen.append)

    _select(chooser, "Drive")
    chooser.periodic()
    chooser.periodic()
    assert seen == ["drive"]


def test_on_change_replaces_previous_listener(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.add_option("A", "a")
    first, second = MagicMock(), MagicMock()
    chooser.on_change(first)
    chooser.on_change(second)
    _select(chooser, "A")
    chooser.periodic()
    first.assert_not_called()
    second.assert_called_once_with("a")


def test_replay_mode_does_not_read_selectable(logger):
    logger.is_replay.return_value = True
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.add_option("A", "a")
    chooser.selected_value = "A"
    _select(chooser, "")
    chooser.periodic()
    assert chooser.selected_value == "A"


def test_to_log_and_from_log_round_trip(logger):
    chooser = LoggedDashboardChooser[str]("Test")
    chooser.selected_value = "Drive"
    table = MagicMock(spec=LogTable)
    chooser.to_log(table, "Prefix")
    table.put.assert_called_once_with("Prefix/Test", "Drive")

    table.get.return_value = "Replayed"
    chooser.from_log(table, "Prefix")
    table.get.assert_called_once_with("Prefix/Test", "Drive")
    assert chooser.selected_value == "Replayed"
