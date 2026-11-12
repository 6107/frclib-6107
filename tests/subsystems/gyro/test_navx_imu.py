"""Unit tests for the NavX3 (2027 ``navx.Navx``) gyro wrapper."""

from unittest.mock import MagicMock

import pytest

from lib_6107.subsystems.gyro.navx_imu import NavX


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
