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
"""Robot constants and configuration for frclib-6107.

This module defines three primary dataclasses for robot configuration:

- **RobotConstants**: Physical robot dimensions, motor limits, and periodic rates.
  Teams typically override this with actual measurements from their robot.

- **SimulationConstants**: Starting positions and poses for simulation mode.
  Used by PhysicsEngine to initialize robot position based on alliance and location.

- **NetworkConstants**: Network addresses and team number. Teams update TEAM
  to match their FRC team number, which cascades to roboRIO, radio, and mDNS addresses.

All constants use WPILib unit converters (inchesToMeters, lbsToKilograms, etc.)
and type hints (meters, kilograms, meters_per_second, etc.) for clarity and
to enable integration with WPILib trajectory and motion planning tools.

Mode Detection:
  The ROBOT_MODE global detects execution environment automatically:
  - REAL: Robot hardware (roboRIO)
  - SIMULATION: Desktop pyfrc simulation
  - REPLAY: Log playback mode (when LOG_PATH environment variable is set)

Usage:
  Teams create custom constants classes by extending RobotConstants,
  SimulationConstants, and NetworkConstants, then pass them to Robot.__init__().
  This allows per-robot configuration without modifying frclib-6107 core code.
"""

import math
import os

from dataclasses import dataclass
from enum import Enum

from wpilib import RobotBase
from wpimath.geometry import Pose2d, Rotation2d
from wpimath.units import (
    meters, seconds, rotationsToRadians, inchesToMeters, lbsToKilograms,
    kilograms, meters_per_second, radians_per_second
)
from wpimath.trajectory import TrapezoidProfileRadians


class RobotModes(Enum):
    """Execution mode enumeration for robot mode detection.

    Used by pykit (AdvantageScope) logging to determine telemetry pipeline
    and behavior. The ROBOT_MODE global constant automatically detects which
    mode the robot is running in.

    Attributes:
        REAL: Robot running on physical hardware (roboRIO). Logs to USB drive
            and NetworkTables. Full hardware support for motors, pneumatics, etc.
        SIMULATION: Robot running in desktop pyfrc simulation. Logs to local file
            and simulated NetworkTables. Used for development and testing without hardware.
        REPLAY: Log playback mode. Reads a .wpilog file specified by LOG_PATH
            environment variable and outputs analysis to a new _sim.wpilog file.

    Note:
        Do not create subclasses or instances; use only the three enum values.
    """
    REAL = 1
    SIMULATION = 2
    REPLAY = 3


# Automatic mode detection based on environment
SIM_MODE = (
    RobotModes.REPLAY if "LOG_PATH" in os.environ and os.environ["LOG_PATH"] != ""
    else RobotModes.SIMULATION
)
"""RobotModes: Simulation mode detection (REPLAY if LOG_PATH set, else SIMULATION)."""

ROBOT_MODE = RobotModes.REAL if RobotBase.isReal() else SIM_MODE
"""RobotModes: Global robot mode. REAL if on roboRIO, else SIMULATION or REPLAY.

Used throughout frclib-6107 to configure logging, constants, and behavior
based on execution environment. Automatically detected at startup.
"""


@dataclass(slots=True)
class RobotConstants:
    """Physical robot dimensions and time constants.

    This dataclass defines all configurable robot parameters related to physical
    dimensions, drivetrain limits, and timing. The default values are reasonable
    starting points but should be overridden in team implementations to match
    actual robot hardware.

    Many values are used by PathPlanner, odometry, and motion planning systems,
    so accuracy is critical for smooth autonomous routines and accurate odometry.

    Teams should create a subclass and override values like MAX_SPEED with
    actual tuner-generated constants from CTRE/REV characterization tools.

    Attributes:
        ROBOT_MASS (kilograms): Total robot mass including battery, bumpers,
            mechanisms, and frame. Default 60 lbs. Used for drive characterization
            and trajectory planning.
        ROBOT_BUMPER_THICKNESS (meters): Thickness of robot bumpers. Default 4 inches.
            Added to chassis dimensions to get total robot footprint for collision
            detection and field geometry.
        ROBOT_CHASSIS_X_WIDTH (meters): Forward dimension of robot chassis (excluding bumpers).
            Default 24 inches. Combined with bumpers to get ROBOT_X_WIDTH property.
        ROBOT_CHASSIS_Y_WIDTH (meters): Leftward dimension of robot chassis (excluding bumpers).
            Default 24 inches. Combined with bumpers to get ROBOT_Y_WIDTH property.
        WHEEL_RADIUS (meters): Radius of drive wheels. Default 2 inches. Used for
            odometry calculations and wheel circumference derivations.
        ROBOT_PERIOD (seconds): Periodic update rate for robotPeriodic() calls.
            Default 0.020 (20 mS). Critical for command scheduling and timing accuracy.
            Must remain <20 mS for 2026 competition targets.
        ODOMETRY_PERIOD (seconds): Odometry update rate. Default 0.010 (10 mS).
            Run in background thread; independent of main robot loop.
        MAX_SPEED (meters_per_second): Maximum allowed drive speed. Default 5 m/s.
            Should match characterization data from Tuner. Limited by motor,
            gearing, and battery voltage.
        MIN_SPEED (meters_per_second): Minimum speed command to overcome friction.
            Default 0.002 m/s. Used to prevent motion delays at low speeds.
        MAX_ANGULAR_VELOCITY (radians_per_second): Max rotational speed. Default 0.75 rotations/sec.
            Applied to turn commands and motion planning.
        MAX_ANGULAR_ACCELERATION (radians_per_second): Max rotational acceleration in rad/s².
            Used for trajectory profiling. Same as velocity value for defaults.
        MAX_WHEEL_LINEAR_VELOCITY (meters_per_second): Individual wheel max speed.
            Default 1.0 m/s. May differ from drivetrain max for holonomic drives.
        WHEEL_LOCK_TIME (seconds): Duration to apply motor brakes when disabled.
            Default 3 seconds. Prevents mechanisms from drifting at mode transitions.
        DRIVER_CONTROLLER_PORT (int): USB port for driver Xbox controller on roboRIO.
            Default 0.
        OPERATOR_CONTROLLER_PORT (int): USB port for operator Xbox controller.
            Default 1.
        CALIBRATION_CONTROLLER_PORT (int): USB port for optional tuning controller.
            Default 2. Set to negative value to disable initialization.
        JOYSTICK_DEADBAND (float): Joystick input deadband. Default 0.1 (10%).
            Inputs between -0.1 and +0.1 are ignored to prevent drift.
    """

    ROBOT_MASS: kilograms = lbsToKilograms(60)

    ROBOT_BUMPER_THICKNESS: meters = inchesToMeters(4)
    ROBOT_CHASSIS_X_WIDTH: meters = inchesToMeters(24)
    ROBOT_CHASSIS_Y_WIDTH: meters = inchesToMeters(24)

    WHEEL_RADIUS: meters = inchesToMeters(2)

    # Robot periodic rates
    ROBOT_PERIOD: seconds = 0.020
    """Robot main loop period. Default 20 mS. Must stay <20 mS for 2026 targets."""

    ODOMETRY_PERIOD: seconds = 0.010
    """Odometry update period. Default 10 mS. Runs in background thread."""

    # Drivetrain limits (often overridden from Tuner-X characterization)
    MAX_SPEED: meters_per_second = 5
    """Maximum drive speed (m/s). Override with Tuner-X characterization data."""

    MIN_SPEED: meters_per_second = 0.002
    """Minimum speed to overcome friction. Prevents motion delays at low commands."""

    MAX_ANGULAR_VELOCITY: radians_per_second = rotationsToRadians(0.75)
    """Maximum rotation speed. Default 0.75 rotations/second."""

    MAX_ANGULAR_ACCELERATION: radians_per_second = rotationsToRadians(0.75)
    """Maximum rotation acceleration in rad/s². Used for trajectory profiling."""

    MAX_WHEEL_LINEAR_VELOCITY: meters_per_second = 1.0
    """Individual wheel maximum speed. May differ from drivetrain max."""

    # Motor brake hold time on disable
    WHEEL_LOCK_TIME: seconds = 3
    """Duration to hold motor brakes after entering disabled mode."""

    # Xbox controller ports
    DRIVER_CONTROLLER_PORT: int = 0
    """USB port for driver controller."""

    OPERATOR_CONTROLLER_PORT: int = 1
    """USB port for operator controller."""

    CALIBRATION_CONTROLLER_PORT: int = 2
    """USB port for calibration/tuning controller (set <0 to disable)."""

    JOYSTICK_DEADBAND: float = 0.1
    """Joystick deadband (0.0–1.0). Inputs within ±deadband are ignored."""

    @property
    def ROBOT_X_WIDTH(self) -> meters:
        """Total robot width in X direction (forward).

        Combines chassis X-width with bumper thickness on both sides.

        Returns:
            meters: Total X-dimension including bumpers.
        """
        return self.ROBOT_CHASSIS_X_WIDTH + (2 * self.ROBOT_BUMPER_THICKNESS)

    @property
    def ROBOT_Y_WIDTH(self) -> meters:
        """Total robot width in Y direction (left).

        Combines chassis Y-width with bumper thickness on both sides.

        Returns:
            meters: Total Y-dimension including bumpers.
        """
        return self.ROBOT_CHASSIS_Y_WIDTH + (2 * self.ROBOT_BUMPER_THICKNESS)

    @property
    def WHEEL_DIAMETER(self) -> meters:
        """Wheel diameter (2 × WHEEL_RADIUS).

        Returns:
            meters: Wheel diameter in meters.
        """
        return self.WHEEL_RADIUS * 2

    @property
    def WHEEL_CIRCUMFERENCE(self) -> meters:
        """Wheel circumference (π × WHEEL_DIAMETER).

        Used for odometry calculations to convert wheel rotations to distance.

        Returns:
            meters: Wheel circumference in meters.
        """
        return self.WHEEL_DIAMETER * math.pi

    def THETA_CONTROLLER_CONSTRAINTS(self) -> TrapezoidProfileRadians.Constraints:
        """Get motion profile constraints for robot rotation control.

        Creates a TrapezoidProfileRadians.Constraints object using this robot's
        maximum angular velocity and acceleration. Used by PathPlanner and
        rotational PID controllers for smooth motion profiling.

        Returns:
            TrapezoidProfileRadians.Constraints: Motion profile constraints for
                rotation, with max velocity and max acceleration.
        """
        return TrapezoidProfileRadians.Constraints(
            self.MAX_ANGULAR_VELOCITY,
            self.MAX_ANGULAR_ACCELERATION
        )


@dataclass(slots=True)
class SimulationConstants:
    """Simulation configuration and starting positions for robot.

    Defines robot starting poses for each alliance and location during
    simulation and test matches. Poses include position (x, y) and rotation,
    matching FRC field geometry for accuracy.

    Default poses are calibrated for the 2026-Rebuilt field but can be
    overridden for future years' fields.

    The starting line coordinates are measured from the blue alliance side:
    - BLUE_START_LINE: Starting X coordinate for blue alliance
    - RED_START_LINE: Starting X coordinate for red alliance (mirrored)

    Attributes:
        BLUE_START_LINE (meters): X coordinate of blue alliance starting line.
            Calculated from 2026 field: 182.11 inches − 47 inches (robot) ÷ 2 − 2 inches.
        RED_START_LINE (meters): X coordinate of red alliance starting line.
            Mirror of BLUE_START_LINE across field centerline (16.54 m field width).
        BLUE_TEST_POSE (Dict[int, Pose2d]): Starting poses for blue alliance
            by location (1=left, 2=center, 3=right). Each pose includes position
            and rotation. Blue alliance poses face field (rotation π).
        RED_TEST_POSE (Dict[int, Pose2d]): Starting poses for red alliance
            by location (1=left, 2=center, 3=right). Red alliance poses face
            opposite direction (rotation 0).
    """

    BLUE_START_LINE: meters = inchesToMeters(182.11 - (47 / 2) - 2)
    """X coordinate of blue alliance starting line in meters."""

    RED_START_LINE: meters = 16.54 - inchesToMeters(182.11 - (47 / 2) - 2)
    """X coordinate of red alliance starting line in meters (field-mirrored)."""

    BLUE_TEST_POSE = {
        1: Pose2d(BLUE_START_LINE, 7.3, Rotation2d(math.pi)),
        2: Pose2d(BLUE_START_LINE, 6.16, Rotation2d(math.pi)),
        3: Pose2d(BLUE_START_LINE, 0.9, Rotation2d(math.pi))
    }
    """Blue alliance starting poses by location (1=left, 2=center, 3=right)."""

    RED_TEST_POSE = {
        1: Pose2d(RED_START_LINE, 0.9, 0),
        2: Pose2d(RED_START_LINE, 1.9, 0),
        3: Pose2d(RED_START_LINE, 7.3, 0)
    }
    """Red alliance starting poses by location (1=left, 2=center, 3=right)."""


@dataclass(slots=True)
class NetworkConstants:
    """Network and deployment addresses for roboRIO communication.

    Defines static IP addresses, mDNS names, and USB fallback addresses for
    connecting to the roboRIO and other robot network infrastructure.

    The team number is configurable and can be updated via the team property
    setter, which cascades updates to all derived addresses (static IPs, mDNS).

    Network Layout (for team 6107):
    - roboRIO: 10.61.07.2 (static) or roboRIO-6107-frc.local (mDNS)
    - Radio: 10.61.07.1 (static)
    - Access Point: 10.61.07.4 (static)
    - Driver Station: 10.61.07.5 (static)
    - USB: 172.22.11.2 (fallback if Ethernet fails)

    Attributes:
        TEAM (str): Team number as string (format "TEAM_NUMBER"). Default "61.07"
            for team 6107. Update via the team property.
        ROBORIO_STATIC (str): Static IP address of roboRIO (10.{TEAM}.2).
        ROBOT_RADIO_STATIC (str): Static IP address of robot radio (10.{TEAM}.1).
        AP_RADIO_STATIC (str): Static IP address of access point radio (10.{TEAM}.4).
        DRIVER_STATION_STATIC (str): Static IP address of driver station (10.{TEAM}.5).
        DRIVER_STATION_ALT_STATIC (str): Alternate driver station IP (10.{TEAM}.6).
        ROBORIO_MDNS (str): mDNS hostname for roboRIO (roboRIO-{TEAM}-frc.local).
            Case-insensitive; preferred over static IP for flexibility.
        ROBORIO_USB_STATIC (str): USB fallback IP address (172.22.11.2).
            Used when Ethernet connection is unavailable.
    """

    TEAM: str = "61.07"
    """Team number (format 'XX.XX'). Update via team property to cascade changes."""

    ROBORIO_STATIC: str = f"10.{TEAM}.2"
    """Static IP of roboRIO."""

    ROBOT_RADIO_STATIC: str = f"10.{TEAM}.1"
    """Static IP of robot radio."""

    AP_RADIO_STATIC: str = f"10.{TEAM}.4"
    """Static IP of access point radio."""

    DRIVER_STATION_STATIC: str = f"10.{TEAM}.5"
    """Static IP of driver station."""

    DRIVER_STATION_ALT_STATIC: str = f"10.{TEAM}.6"
    """Alternate driver station static IP."""

    ROBORIO_MDMS: str = f"roboRIO-{TEAM}-frc.local"
    """mDNS hostname for roboRIO (preferred over static IP)."""

    ROBORIO_USB_STATIC: str = "172.22.11.2"
    """USB fallback IP address (no team number—universal for all robots)."""

    @property
    def team(self) -> str:
        """Get the current team number.

        Returns:
            str: Team number in format "XX.XX" (e.g., "61.07").
        """
        return self.TEAM

    @team.setter
    def team(self, team: str) -> None:
        """Set the team number and cascade updates to all network addresses.

        When team is changed, all static IPs, mDNS names, and derived addresses
        are automatically updated to reflect the new team number.

        Args:
            team (str): New team number in format "XX.XX" (e.g., "61.07").

        Example:
            net_constants = NetworkConstants()
            net_constants.team = "6328"  # Updates all addresses for team 6328
        """
        if self.TEAM != team:
            self.TEAM = team
            self.ROBORIO_STATIC = f"10.{team}.2"
            self.ROBOT_RADIO_STATIC = f"10.{team}.1"
            self.AP_RADIO_STATIC = f"10.{team}.4"

            self.DRIVER_STATION_STATIC = f"10.{team}.5"
            self.DRIVER_STATION_ALT_STATIC = f"10.{team}.6"

            self.ROBORIO_MDMS = f"roboRIO-{team}-frc.local"