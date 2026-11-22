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


def _signals(sub, velocity=60.0, position=2.0, valid=True):
    from rev import SparkBase, Signal_SparkFaults, Signal_SparkWarnings

    err = REVLibError.OK if valid else REVLibError.TIMEOUT
    sub._encoder = MagicMock()
    sub._encoder.get_velocity.return_value = Signal_double(velocity, err, 0)
    sub._encoder.get_position.return_value = Signal_double(position, err, 0)
    sub._motor = MagicMock()
    sub._motor.get_applied_output.return_value = Signal_double(0.5, err, 0)
    sub._motor.get_bus_voltage.return_value = Signal_double(12.0, err, 0)
    sub._motor.get_output_current.return_value = Signal_double(7.0, err, 0)
    sub._motor.get_motor_temperature.return_value = Signal_double(40.0, err, 0)
    sub._motor.get_faults.return_value = Signal_SparkFaults(SparkBase.Faults(4), err, 0)
    sub._motor.get_warnings.return_value = Signal_SparkWarnings(SparkBase.Warnings(1), err, 0)


def test_update_inputs_converts_units_and_reads_once(container):
    import math

    from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO

    sub, _, _ = _build(container, ControllerType.SparkFlex)
    sub._is_connected = True
    _signals(sub)
    inputs = RpmMechanismIO.RpmMechanismIOInputs()
    sub.update_inputs(inputs)
    assert inputs.mechanism_velocity == pytest.approx(60.0 * 2 * math.pi / 60.0)
    assert inputs.mechanism_position == pytest.approx(2.0 * 2 * math.pi)
    assert inputs.mechanism_applied_voltage == pytest.approx(6.0)
    assert inputs.mechanism_supply_current == 7.0
    assert inputs.mechanism_temperature == 40.0
    assert (inputs.mechanism_faults_raw, inputs.mechanism_warnings_raw) == (4, 1)
    assert inputs.mechanism_connected and inputs.mechanism_last_error == 0
    sub._encoder.get_velocity.assert_called_once()
    sub._encoder.get_position.assert_called_once()
    sub._motor.get_faults.assert_called_once()


def test_update_inputs_inverted_flips_velocity(container):
    from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO

    sub, _, _ = _build(container, ControllerType.SparkFlex)
    sub._is_connected = True
    sub._inverted = True
    _signals(sub)
    inputs = RpmMechanismIO.RpmMechanismIOInputs()
    sub.update_inputs(inputs)
    assert inputs.mechanism_velocity < 0


def test_update_inputs_invalid_signal_reports_error(container):
    from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO

    sub, _, _ = _build(container, ControllerType.SparkFlex)
    sub._is_connected = True
    sub._is_simulation = False
    _signals(sub, valid=False)
    inputs = RpmMechanismIO.RpmMechanismIOInputs()
    sub.update_inputs(inputs)
    assert inputs.mechanism_connected is False
    assert inputs.mechanism_last_error != 0
    assert (inputs.mechanism_velocity, inputs.mechanism_faults_raw) == (0.0, 0)


def test_motor_config_builds_with_signal_periods(container):
    sub, _, _ = _build(container, ControllerType.SparkFlex)
    assert sub._motor_config(True) is not None
