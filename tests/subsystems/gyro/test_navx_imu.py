"""Unit tests for the NavX3 (2027 ``navx.Navx``) gyro wrapper."""

import itertools
import math
import time
from unittest.mock import MagicMock

import pytest

from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.gyro.navx_imu import NavX
from lib_6107.subsystems.pykit.gyro_io import GyroIO


@pytest.fixture
def hardware():
    mock = MagicMock()
    mock.getYaw.return_value = 30.0
    mock.getPitch.return_value = 2.0
    mock.getRoll.return_value = -1.0
    mock.getAngle.return_value = 390.0
    mock.getAngularVelocity.return_value = MagicMock(z=90.0)
    mock.isConnected.return_value = True
    return mock


@pytest.fixture
def imu(hardware, monkeypatch):
    monkeypatch.setattr("lib_6107.subsystems.gyro.navx_imu.RobotBase.is_simulation", lambda: False)
    return NavX(is_reversed=False, inst=hardware)


def test_reads_hardware_values(imu):
    assert imu.yaw == 30.0
    assert imu.angle == 390.0
    assert imu.turn_rate_degrees_per_second == 90.0


def test_reversed_negates_angles(hardware, monkeypatch):
    monkeypatch.setattr("lib_6107.subsystems.gyro.navx_imu.RobotBase.is_simulation", lambda: False)
    imu = NavX(is_reversed=True, inst=hardware)
    assert imu.yaw == -30.0
    assert imu.turn_rate_degrees_per_second == -90.0


def test_missing_data_reads_as_zero(imu, hardware):
    hardware.getYaw.return_value = None
    hardware.getAngularVelocity.return_value = None
    assert imu.yaw == 0.0
    assert imu.turn_rate_degrees_per_second == 0.0


def test_zero_yaw_and_reset_use_reset_yaw(imu, hardware):
    imu.zero_yaw()
    imu.reset()
    assert hardware.resetYaw.call_count == 2


def test_calibrating_follows_connection(imu, hardware):
    assert not imu.is_calibrating
    hardware.isConnected.return_value = False
    assert imu.is_calibrating


def test_update_inputs_fills_radians_and_timestamps(imu, hardware):
    hardware.getTimestamp.return_value = 42.0
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    assert inputs.connected
    assert inputs.yaw == pytest.approx(math.radians(30.0))
    assert inputs.yaw_rate == pytest.approx(math.pi / 2)
    assert inputs.pitch == pytest.approx(math.radians(2.0))
    assert inputs.roll == pytest.approx(math.radians(-1.0))
    assert inputs.yaw_timestamp == inputs.yaw_rate_timestamp == 42.0
    assert inputs.roll_timestamp == inputs.pitch_timestamp == 42.0


def test_update_inputs_timestamp_falls_back_to_current_time(imu, hardware, monkeypatch):
    hardware.getTimestamp.return_value = None
    monkeypatch.setattr("lib_6107.subsystems.gyro.navx_imu.Timer.get_timestamp", lambda: 7.5)
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    assert inputs.yaw_timestamp == 7.5


def test_update_inputs_reports_disconnected(imu, hardware):
    hardware.isConnected.return_value = False
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    assert not inputs.connected


def test_can_id_is_used_for_default_device(monkeypatch):
    monkeypatch.setattr("lib_6107.subsystems.gyro.navx_imu.navx.Navx", MagicMock())
    from lib_6107.subsystems.gyro import navx_imu

    NavX(is_reversed=False, can_id=7)
    navx_imu.navx.Navx.assert_called_once_with(7)


def test_factory_passes_device_id_as_can_id(monkeypatch):
    monkeypatch.setattr("lib_6107.subsystems.gyro.navx_imu.navx.Navx", MagicMock())
    from lib_6107.subsystems.gyro import navx_imu

    assert Gyro.create("navx", False, device_id=9) is not None
    navx_imu.navx.Navx.assert_called_once_with(9)


# The following tests use the real simulated NavX3 (a SimDevice named "NavX3[<can_id>]").
# The NavX3 copies SimDevice values on a background thread, so reads must be polled.
_next_can_id = itertools.count(40)


def _eventually(read, expected, timeout=2.0):
    deadline = time.monotonic() + timeout
    value = read()
    while value != expected and time.monotonic() < deadline:
        time.sleep(0.01)
        value = read()
    return value


@pytest.fixture
def sim_imu():
    gyro = NavX(is_reversed=False, can_id=next(_next_can_id))
    gyro.sim_init(MagicMock())
    return gyro


def test_sim_yaw_round_trips_through_real_navx(sim_imu):
    sim_imu.sim_yaw = 45.0
    assert sim_imu.sim_yaw == 45.0
    assert _eventually(lambda: sim_imu.yaw, 45.0) == 45.0
    assert sim_imu.angle == 45.0
    assert sim_imu.raw_angle == 45.0


def test_sim_zero_yaw_resets_yaw_and_angle(sim_imu):
    sim_imu.sim_yaw = 90.0
    assert _eventually(lambda: sim_imu.yaw, 90.0) == 90.0
    sim_imu.zero_yaw()
    assert _eventually(lambda: sim_imu.yaw, 0.0) == 0.0
    assert _eventually(lambda: sim_imu.angle, 0.0) == 0.0


def test_sim_reversed_reads_back_set_value():
    gyro = NavX(is_reversed=True, can_id=next(_next_can_id))
    gyro.sim_init(MagicMock())
    gyro.sim_yaw = 30.0
    assert _eventually(lambda: gyro.yaw, 30.0) == 30.0


def test_sim_pitch_roll_and_rate_come_from_sim_device(sim_imu):
    device = sim_imu._sim_device()
    device.get_double("Pitch").set(3.0)
    device.get_double("Roll").set(-2.0)
    device.get_double("Angular Velocity Z").set(20.0)
    assert _eventually(lambda: sim_imu.pitch, 3.0) == 3.0
    assert _eventually(lambda: sim_imu.roll, -2.0) == -2.0
    assert _eventually(lambda: sim_imu.turn_rate_degrees_per_second, 20.0) == 20.0
