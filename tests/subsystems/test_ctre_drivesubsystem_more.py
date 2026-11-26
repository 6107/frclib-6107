"""Additional CtreDriveSubsystem tests: construction and the request/command/module helpers."""

from unittest.mock import MagicMock, patch

import pytest
from wpimath import Pose2d, Rotation2d, SwerveModulePosition, SwerveModuleVelocity

import lib_6107.subsystems.drivetrain.ctre_drivesubsystem as mod
import lib_6107.subsystems.drivetrain.drivesubsystem as base_mod
from lib_6107.subsystems.drivetrain.ctre_drivesubsystem import CtreDriveSubsystem


def _container():
    c = MagicMock()
    c.robot.period = 0.02
    c.robot.counter = 1
    c.robot.robot_constants.MAX_SPEED = 4.0
    c.robot.robot_constants.MAX_ANGULAR_VELOCITY = 3.0
    c.robot.robot_constants.JOYSTICK_DEADBAND = 0.1
    c.robot.robot_constants.WHEEL_CIRCUMFERENCE = 0.3
    c.robot.robot_constants.WHEEL_RADIUS = 0.05
    c.robot.robot_constants.MIN_SPEED = 0.1
    c.is_red_alliance = False
    c.alliance_location = 0
    return c


def _consts(vendor="CTRE"):
    k = MagicMock()
    k.VendorConstants.vendor = vendor
    k.DriveSlewRate = k.RotationSlewRate = 3.0
    k.TranslationStepVoltage = k.SteerStepVoltage = k.RotationStepVoltage = 4.0
    k.RotationRampRate = 1.0
    return k


def _tuner():
    t = MagicMock()
    t._sim_notifier = None
    t.get_state.return_value = MagicMock(pose=Pose2d())
    t.modules = [MagicMock() for _ in range(4)]
    for m in t.modules:
        m.get_position.return_value = SwerveModulePosition()
        m.drive_motor.get_position.return_value.value = 0.0
    return t


@pytest.fixture
def drive():
    with (
        patch.object(base_mod.RobotBase, "is_simulation", return_value=False),
        patch.object(mod, "Logger"),
        patch.object(mod, "LogTracer"),
        patch.object(mod, "CtreSwerveModule", side_effect=lambda m, n, c: MagicMock()),
    ):
        yield CtreDriveSubsystem(_tuner(), _consts(), _container())


def test_wrong_vendor_rejected():
    with pytest.raises(TypeError):
        CtreDriveSubsystem(_tuner(), _consts("REV"), _container())


def test_constructed_and_initialized(drive):
    assert drive.is_initialized
    assert list(drive._swerve_modules) == ["front-left", "front-right", "back-left", "back-right"]


def test_drive_request_follows_field_centric_flag(drive):
    assert drive.drive_request is drive._field_centric_drive
    drive.set_field_centric_drive(False)
    assert drive.drive_request is drive._robot_centric_drive


def test_request_properties(drive):
    assert drive.point_at_request is drive._point
    assert drive.forward_straight_request is drive._forward_straight
    assert drive.brake_request is drive._brake


def test_forwarding_helpers(drive):
    t = drive._tuner_x_subsystem
    drive.set_operator_forward_direction(Rotation2d(1.0))
    t.set_operator_forward_direction.assert_called_once()
    drive.set_control("req")
    t.set_control.assert_called_once_with("req")
    drive.sample_pose_at(1.0)
    t.sample_pose_at.assert_called_once_with(1.0)
    drive.update_sim_state(0.02, 12.0)
    t.update_sim_state.assert_called_once_with(0.02, 12.0)
    drive.set_vision_measurement_std_devs((1, 1, 1))
    t.set_vision_measurement_std_devs.assert_called_with((1, 1, 1))


def test_apply_request_runs_supplied_request(drive):
    cmd = drive.apply_request(lambda: "req")
    cmd.initialize()
    cmd.execute()
    drive._tuner_x_subsystem.set_control.assert_called_with("req")


def test_set_module_states_commands_each_module(drive):
    states = [SwerveModuleVelocity(1.0, Rotation2d(0.5)) for _ in range(4)]
    for m in drive._tuner_x_subsystem.modules:
        m.get_position.return_value = SwerveModulePosition(0.0, Rotation2d(0.0))
    drive.set_module_states(states)
    for m in drive._tuner_x_subsystem.modules:
        m.drive_motor.set_control.assert_called_once()
        m.steer_motor.set_control.assert_called_once()


def test_brake_and_straight(drive):
    with patch.object(drive, "stop") as stop:
        drive.set_motor_brake(True)
    stop.assert_called_once()
    drive._tuner_x_subsystem.set_control.assert_called_with(drive.brake_request)
    drive.set_motor_brake(False)
    assert drive._tuner_x_subsystem.set_control.call_count == 2


def test_get_module_positions_reads_tuner_modules(drive):
    assert len(drive.get_module_positions()) == 4
    for m in drive._tuner_x_subsystem.modules:
        m.get_position.assert_called_with(True)


@pytest.mark.parametrize("rotation", [None, Rotation2d(1.0)])
def test_seed_field_centric(drive, rotation):
    drive.seed_field_centric(rotation)
    sent = drive._tuner_x_subsystem.seed_field_centric.call_args.args[0]
    assert sent.radians() == pytest.approx(0.0 if rotation is None else 1.0)
