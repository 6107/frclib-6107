"""Unit tests for CtreSwerveModule using mocked Phoenix6 devices (no hardware)."""

from unittest.mock import MagicMock, patch

import pytest
from wpimath import Rotation2d, SwerveModulePosition, SwerveModuleVelocity
from wpimath.units import radians_to_rotations

import lib_6107.subsystems.drivetrain.ctre_swervedrive as mod
from lib_6107.subsystems.drivetrain.ctre_swervedrive import CtreSwerveModule
from lib_6107.subsystems.pykit.swervedrive_io import SwerveModuleIO


def _signal(value=0.0):
    s = MagicMock()
    s.value = value
    s.refresh.return_value = s
    s.value_as_double = value
    return s


@pytest.fixture(autouse=True)
def quiet():
    with patch.object(mod, "Logger"), patch.object(mod, "LogTracer"):
        yield


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.robot_constants.WHEEL_RADIUS = 0.05
    c.robot.robot_constants.MIN_SPEED = 0.1
    return c


@pytest.fixture
def module(container):
    hw = MagicMock()
    sig = _signal
    hw.drive_motor.get_position.return_value = sig(2.0)
    hw.drive_motor.get_velocity.return_value = sig(3.0)
    hw.drive_motor.get_supply_current.return_value = sig(0.0)
    hw.steer_motor.get_supply_current.return_value = sig(0.0)
    hw.encoder.get_absolute_position.return_value = sig(0.25)
    return CtreSwerveModule(hw, "front-left", container)


def test_init_registers_signals_and_reads_constants(module):
    assert module.wheel_radius == 0.05
    assert module._min_wheel_linear_velocity == 0.1
    assert module.name == "front-left"


def test_sim_hooks_are_noops(module):
    assert module.sim_init(MagicMock()) is None
    assert module.simulation_periodic() is None


def _set_currents(module, drive, steer):
    module.drive_supply_current = _signal(drive)
    module.turn_supply_current = _signal(steer)


def test_update_sim_sums_positive_currents(module):
    _set_currents(module, 3.0, 2.0)
    assert module.update_sim(0.0, 0.02) == pytest.approx(5.0)


def test_update_sim_backs_out_regen_current(module):
    _set_currents(module, -4.0, -1.0)
    assert module.update_sim(0.0, 0.02) == 0.0
    assert module._sim_drive_regen_amps == 4.0
    assert module._sim_steer_regen_amps == 1.0
    _set_currents(module, 3.0, 5.0)
    assert module.update_sim(0.0, 0.02) == pytest.approx(4.0)
    assert module._sim_drive_regen_amps == pytest.approx(1.0)
    assert module._sim_steer_regen_amps == 0.0
    _set_currents(module, 0.0, 0.0)
    assert module.update_sim(0.0, 0.02) == 0.0


def test_angle_setters_and_getters(module):
    module._inputs.turn_position = 0.25
    module._inputs.turn_absolute_position = 0.5
    assert module.get_swerve_angle().radians() == pytest.approx(0.25)
    assert module.get_swerve_encoder_angle().radians() == pytest.approx(0.5)
    module.set_swerve_angle(Rotation2d(1.0))
    module._steer_motor.set_position.assert_called_once_with(radians_to_rotations(1.0))


def test_targets_send_controls(module):
    module.set_swerve_angle_target(Rotation2d(1.0))
    module._steer_motor.set_control.assert_called_once()
    module.set_wheel_linear_velocity_target(2.0)
    module._drive_motor.set_control.assert_called_once()


def test_wheel_measurements_scale_by_radius(module):
    module._inputs.drive_velocity = 4.0
    module._inputs.drive_position = 10.0
    assert module.get_wheel_linear_velocity() == pytest.approx(0.2)
    assert module.get_wheel_total_position() == pytest.approx(0.5)
    assert isinstance(module.get_position(), SwerveModulePosition)
    assert isinstance(module.get_state(), SwerveModuleVelocity)


def test_reset_seeds_steer_from_encoder(module):
    module._inputs.turn_absolute_position = 0.5
    module.reset()
    module._steer_motor.set_position.assert_called_once_with(radians_to_rotations(0.5))


@pytest.mark.parametrize("velocity, steer_commanded", [(2.0, True), (0.0, False)])
def test_apply_states_skips_steer_below_min_speed(module, velocity, steer_commanded):
    module.apply_states(SwerveModuleVelocity(velocity, Rotation2d(0.2)))
    module._drive_motor.set_control.assert_called_once()
    assert module._steer_motor.set_control.called is steer_commanded


def test_update_inputs_copies_signal_values(module):
    for name in (
        "drive_position",
        "drive_velocity",
        "drive_applied",
        "drive_supply_current",
        "drive_torque_current",
        "turn_position",
        "turn_velocity",
        "turn_applied",
        "turn_supply_current",
        "turn_torque_current",
        "turn_absolute_position",
    ):
        setattr(module, name, _signal(1.5))
    inputs = SwerveModuleIO.SwerveModuleIOInputs()
    with patch.object(mod.StatusSignal, "is_all_good", return_value=True):
        module.update_inputs(inputs)
    assert inputs.drive_connected and inputs.steer_connected and inputs.encoder_connected
    assert inputs.drive_position == pytest.approx(radians_to_rotations(1.5))
    assert inputs.turn_absolute_position == pytest.approx(radians_to_rotations(1.5))
    assert inputs.drive_applied == 1.5
    assert inputs.turn_torque_current == 1.5


def test_periodic_updates_position_and_logs(module):
    with patch.object(module, "update_inputs") as update:
        module.periodic()
    update.assert_called_once_with(module._inputs)
    mod.Logger.process_inputs.assert_called_once()
    mod.LogTracer.record_total.assert_called_once()


def test_periodic_always_records_total_on_error(module):
    with patch.object(module, "update_inputs", side_effect=RuntimeError("x")):
        with pytest.raises(RuntimeError):
            module.periodic()
    mod.LogTracer.record_total.assert_called_once()
