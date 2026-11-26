"""Unit tests for the RpmSubsystem base class (abstract hooks, readiness, periodic, sim, SysId)."""

from unittest.mock import MagicMock, patch

import pytest
from commands2.sysid import SysIdRoutine
from wpimath import DCMotor

from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.rpm.rpm_subsystem import (
    ControllerType,
    RpmConfig,
    RpmSubsystem,
    _default_max_rpm,
)

MOD = "lib_6107.subsystems.rpm.rpm_subsystem"


class _Config(RpmConfig):
    max_rpm = 5000


class _Sub(RpmSubsystem):
    """Concrete subclass that overrides only what a test needs."""

    rps = 0.0

    @property
    def velocity_in_rps(self):
        return self.rps


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.period = 0.02
    return c


@pytest.fixture
def sub(container):
    s = _Sub(container, 1, False, "flywheel", ControllerType.SparkFlex, _Config(), None)
    s._motor = MagicMock()
    s._encoder = MagicMock()
    return s


def test_init_defaults(sub):
    assert sub._long_name == "flywheel"
    assert sub.goal == 0.0 and sub.tolerance == 0.0
    assert sub._sim_motor is None


def test_long_name_used(container):
    s = RpmSubsystem(container, 1, False, "flywheel", ControllerType.SparkFlex, _Config(), "shooter/flywheel")
    assert s._long_name == "shooter/flywheel"


def test_default_max_rpm_placeholder():
    assert _default_max_rpm(ControllerType.SparkMax, DCMotor.neo()) == 0.0


def test_required_attributes():
    assert "max_rpm" in RpmConfig().required_attributes


def test_post_init_validates_and_copies(sub):
    original = sub._constants
    sub.post_init(True, False)
    assert sub._constants is not original
    assert sub._constants.max_rpm == 5000


def test_validate_constants_defaults_none(container):
    class Cfg(_Config):
        limit_current = None
        derivative_coefficient = None

    s = RpmSubsystem(container, 1, False, "f", ControllerType.SparkMax, Cfg(), None)
    out = s._validate_constants()
    assert out.limit_current == 40
    assert out.derivative_coefficient == 0


def test_validate_constants_missing_attribute_raises(container):
    class Bare:
        pass

    s = RpmSubsystem(container, 1, False, "f", ControllerType.SparkMax, Bare(), None)
    with pytest.raises(ValueError):
        s._validate_constants()


def test_abstract_hooks_raise(sub, container):
    base = RpmSubsystem(container, 1, False, "f", ControllerType.SparkMax, _Config(), None)
    with pytest.raises(NotImplementedError):
        base._motor_config(True)
    with pytest.raises(NotImplementedError):
        _ = base.velocity_in_rps
    with pytest.raises(NotImplementedError):
        _ = base.position
    with pytest.raises(NotImplementedError):
        base._set_velocity_goal(1, 1)
    with pytest.raises(NotImplementedError):
        base.update_inputs(RpmMechanismIO.RpmMechanismIOInputs())


def test_velocity_in_rpm_and_active(sub):
    sub.rps = 2 * 3.141592653589793  # 1 rev/s
    assert sub.velocity_in_rpm == pytest.approx(60.0)
    sub._velocity_goal = 100.0
    assert sub.active is True
    sub._velocity_goal = 0.0
    assert sub.active is False
    sub._velocity_goal = 100.0
    sub.rps = 0.0
    assert sub.active is False


def test_not_ready_messages(sub):
    sub.rps = 2 * 3.141592653589793  # 60 rpm
    sub._velocity_tolerance = 5.0
    sub._velocity_goal = 100.0
    assert "under velocity goal" in sub.not_ready
    sub._velocity_goal = 10.0
    assert "above velocity goal" in sub.not_ready
    sub._velocity_goal = 62.0
    assert sub.not_ready == ""


def test_stop_zeroes_goal_and_disables(sub):
    with patch.object(sub, "_set_velocity_goal") as goal:
        sub.stop()
    goal.assert_called_once_with(0, 0)
    sub._motor.disable.assert_called_once()


def _prep_periodic(sub, counter, enabled):
    sub._initialized = True
    sub._robot = MagicMock(counter=counter)
    sub._robot.is_enabled.return_value = enabled


def test_periodic_not_initialized_does_nothing(sub):
    sub._initialized = False
    with patch.object(sub, "update_inputs") as upd:
        sub.periodic()
    upd.assert_not_called()


@pytest.mark.parametrize(
    "counter,enabled,expected",
    [(100, False, True), (1, False, False), (31, True, True), (31, False, False)],
)
def test_periodic_dashboard_throttle(sub, counter, enabled, expected):
    _prep_periodic(sub, counter, enabled)
    with (
        patch(f"{MOD}.Logger") as logger,
        patch(f"{MOD}.LogTracer") as tracer,
        patch.object(sub, "update_inputs") as upd,
        patch.object(sub, "dashboard_periodic") as dash,
    ):
        sub.periodic()
    upd.assert_called_once_with(sub._inputs)
    assert dash.called is expected
    assert logger.record_output.call_count == 3
    tracer.record_total.assert_called_once()


def test_periodic_records_total_even_on_error(sub):
    _prep_periodic(sub, 1, False)
    with (
        patch(f"{MOD}.Logger"),
        patch(f"{MOD}.LogTracer") as tracer,
        patch.object(sub, "update_inputs", side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(RuntimeError):
            sub.periodic()
    tracer.record_total.assert_called_once()


def test_dashboard_periodic_and_telemetry_init(sub):
    with patch(f"{MOD}.Logger") as logger:
        sub.telemetry_init()
        sub.dashboard_periodic()
    names = [c.args[0] for c in logger.record_output.call_args_list]
    assert names == ["flywheel/voltage", "flywheel/supply_current"]


def test_update_sim_branches(sub):
    sub._robot = MagicMock()
    sub.rps = 1.0
    sim = MagicMock()
    sim.get_motor_current.return_value = 7.0

    # no sim motor
    sub._robot.is_enabled.return_value = True
    assert sub.update_sim(0, 0.02) is None

    # sim motor but disabled
    sub._sim_motor = sim
    sub._robot.is_enabled.return_value = False
    assert sub.update_sim(0, 0.02) is None
    sim.iterate.assert_not_called()

    # enabled with sim motor
    sub._robot.is_enabled.return_value = True
    with patch(f"{MOD}.RoboRioSim") as rio:
        rio.get_vin_voltage.return_value = 12.5
        assert sub.update_sim(0, 0.02) == 7.0
    args = sim.iterate.call_args.args
    assert args[1] == 12.5 and args[2] == 0.02


def test_log_motor(sub):
    sub._encoder.get_position.return_value.get.return_value = 1.0
    sub._encoder.get_velocity.return_value.get.return_value = 2.0
    sub._motor.get_applied_output.return_value.get.return_value = 0.5
    sub._motor.get_bus_voltage.return_value.get.return_value = 12.0
    log = MagicMock()
    sub._log_motor(log)
    log.motor.assert_called_once_with("flywheel")
    log.motor.return_value.position.assert_called_once_with(1.0)
    log.motor.return_value.position.return_value.velocity.assert_called_once_with(2.0)
    log.motor.return_value.position.return_value.velocity.return_value.voltage.assert_called_once_with(6.0)


def test_set_voltage_only_when_different(sub):
    sub._motor.get_applied_output.return_value.get.return_value = 3.0
    sub._set_voltage(3.0)
    sub._motor.set_voltage.assert_not_called()
    sub._set_voltage(5.0)
    sub._motor.set_voltage.assert_called_once_with(5.0)


def test_sysid_commands(sub):
    assert sub.sys_id_quasistatic(SysIdRoutine.Direction.FORWARD) is not None
    assert sub.sys_id_dynamic(SysIdRoutine.Direction.REVERSE) is not None
