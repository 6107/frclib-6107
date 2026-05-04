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
"""Base robot class with integrated pykit logging and WPILib Commands-v2 support.

This module provides the Robot class, the central coordinating hub for all FRC robot
operations. It extends pykit's LoggedRobot with:

- Mode detection (REAL robot, SIMULATION, REPLAY from logs)
- Automatic telemetry setup via pykit Logger (AdvantageScope integration)
- Constants override pattern (RobotConstants, SimulationConstants, NetworkConstants)
- State machine management (Disabled, Autonomous, Teleop, Test modes)
- Performance profiling via LogTracer for periodic loop analysis
- Subsystem lifecycle hooks (fault detection, stop on mode transitions)
- Field visualization with WPILib Field2d
- Command scheduler integration with telemetry logging

A team's robot implementation typically subclasses Robot and passes a container_init
callable to robotInit() to provide the RobotContainer with custom subsystems.

Supported years: 2026–2050

Key Design Patterns:
    - Callback-driven mode transitions (Init/Periodic/Exit for each mode)
    - Subsystem hooks: stop(), fault_detection(), sim_init(), update_sim()
    - Constants driven configuration via dataclass slots
    - All telemetry via pykit Logger, not SmartDashboard

Mode Detection:
    - REAL: On-field robot (roboRIO). Logs to USB drive or fallback directory.
    - SIMULATION: Desktop pyfrc simulation. Real-time logging to file and NT4.
    - REPLAY: Log playback with LOG_PATH environment variable.
"""

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
    """Central robot coordinator for frclib-6107 FRC applications.

    Extends LoggedRobot to provide:
    - Automatic mode-aware telemetry pipeline setup (real/sim/replay)
    - Subsystem and command lifecycle management
    - Constants override pattern with RobotConstants, SimulationConstants, NetworkConstants
    - State machine for robot modes (Disabled, Autonomous, Teleop, Test)
    - Performance profiling integration via LogTracer
    - Optional subsystem hooks: stop(), fault_detection(), sim_init(), update_sim()

    The Robot class acts as the main entry point and orchestrator. Teams instantiate
    this class (or a subclass) with optional custom constants, then pass a container_init
    callback to robotInit() to supply the RobotContainer with subsystems.

    Lifecycle:
        1. __init__(): Set constants, configure logging pipeline based on mode, start Logger
        2. robotInit(): Initialize pathfinding, set up field, call container_init callback
        3. mode transitions: Call Init/Periodic/Exit for each mode (Disabled, Autonomous,
           Teleop, Test)
        4. Per-mode periodic: robotPeriodic() runs every cycle; mode-specific callbacks follow

    Performance Monitoring:
        - robotPeriodic() includes LogTracer profiling for Phoenix updates, container,
          and command scheduler
        - Periodic duration stats tracked in RobotStatistics for SmartDashboard display
        - Shows % CPU utilization relative to robot period (default 20 mS)

    Attributes:
        robot_constants (RobotConstants): Configuration for robot behavior (periods,
            constraints, etc.). Teams can override.
        simulation_constants (SimulationConstants): Simulation-specific config (starting
            poses, physics parameters). Used in SIMULATION and REPLAY modes.
        network_constants (NetworkConstants): Network configuration (team number,
            addresses, ports).
        field (Field2d): WPILib field visualization. Updated by odometry.
        match_started (bool): Set True when autonomous or teleop begins; used to
            validate alliance selection.
        container (RobotContainer): Reference to all subsystems and commands.
    """

    def __init__(self, build_year: str,
                 robot_constants: Optional[RobotConstants] = None,
                 simulation_constants: Optional[SimulationConstants] = None,
                 network_constants: Optional[NetworkConstants] = None):
        """Initialize the robot with constants and configure logging pipeline.

        This constructor:
        1. Stores or creates default values for the three constants dataclasses
        2. Calls LoggedRobot.__init__() with the configured robot period
        3. Validates the build year (2026–2050)
        4. Logs robot metadata (name, team, year, deploy info for real robots)
        5. Configures the telemetry pipeline based on robot mode (REAL/SIMULATION/REPLAY):
           - REAL: NT4Publisher + WPILOGWriter (USB /U/logs or fallback /home/lvuser/pyLogs)
           - SIMULATION: WPILOGWriter + NT4Publisher
           - REPLAY: WPILOGReader (input) + WPILOGWriter (output with _sim suffix)
        6. Starts Logger to commence telemetry collection

        Args:
            build_year (str): Year the robot code was built (e.g., "2026"). Must be
                between 2026 and 2050 inclusive.
            robot_constants (Optional[RobotConstants]): Custom robot configuration.
                If None, uses default RobotConstants().
            simulation_constants (Optional[SimulationConstants]): Custom simulation
                config (starting poses, physics). If None, uses default SimulationConstants().
            network_constants (Optional[NetworkConstants]): Custom network config
                (team number, server addresses). If None, uses default NetworkConstants().

        Raises:
            ValueError: If build_year is not between 2026 and 2050 inclusive.

        Note:
            For REPLAY mode, the LOG_PATH environment variable must be set to the
            absolute path of the .wpilog file to replay. Example:
                LOG_PATH=/path/to/log.wpilog robotpy --main src sim

            On REAL robots, USB drive detection tries /U/logs; if not found, logs to
            /home/lvuser/pyLogs as fallback to handle network outages.
        """
        # ...existing code...
        self.robot_constants: RobotConstants = robot_constants or RobotConstants()
        self.simulation_constants: SimulationConstants = simulation_constants or SimulationConstants()
        self.network_constants: NetworkConstants = network_constants or NetworkConstants()

        # Initialize base LoggedRobot with configured period
        super().__init__(period=self.robot_constants.ROBOT_PERIOD)

        self._period: seconds = self.getPeriod()

        # Validate build year against supported range
        if not 2026 <= int(build_year) <= 2050:
            raise ValueError("Not within supported rage of [2026..2050]")

        # Record metadata for AdvantageScope telemetry
        Logger.recordMetadata("Robot", type(self).__name__)
        Logger.recordMetadata("Team", self.network_constants.TEAM)
        Logger.recordMetadata("Year", build_year)

        # Log deployment info on real robots for traceability
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

                # Real robot: use NT4 for dashboard and WPILOGWriter for resilience
                Logger.addDataReciever(NT4Publisher(True))
                usb_mount = "/U"
                usb_logs = os.path.join(usb_mount, "logs")

                if os.path.ismount(usb_mount) or os.path.exists(usb_mount):
                    os.makedirs(usb_logs, exist_ok=True)
                    Logger.addDataReciever(WPILOGWriter())
                else:
                    # Fallback to /home/lvuser/pyLogs if USB unavailable
                    current_dir = os.getcwd()
                    if current_dir in ("", "/"):
                        current_dir = "/home/lvuser"

                    fallback = os.path.join(current_dir, "pyLogs")
                    fallback_dir = os.path.abspath(fallback)
                    os.makedirs(fallback_dir, exist_ok=True)
                    Logger.addDataReciever(WPILOGWriter(filename=None,
                                                        path=fallback_dir))

            case RobotModes.SIMULATION:
                # Simulation: both file logging and NT4 for rapid iteration
                Logger.addDataReciever(WPILOGWriter())
                Logger.addDataReciever(NT4Publisher(True))

            case RobotModes.REPLAY:
                # Replay: read from LOG_PATH, write output with _sim suffix
                # Disable WPILib timing to run as fast as possible
                self.UseTiming = False

                log_path = os.environ["LOG_PATH"]
                log_path = os.path.abspath(log_path)

                Logger.setReplaySource(WPILOGReader(log_path))
                Logger.addDataReciever(WPILOGWriter(log_path[:-7] + "_sim.wpilog"))

        # Start telemetry collection
        Logger.start()

        # Initialize internal state for robot operation
        self._counter = 0  # Incremented each periodic; used for throttled logging/SmartDashboard updates

        self._container: Optional[RobotContainer] = None
        self._autonomous_command: Optional[Command] = None
        self.disabledTimer: Timer = Timer()
        self.field: wpilib.Field2d = Field2d()
        self._stats: RobotStatistics = RobotStatistics(self)

        self._command_scheduler: CommandScheduler | None = None
        self._network_tables_instance = NetworkTableInstance.getDefault()

        # Visualization and match state
        self.match_started = False  # Set True when autonomous or teleop begins

    @property
    def container(self) -> RobotContainer:
        """Access the robot's RobotContainer (subsystems and commands).

        Returns:
            RobotContainer: The container initialized during robotInit().
        """
        return self._container

    @property
    def period(self) -> seconds:
        """Get the robot's periodic update period in seconds.

        Returns:
            seconds: The period of robotPeriodic() calls (default 0.020 seconds / 20 mS).
        """
        return self._period

    @property
    def counter(self) -> int:
        """Get the number of periodic cycles executed since robot startup.

        Used for throttling logging/SmartDashboard updates (e.g., every 75 cycles).

        Returns:
            int: Current periodic cycle count, incremented each robotPeriodic() call.
        """
        return self._counter

    def robotInit(self, container_init: Callable[[Robot], RobotContainer]) -> None:
        """Initialize the robot after boot and configure subsystems.

        Called once at robot startup. This method:
        1. Disables built-in hardware logging (Phoenix6, REV) in favor of pykit
        2. Sets up command scheduler callbacks to track active commands via Logger
        3. Configures logging levels based on robot mode
        4. Initializes LocalADStar pathfinding globally
        5. Creates the Field2d visualization
        6. Sets up SmartDashboard entries for periodic monitoring
        7. Calls the container_init callback to create RobotContainer with subsystems

        Args:
            container_init (Callable[[Robot], RobotContainer]): Factory function that
                takes this Robot instance and returns a configured RobotContainer.
                Typically: lambda robot: MyRobotContainer(robot)

        Note:
            The container_init callback is called at the end of robotInit(), allowing
            teams to override constants or add custom subsystems before container creation.
        """
        logger.info("robotInit: entry")
        super().robotInit()

        # Disable vendor-specific auto-logging; use pykit Logger instead
        SignalLogger.enable_auto_logging(False)
        StatusLogger.disableAutoLogging()
        LiveWindow.disableAllTelemetry()

        command_count: dict[str, int] = {}

        # Helper to track active commands for telemetry
        def logCommandFunction(command: Command, active: bool) -> None:
            """Track command state changes for Logger telemetry."""
            name = command.getName()
            count = command_count.get(name, 0) + (1 if active else -1)
            command_count[name] = count
            Logger.recordOutput(f"Commands/{name}", count > 0)

        scheduler = CommandScheduler.getInstance()

        # Register callbacks to log command lifecycle events
        scheduler.onCommandInitialize(lambda c: logCommandFunction(c, True))
        scheduler.onCommandFinish(lambda c: logCommandFunction(c, False))
        scheduler.onCommandInterrupt(lambda c: logCommandFunction(c, False))

        # Configure logging levels
        self._logging_init()
        logger.info("Python: %s.%s.%s", sys.version_info.major,
                    sys.version_info.minor, sys.version_info.micro)

        # Set up global pathfinding (PathPlanner)
        # TODO: LocalADStar has a dynamic obstacle field. Can we use that in future with vision?
        Pathfinding.setPathfinder(LocalADStar())

        # Initialize field visualization
        # May be overwritten by simulation or vision odometry in container
        self.field = Field2d()
        if self._is_simulation:
            SmartDashboard.putData("Field", self.field)

        # Set up SmartDashboard entries for periodic performance monitoring
        SmartDashboard.putNumber("Periodic/Robot/auto-periodic-%", 0.0)
        SmartDashboard.putNumber("Periodic/Robot/teleop-periodic-%", 0.0)

        # Start on preflight screen
        select_tab("PREFLIGHT")

        # Create the robot container with all subsystems (teams customize via callback)
        self._container = container_init(self)

    def _logging_init(self) -> None:
        """Configure logging levels based on robot mode.

        REAL: Minimize logging (ERROR level) for on-field performance.
        SIMULATION: Enable verbose logging (DEBUG) for development debugging.
        REPLAY: Minimize logging (ERROR level) since data comes from log file.
        """
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
        """Called when the competition ends (robot power lost or match timeout).

        Performs cleanup:
        - Calls fault_detection("End-Competition") on all subsystems
        - Sends end-of-competition notification to Elastic dashboard
        - Calls parent endCompetition() to stop the main loop

        Note:
            This is the final callback before robot shutdown.
        """
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("End-Competition", clear=True, notify=True)

        send_notification(Notification(title="Game Over",
                                       description="The competition has ended",
                                       display_time=5000))
        # That's All Folks...
        super().endCompetition()

    def robotPeriodic(self) -> None:
        """Execute robot logic that runs every periodic cycle.

        Runs at ROBOT_PERIOD (default 20 mS). All subsystems' periodic() methods
        are called automatically after this function via WPILib's Subsystem base class.

        Execution order:
        1. Increment counter and reset LogTracer outer span
        2. Update Phoenix signals (TODO: performance investigation needed)
        3. Call container.robotPeriodic() (RobotState, odometry updates)
        4. Run CommandScheduler (execute active commands)
        5. Record total LogTracer duration and periodic execution time

        Profiling:
            Uses LogTracer to measure each phase. Performance stats tracked in
            RobotStatistics for SmartDashboard display. Mode-specific periodic methods
            (autonomousPeriodic, teleopPeriodic) also update % CPU utilization.

        Note:
            Non-subsystem code should generally go in mode-specific periodic methods,
            not here. Keep robotPeriodic() fast to maintain <20 mS loop time.
        """
        start = time.monotonic()
        self._counter += 1

        # Start LogTracer profiling for this cycle
        LogTracer.resetOuter("RobotPeriodic")

        # Update Phoenix signal cache (TODO: performance investigation needed)
        # _status = Phoenix6Signals.refresh()
        LogTracer.record("PhoenixUpdate")

        # RobotState update (odometry, gyro state) from container
        self.container.robotPeriodic()
        LogTracer.record("ContainerPeriodic")

        # Get or initialize CommandScheduler and run active commands
        if self._command_scheduler is None:
            self._command_scheduler = CommandScheduler.getInstance()

        self._command_scheduler.run()
        LogTracer.record("CommandsPeriodic")

        # Record profiling data
        LogTracer.recordTotal()
        self._stats.add("periodic-duration", time.monotonic() - start)

    def disabledInit(self) -> None:
        """Enter Disabled mode. Called when robot transitions from enabled to disabled.

        Initialization tasks:
        - Stop all subsystems by calling their stop() methods
        - Disable PID subsystems
        - Reset and start disabledTimer (used to delay motor brake release)
        - Call fault_detection("Disabled-Init") on all subsystems
        """
        super().disabledInit()

        # Stop and zero out all mechanism power
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "stop") and callable(getattr(subsystem, "stop")):
                subsystem.stop()

        # Disable PID controllers to prevent integral windup
        self.container.disable_pid_subsystems()

        # Start wheellock timer (motor brakes applied initially)
        self.disabledTimer.reset()
        self.disabledTimer.start()

        # Scan for any faults and log them
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Disabled-Init", clear=True, notify=True)

    def disabledPeriodic(self) -> None:
        """Execute Disabled mode logic each cycle.

        Behavior:
        - Call container.disable_periodic() for pre-flight checks/alerts
        - After WHEEL_LOCK_TIME (configurable), release motor brakes
        - Validate alliance color/location when match hasn't started

        Note:
            Motor brakes are applied in Disabled to simplify odometry offsets at
            mode transitions. After WHEEL_LOCK_TIME expires, brakes are released
            to prepare for the next match.
        """
        # Alert updates for pre-flight system checks
        self.container.disable_periodic()

        # Release motor brakes after a delay to lock mechanisms at mode transition
        if self.disabledTimer.hasElapsed(self.robot_constants.WHEEL_LOCK_TIME):
            self.container.robot_drive.set_motor_brake(False)
            self.disabledTimer.stop()
            self.disabledTimer.reset()

        # Validate alliance if match hasn't started yet
        if not self.match_started:
            self.container.check_alliance()

    def disabledExit(self) -> None:
        """Exit Disabled mode. Called when robot transitions from disabled to enabled.

        Cleanup tasks:
        - Stop and reset disabledTimer
        - Call fault_detection("Disabled-Exit") on all subsystems
        """
        super().disabledExit()

        self.disabledTimer.stop()
        self.disabledTimer.reset()

        # Scan for faults at mode transition
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Disabled-Exit", clear=True, notify=True)

    def autonomousInit(self) -> None:
        """Enter Autonomous mode. Called when autonomous period begins.

        Initialization tasks:
        - Call container.set_start_time() to establish start timestamp
        - Apply motor brakes
        - Validate alliance (if not already done)
        - Mark match_started = True
        - Schedule the autonomous command from container
        - Clear autonomousPeriodic timing stats
        - Switch to "Autonomous" tab on Elastic (if simulation)

        Note:
            Autonomous command is obtained from container and scheduled if present.
            Alliance validation may occur here if robotInit() didn't run autonomous
            or teleop mode (e.g., in test mode only).
        """
        super().autonomousInit()
        logger.info("autonomousInit: entry")

        # Set start time for relative timer tracking
        self.container.set_start_time()

        # Lock mechanisms at mode transition
        self.container.robot_drive.set_motor_brake(True)

        # Validate alliance if not yet confirmed
        if not self.match_started:
            self.container.check_alliance()
            self.match_started = True

        # Get and schedule the autonomous command
        self._autonomous_command = self.container.get_autonomous_command()

        if self._autonomous_command:
            self._autonomous_command.schedule()

        # Reset stats for this match phase
        self._stats.clear("auto-duration")

        if self._is_simulation:
            select_tab("Autonomous")

    def autonomousPeriodic(self) -> None:
        """Execute Autonomous mode logic each cycle.

        Behavior:
        - Track periodic execution time in RobotStatistics
        - Every 1.5 seconds (75 cycles), update SmartDashboard with % CPU used

        The autonomous command is run by the CommandScheduler (in robotPeriodic).
        """
        start = time.monotonic()

        # Every 1.5 seconds (not on first pass), report CPU usage
        if self.counter % 75 == 5:
            moving_avg = self._stats.get("auto-duration")
            if moving_avg is not None:
                # Calculate percentage of robot period used on average
                average_percent = (moving_avg.average / self._period) * 100
                SmartDashboard.putNumber("Periodic/Robot/auto-periodic-%", average_percent)

        self._stats.add("auto-duration", time.monotonic() - start)

    def autonomousExit(self) -> None:
        """Exit Autonomous mode. Called when autonomous period ends.

        Cleanup tasks:
        - Cancel the autonomous command
        - Call fault_detection("Autonomous-Exit") on all subsystems
        """
        super().autonomousExit()
        logger.info("autonomousExit: entry")

        # Cancel any running autonomous command
        if self._autonomous_command:
            self._autonomous_command.cancel()

        # Scan for faults at mode transition
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Autonomous-Exit", clear=True, notify=True)

    def teleopInit(self) -> None:
        """Enter Teleop mode. Called when driver control period begins.

        Initialization tasks:
        - Call container.set_start_time() to establish start timestamp
        - Cancel autonomous command (if still running)
        - Cancel all other commands via CommandScheduler
        - Validate alliance (if not already done)
        - Mark match_started = True
        - Clear teleopPeriodic timing stats
        - Switch to "Teleop" tab on Elastic (if simulation)

        Note:
            Command cancellation ensures clean transition; teleop commands are
            expected to be triggered by joystick inputs via operator interface.
        """
        super().teleopInit()
        logger.debug("*** called teleopInit")

        # Set start time for match duration tracking
        self.container.set_start_time()

        # Clean up any remaining commands from autonomous
        if self._autonomous_command:
            self._autonomous_command.cancel()
        else:
            CommandScheduler.getInstance().cancelAll()

        # Validate alliance if not yet confirmed
        if not self.match_started:
            self.container.check_alliance()
            self.match_started = True

        # Reset stats for this match phase
        self._stats.clear("teleop-duration")

        if self._is_simulation:
            select_tab("Teleop")

    def teleopPeriodic(self) -> None:
        """Execute Teleop mode logic each cycle.

        Behavior:
        - Track periodic execution time in RobotStatistics
        - Every 1.5 seconds (75 cycles), update SmartDashboard with % CPU used

        Driver commands are triggered by joystick inputs via operator interface,
        and executed by the CommandScheduler (in robotPeriodic).
        """
        start = time.monotonic()

        # Every 1.5 seconds (not on first pass), report CPU usage
        if self.counter % 75 == 5:
            moving_avg = self._stats.get("teleop-duration")
            if moving_avg is not None:
                # Calculate percentage of robot period used on average
                average_percent = (moving_avg.average / self._period) * 100

                SmartDashboard.putNumber("Periodic/Robot/teleop-periodic-%", average_percent)

        self._stats.add("teleop-duration", time.monotonic() - start)

    def teleopExit(self) -> None:
        """Exit Teleop mode. Called when driver control period ends.

        Cleanup tasks:
        - Stop all subsystems by calling their stop() methods
        - Set drivetrain to neutral/straight for safety
        - Call fault_detection("Teleop-Exit") on all subsystems
        """
        super().teleopExit()
        # ...existing code...
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "stop") and callable(getattr(subsystem, "stop")):
                subsystem.stop()

        # Set drivetrain to safe state
        self.container.robot_drive.set_straight()

        # Scan for faults at mode transition
        for subsystem in self.container.subsystems:
            if hasattr(subsystem, "fault_detection"):
                subsystem.fault_detection("Teleop-Exit", clear=True, notify=True)

    def testInit(self) -> None:
        """Enter Test mode. Called when test mode begins.

        Initialization tasks:
        - Cancel all scheduled commands to start clean

        Test mode is used for tuning, subsystem verification, and diagnostics
        in the test/tuning environment.
        """
        super().testInit()
        logger.debug("*** called testInit")
        CommandScheduler.getInstance().cancelAll()