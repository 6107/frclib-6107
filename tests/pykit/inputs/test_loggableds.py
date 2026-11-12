"""Tests for LoggedDriverStation against the 2027 DriverStationBackend / DriverStationSim APIs."""

import pytest
from hal import AllianceStationID, RobotMode
from wpilib.simulation import DriverStationSim

from lib_6107.pykit.inputs.loggableds import LoggedDriverStation
from lib_6107.pykit.logtable import LogTable


@pytest.fixture(autouse=True)
def _reset_ds():
    DriverStationSim.reset_data()
    yield
    DriverStationSim.reset_data()


def _snapshot() -> dict:
    table = LogTable(0)
    LoggedDriverStation.save_to_table(table)
    return {key: value.value for key, value in table.get_all().items()}


def test_save_records_match_and_mode_information():
    DriverStationSim.set_alliance_station_id(AllianceStationID.BLUE_2)
    DriverStationSim.set_event_name("TEST")
    DriverStationSim.set_match_number(7)
    DriverStationSim.set_enabled(True)
    DriverStationSim.set_ds_attached(True)
    DriverStationSim.notify_new_data()

    data = _snapshot()

    assert data["/AllianceStation"] == 5
    assert data["/EventName"] == "TEST"
    assert data["/MatchNumber"] == 7
    assert data["/RobotMode"] == RobotMode.UNKNOWN.value
    assert data["/Autonomous"] is False
    assert data["/Teleop"] is False
    assert data["/Enabled"] is True
    assert data["/DSAttached"] is True


def test_save_records_every_joystick_port():
    data = _snapshot()
    names = [key for key in data if key.endswith("/Name")]
    assert len(names) == 6


def test_save_then_load_round_trips():
    DriverStationSim.set_alliance_station_id(AllianceStationID.RED_3)
    DriverStationSim.set_enabled(True)
    DriverStationSim.set_ds_attached(True)
    DriverStationSim.set_joystick_axes_maximum_index(0, 1)
    DriverStationSim.set_joystick_axis(0, 1, 0.5)
    DriverStationSim.notify_new_data()

    table = LogTable(0)
    LoggedDriverStation.save_to_table(table)
    DriverStationSim.reset_data()
    LoggedDriverStation.load_from_table(table)

    assert _snapshot() == {key: value.value for key, value in table.get_all().items()}
