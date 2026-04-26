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

import logging
import os
import sys
import time
from typing import Callable, Optional

import wpilib
from commands2 import CommandScheduler
from commands2.command import Command
from ntcore import NetworkTableInstance
from pathplannerlib.pathfinding import LocalADStar, Pathfinding
from phoenix6 import SignalLogger
from rev import StatusLogger
from wpilib import DriverStation, Field2d, LiveWindow, SmartDashboard, Timer
from wpimath.units import seconds

from lib_6107.constants import ROBOT_MODE, RobotConstants, RobotModes, SimulationConstants, NetworkConstants
from lib_6107.pykit.loggedrobot import LoggedRobot
from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer
from lib_6107.pykit.networktables.nt4Publisher import NT4Publisher
from lib_6107.pykit.wpilog.wpilogreader import WPILOGReader
from lib_6107.pykit.wpilog.wpilogwriter import WPILOGWriter
from lib_6107.robotcontainer import RobotContainer
from lib_6107.util.elastic_utils import Notification, select_tab, send_notification
from lib_6107.util.statistics import RobotStatistics

# Setup Logging
logger = logging.getLogger(__name__)


class Robot(LoggedRobot):
    """
    A base-robot class derived off of the pykit 'Logged' robot. It provides a
    little bit of the boilerplate that all robots need, but the main purpose
    is to be a container where our final runtime constants are performed

    Call this at the beginning of your derived class after setting up any of
    your own robot's constants overrides
    """
    def __init__(self, build_year: str,
                 robot_constants: Optional[RobotConstants] = None,
                 simulation_constants: Optional[SimulationConstants] = None,
                 network_constants: Optional[NetworkConstants] = None):
        #------------------------------------------------
        # Save off the constants for this robot first
        self.robot_constants: RobotConstants = robot_constants or RobotConstants()
        self.simulation_constants: SimulationConstants = simulation_constants or SimulationConstants()
        self.network_constants: NetworkConstants = network_constants or NetworkConstants()

        # Initialize our base class, choosing the default scheduler period
        super().__init__(period=self.robot_constants.ROBOT_PERIOD)

        self._period: seconds = self.getPeriod()

        # Validate year. 2026 is first supported year. 2050 is so far way
        # that the robots will probably be building humans to use in competitions :-)
        if not 2026 <= int(build_year) <= 2050:
            raise ValueError("Not within supported rage of [2026..2050]")

        Logger.recordMetadata("Robot", type(self).__name__)
        Logger.recordMetadata("Team", self.network_constants.TEAM)
        Logger.recordMetadata("Year", build_year)

        # More metadata for AdvantageScope purposes
        match ROBOT_MODE:
            case RobotModes.REAL:
                deploy_config = wpilib.deployinfo.getDeployData()

                if deploy_config is not None:
                    Logger.recordMetadata("Deploy Host", deploy_config.get("deploy-host", ""))
                    Logger.recordMetadata("Deploy User", deploy_config.get("deploy-user", ""))
                    Logger.recordMetadata("Deploy Date", deploy_config.get("deploy-date", ""))
                    Logger.recordMetadata("Code Path", deploy_config.get("code-path", ""))
                    Logger.recordMetadata("Git Hash", deploy_config.get("git-hash", ""))
                    Logger.recordMetadata("Git Branch", deploy_config.get("git-branch", ""))
                    Logger.recordMetadata("Git Description", deploy_config.get("git-desc", ""))

                Logger.addDataReciever(NT4Publisher(True))
                usb_mount = "/U"
                usb_logs = os.path.join(usb_mount, "logs")

                if os.path.ismount(usb_mount) or os.path.exists(usb_mount):
                    os.makedirs(usb_logs, exist_ok=True)
                    Logger.addDataReciever(WPILOGWriter())
                else:
                    current_dir = os.getcwd()
                    if current_dir in ("", "/"):
                        current_dir = "/home/lvuser"

                    fallback = os.path.join(current_dir, "pyLogs")
                    fallback_dir = os.path.abspath(fallback)
                    os.makedirs(fallback_dir, exist_ok=True)
                    Logger.addDataReciever(WPILOGWriter(filename=None,
                                                        path=fallback_dir))

            case RobotModes.SIMULATION:
                Logger.addDataReciever(WPILOGWriter())
                Logger.addDataReciever(NT4Publisher(True))

            case RobotModes.REPLAY:
                #
                #  To run back a log file in replay mode, set the `LOG_PATH` environment variable
                #  and then run in simulation.
                #
                #  An example is to run the following:
                #
                #    LOG_PATH=/path/to/log/file.wpilog robotpy --main src sim
                #
                self.UseTiming = False  # Disable timing in replay mode, run as fast as possible

                log_path = os.environ["LOG_PATH"]
                log_path = os.path.abspath(log_path)

                Logger.setReplaySource(WPILOGReader(log_path))
                Logger.addDataReciever(WPILOGWriter(log_path[:-7] + "_sim.wpilog"))

        # Start the AdvantageScope logging subsystem
        Logger.start()

        # Some base class values that will often be used elsewhere and perhaps initialized
        # when 'robotInit' is called

        self._counter = 0  # Updated on each periodic call. Can be used to logging/smartdashboard updates

        self._container: Optional[RobotContainer] = None
        self._autonomous_command: Optional[Command] = None
        self.disabledTimer: Timer = Timer()
        self.field: wpilib.Field2d = Field2d()
        self._stats: RobotStatistics = RobotStatistics(self)

        self._command_scheduler: CommandScheduler | None = None
        self._network_tables_instance = NetworkTableInstance.getDefault()

        # Visualization and pose support
        self.match_started = False  # Set true on Autonomous or Teleop init

    @property
    def container(self) -> RobotContainer:
        return self._container

    @property
    def period(self) -> seconds:
        """
        The periodic that the '_periodic' calls are made
        """
        return self._period

    @property
    def counter(self) -> int:
        return self._counter

    # @tracer.start_as_current_span("robotInit")
    def robotInit(self, container_init: Callable[[Robot], RobotContainer]) -> None:  # pylint: disable=arguments-differ
        """
        This function is run when the robot is first started up and should be used for any
        initialization code.
        """
        logger.info("robotInit: entry")
        super().robotInit()

        # Disable most logging. Rely upon pykit/AdvantageScope
        SignalLogger.enable_auto_logging(False)
        StatusLogger.disableAutoLogging()
        LiveWindow.disableAllTelemetry()

        command_count: dict[str, int] = {}

        # Tracks active commands.
        def logCommandFunction(command: Command, active: bool) -> None:
            name = command.getName()
            count = command_count.get(name, 0) + (1 if active else -1)
            command_count[name] = count
            Logger.recordOutput(f"Commands/{name}", count > 0)

        scheduler = CommandScheduler.getInstance()

        scheduler.onCommandInitialize(lambda c: logCommandFunction(c, True))
        scheduler.onCommandFinish(lambda c: logCommandFunction(c, False))
        scheduler.onCommandInterrupt(lambda c: logCommandFunction(c, False))

        # Set up logging
        self._logging_init()
        logger.info("Python: %s.%s.%s",sys.version_info.major,
                    sys.version_info.minor, sys.version_info.micro)

        # Set up our pathfinding algorithm
        # TODO: LocalADStar has a dynamic obstacle field.  Can we use that in future with vision?
        Pathfinding.setPathfinder(LocalADStar())

        # Set up our playing field. May get overwritten if simulation is running or if we
        # support vision based odometry
        self.field = Field2d()
        if self._is_simulation:
            SmartDashboard.putData("Field", self.field)

        # Track periodic percent used during telop and autonomous
        SmartDashboard.putNumber("Periodic/Robot/auto-periodic-%", 0.0)
        SmartDashboard.putNumber("Periodic/Robot/teleop-periodic-%", 0.0)

        # Start off in the preflight screen
        select_tab("PREFLIGHT")

        # Set up the robot container with all of our subsystems. An initialier
        # function is passed in that creates this container so it can be
        # customized each here in the base class near the end of robotInit

        self._container = container_init(self)

    def _logging_init(self) -> None:
        DriverStation.silenceJoystickConnectionWarning(True)
        match ROBOT_MODE:
            case RobotModes.REAL:
                logger.setLevel(logging.ERROR)  # Python logging
                logging.getLogger("wpilib").setLevel(logging.ERROR)
                logging.getLogger("commands2").setLevel(logging.ERROR)

            case RobotModes.SIMULATION:
                DriverStation.silenceJoystickConnectionWarning(True)
                logger.setLevel(logging.INFO)  # Python logging
                logging.getLogger("wpilib").setLevel(logging.DEBUG)
                logging.getLogger("commands2").setLevel(logging.DEBUG)

            case RobotModes.REPLAY:
                logger.setLevel(logging.ERROR)  # Python logging
                logging.getLogger("wpilib").setLevel(logging.ERROR)
                logging.getLogger("commands2").setLevel(logging.ERROR)

    def endCompetition(self) -> None:
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("End-Competition", clear=True, notify=True)

        send_notification(Notification(title="Game Over",
                                       description="The competition has ended",
                                       display_time=5000))
        # That's All Folks...
        super().endCompetition()

    def robotPeriodic(self) -> None:
        """
        Periodic code for all modes should go here.

        This function is called each time a new packet is received from the driver
        station. All classes derived from 'Subsystem' will have their 'periodic'
        function called automatically (right after this function). So only do
        non-Subsystem updates here

        Default period is 20 mS.
        """
        start = time.monotonic()
        self._counter += 1

        # This routine is called
        LogTracer.resetOuter("RobotPeriodic")

        # _status = Phoenix6Signals.refresh()       # TODO: Investigate
        LogTracer.record("PhoenixUpdate")

        # robotPeriodic covers the RobotState update which is for the
        # drivetrain and gyro
        self.container.robotPeriodic()
        LogTracer.record("ContainerPeriodic")

        if self._command_scheduler is None:
            self._command_scheduler = CommandScheduler.getInstance()

        self._command_scheduler.run()
        LogTracer.record("CommandsPeriodic")

        LogTracer.recordTotal()
        self._stats.add("periodic-duration", time.monotonic() - start)

    def disabledInit(self) -> None:
        """
        Initialization code for disabled mode should go here.

        Users should override this method for initialization code which will be
        called each time the robot enters disabled mode.
        """
        super().disabledInit()

        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "stop") and callable(getattr(subsystem, "stop")):
                subsystem.stop()

        self.container.disable_pid_subsystems()

        self.disabledTimer.reset()
        self.disabledTimer.start()

        # Scan all subsystems for any faults that occurred. Log and clear them
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Disabled-Init", clear=True, notify=True)

    def disabledPeriodic(self) -> None:
        """
        Periodic code for disabled mode should go here.

        Users should override this method for code which will be called each time a
        new packet is received from the driver station and the robot is in disabled
        mode.
        """
        # Alert updates for pre-flight
        self.container.disable_periodic()

        if self.disabledTimer.hasElapsed(self.robot_constants.WHEEL_LOCK_TIME):
            self.container.robot_drive.set_motor_brake(False)
            self.disabledTimer.stop()
            self.disabledTimer.reset()

        # Validate who we are working for
        if not self.match_started:
            self.container.check_alliance()

    def disabledExit(self) -> None:
        """
        Exit code for disabled mode should go here.

        Users should override this method for code which will be called each time
        the robot exits disabled mode.
        """
        super().disabledExit()

        self.disabledTimer.stop()
        self.disabledTimer.reset()

        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Disabled-Exit", clear=True, notify=True)

    def autonomousInit(self) -> None:
        """
        Initialization code for autonomous mode should go here.

        Users should override this method for initialization code which will be
        called each time the robot enters autonomous mode.
        """
        super().autonomousInit()
        logger.info("autonomousInit: entry")

        self.container.set_start_time()

        # Stop what we are doing...
        self.container.robot_drive.set_motor_brake(True)

        # Validate who we are working for. This may not be valid until autonomous or teleop init
        if not self.match_started:
            self.container.check_alliance()
            self.match_started = True

        self._autonomous_command = self.container.get_autonomous_command()

        if self._autonomous_command:
            self._autonomous_command.schedule()

        self._stats.clear("auto-duration")

        if self._is_simulation:
            select_tab("Autonomous")

    def autonomousPeriodic(self) -> None:
        """
        Periodic code for autonomous mode should go here.

        Users should override this method for code which will be called each time a
        new packet is received from the driver station and the robot is in
        autonomous mode.
        """
        start = time.monotonic()

        if self.counter % 75 == 5:  # Call every 1.5 seconds, but not on the first pass
            moving_avg = self._stats.get("auto-duration")
            if moving_avg is not None:
                # What percentage of time are we using up before the next periodic tick event
                average_percent = (moving_avg.average / self._period) * 100
                SmartDashboard.putNumber("Periodic/Robot/auto-periodic-%", average_percent)

        self._stats.add("auto-duration", time.monotonic() - start)

    def autonomousExit(self) -> None:
        """
        Exit code for autonomous mode should go here.

        Users should override this method for code which will be called each time
        the robot exits autonomous mode.
        """
        super().autonomousExit()
        logger.info("autonomousExit: entry")

        if self._autonomous_command:
            self._autonomous_command.cancel()

        # Scan all subsystems for any faults that occurred. Log and clear them
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Autonomous-Exit", clear=True, notify=True)

    def teleopInit(self) -> None:
        """
        Initialization code for teleop mode should go here.

        Users should override this method for initialization code which will be
        called each time the robot enters teleop mode.
        """
        super().teleopInit()
        logger.debug("*** called teleopInit")

        self.container.set_start_time()

        # Stop what we are doing...
        if self._autonomous_command:
            self._autonomous_command.cancel()
        else:
            CommandScheduler.getInstance().cancelAll()

        # Validate who we are working for. This may not be valid until autonomous or teleop init
        if not self.match_started:
            self.container.check_alliance()
            self.match_started = True

        self._stats.clear("teleop-duration")

        if self._is_simulation:
            select_tab("Teleop")

    def teleopPeriodic(self) -> None:
        """
        Periodic code for teleop mode should go here.

        Users should override this method for code which will be called each time a
        new packet is received from the driver station and the robot is in teleop
        mode.
        """
        start = time.monotonic()

        if self.counter % 75 == 5:  # Call every 1.5 seconds, but not on the first pass
            moving_avg = self._stats.get("teleop-duration")
            if moving_avg is not None:
                # What percentage of time are we using up before the next periodic tick event
                average_percent = (moving_avg.average / self._period) * 100

                SmartDashboard.putNumber("Periodic/Robot/teleop-periodic-%", average_percent)

        self._stats.add("teleop-duration", time.monotonic() - start)

    def teleopExit(self) -> None:
        """
        Exit code for teleop mode should go here.

        Users should override this method for code which will be called each time
        the robot exits teleop mode.
        """
        super().teleopExit()
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "stop") and callable(getattr(subsystem, "stop")):
                subsystem.stop()

        self.container.robot_drive.set_straight()

        # Scan all subsystems for any faults that occurred. Log and clear them
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Teleop-Exit", clear=True, notify=True)

    def testInit(self) -> None:
        """
        Initialization code for test mode should go here.

        Users should override this method for initialization code which will be
        called each time the robot enters test mode.
        """
        super().testInit()
        logger.debug("*** called testInit")
        CommandScheduler.getInstance().cancelAll()
