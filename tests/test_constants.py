"""Unit tests for lib_6107.constants."""

import importlib
import math

import pytest
from lib_6107 import constants
from lib_6107.constants import NetworkConstants, RobotConstants, RobotModes, SimulationConstants


def test_robot_modes_values():
    assert {m.name for m in RobotModes} == {"REAL", "SIMULATION", "REPLAY"}
    assert RobotModes.REAL.value == 1


def test_robot_constants_derived_properties():
    c = RobotConstants()
    assert c.ROBOT_X_WIDTH == pytest.approx(c.ROBOT_CHASSIS_X_WIDTH + 2 * c.ROBOT_BUMPER_THICKNESS)
    assert c.ROBOT_Y_WIDTH == pytest.approx(c.ROBOT_CHASSIS_Y_WIDTH + 2 * c.ROBOT_BUMPER_THICKNESS)
    assert c.WHEEL_DIAMETER == pytest.approx(c.WHEEL_RADIUS * 2)
    assert c.WHEEL_CIRCUMFERENCE == pytest.approx(c.WHEEL_DIAMETER * math.pi)


def test_theta_controller_constraints():
    c = RobotConstants()
    constraints = c.THETA_CONTROLLER_CONSTRAINTS()
    assert constraints.max_velocity == pytest.approx(c.MAX_ANGULAR_VELOCITY)
    assert constraints.max_acceleration == pytest.approx(c.MAX_ANGULAR_ACCELERATION)


def test_simulation_constants_poses():
    assert set(SimulationConstants.BLUE_TEST_POSE) == {1, 2, 3}
    assert set(SimulationConstants.RED_TEST_POSE) == {1, 2, 3}
    blue_x = SimulationConstants.BLUE_TEST_POSE[1].x
    red_x = SimulationConstants.RED_TEST_POSE[3].x
    assert blue_x == pytest.approx(SimulationConstants.BLUE_TEST_POSE[2].x)
    assert red_x == pytest.approx(16.54 - blue_x)


def test_network_constants_defaults():
    n = NetworkConstants()
    assert n.team == "61.07"
    assert n.ROBORIO_STATIC == "10.61.07.2"
    assert n.ROBORIO_USB_STATIC == "172.22.11.2"


def test_network_constants_team_setter_cascades():
    n = NetworkConstants()
    n.team = "63.28"
    assert n.team == "63.28"
    assert n.ROBORIO_STATIC == "10.63.28.2"
    assert n.ROBOT_RADIO_STATIC == "10.63.28.1"
    assert n.AP_RADIO_STATIC == "10.63.28.4"
    assert n.DRIVER_STATION_STATIC == "10.63.28.5"
    assert n.DRIVER_STATION_ALT_STATIC == "10.63.28.6"
    assert n.ROBORIO_MDMS == "roboRIO-63.28-frc.local"


def test_network_constants_team_setter_same_team_is_noop():
    n = NetworkConstants()
    before = n.ROBORIO_STATIC
    n.team = n.TEAM
    assert n.ROBORIO_STATIC == before


@pytest.mark.parametrize(
    "is_real, log_path, expected",
    [
        (True, None, "REAL"),
        (False, None, "SIMULATION"),
        (False, "", "SIMULATION"),
        (False, "some.wpilog", "REPLAY"),
    ],
)
def test_mode_detection(monkeypatch, is_real, log_path, expected):
    if log_path is None:
        monkeypatch.delenv("LOG_PATH", raising=False)
    else:
        monkeypatch.setenv("LOG_PATH", log_path)
    monkeypatch.setattr("wpilib.RobotBase.is_real", staticmethod(lambda: is_real))
    try:
        mod = importlib.reload(constants)
        assert mod.ROBOT_MODE.name == expected
    finally:
        monkeypatch.undo()
        importlib.reload(constants)
