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

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from wpilib import get_deploy_directory

# from pathplannerlib.auto import AutoBuilder, RobotConfig   # TODO: pathplannerlib not yet supported
# from pathplannerlib.controller import PIDConstants, PPHolonomicDriveController
# from pathplannerlib.logging import PathPlannerLogging
from lib_6107.commands.drivetrain.aimtodirection import AimToDirection
from lib_6107.commands.drivetrain.arcade_drive import ArcadeDrive
from lib_6107.commands.drivetrain.gotopoint import GoToPoint
from lib_6107.commands.drivetrain.swervetopoint import SwerveMove, SwerveToPoint
from lib_6107.commands.vision.approach_tag import ApproachTag
from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser

if TYPE_CHECKING:
    from lib_6107.robotcontainer import RobotContainer
    from lib_6107.subsystems.drivetrain.drivesubsystem import DriveSubsystem

logger = logging.getLogger(__name__)


class PathPlanner:
    def __init__(self, drivetrain: DriveSubsystem, container: RobotContainer):
        self._drivetrain = drivetrain
        self._container = container

    def configure_auto_builder(self, default_command: str | None = "") -> LoggedDashboardChooser | None:

        # Register named commands first
        self.register_commands_and_triggers()
        print("TODO: PathPlanner is not yet supported in 2027.  Skipping auto builder configuration.")
        print("TODO: Fix pathplanner settings.json for our practice bot")
        # Does pathplanner exist yet?
        file_path = os.path.join(get_deploy_directory(), "pathplanner", "settings.json")

        if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
            return LoggedDashboardChooser("Autonomous")  # TODO: Not yet supported
        #     config = RobotConfig.fromGUISettings()
        #
        #     AutoBuilder.configure(
        #         lambda: self._drivetrain.get_state().pose,  # Supplier of current robot pose
        #         self._drivetrain.reset_pose,  # Consumer for seeding pose against auto
        #         lambda: self._drivetrain.get_state().speeds,  # Supplier of current robot speeds
        #         # Consumer of ChassisVelocities and feedforwards to drive the robot
        #         # TODO:  Create a 'drive-with-path-planned' and set it to following
        #         #        see 'drivePathPlanned' in westwood project. Also it calls
        #         #        and does a log for each time called'.
        #         lambda speeds, feedforwards: self._drivetrain.set_control(
        #             self._drivetrain.apply_robot_speeds.with_speeds(
        #                 ChassisVelocities.discretize(speeds, self._container.robot.period)
        #             )
        #             .with_wheel_force_feedforwards_x(feedforwards.robotRelativeForcesXNewtons)
        #             .with_wheel_force_feedforwards_y(feedforwards.robotRelativeForcesYNewtons)
        #         ),
        #         PPHolonomicDriveController(
        #             # PID constants for translation
        #             PIDConstants(10.0, 0.0, 0.0),
        #             # PID constants for rotation
        #             PIDConstants(7.0, 0.0, 0.0),
        #         ),
        #         config,
        #         # Assume the path needs to be flipped for Red vs Blue, this is normally the case
        #         lambda: (DriverStationBackend.get_alliance() or Alliance.BLUE) == Alliance.RED,
        #         self._drivetrain,  # Subsystem for requirements
        #     )
        #
        #     # Setup pykit support in PathPlanner
        #     command_count: dict[str, int] = {}
        #
        #     def log_command_function(command: Command, active: bool) -> None:
        #         name = command.get_name()
        #         count = command_count.get(name, 0) + (1 if active else -1)
        #         command_count[name] = count
        #         Logger.record_output(f"Commands/{name}", count > 0)
        #
        #     CommandScheduler.get_instance().on_command_initialize(lambda c: log_command_function(c, True))
        #     CommandScheduler.get_instance().on_command_finish(lambda c: log_command_function(c, False))
        #     CommandScheduler.get_instance().on_command_interrupt(lambda c: log_command_function(c, False))
        #
        #     PathPlannerLogging.setLogCurrentPoseCallback(
        #         lambda pose: Logger.record_output("PathPlanner/CurrentPose", pose)
        #     )
        #     PathPlannerLogging.setLogTargetPoseCallback(
        #         lambda pose: Logger.record_output("PathPlanner/TargetPose", pose)
        #     )
        #     PathPlannerLogging.setLogActivePathCallback(
        #         lambda poses: Logger.record_output("PathPlanner/CurrentPath", poses)
        #     )
        #
        #     return self.build_auto_chooser(default_command)
        logger.error(f"PathPlanner settings {file_path} not found or is not readable")
        logger.error("Assuming this is an initial run to import Named Commands before creating first Paths/Autos")

        return LoggedDashboardChooser("Autonomous")

    def build_auto_chooser(self, default_auto_name: str = "") -> LoggedDashboardChooser:
        """
        Create and populate a sendable chooser with all PathPlannerAutos in the project and the default auto name selected.

        :param default_auto_name: the name of the default auto to be selected in the chooser
        :return: a sendable chooser object populated with all of PathPlannerAutos in the project
        """
        print("TODO: PathPlanner is not yet supported in 2027.")

        # if not AutoBuilder.isConfigured():
        #     raise RuntimeError("AutoBuilder was not configured before attempting to build an auto chooser")
        #
        # auto_folder_path = os.path.join(get_deploy_directory(), "pathplanner", "autos")
        # auto_list = os.listdir(auto_folder_path)
        #
        # chooser = LoggedDashboardChooser("Autonomous")
        #
        # # default_auto_added = False
        #
        # for auto in auto_list:
        #     auto = auto.removesuffix(".auto")
        #     if auto == default_auto_name:
        #         # default_auto_added = True
        #         chooser.set_default_option(auto, AutoBuilder.buildAuto(auto))
        #     else:
        #         try:
        #             chooser.add_option(auto, AutoBuilder.buildAuto(auto))
        #
        #         except FileNotFoundError as e:
        #             logger.error(f"AutoBuilder add option File not found exception: {e}")
        #
        #         except Exception as e:
        #             logger.error(f"AutoBuilder add option exception: {e}")
        #
        # # if not default_auto_added:
        # #     chooser.set_default_option("None", cmd.none())
        # # else:
        # #     chooser.add_option("None", cmd.none())
        #
        # return chooser

    def register_commands_and_triggers(self) -> None:
        # Register Named Commands.
        #
        #   Format is  <command-object-name>, <first-required-parameter>
        commands = [
            # DriveTrian
            (ArcadeDrive, self._drivetrain),
            (AimToDirection, self._drivetrain),
            (GoToPoint, self._drivetrain),
            (SwerveToPoint, self._drivetrain),
            (SwerveMove, self._drivetrain),
            # Entertainment
        ]
        for obj, param in commands:
            obj.pathplanner_register(param)

        # And a few special ones depending upon support
        front_camera = self._drivetrain.container.camera("front")

        if front_camera is not None:
            # TODO: Add more to this location
            ApproachTag.pathplanner_register(self._drivetrain)
