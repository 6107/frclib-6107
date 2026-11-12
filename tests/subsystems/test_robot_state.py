"""Unit tests for RobotState odometry configuration."""

import pytest
from wpimath import Rotation2d, SwerveDrive4Kinematics, Translation2d

from lib_6107.subsystems.pykit.robot_state import RobotState


def test_odometry_is_unset_until_configured():
    RobotState.odometry = None
    assert RobotState.odometry is None


def test_configure_creates_odometry():
    kinematics = SwerveDrive4Kinematics(
        Translation2d(0.3, 0.3), Translation2d(0.3, -0.3), Translation2d(-0.3, 0.3), Translation2d(-0.3, -0.3)
    )
    RobotState.configure(kinematics)
    assert RobotState.odometry is not None
    assert RobotState.odometry.get_pose().rotation() == Rotation2d()
