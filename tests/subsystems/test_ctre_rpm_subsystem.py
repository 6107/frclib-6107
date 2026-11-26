"""Unit tests for CtreRpmSubsystem (TalonFX / Kraken X60) without hardware."""

import math
from unittest.mock import MagicMock, patch

import pytest
from phoenix6 import StatusCode
from phoenix6.signals import NeutralModeValue
from wpimath import DCMotor

from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.rpm.ctre_rpm_subsystem import CtreRpmConfig, CtreRpmSubsystem
from lib_6107.subsystems.rpm.rpm_subsystem import ControllerType

MOD = "lib_6107.subsystems.rpm.ctre_rpm_subsystem"


class _Config(CtreRpmConfig):
    max_rpm = 5000


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.period = 0.02
    return c


def _build(container, controller_type=ControllerType.KrakenX60, status_ok=True, constants=None, **kwargs):
    with (
        patch(f"{MOD}.TalonFX") as talon,
        patch(f"{MOD}.StatusSignal") as status_signal,
        patch(f"{MOD}.Phoenix6Signals") as registry,
    ):
        status_signal.set_update_frequency_for_all.return_value = StatusCode.OK if status_ok else StatusCode.RX_TIMEOUT
        talon.return_value.optimize_bus_utilization.return_value = StatusCode.OK if status_ok else StatusCode.RX_TIMEOUT
        sub = CtreRpmSubsystem(
            container, 3, False, "shooter", DCMotor.kraken_x60(1), controller_type, constants or _Config(), **kwargs
        )
    return sub, talon, status_signal, registry


def test_init_creates_talon_and_registers_signals(container):
    sub, talon, _, registry = _build(container)
    talon.assert_called_once_with(3, "")
    registry.register_signals.assert_called_once()
    assert sub._motor is talon.return_value


def test_init_bus_optimization_failure_logs_warning(container, caplog):
    _build(container, status_ok=False)
    assert "bus optimization" in caplog.text


def test_init_unsupported_controller_raises(container):
    with pytest.raises(NotImplementedError):
        _build(container, ControllerType.SparkMax)


def test_validate_constants_fills_none(container):
    class Cfg(_Config):
        proportional_coefficient = None

    sub, *_ = _build(container, constants=Cfg())
    assert sub._constants.proportional_coefficient == 0.0001


def test_post_init_applies_config_and_connects(container):
    sub, *_ = _build(container)
    sub._motor = MagicMock()
    sub._motor.configurator.apply.return_value = StatusCode.OK
    sub.post_init(True, False)
    sub._motor.configurator.apply.assert_called()
    assert sub._is_connected is True
    assert sub.is_connected is True


def test_post_init_failed_config_is_not_connected(container):
    sub, *_ = _build(container)
    sub._motor = MagicMock()
    sub._motor.configurator.apply.return_value = StatusCode.RX_TIMEOUT
    sub.post_init(False, False)
    assert sub._is_connected is False
    assert sub.is_connected is False


def test_check_is_connected_variants(container):
    sub, *_ = _build(container)
    assert sub._check_is_connected(StatusCode.OK) is True
    with patch(f"{MOD}.StatusSignal") as status_signal:
        status_signal.is_all_good.return_value = True
        assert sub._check_is_connected(None) is True
        status_signal.is_all_good.return_value = False
        assert sub._check_is_connected(None) is False
    assert sub._check_is_connected(StatusCode.RX_TIMEOUT) is False


def test_is_connected_other_controller_type_false(container):
    sub, *_ = _build(container)
    sub._controller_type = ControllerType.SparkMax
    assert sub.is_connected is False


@pytest.mark.parametrize("coast,mode", [(True, NeutralModeValue.COAST), (False, NeutralModeValue.BRAKE)])
def test_motor_config_neutral_mode(container, coast, mode):
    sub, *_ = _build(container)
    config = sub._motor_config(coast)
    assert config.motor_output.neutral_mode == mode
    assert config.current_limits.supply_current_limit == 40
    assert config.slot0.k_p == pytest.approx(0.0001)


def test_motor_config_feedforward(container):
    class Cfg(_Config):
        velocity_feedforward = 0.12

    sub, *_ = _build(container, constants=Cfg())
    assert sub._motor_config(True).slot0.k_v == pytest.approx(0.12)


def test_motor_config_unsupported_type(container):
    sub, *_ = _build(container)
    sub._controller_type = ControllerType.SparkMax
    with pytest.raises(NotImplementedError):
        sub._motor_config(True)


@pytest.mark.parametrize("inverted,sign", [(False, 1), (True, -1)])
def test_velocity_and_position(container, inverted, sign):
    sub, *_ = _build(container)
    sub._inverted = inverted
    sub._velocity = MagicMock(value=2.0)
    sub._position = MagicMock(value=0.5)
    assert sub.velocity_in_rps == pytest.approx(sign * 2.0 * 2 * math.pi)
    assert sub.position == pytest.approx(0.5 * 2 * math.pi)


def test_set_velocity_goal_clamps_and_updates(container):
    sub, *_ = _build(container)
    sub._pid_controller = None
    sub._velocity_request = MagicMock()
    sub._motor = MagicMock()
    sub._set_velocity_goal(-9999, 25)
    assert sub.goal == 5000
    assert sub.tolerance == 25
    sub._velocity_request.with_velocity.assert_called_once_with(pytest.approx(5000 / 60.0))
    sub._motor.set_control.assert_called_once()

    # Same goal and tolerance: no new request
    sub._velocity_request.reset_mock()
    sub._motor.reset_mock()
    sub._set_velocity_goal(5000, 25)
    sub._velocity_request.with_velocity.assert_not_called()
    sub._motor.set_control.assert_not_called()

    # Tolerance-only change: new request
    sub._set_velocity_goal(5000, None)
    assert sub.tolerance == 0.0
    sub._motor.set_control.assert_called_once()


def test_set_velocity_goal_negative_clamps_to_zero_when_none(container):
    sub, *_ = _build(container)
    sub._set_velocity_goal(0, None)
    assert sub.goal == 0.0


def test_update_inputs(container):
    sub, *_ = _build(container)
    sub._is_connected = True
    sub._velocity = MagicMock(value=1.0)
    sub._position = MagicMock(value=2.0)
    sub._applied_output = MagicMock(value=6.0)
    sub._supply_current = MagicMock(value=9.0)
    inputs = RpmMechanismIO.RpmMechanismIOInputs()
    sub.update_inputs(inputs)
    assert inputs.mechanism_connected is True
    assert inputs.mechanism_velocity == pytest.approx(2 * math.pi)
    assert inputs.mechanism_position == pytest.approx(4 * math.pi)
    assert inputs.mechanism_applied_voltage == 6.0
    assert inputs.mechanism_supply_current == 9.0


def test_log_motor(container):
    sub, *_ = _build(container)
    sub._velocity = MagicMock(value=1.0)
    sub._position = MagicMock(value=2.0)
    sub._applied_output = MagicMock(value=6.0)
    log = MagicMock()
    sub._log_motor(log)
    log.motor.assert_called_once_with("shooter")
    chain = log.motor.return_value
    chain.position.return_value.velocity.return_value.voltage.assert_called_once_with(6.0)


def test_set_voltage_only_when_changed(container):
    sub, *_ = _build(container)
    sub._motor = MagicMock()
    sub._voltage_request = MagicMock()
    sub._applied_output = MagicMock(value=3.0)
    sub._set_voltage(3.0)
    sub._motor.set_control.assert_not_called()
    sub._set_voltage(4.0)
    sub._motor.set_control.assert_called_once()
    sub._voltage_request.with_output.assert_called_once_with(4.0)


def test_fault_detection_delegates(container):
    sub, *_ = _build(container)
    with patch(f"{MOD}.handle_faults") as handle:
        sub.fault_detection("auto", clear=False, notify=False)
    handle.assert_called_once_with("shooter", "auto", sub._motor, clear=False, notify=False)


def test_stop_sets_zero_goal_and_disables(container):
    sub, *_ = _build(container)
    sub._pid_controller = MagicMock()
    sub._motor = MagicMock()
    sub._velocity_goal = 1000.0
    sub.stop()
    assert sub.goal == 0.0
    sub._motor.disable.assert_called_once()


def _periodic_setup(sub, counter=1, enabled=False):
    sub._initialized = True
    sub._velocity = MagicMock(value=0.0)
    sub._position = MagicMock(value=0.0)
    sub._applied_output = MagicMock(value=0.0)
    sub._supply_current = MagicMock(value=0.0)
    sub._robot = MagicMock(counter=counter)
    sub._robot.is_enabled.return_value = enabled


def test_periodic_runs_and_throttles_dashboard(container):
    sub, *_ = _build(container)
    _periodic_setup(sub, counter=100)
    with (
        patch("lib_6107.subsystems.rpm.rpm_subsystem.Logger") as logger,
        patch("lib_6107.subsystems.rpm.rpm_subsystem.LogTracer"),
        patch.object(sub, "dashboard_periodic") as dash,
    ):
        sub.periodic()
        dash.assert_called_once()
        logger.process_inputs.assert_called_once()

        dash.reset_mock()
        sub._robot.counter = 1
        sub.periodic()
        dash.assert_not_called()

        sub._robot.counter = 31
        sub._robot.is_enabled.return_value = True
        sub.periodic()
        dash.assert_called_once()


def test_periodic_skipped_when_not_initialized(container):
    sub, *_ = _build(container)
    sub._initialized = False
    with patch.object(sub, "update_inputs") as upd:
        sub.periodic()
    upd.assert_not_called()


def test_dashboard_and_telemetry(container):
    sub, *_ = _build(container)
    with patch("lib_6107.subsystems.rpm.rpm_subsystem.Logger") as logger:
        sub.telemetry_init()
        sub.dashboard_periodic()
    assert logger.record_output.call_count == 2


def test_not_ready_and_active(container):
    sub, *_ = _build(container)
    sub._velocity = MagicMock(value=1.0)  # 60 rpm
    sub._velocity_goal = 1000.0
    sub._velocity_tolerance = 10.0
    assert sub.not_ready.startswith("under")
    assert sub.active is True
    sub._velocity_goal = 10.0
    assert sub.not_ready.startswith("above")
    sub._velocity_goal = 60.0
    assert sub.not_ready == ""


def test_update_sim_branches(container):
    sub, *_ = _build(container)
    sub._velocity = MagicMock(value=1.0)
    sub._robot = MagicMock()
    sub._sim_motor = None
    sub._robot.is_enabled.return_value = True
    assert sub.update_sim(0, 0.02) is None

    sim = MagicMock()
    sim.get_motor_current.return_value = 12.5
    sub._sim_motor = sim
    with patch("lib_6107.subsystems.rpm.rpm_subsystem.RoboRioSim") as rio:
        rio.get_vin_voltage.return_value = 12.0
        assert sub.update_sim(0, 0.02) == 12.5
        sim.iterate.assert_called_once()
        sub._robot.is_enabled.return_value = False
        assert sub.update_sim(0, 0.02) is None
