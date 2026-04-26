# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
#
# Commonly used constants not found in existing wpilib modules
import math
import os

from dataclasses import dataclass
from enum import Enum

from wpilib import RobotBase
from wpimath.geometry import Pose2d, Rotation2d
from wpimath.units import meters, seconds, rotationsToRadians, inchesToMeters, lbsToKilograms, \
    kilograms, meters_per_second, radians_per_second
from wpimath.trajectory import TrapezoidProfileRadians


class RobotModes(Enum):
    """
    PyKit Enum for robot modes.

    These constants and the ROBOT_MODE constant are used to automatically
    detect the AdvantageScope/pykit mode that the robot is currently running
    in.

    NOTE: Do not derive a subclass as there is not a way to register any deviations
    """
    REAL = 1
    SIMULATION = 2
    REPLAY = 3

SIM_MODE = (
    RobotModes.REPLAY if "LOG_PATH" in os.environ and os.environ["LOG_PATH"] != ""
    else RobotModes.SIMULATION
)
ROBOT_MODE = RobotModes.REAL if RobotBase.isReal() else SIM_MODE

@dataclass(slots=True)
class RobotConstants:       # pylint: disable=too-many-instance-attributes
    """
    Contains constants related to the physical robot and values often used
    in the 'Robot', 'RobotContainer', or 'PhysicsEngine' classes.

    The first set of constants are used in PathPlanner and other tools and should
    often be overridden by subclasses to more closely match your actual robot.
    """
    ROBOT_MASS: kilograms = lbsToKilograms(60)

    ROBOT_BUMPER_THICKNESS: meters = inchesToMeters(4)
    ROBOT_CHASSIS_X_WIDTH: meters = inchesToMeters(24)
    ROBOT_CHASSIS_Y_WIDTH: meters = inchesToMeters(24)

    WHEEL_RADIUS: meters = inchesToMeters(2)

    ###########################
    # Robot periodic rate
    ROBOT_PERIOD: seconds = 0.020       # Period that the '_periodic' calls are mode
    ODOMETRY_PERIOD: seconds = 0.010    # Odometry update period (background thread based on drive/vision type)

    ###########################
    # Drivetrain  (often overridden in real-robot based on Tuner-X constants)
    MAX_SPEED: meters_per_second = 5
    MIN_SPEED: meters_per_second = 0.002
    MAX_ANGULAR_VELOCITY: radians_per_second = rotationsToRadians(0.75)
    MAX_ANGULAR_ACCELERATION: radians_per_second = rotationsToRadians(0.75)  # Actually is radians/second^2
    MAX_WHEEL_LINEAR_VELOCITY: meters_per_second = 1.0

    # Hold time on motor brakes when disabled
    WHEEL_LOCK_TIME: seconds = 3  # seconds

    # TODO: Do we need an 'Autonomous Mode' max speed, max accel, max_angular, ...

    ###########################
    # X-Box Controllers
    DRIVER_CONTROLLER_PORT: int = 0
    OPERATOR_CONTROLLER_PORT: int = 1
    CALIBRATION_CONTROLLER_PORT: int = 2  # Set to < 0 to disable initialization

    JOYSTICK_DEADBAND: float = 0.1

    ###############################
    # Runtime derivable 'constants'
    @property
    def ROBOT_X_WIDTH(self) -> meters:
        return self.ROBOT_CHASSIS_X_WIDTH + (2 *  self.ROBOT_BUMPER_THICKNESS)

    @property
    def ROBOT_Y_WIDTH(self) -> meters:
        return self.ROBOT_CHASSIS_Y_WIDTH + (2 *  self.ROBOT_BUMPER_THICKNESS)

    @property
    def WHEEL_DIAMETER(self) -> meters:
        return self.WHEEL_RADIUS * 2

    @property
    def WHEEL_CIRCUMFERENCE(self) -> meters:
        return self.WHEEL_DIAMETER * math.pi

    def THETA_CONTROLLER_CONSTRAINTS(self) -> TrapezoidProfileRadians.Constraints:
        """
        Constraint for the motion profiled robot angle controller
        """
        return TrapezoidProfileRadians.Constraints(self.MAX_ANGULAR_VELOCITY,
                                                   self.MAX_ANGULAR_ACCELERATION)


@dataclass(slots=True)
class SimulationConstants:
    """
    A few values that can be used to set up simulation. The default values are for
    the 2026-Rebuilt field, but it is assumed we may have something similar in future
    years.
    """
    BLUE_START_LINE: meters = inchesToMeters(182.11 - (47 / 2) - 2)
    RED_START_LINE: meters = 16.54 - inchesToMeters(182.11 - (47 / 2) - 2)

    BLUE_TEST_POSE = {
        1: Pose2d(BLUE_START_LINE, 7.3, Rotation2d(math.pi)),
        2: Pose2d(BLUE_START_LINE, 6.16, Rotation2d(math.pi)),
        3: Pose2d(BLUE_START_LINE, 0.9, Rotation2d(math.pi))
    }
    RED_TEST_POSE = {
        1: Pose2d(RED_START_LINE, 0.9, 0),
        2: Pose2d(RED_START_LINE, 1.9, 0),
        3: Pose2d(RED_START_LINE, 7.3, 0)
    }

@dataclass(slots=True)
class NetworkConstants:
    """
    This class of constants contains common network endpoint information that is
    expected to be constant across multiple build seasons.

    Since the Team number is different for each team, a 'team' property with getters
    and setters is available.

    Each build, robots can add to a derived local copy, but changes to the values
    below are not expected.
    The first set of constants are used in PathPlanner and other tools and should
    often be overridden by subclasses to more closely match your actual robot.
    """
    TEAM: str = "61.07"

    ROBORIO_STATIC: str = f"10.{TEAM}.2"
    ROBOT_RADIO_STATIC: str = f"10.{TEAM}.1"
    AP_RADIO_STATIC: str = f"10.{TEAM}.4"

    DRIVER_STATION_STATIC: str = f"10.{TEAM}.5"
    DRIVER_STATION_ALT_STATIC: str = f"10.{TEAM}.6"

    # mDNS (DNS names are case-insensitive)
    ROBORIO_MDMS: str = f"roboRIO-{TEAM}-frc.local"

    # USB
    ROBORIO_USB_STATIC: str = "172.22.11.2"

    ###############################
    # Runtime derivable 'constants'
    @property
    def team(self) -> str:
        return self.TEAM

    @team.setter
    def team(self, team: str) -> None:
        if self.TEAM != team:
            self.TEAM = team
            self.ROBORIO_STATIC = f"10.{team}.2"
            self.ROBOT_RADIO_STATIC = f"10.{team}.1"
            self.AP_RADIO_STATIC = f"10.{team}.4"

            self.DRIVER_STATION_STATIC = f"10.{team}.5"
            self.DRIVER_STATION_ALT_STATIC = f"10.{team}.6"

            # mDNS (DNS names are case-insensitive)
            self.ROBORIO_MDMS = f"roboRIO-{team}-frc.local"
