"""Unit tests for the Systemcore onboard IMU (``wpilib.OnboardIMU``) gyro wrapper."""

import math
from unittest.mock import MagicMock

import pytest
import wpilib

from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.gyro.onboard_imu import OnboardImu
from lib_6107.subsystems.pykit.gyro_io import GyroIO

MODULE = "lib_6107.subsystems.gyro.onboard_imu"


@pytest.fixture
def hardware():
    mock = MagicMock()
    mock.get_yaw.return_value = math.radians(30.0)
    mock.get_angle_y.return_value = math.radians(2.0)
    mock.get_angle_x.return_value = math.radians(-1.0)
    mock.get_gyro_rate_z.return_value = math.pi / 2
    return mock


@pytest.fixture
def real_mode(monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: False)


@pytest.fixture
def imu(hardware, real_mode):
    return OnboardImu(is_reversed=False, inst=hardware)


def test_reads_hardware_values_in_degrees(imu):
    assert imu.yaw == pytest.approx(30.0)
    assert imu.angle == pytest.approx(30.0)
    assert imu.raw_angle == pytest.approx(30.0)
    assert imu.pitch == pytest.approx(2.0)
    assert imu.roll == pytest.approx(-1.0)
    assert imu.turn_rate == pytest.approx(math.pi / 2)
    assert imu.turn_rate_degrees_per_second == pytest.approx(90.0)


def test_reversed_negates_yaw_and_rate_but_not_raw(hardware, real_mode):
    imu = OnboardImu(is_reversed=True, inst=hardware)
    assert imu.yaw == pytest.approx(-30.0)
    assert imu.angle == pytest.approx(-30.0)
    assert imu.turn_rate_degrees_per_second == pytest.approx(-90.0)
    assert imu.raw_angle == pytest.approx(30.0)


def test_zero_yaw_reset_and_initialize_call_reset_yaw(imu, hardware):
    imu.zero_yaw()
    imu.reset()
    imu.initialize()
    assert hardware.reset_yaw.call_count == 3


def test_never_calibrating(imu):
    assert imu.calibrated
    assert not imu.is_calibrating


def test_update_inputs_fills_radians(imu):
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    assert inputs.connected
    assert inputs.yaw == pytest.approx(math.radians(30.0))
    assert inputs.yaw_rate == pytest.approx(math.pi / 2)
    assert inputs.pitch == pytest.approx(math.radians(2.0))
    assert inputs.roll == pytest.approx(math.radians(-1.0))


def test_simulation_uses_sim_yaw(hardware, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: True)
    imu = OnboardImu(is_reversed=False, inst=hardware)

    imu.sim_yaw = 45.0
    assert imu.yaw == 45.0
    assert imu.pitch == 0.0
    assert imu.turn_rate == 0.0

    imu.zero_yaw()
    assert imu.sim_yaw == 0.0
    hardware.reset_yaw.assert_not_called()
    hardware.get_yaw.assert_not_called()


def test_update_inputs_stamps_all_timestamps(imu, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.Timer.get_timestamp", lambda: 12.5)
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    assert inputs.yaw_timestamp == 12.5
    assert inputs.yaw_rate_timestamp == 12.5
    assert inputs.roll_timestamp == 12.5
    assert inputs.pitch_timestamp == 12.5


def test_simulation_yaw_rate_is_derived_from_sim_yaw(hardware, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: True)
    times = iter([1.0, 1.5, 2.0])
    monkeypatch.setattr(f"{MODULE}.Timer.get_timestamp", lambda: next(times))
    imu = OnboardImu(is_reversed=False, inst=hardware)
    inputs = GyroIO.GyroIOInputs()

    imu.update_inputs(inputs)
    assert inputs.yaw_rate == 0.0
    imu.sim_yaw = 90.0
    imu.update_inputs(inputs)
    assert inputs.yaw_rate == pytest.approx(math.pi)
    imu.update_inputs(inputs)
    assert inputs.yaw_rate == 0.0


def test_simulation_yaw_rate_reversed(hardware, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: True)
    times = iter([0.0, 1.0])
    monkeypatch.setattr(f"{MODULE}.Timer.get_timestamp", lambda: next(times))
    imu = OnboardImu(is_reversed=True, inst=hardware)
    inputs = GyroIO.GyroIOInputs()
    imu.update_inputs(inputs)
    imu.sim_yaw = 90.0
    imu.update_inputs(inputs)
    assert inputs.yaw_rate == pytest.approx(-math.pi / 2)


def test_set_yaw_uses_offset_on_hardware(imu, hardware):
    imu.set_yaw(math.radians(100.0))
    assert imu.yaw == pytest.approx(100.0)
    hardware.get_yaw.return_value = math.radians(40.0)
    assert imu.yaw == pytest.approx(110.0)
    assert imu.raw_angle == pytest.approx(40.0)
    imu.zero_yaw()
    assert imu.yaw == pytest.approx(40.0)


def test_set_yaw_reversed_on_hardware(hardware, real_mode):
    imu = OnboardImu(is_reversed=True, inst=hardware)
    imu.set_yaw(math.radians(25.0))
    assert imu.yaw == pytest.approx(25.0)


def test_set_yaw_in_simulation(hardware, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: True)
    imu = OnboardImu(is_reversed=True, inst=hardware)
    imu.set_yaw(math.radians(25.0))
    assert imu.yaw == pytest.approx(25.0)
    assert imu.sim_yaw == pytest.approx(-25.0)


def test_simulation_reversed_yaw(hardware, monkeypatch):
    monkeypatch.setattr(f"{MODULE}.RobotBase.is_simulation", lambda: True)
    imu = OnboardImu(is_reversed=True, inst=hardware)
    imu.sim_yaw = 45.0
    assert imu.yaw == -45.0


@pytest.mark.parametrize("name", ["flat", "LANDSCAPE", " Portrait "])
def test_mount_orientation_strings_are_parsed(name, real_mode, monkeypatch):
    fake_class = MagicMock()
    fake_class.MountOrientation.__members__ = {"FLAT": 0, "LANDSCAPE": 1, "PORTRAIT": 2}
    monkeypatch.setattr(wpilib, "OnboardIMU", fake_class, raising=False)

    OnboardImu(is_reversed=False, mount_orientation=name)

    fake_class.assert_called_once_with(fake_class.MountOrientation.__members__[name.strip().upper()])


def test_mount_orientation_enum_is_passed_through(real_mode, monkeypatch):
    fake_class = MagicMock()
    monkeypatch.setattr(wpilib, "OnboardIMU", fake_class, raising=False)
    orientation = object()

    OnboardImu(is_reversed=False, mount_orientation=orientation)

    fake_class.assert_called_once_with(orientation)


def test_invalid_mount_orientation_raises(real_mode, monkeypatch):
    fake_class = MagicMock()
    fake_class.MountOrientation.__members__ = {"FLAT": 0}
    monkeypatch.setattr(wpilib, "OnboardIMU", fake_class, raising=False)

    with pytest.raises(ValueError, match="Invalid mount orientation"):
        OnboardImu(is_reversed=False, mount_orientation="sideways")


def test_missing_wpilib_class_raises_import_error(monkeypatch):
    monkeypatch.delattr(wpilib, "OnboardIMU", raising=False)
    with pytest.raises(ImportError):
        OnboardImu(is_reversed=False)


def test_factory_creates_onboard_imu(hardware, real_mode):
    gyro = Gyro.create("onboard", is_reversed=False, inst=hardware)
    assert isinstance(gyro, OnboardImu)
    assert Gyro.create("ONBOARD", is_reversed=True, inst=hardware).gyro_type == "OnboardIMU"


def test_factory_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delattr(wpilib, "OnboardIMU", raising=False)
    assert Gyro.create("onboard", is_reversed=False) is None


def test_factory_builds_real_wpilib_imu():
    if not hasattr(wpilib, "OnboardIMU"):
        pytest.skip("wpilib.OnboardIMU not available")
    gyro = Gyro.create("onboard", is_reversed=False, mount_orientation="landscape")
    assert isinstance(gyro, OnboardImu)
    assert gyro.gyro_type == "OnboardIMU"
