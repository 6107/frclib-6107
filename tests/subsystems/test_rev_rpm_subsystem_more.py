"""Additional RevRpmSubsystem tests: goal, post_init, connectivity, sim, motor config, faults."""

from unittest.mock import MagicMock, patch

import pytest
from rev import REVLibError, Signal_double
from wpimath import DCMotor

from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.rpm.rev_rpm_subsystem import RevRpmConfig, RevRpmSubsystem
from lib_6107.subsystems.rpm.rpm_subsystem import ControllerType

MOD = "lib_6107.subsystems.rpm.rev_rpm_subsystem"


class _Config(RevRpmConfig):
    max_rpm = 5000


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.period = 0.02
    return c


def _build(container, controller_type=ControllerType.SparkFlex, simulation=False, constants=None, **kwargs):
    with (
        patch(f"{MOD}.SparkFlex") as flex,
        patch(f"{MOD}.SparkMax") as spark_max,
        patch(f"{MOD}.SparkFlexSim") as flex_sim,
        patch(f"{MOD}.SparkMaxSim") as max_sim,
        patch("lib_6107.subsystems.subsystem.RobotBase") as robot_base,
    ):
        robot_base.is_simulation.return_value = simulation
        for m in (flex, spark_max):
            m.MotorType.BRUSHLESS = "brushless"
            m.return_value.configure.return_value = REVLibError.OK
            m.return_value.get_firmware_version.return_value = 1
        sub = RevRpmSubsystem(
            container, 5, False, "shooter", DCMotor.neo_vortex(1), controller_type, constants or _Config(), **kwargs
        )
    return sub, flex_sim, max_sim


def test_sim_motor_created_in_simulation(container):
    sub, flex_sim, _ = _build(container, ControllerType.SparkFlex, simulation=True)
    assert sub._sim_motor is flex_sim.return_value
    assert sub.is_connected is True

    sub, _, max_sim = _build(container, ControllerType.SparkMax, simulation=True)
    assert sub._sim_motor is max_sim.return_value


def test_no_sim_motor_outside_simulation(container):
    sub, flex_sim, max_sim = _build(container)
    assert sub._sim_motor is None
    flex_sim.assert_not_called()
    max_sim.assert_not_called()


def test_post_init_persist_and_connected(container):
    sub, *_ = _build(container, persist_config=True, coast=False)
    # __init__ now runs the Rev post_init (connected, set_setpoint once)
    assert sub._is_connected is True
    assert sub.is_connected is True
    sub._pid_controller.set_setpoint.assert_called_once()


def test_post_init_config_failure_not_connected(container):
    sub, *_ = _build(container)
    sub._motor.configure.return_value = REVLibError.TIMEOUT
    sub.post_init(True, False)
    assert sub._is_connected is False
    assert sub.is_connected is False
    assert sub._motor.configure.call_count >= 5


def test_try_until_ok_wrapper(container):
    sub, *_ = _build(container)
    calls = iter([REVLibError.TIMEOUT, REVLibError.OK])
    assert sub.try_until_ok("x", 3, lambda: next(calls)) == REVLibError.OK


def test_check_is_connected_branches(container, caplog):
    sub, *_ = _build(container)
    sub._motor.get_firmware_version.return_value = 7
    assert sub._check_is_connected(None) is True
    assert sub._check_is_connected(REVLibError.OK) is True
    sub._motor.get_firmware_version.return_value = 0
    assert not sub._check_is_connected(REVLibError.OK)
    sub._motor.get_firmware_version.return_value = 7
    assert not sub._check_is_connected(REVLibError.TIMEOUT)
    sub._is_simulation = True
    assert sub._check_is_connected(REVLibError.TIMEOUT)
    sub._controller_type = ControllerType.KrakenX60
    with pytest.raises(NotImplementedError):
        sub._check_is_connected(None)


def test_motor_config_unsupported_type(container):
    sub, *_ = _build(container)
    sub._controller_type = ControllerType.KrakenX60
    with pytest.raises(NotImplementedError):
        sub._motor_config(True)


@pytest.mark.parametrize("ctype", [ControllerType.SparkMax, ControllerType.SparkFlex])
@pytest.mark.parametrize("coast", [True, False])
def test_motor_config_with_optional_gains(container, ctype, coast):
    class Cfg(_Config):
        velocity_feedforward = 0.002
        imax_accum = 0.5
        izone = 100.0

    sub, *_ = _build(container, ctype, constants=Cfg())
    assert sub._motor_config(coast) is not None


def test_motor_config_without_optional_gains(container):
    sub, *_ = _build(container, ControllerType.SparkMax)
    assert sub._motor_config(True) is not None


@pytest.mark.parametrize("inverted,sign", [(False, 1), (True, -1)])
def test_velocity_and_position(container, inverted, sign):
    import math

    sub, *_ = _build(container)
    sub._inverted = inverted
    sub._encoder = MagicMock()
    sub._encoder.get_velocity.return_value = Signal_double(60.0, REVLibError.OK, 0)
    sub._encoder.get_position.return_value = Signal_double(2.0, REVLibError.OK, 0)
    assert sub.velocity_in_rps == pytest.approx(sign * 2 * math.pi)
    assert sub.velocity_in_rpm == pytest.approx(sign * 60.0)
    assert sub.position == pytest.approx(4 * math.pi)


def test_set_velocity_goal_clamps_and_commands(container):
    sub, *_ = _build(container)
    sub._pid_controller = MagicMock()
    sub._pid_controller.get_setpoint.return_value = 0.0
    sub._set_velocity_goal(99999, 50)
    assert sub.goal == 5000 and sub.tolerance == 50
    sub._pid_controller.set_setpoint.assert_called_once()

    sub._pid_controller.reset_mock()
    sub._set_velocity_goal(-100, None)  # abs -> 100, tolerance None -> 0
    assert sub.goal == 100 and sub.tolerance == 0.0
    sub._pid_controller.set_setpoint.assert_called_once()

    sub._pid_controller.reset_mock()
    sub._set_velocity_goal(100, 0)  # unchanged
    sub._pid_controller.set_setpoint.assert_not_called()


def test_stop_zeroes_goal(container):
    sub, *_ = _build(container)
    sub._pid_controller = MagicMock()
    sub._motor = MagicMock()
    sub._set_velocity_goal(1000, 10)
    sub.stop()
    assert sub.goal == 0.0 and sub.tolerance == 0.0
    sub._motor.disable.assert_called_once()


def test_not_ready_at_speed(container):
    sub, *_ = _build(container)
    sub._encoder = MagicMock()
    sub._encoder.get_velocity.return_value = Signal_double(1000.0, REVLibError.OK, 0)
    sub._velocity_goal, sub._velocity_tolerance = 1020.0, 50.0
    assert sub.not_ready == ""
    sub._velocity_goal = 2000.0
    assert "under" in sub.not_ready
    sub._velocity_goal = 100.0
    assert "above" in sub.not_ready


def test_update_inputs_simulation_invalid_signals_still_connected(container):
    from rev import SparkBase, Signal_SparkFaults, Signal_SparkWarnings

    sub, *_ = _build(container, simulation=True)
    err = REVLibError.TIMEOUT
    sub._encoder = MagicMock()
    sub._encoder.get_velocity.return_value = Signal_double(1.0, err, 0)
    sub._encoder.get_position.return_value = Signal_double(1.0, err, 0)
    sub._motor = MagicMock()
    for name in ("get_applied_output", "get_bus_voltage", "get_output_current", "get_motor_temperature"):
        getattr(sub._motor, name).return_value = Signal_double(1.0, err, 0)
    sub._motor.get_faults.return_value = Signal_SparkFaults(SparkBase.Faults(0), err, 0)
    sub._motor.get_warnings.return_value = Signal_SparkWarnings(SparkBase.Warnings(0), err, 0)
    inputs = RpmMechanismIO.RpmMechanismIOInputs()
    sub.update_inputs(inputs)
    assert inputs.mechanism_connected is True
    assert inputs.mechanism_last_error != 0


def test_fault_detection_delegates(container):
    sub, *_ = _build(container)
    with patch(f"{MOD}.handle_faults") as handle:
        sub.fault_detection("teleop", clear=False, notify=False)
        sub.fault_detection("auto")
    assert handle.call_count == 2
    handle.assert_any_call("shooter", "teleop", sub._motor, clear=False, notify=False)


def test_update_sim_enabled_disabled_none(container):
    sub, *_ = _build(container, simulation=True)
    sub._encoder = MagicMock()
    sub._encoder.get_velocity.return_value = Signal_double(60.0, REVLibError.OK, 0)
    sub._robot = MagicMock()
    sim = MagicMock()
    sim.get_motor_current.return_value = 3.0
    sub._sim_motor = sim
    sub._robot.is_enabled.return_value = False
    assert sub.update_sim(0, 0.02) is None
    sub._robot.is_enabled.return_value = True
    with patch("lib_6107.subsystems.rpm.rpm_subsystem.RoboRioSim") as rio:
        rio.get_vin_voltage.return_value = 12.0
        assert sub.update_sim(0, 0.02) == 3.0
    sub._sim_motor = None
    assert sub.update_sim(0, 0.02) is None
