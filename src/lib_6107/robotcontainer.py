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
"""Robot subsystem and command configuration container.

This module provides RobotContainer, the declarative definition of all robot
subsystems, commands, button bindings, and autonomous routines. Teams subclass
this to customize their robot's behavior.

In the Command-based paradigm, the container centralizes robot structure,
allowing Robot.py to focus purely on state management and periodic coordination.

Key Responsibilities:
    - Instantiate all subsystems via subsystem_init() (abstract, team-implemented)
    - Set up operator interface (Xbox controllers on driver, operator, calibration ports)
    - Configure button-to-command bindings via Xbox controller events
    - Manage alliance color/location with callback support
    - Set up autonomous command selection via LoggedDashboardChooser
    - Provide speed limiting and field-relative coordinate system support
    - Track match elapsed time and state
    - Initialize Elastic telemetry for all subsystems

Lifecycle:
    1. Robot.__init__() creates Robot instance
    2. Robot.robot_init() calls container_init callback
    3. RobotContainer.__init__() runs full initialization:
       - Controllers initialized and ready for binding
       - subsystem_init() called (team code creates subsystems here)
       - PathPlanner configured for autonomous
       - Button bindings set up via configure_button_bindings_xbox()
       - Elastic displays initialized
    4. During match:
       - robot_periodic() updates telemetry and alerts
       - check_alliance() validates alliance (until match_started)
       - Commands run via CommandScheduler (independent of container)

Coordinate System:
    - Blue Alliance is default (to the left, lower x-axis)
    - Red Alliance flips the field view if is_red_alliance is True
    - Teams query is_red_alliance and alliance_location for coordinate transforms
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from commands2 import Command, InstantCommand, PrintCommand, button
from commands2.button import CommandXboxController
from ntcore import NetworkTableInstance
from wpilib import Alliance, DriverStationBackend, Field2d, RobotBase, get_deploy_directory
from wpimath.units import meters, meters_per_second, radians_per_second, rotations_to_radians, seconds

from lib_6107.commands.pathplanner import PathPlanner
from lib_6107.dashboard.alerts import RobotAlerts
from lib_6107.field.game_field import GameField
from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser
from lib_6107.subsystems.subsystem import SubsystemBase
from lib_6107.subsystems.vision.visionsubsystem import VisionSubsystem

if TYPE_CHECKING:
    from lib_6107.robot import Robot

logger = logging.getLogger(__name__)


class RobotContainer:
    """Central container for all robot subsystems, commands, and operator interface.

    In the Command-based architecture, this class declares the structure of the robot
    (subsystems, commands, button bindings) in a declarative style, keeping Robot.py
    focused on state management and mode transitions.

    Teams typically subclass RobotContainer and override:
        - subsystem_init(): Create and return all subsystems
        - _configure_driver_button_bindings_xbox(): Bind driver controller buttons to commands
        - _configure_operator_button_bindings_xbox(): Bind operator controller buttons to commands
        - _configure_calibration_button_bindings_xbox(): Bind calibration controller buttons (optional)

    Key Features:
        - Three operator controllers (driver, operator, optional calibration)
        - Alliance management with callback support for coordinate transforms
        - Autonomous command selection via LoggedDashboardChooser (integrates with PathPlanner)
        - Speed limiting and field-centric drive support
        - Match elapsed time tracking
        - Robot alerts and preflight system
        - Field visualization (both 2D diagram and coordinate system)

    Attributes:
        robot (Robot): Reference to the parent Robot instance.
        network_table (NetworkTableInstance): Default NetworkTable instance.
        subsystems (Tuple[Subsystem]): All subsystems in order, used by Robot for periodic
            updates and fault detection.
        robot_drive (Subsystem): The drivetrain subsystem (set by subsystem_init).
        field2d (Field2d): WPILib field visualization (Elastic widget) with robot pose.
        game_field (GameField): Year-specific field object (size, AprilTags, alliance, change callbacks).
        auto_chooser (LoggedDashboardChooser): Elastic chooser for autonomous routine selection.
        simulation (bool): True if running in simulation mode.
        match_started (bool): Set to True in Robot when autonomous/teleop begins.
    """

    def __init__(self, robot: Robot) -> None:
        """Initialize the robot container and all subsystems.

        Initialization sequence:
        1. Store robot reference and initialize NetworkTable
        2. Create operator controllers (driver, operator, optional calibration)
        3. Call subsystem_init() for teams to create all subsystems
        4. Initialize alerts/preflight system
        5. Set up PathPlanner integration and autonomous command selection
        6. Load and validate robot dimensions from PathPlanner settings (if in simulation)
        7. Configure speed limiting chooser (Elastic)
        8. Call telemetry_init() on all subsystems that support it
        9. Configure button bindings for each controller

        Args:
            robot (Robot): The parent Robot instance. Used to access constants and
                field visualization.

        Note:
            Subclasses must implement subsystem_init() to create actual subsystems.
            Teams also implement _configure_*_button_bindings_xbox() methods to bind
            controller inputs to commands.

            PathPlanner integration is optional; if 'autos' directory doesn't exist,
            a basic autonomous chooser is created with "Do nothing" as default.
        """
        # Store references to robot and network infrastructure
        self.start_time: seconds = time.time()
        self.robot = robot
        self.network_table = NetworkTableInstance.get_default()

        # Note: robot_drive is initialized in the subsystem_init of derived robotcontainer
        self.robot_drive = None

        self.simulation = RobotBase.is_simulation()

        # Phoenix6 max speed/angular rate configuration
        # Applied via scale factor in drive commands to limit robot capability
        self._max_speed: meters_per_second = robot.robot_constants.MAX_SPEED
        self._max_angular_rate: radians_per_second = rotations_to_radians(0.75)

        # Alliance management: Coordinate system based on blue being to the left
        self._is_red_alliance: bool = self.simulation  # Default false (blue)
        self._alliance_location: int = 1  # Valid: 1, 2, 3 (FMS or chooser selection)
        self._alliance_change_callbacks: list[Callable[[bool, int], None]] = []
        print("TODO: NT listener for FMS alliance changes not working; using polling in robot")

        # Operator interface: Three Xbox controllers
        self._driver_controller: CommandXboxController = CommandXboxController(
            robot.robot_constants.DRIVER_CONTROLLER_PORT
        )

        self._operator_controller: CommandXboxController = CommandXboxController(
            robot.robot_constants.OPERATOR_CONTROLLER_PORT
        )

        self._controllers = [
            (self._driver_controller, robot.robot_constants.DRIVER_CONTROLLER_PORT),
            (self._operator_controller, robot.robot_constants.OPERATOR_CONTROLLER_PORT),
        ]

        # Optional third controller for calibration/tuning
        if (
            robot.robot_constants.CALIBRATION_CONTROLLER_PORT > 0
            and robot.robot_constants.CALIBRATION_CONTROLLER_PORT not in self._controllers
        ):
            self._calibration_controller: CommandXboxController = CommandXboxController(
                robot.robot_constants.CALIBRATION_CONTROLLER_PORT
            )
            self._controllers.append((self._calibration_controller, robot.robot_constants.CALIBRATION_CONTROLLER_PORT))

        # Initialize subsystems (team-implemented in subclass)
        self.subsystems: tuple[SubsystemBase] = self.subsystem_init()

        # Camera/vision support
        self._cameras = {}

        # Alerts and preflight checks
        self._alerts: RobotAlerts = RobotAlerts(self)

        # PathPlanner integration for autonomous routines
        try:
            planner: PathPlanner = PathPlanner(self.robot_drive, self)
            self.auto_chooser: LoggedDashboardChooser | None = planner.configure_auto_builder("")

        except FileNotFoundError:
            logger.warning("PathPlanner 'autos' directory does not exist")
            self.auto_chooser: LoggedDashboardChooser = LoggedDashboardChooser("Autonomous")

        self.auto_chooser.set_default_option("Do nothing", self.get_do_nothing(stop=True))

        # End-of-autonomous command chooser for endgame routines
        self._auto_end_chooser: LoggedDashboardChooser = LoggedDashboardChooser("Autonomous-EndGame")

        # Robot dimensions for PathPlanner and collision detection
        self._robot_x_width: meters = robot.robot_constants.ROBOT_X_WIDTH
        self._robot_y_width: meters = robot.robot_constants.ROBOT_Y_WIDTH

        # Validate robot dimensions against PathPlanner settings (simulation only)
        if self.simulation:
            try:
                path = os.path.join(get_deploy_directory(), "pathplanner", "settings.json")

                with open(path) as f:
                    settings = json.loads(f.read())

                    x_width = settings.get("robotWidth", self._robot_x_width)
                    y_width = settings.get("robotWidth", self._robot_y_width)

                    margin: meters = 0.10
                    if not (x_width - margin <= self._robot_x_width <= x_width + margin):
                        raise ValueError("PathPlanner robot x-width not valid")
                    if not (y_width - margin <= self._robot_y_width <= y_width + margin):
                        raise ValueError("PathPlanner robot y-width not valid")

            except FileNotFoundError:
                pass

        # Speed limiter for development and testing
        self._limit_chooser = self.configure_speed_limiter()

        # Initialize Elastic telemetry for each subsystem
        for subsystem in self.subsystems:
            if hasattr(subsystem, "telemetry_init") and callable(subsystem.telemetry_init):
                subsystem.telemetry_init()

        # Autonomous end-game command
        self._autonomous_end_game_command = None

        # TODO: Default drive command setup (currently using PathPlanner)
        # Commented code shows how to set up MechanumDrive with Xbox sticks

    @property
    def max_speed(self) -> meters_per_second:
        """Get the maximum allowed drive speed, including speed limiter scale factor.

        Returns:
            meters_per_second: Max speed after applying drive scale factor from drivetrain.
        """
        return self._max_speed * self.robot_drive.drive_scale_factor

    @property
    def max_angular_rate(self) -> radians_per_second:
        """Get the maximum allowed angular (rotation) rate, including speed limiter scale factor.

        Returns:
            radians_per_second: Max angular velocity after applying drive scale factor.
        """
        return self._max_angular_rate * self.robot_drive.drive_scale_factor

    @property
    def robot_x_width(self) -> meters:
        """Get the robot's width in the X direction (forward direction).

        Returns:
            meters: Robot X-axis width, used for collision detection and PathPlanner.
        """
        return self._robot_x_width

    @property
    def robot_y_width(self) -> meters:
        """Get the robot's width in the Y direction (left direction).

        Returns:
            meters: Robot Y-axis width, used for collision detection and PathPlanner.
        """
        return self._robot_y_width

    @property
    def game_field(self) -> GameField:
        """Get the year-specific game field (field size, AprilTags, alliance, change callbacks).

        Not to be confused with ``field2d``, the WPILib Elastic widget.

        Returns:
            GameField: The game field object set up by the team's container.
        """
        return self.robot.game_field

    @property
    def field2d(self) -> Field2d:
        """Get the WPILib field visualization object.

        Returns:
            Field2d: The field with robot pose diagram for Elastic display.
        """
        return self.robot.field2d

    def camera(self, label: str) -> VisionSubsystem | None:
        """Retrieve a vision subsystem by label.

        Args:
            label (str): Unique label for the camera/vision system.

        Returns:
            Optional[VisionSubsystem]: The vision subsystem, or None if not found.
        """
        return self._cameras.get(label)

    @property
    def alliance_location(self) -> int:
        """Get the robot's starting location on the field.

        Valid values are 1 (left), 2 (center), 3 (right) as defined by FMS or
        team's field configuration.

        Returns:
            int: Current alliance location (1, 2, or 3).
        """
        return self._alliance_location

    @property
    def is_red_alliance(self) -> bool:
        """Check if the robot is on the red alliance.

        The coordinate system assumes blue alliance is to the left (lower x-axis).
        This property allows subsystems and commands to apply coordinate transforms
        when on the red alliance.

        Returns:
            bool: True if red alliance, False if blue alliance.
        """
        return self._is_red_alliance

    def check_alliance(self) -> None:
        """Check and update alliance color/location from FMS or Elastic.

        Called during disable, autonomous, and teleop init to detect alliance
        changes before the match is locked (match_started becomes True).
        Valid alliance locations are 1, 2, 3. Invalid values are logged and ignored.

        When alliance changes, all registered callbacks are invoked with the new
        values, allowing subsystems to update coordinate frames.

        Only operates if robot.match_started is False (not yet locked).
        """
        if not self.robot.match_started:
            # Default to blue if FMS doesn't provide alliance
            is_red = DriverStationBackend.get_alliance() == Alliance.RED
            location = DriverStationBackend.get_location()

            # Validate location (1, 2, 3 are valid; None/others are ignored)
            if location not in (1, 2, 3):
                if location is not None:
                    logger.error(f"Invalid alliance location value: {location}")

                location = self._alliance_location

            # Notify listeners if alliance or location changed
            if self._is_red_alliance != is_red or self._alliance_location != location:
                self._is_red_alliance = is_red
                self._alliance_location = location

                for callback in self._alliance_change_callbacks:
                    callback(is_red, location)

    def register_alliance_change_callback(self, callback: Callable[[bool, int], None]) -> None:
        """Register a callback to receive alliance change notifications.

        The callback is invoked when alliance color or location changes before
        the match starts. Used by subsystems and simulation to update coordinate
        frames and starting poses.

        Args:
            callback (Callable[[bool, int], None]): Function called with
                (is_red: bool, location: int) on alliance change.
        """
        self._alliance_change_callbacks.append(callback)

    def set_start_time(self) -> None:
        """Reset the match start time to current time.

        Called in autonomous_init() and teleop_init() to establish match duration
        reference point. Used by elapsed_time() and get_elapsed_time() for
        relative timing within the match.
        """
        self.start_time = time.time()

    def get_elapsed_time(self) -> seconds:
        """Get the elapsed time since match start.

        Returns:
            float: Seconds since set_start_time() was last called.
        """
        return time.time() - self.start_time

    def elapsed_time(self) -> seconds:
        """Get the elapsed time since match start (alias for get_elapsed_time).

        Returns:
            float: Seconds since set_start_time() was last called.
        """
        return time.time() - self.start_time

    def subsystem_init(self) -> tuple[SubsystemBase, ...]:
        """Initialize and return all robot subsystems.

        Abstract method implemented by team subclasses. Should create and return
        a tuple of all subsystems in the order they should be updated.

        The subsystems returned here are used by Robot for:
        - Periodic updates via the CommandScheduler
        - Fault detection at mode transitions
        - stop() calls when disabling
        - sim_init() and update_sim() calls in simulation

        Returns:
            Tuple[Subsystem]: All subsystems in initialization order.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("Implement in a subclass")

    def configure_button_bindings_xbox(self, controller: button.CommandXboxController, port_id: int) -> None:
        """Route controller button binding configuration to appropriate method.

        Called for each Xbox controller to set up button-to-command bindings.
        Routes to driver, operator, or calibration setup based on port ID.

        Args:
            controller (CommandXboxController): The Xbox controller to configure.
            port_id (int): The port ID of the controller (matches robot_constants
                DRIVER_CONTROLLER_PORT, OPERATOR_CONTROLLER_PORT, or
                CALIBRATION_CONTROLLER_PORT).

        Note:
            X is forward and Y is left according to WPILib convention.
            Calibration port can be set to same as another port to share bindings;
            calibration bindings override if both are configured.
        """
        # Route to appropriate binding configuration based on port
        match port_id:
            case self.robot.robot_constants.DRIVER_CONTROLLER_PORT:
                return self._configure_driver_button_bindings_xbox(controller)

            case self.robot.robot_constants.OPERATOR_CONTROLLER_PORT:
                return self._configure_operator_button_bindings_xbox(controller)

            case self.robot.robot_constants.CALIBRATION_CONTROLLER_PORT:
                # NOTE: calibration port can share buttons with other ports
                return self._configure_calibration_button_bindings_xbox(controller)

    def _configure_driver_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        """Configure driver controller button-to-command bindings.

        Implement in subclass to bind driver inputs (left stick, right stick, buttons)
        to drive commands (e.g., arcade drive, field-centric drive, align to goal).

        Args:
            controller (CommandXboxController): The driver's Xbox controller.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("Implement in a subclass")

    def _configure_operator_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        """Configure operator controller button-to-command bindings.

        Implement in subclass to bind operator inputs (buttons, triggers) to subsystem
        commands (e.g., shooter, intake, arm, climbing).

        Args:
            controller (CommandXboxController): The operator's Xbox controller.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("Implement in a subclass")

    def _configure_calibration_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        """Configure calibration controller button-to-command bindings.

        Optional method for tuning/diagnostic inputs. Implement in subclass if using
        a third controller for calibration and testing.

        Args:
            controller (CommandXboxController): The calibration Xbox controller.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("Implement in a subclass")

    def disable_pid_subsystems(self) -> None:
        """Disable PID controllers to prevent integral windup during disabled mode.

        Called from Robot.disabled_init(). Engages motor brakes and zeros out
        all active PID controllers to prevent wind-up and unintended motion
        when robot re-enters enabled mode.
        """
        self.robot_drive.set_motor_brake(True)

    def get_autonomous_command(self) -> Command | None:
        """Get the selected autonomous command from the Elastic chooser.

        Returns:
            Command | None: The autonomous command to run, or None if none selected.
        """
        command = self.auto_chooser.get_selected()
        return command

    def get_autonomous_end_game_command(self) -> Command | None:
        """Get the selected end-of-autonomous command from the Elastic chooser.

        Returns:
            Optional[Command]: The endgame command to run after autonomous, or None.
        """
        return self._auto_end_chooser.get_selected()

    @staticmethod
    def configure_speed_limiter() -> LoggedDashboardChooser:
        """Set up the speed limiter Elastic chooser for development/testing.

        Creates a LoggedDashboardChooser with speed limit options: 10%, 20%, 40%,
        60% (default), 80%, 100%. The selected value is available via
        _limit_chooser.get_selected() for applying to drive scale factor.

        Useful during initial development to safely test commands without full
        speed capability.
        """
        limit_chooser = LoggedDashboardChooser("Drive Rate Limiter")

        limit_chooser.add_option("10%", 0.1)
        limit_chooser.add_option("20%", 0.2)
        limit_chooser.add_option("40%", 0.4)
        limit_chooser.set_default_option("60%", 0.6)
        limit_chooser.add_option("80%", 0.8)
        limit_chooser.add_option("100%", 1.0)

        return limit_chooser

    def get_do_nothing(self, stop: bool | None = True) -> Command:
        """Create a "do nothing" command for autonomous defaults.

        Useful during development when autonomous routines aren't ready yet.

        Args:
            stop (Optional[bool]): If True, returns InstantCommand that stops the
                drivetrain. If False, returns a PrintCommand for logging only.

        Returns:
            Command: The do-nothing command (either stop or print).
        """
        if stop:
            return InstantCommand(lambda: self.robot_drive.stop())

        return PrintCommand("Do-Nothing Command")

    def disable_periodic(self) -> None:
        """Execute disabled mode periodic tasks (preflight checks, alerts).

        Called from Robot.disabled_periodic() to run preflight system checks and
        update alert status on the Elastic.
        """
        self._alerts.preflight_update()
        # TODO: Also look at supporting vision odometry while in disabled mode

    def robot_periodic(self) -> None:
        """Execute container periodic tasks (telemetry updates, alerts).

        Called from Robot.robot_periodic() after Phoenix6 signal updates are requested.

        Note that subsystem periodic() methods are called by the CommandScheduler
        (after robot_periodic returns) via the scheduler run() call in Robot.robot_periodic().

        Tasks:
        - Update alert status for display on Elastic
        - (TODO) Log 3D mechanism poses for visualization

        This should update saved robot state (via pykit Logger) that commands
        can later query for decision-making.
        """
        self._alerts.update()
        game_field = self.game_field

        if game_field is not None:
            game_field.periodic()  # Applies the simulation field selector choice

        # TODO: Logger.record_output("Component Poses", RobotMechanism.get_poses())
