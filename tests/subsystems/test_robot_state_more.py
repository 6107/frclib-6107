"""Additional unit tests for lib_6107.subsystems.pykit.robot_state."""

from unittest.mock import MagicMock

import pytest
from lib_6107.subsystems.pykit import robot_state
from lib_6107.subsystems.pykit.robot_state import RobotState
from wpimath import (
    ChassisVelocities,
    Pose2d,
    Pose3d,
    Rotation2d,
    SwerveDrive4Kinematics,
    SwerveModulePosition,
    Translation2d,
)

MODULE = "lib_6107.subsystems.pykit.robot_state"


@pytest.fixture(autouse=True)
def restore_state(monkeypatch):
    for name in ("odometry", "robot_pose", "robot_heading", "heading_offset", "module_positions", "robot_field_velocity"):
        monkeypatch.setattr(RobotState, name, getattr(RobotState, name))
    logger = MagicMock()
    tracer = MagicMock()
    monkeypatch.setattr(robot_state, "Logger", logger)
    monkeypatch.setattr(robot_state, "LogTracer", tracer)
    return logger, tracer


def _kin():
    return SwerveDrive4Kinematics(
        Translation2d(0.3, 0.3), Translation2d(0.3, -0.3), Translation2d(-0.3, 0.3), Translation2d(-0.3, -0.3)
    )


def _mods():
    return tuple(SwerveModulePosition() for _ in range(4))


def test_periodic_updates_state_and_logs(restore_state):
    logger, tracer = restore_state
    RobotState.configure(_kin())
    pose = Pose2d(0.0, 0.0, Rotation2d())
    mods = _mods()
    vel = ChassisVelocities()
    RobotState.periodic(pose, Rotation2d(), Pose3d(), 0.0, 0.1, vel, mods)
    assert RobotState.robot_pose == pose
    assert RobotState.module_positions == mods
    assert RobotState.robot_field_velocity == vel
    keys = [c.args[0] for c in logger.record_output.call_args_list]
    assert "Auto/PositionCorrect" in keys and "Odometry/Robot" in keys
    correct = {c.args[0]: c.args[1] for c in logger.record_output.call_args_list}
    assert correct["Auto/PositionCorrect"] is True
    assert correct["Auto/RotationCorrect"] is True
    tracer.reset_outer.assert_called_once_with("RobotState")
    tracer.record_total.assert_called_once()


def test_periodic_flags_offsets(restore_state):
    logger, _ = restore_state
    RobotState.configure(_kin())
    RobotState.periodic(Pose2d(5.0, 0.0, Rotation2d(1.0)), Rotation2d(), Pose3d(), 0.0, 0.0, ChassisVelocities(), _mods())
    out = {c.args[0]: c.args[1] for c in logger.record_output.call_args_list}
    assert out["Auto/PositionCorrect"] is False


def test_periodic_without_configure_still_records_total(restore_state):
    _, tracer = restore_state
    RobotState.odometry = None
    with pytest.raises(AttributeError):
        RobotState.periodic(Pose2d(), Rotation2d(), Pose3d(), 0.0, 0.0, ChassisVelocities(), _mods())
    tracer.record_total.assert_called_once()


def test_get_rotation():
    RobotState.robot_pose = Pose2d(1.0, 2.0, Rotation2d(0.5))
    assert RobotState.get_rotation().radians() == pytest.approx(0.5)


def test_get_pose_returns_odometry_pose():
    RobotState.configure(_kin())
    RobotState.reset_pose(Pose2d(1.0, 1.0, Rotation2d()))
    assert RobotState.get_pose().x == pytest.approx(1.0)


def test_reset_pose_with_and_without_pose():
    RobotState.configure(_kin())
    RobotState.robot_heading = Rotation2d(1.0)
    RobotState.reset_pose(Pose2d(1.0, 2.0, Rotation2d(0.25)))
    assert RobotState.heading_offset.radians() == pytest.approx(0.75)
    assert RobotState.odometry.get_pose().x == pytest.approx(1.0)
    RobotState.reset_pose()
    assert RobotState.heading_offset.radians() == pytest.approx(1.0)
    assert RobotState.odometry.get_pose().x == pytest.approx(0.0)
