"""Unit tests for RevRpmSubsystem (REVLib 2027: CAN port is a required constructor argument)."""

from unittest.mock import MagicMock, patch

import pytest
from rev import REVLibError, Signal_double
from wpilib import CANPort
from wpimath import DCMotor

from lib_6107.subsystems.rpm.rev_rpm_subsystem import RevRpmConfig, RevRpmSubsystem
from lib_6107.subsystems.rpm.rpm_subsystem import ControllerType


class _Config(RevRpmConfig):
    max_rpm = 5000


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.period = 0.02
    return c


def _build(container, controller_type, **kwargs):
    with (
        patch("lib_6107.subsystems.rpm.rev_rpm_subsystem.SparkFlex") as flex,
        patch("lib_6107.subsystems.rpm.rev_rpm_subsystem.SparkMax") as spark_max,
        patch("lib_6107.subsystems.rpm.rev_rpm_subsystem.SparkFlexSim"),
        patch("lib_6107.subsystems.rpm.rev_rpm_subsystem.SparkMaxSim"),
    ):
        flex.MotorType.BRUSHLESS = "brushless"
        spark_max.MotorType.BRUSHLESS = "brushless"
        flex.return_value.configure.return_value = REVLibError.OK
        spark_max.return_value.configure.return_value = REVLibError.OK
        sub = RevRpmSubsystem(
            container, 5, False, "shooter", DCMotor.neo_vortex(1), controller_type, _Config(), **kwargs
        )
    return sub, flex, spark_max


def test_spark_flex_defaults_to_can_s0(container):
    _, flex, _ = _build(container, ControllerType.SparkFlex)
    flex.assert_called_once_with(CANPort.CAN_S0, 5, "brushless")


def test_spark_max_defaults_to_can_s0(container):
    _, _, spark_max = _build(container, ControllerType.SparkMax)
    spark_max.assert_called_once_with(CANPort.CAN_S0, 5, "brushless")


def test_can_port_is_passed_through(container):
    _, flex, _ = _build(container, ControllerType.SparkFlex, can_port=CANPort.CAN_S1)
    flex.assert_called_once_with(CANPort.CAN_S1, 5, "brushless")


def test_unsupported_controller_type_raises(container):
    with pytest.raises(NotImplementedError):
        _build(container, ControllerType.KrakenX60)


def test_real_signal_objects_unwrap():
    # 2027 getters return Signal wrappers; the subsystem relies on .get()
    sig = Signal_double(1.5, REVLibError.OK, 0)
    assert sig.is_valid() and sig.get() == 1.5
