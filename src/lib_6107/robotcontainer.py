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

import json
import logging
import os
import time
from typing import  Callable, List, Optional, Tuple

from commands2 import button, Command, InstantCommand, PrintCommand,  Subsystem
from commands2.button import CommandXboxController
from ntcore import NetworkTableInstance

from wpilib import DriverStation, Field2d, getDeployDirectory, RobotBase
from wpimath.units import meters, meters_per_second, radians_per_second, rotationsToRadians

from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser
from lib_6107.subsystems.vision.visionsubsystem import VisionSubsystem
from lib_6107.util.field import Field
from lib_6107.util.alerts import RobotAlerts


logger = logging.getLogger(__name__)


class RobotContainer:
    """
    This class is where the bulk of the robot should be declared. Since Command-based is a
    "declarative" paradigm, very little robot logic should actually be handled in the :class:`.Robot`
    periodic methods (other than the scheduler calls). Instead, the structure of the robot (including
    subsystems, commands, and button mappings) should be declared here.
    """
    def __init__(self, robot: 'Robot') -> None:
        # The robot's subsystems
        self.start_time = time.time()
        self.robot = robot
        self.network_table = NetworkTableInstance.getDefault()

        self._field = None          # TODO: These two need to be standardized
        self.robot_drive = None

        self.simulation = RobotBase.isSimulation()

        # Phoenix6 max settings and telemetry support. During the actual drive command or the
        # arcade_drive function, we apply any scale factor to limit speed
        self._max_speed: meters_per_second = robot.robot_constants.MAX_SPEED  # speed_at_12_volts desired top speed
        self._max_angular_rate: radians_per_second = rotationsToRadians(0.75)  # 3/4 of a rotation per second max angular velocity

        # Alliance support
        self._is_red_alliance: bool = self.simulation  # Coordinate system based off of blue being to the 'left'
        self._alliance_location: int = 1  # Valid numbers are 1, 2, 3
        self._alliance_change_callbacks: List[Callable[[bool, int], None]] = []
        #
        # TODO: Alliance changes do not seem to work here. Rely on old polling method
        # prefixes = ["FMSInfo/IsRedAlliance", "FMSInfo/IsRedAlliance"]
        # self.alliance_change_listener = NetworkTableListener.createListener(self.network_table,
        #                                                                     prefixes,
        #                                                                     EventFlags.kValueAll,
        #                                                                     self._on_alliance_change)
        # The driver's controller
        self._driver_controller: CommandXboxController = CommandXboxController(robot.robot_constants.DRIVER_CONTROLLER_PORT)

        # Shooter's controller
        self._shooter_controller: CommandXboxController = CommandXboxController(robot.robot_constants.OPERATOR_CONTROLLER_PORT)

        self._controllers = [(self._driver_controller, robot.robot_constants.DRIVER_CONTROLLER_PORT),
                             (self._shooter_controller, robot.robot_constants.OPERATOR_CONTROLLER_PORT)]

        if robot.robot_constants.CALIBRATION_CONTROLLER_PORT > 0 and robot.robot_constants.CALIBRATION_CONTROLLER_PORT not in self._controllers:
            self._calibration_controller: CommandXboxController = CommandXboxController(robot.robot_constants.CALIBRATION_CONTROLLER_PORT)
            self._controllers.append((self._calibration_controller, robot.robot_constants.CALIBRATION_CONTROLLER_PORT))

        ##########################################
        # Subsystem Initialization
        #
        # The robot core code will already call the periodic() function
        # as needed, but having our own list (iterated in order) allows us to move much of
        # the other subsystem 'tasks' into a generic loop.
        self.subsystems: Tuple[Subsystem] = self.subsystem_init()

        ##########################################
        #   ALERTS
        #
        self._alerts: RobotAlerts = RobotAlerts(self)

        ##########################################
        #   PathPlanner.  Do this last since it may pull in commands that need the previously
        #                 initialized subsystems.
        # Init the Auto chooser.  PathPlanner init will fill in our choices
        try:
            from lib_6107.commands.pathplanner import PathPlanner
            planner: PathPlanner = PathPlanner(self.robot_drive, self)
            self.auto_chooser: LoggedDashboardChooser | None = planner.configure_auto_builder("")

        except FileNotFoundError:
            logger.warning("PathPlanner 'autos' directory does not exist")
            self.auto_chooser: LoggedDashboardChooser = LoggedDashboardChooser("Autonomous")

        self.auto_chooser.setDefaultOption("Do nothing", self.get_do_nothing(stop=True))

        self._auto_end_chooser: LoggedDashboardChooser = LoggedDashboardChooser("Autonomous-EndGame")

        # Set our robot width and then use pathplanner as the basis if it was provided to verify
        self._robot_x_width: meters = robot.robot_constants.ROBOT_X_WIDTH
        self._robot_y_width: meters =robot.robot_constants.ROBOT_Y_WIDTH

        if self.simulation:
            try:
                path = os.path.join(getDeployDirectory(), 'pathplanner', 'settings.json')

                with open(path, 'r') as f:
                    settings = json.loads(f.read())

                    x_width = settings.get("robotWidth", self._robot_x_width)
                    y_width = settings.get("robotWidth", self._robot_y_width)

                    margin: meters = 0.10
                    assert x_width - margin <= self._robot_x_width <= x_width + margin, "PathPlanner robot x-width not valid"
                    assert y_width - margin <= self._robot_y_width <= y_width + margin, "PathPlanner robot y-width not valid"

            except FileNotFoundError:
                pass


        # Speed limiter useful during initial development
        self._limit_chooser = None
        self.configure_speed_limiter()

        ########################################################
        # Initialize the Smart dashboard for each subsystem
        # Dashboard setup
        for subsystem in self.subsystems:
            if hasattr(subsystem, "dashboard_initialize") and callable(getattr(subsystem,
                                                                               "dashboard_initialize")):
                subsystem.dashboard_initialize()

        #########################################################
        # Specific commands based on time remaining

        self._autonomous_end_game_command = None

        # TODO: Currently we are always field centric wrt commands and using Pathplanner
        # # Configure default command for driving using joystick sticks
        # field_relative = self.robot_drive.field_relative
        #
        # # MacOS fixup
        # right_axis_x = XboxController.Axis.kRightX
        #
        # if platform.system().lower() == "darwin":
        #     hid_axis = self.driver_controller.getHID().Axis
        #     if hid_axis.kRightX != 2:
        #         right_axis_x = XboxController.Axis.kLeftTrigger
        #
        # drive_cmd = HolonomicDrive(self,
        #                            self.robot_drive,
        #                            forwardSpeed=lambda: -self.driver_controller.getRawAxis(XboxController.Axis.kLeftY),
        #                            leftSpeed=lambda: -self.driver_controller.getRawAxis(XboxController.Axis.kLeftX),
        #                            rotationSpeed=lambda: -self.driver_controller.getRawAxis(right_axis_x),
        #                            deadband=OIConstants.DRIVE_DEADBAND,
        #                            field_relative=field_relative,
        #                            square=True)
        #
        # self.robot_drive.setDefaultCommand(drive_cmd)

    @property
    def max_speed(self) -> meters_per_second:
        return self._max_speed * self.robot_drive.drive_scale_factor

    @property
    def max_angular_rate(self) -> radians_per_second:
        return self._max_angular_rate * self.robot_drive.drive_scale_factor

    @property
    def robot_x_width(self) -> meters:
        return self._robot_x_width

    @property
    def robot_y_width(self) -> meters:
        return self._robot_y_width

    @property
    def field2d(self) -> Field2d:  # The field with a diagram
        return self.robot.field

    @property
    def field(self) -> Field:  # The field with all the coordinates and helper properties
        return self._field

    def camera(self, label: str) -> Optional[VisionSubsystem]:
        return self._cameras.get(label)

    @property
    def alliance_location(self) -> int:
        """
        Alliance location/position as defined by FMS or chooser.

        Valid values are 1, 2, 3.
        """
        return self._alliance_location

    @property
    def is_red_alliance(self) -> bool:
        """
        Are we in the red alliance?

        The coordinate system is based on the Blue Alliance being to the left (lower x-axis).
        This method provides an 'if' capable function that can be called by routines that need
        a coordinate transformation if we are in the red alliance.
        """
        return self._is_red_alliance

    def check_alliance(self) -> None:
        """
        Support alliance changes up until we start the competition. Default is the blue
        alliance and this function is called during 'disable_periodic' and at the init functions
        for both the Autonomous and Teleop stages.

        Once 'match_started' is True, we are locked into the alliance.
        """
        if not self.robot.match_started:
            # Note that if 'None' is returned for the alliance, we assume Blue
            is_red = DriverStation.getAlliance() == DriverStation.Alliance.kRed
            location = DriverStation.getLocation()

            # Do not change location if not valid
            if location not in (1, 2, 3):
                if location is not None:
                    logger.error(f"Invalid alliance location value: {location}")

                location = self._alliance_location

            if self._is_red_alliance != is_red or self._alliance_location != location:
                # Change of alliance. Update any subsystem or other object that needs
                # to know.
                self._is_red_alliance = is_red
                self._alliance_location = location

                for callback in self._alliance_change_callbacks:
                    callback(is_red, location)

    def register_alliance_change_callback(self, callback: Callable[[bool, int], None]) -> None:
        """
        For subsystems and objects that need to know about alliance changes before the
        match begins.
        """
        self._alliance_change_callbacks.append(callback)

    def set_start_time(self) -> None:  # call in teleopInit and autonomousInit in the robot
        self.start_time = time.time()

    def get_elapsed_time(self) -> float:
        """
        Called when we want to know the start/elapsed time for status and debug messages
        """
        return time.time() - self.start_time

    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    def subsystem_init(self) -> Tuple[Subsystem]:
        """
        Create all subsystems
        """
        raise NotImplementedError("Implement in a subclass")

    def configure_button_bindings_xbox(self, controller: button.CommandXboxController, port_id: int) -> None:
        # Note that X is defined as forward according to WPILib convention,
        # and Y is defined as to the left according to WPILib convention.
        match port_id:
            case self.robot.robot_constants.DRIVER_CONTROLLER_PORT:
                return self._configure_driver_button_bindings_xbox(controller)

            case self.robot.robot_constants.OPERATOR_CONTROLLER_PORT:
                return self._configure_operator_button_bindings_xbox(controller)

            case self.robot.robot_constants.CALIBRATION_CONTROLLER_PORT:
                # NOTE: can set calibration port to same as another controller, but the
                #       last one called will take over any shared button bindings
                return self._configure_calibration_button_bindings_xbox(controller)

    def _configure_driver_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        raise NotImplementedError("Implement in a subclass")

    def _configure_operator_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        raise NotImplementedError("Implement in a subclass")

    def _configure_calibration_button_bindings_xbox(self, controller: CommandXboxController) -> None:
        raise NotImplementedError("Implement in a subclass")

    def disable_pid_subsystems(self) -> None:
        """
        Disables all ProfiledPIDSubsystem and PIDSubsystem instances.
        This should be called on robot disable to prevent integral windup.
        """
        self.robot_drive.set_motor_brake(True)

    def get_autonomous_command(self) -> Command | None:
        """
        :returns: the command to run in autonomous
        """
        command = self.auto_chooser.getSelected()
        return command

    def get_autonomous_end_game_command(self) -> Optional[Command]:
        """
        :returns: the command to run at the end of autonomous
        """
        return self._auto_end_chooser.getSelected()

    def configure_speed_limiter(self):
        """
        Overall speed limitation scaling factor
        """
        self._limit_chooser = LoggedDashboardChooser("Drive Rate Limiter")

        # you can also set the default option, if needed
        self._limit_chooser.addOption("10%", 0.1)
        self._limit_chooser.addOption("20%", 0.2)
        self._limit_chooser.addOption("40%", 0.4)
        self._limit_chooser.setDefaultOption("60%", 0.6)
        self._limit_chooser.addOption("80%", 0.8)
        self._limit_chooser.addOption("100%", 1.0)

    def get_do_nothing(self, stop: Optional[bool] = True) -> Command:
        """
        Have robot stop

        Makes a good default autonomous default while robot is still under test
        """
        if stop:
            return InstantCommand(lambda: self.robot_drive.stop())

        return PrintCommand("Do-Nothing Command")

    def disable_periodic(self) -> None:
        self._alerts.preflight_update()

    def robotPeriodic(self) -> None:
        """
        This is called from Robot.robotPeriodic() after the Phoenix6 signal updates
        are requested.

        Also remember that the SubSystem 'periodic' calls are from the CommandScheduler
        run() method which is AFTER robotPeriodic returns

        This should update the saved robot state that can then be used later by
        any commands.
        """
        self._alerts.update()
        #
        # TODO: Next returns 3d poses for all mechanisms.  Might be good for our devices as well.
        # Logger.recordOutput("Component Poses", RobotMechanism.getPoses())
