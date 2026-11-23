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
"""
Logged Robot Module

This module provides LoggedRobot, a specialized robot base class that integrates
timing control with pykit logging infrastructure. LoggedRobot extends WPILib's
IterativeRobotBase to inject precise timing, logging synchronization, and replay
support into the robot main loop.

Key Features:
- Precise timing control via HAL notifier for deterministic loop periods
- Integration with pykit Logger for input/output logging at each timestamp
- Overrun detection and recovery for main loop timing violations
- Simulation mode support
- Proper resource cleanup via watchdog and notifier patterns

The main loop execution order for each cycle:
1. Logger.periodic_before_user() - Load sensor inputs/replay data
2. User periodic code (_loop_func) - Execute robot_periodic, mode periodic, etc.
3. Logger.periodic_after_user() - Log output values and timing metrics
"""

import contextlib
import logging

from commands2 import CommandScheduler
from cpy6107 import LoopTiming, OverrunInfo, TimedCommandRobot
from wpilib import RobotBase, RobotController
from wpimath.units import seconds
from wpiutil import report_usage

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer

#: Default main loop period in seconds (20 ms = 50 Hz)
DEFAULT_PERIOD: seconds = 0.02
DEFAULT_SCHEDULER_OFFSET: seconds = TimedCommandRobot.SCHEDULER_OFFSET

# Multiplier from the loop period to the default loop overrun timeout.
DEFAULT_OVERRUN_MULTIPLIER: float = 2.0

logger = logging.getLogger(__name__)


class LoggedRobot(TimedCommandRobot):
    """Robot base class with pykit logging around every main-loop cycle.

    The loop, its HAL notifier and its overrun watchdog live in C++ (``TimedCommandRobot``), so
    ``set_watchdog_timeout()`` really changes when an overrun is reported. Logging runs in the
    ``before_user_loop`` / ``after_user_loop`` hooks, outside the watchdog window.
    """

    #: Class-level default loop period in seconds (20 ms for FRC standard 50 Hz loop)
    default_period = DEFAULT_PERIOD  # seconds

    def __init__(
        self,
        period: seconds = DEFAULT_PERIOD,
        scheduler_offset: seconds = DEFAULT_SCHEDULER_OFFSET,
        watchdog_timeout: seconds | None = None,
    ):
        """
        Initialize the LoggedRobot with precise timing infrastructure.
        """
        super().__init__(period=period, scheduler_offset=scheduler_offset)

        # Traditional Commands V2 Scheduler
        self._scheduler = CommandScheduler.get_instance()
        self.set_scheduler(self._run_command_scheduler)

        # During startup, use a large watchdog timeout
        self._watchdog_timeout = max(watchdog_timeout or period * DEFAULT_OVERRUN_MULTIPLIER, period)
        self.set_watchdog_timeout(5.0)

        # For overrun monitoring
        self.set_overrun_callback(self._overrun_callback)
        self._overrun_count: int = 0

        self._period = period
        self._is_simulation = RobotBase.is_simulation()
        self._init_end: int = 0  # monotonic timestamp (nanoseconds) when robot_init() completes

        # TODO: Dig into 'report_usage'
        report_usage("Framework", "PyKit_LoggedRobot")
        report_usage("LoggingFramework", "PyKit")

    def robot_init(self) -> None:
        """
        One-time initialization hook, called by start_competition() before the main loop.

        WPILib 2027 removed ``robotInit``; this hook is provided by LoggedRobot so subclasses can
        keep a single place for deferred startup work. Override in subclasses (e.g. Robot).
        """
        pass

    @property
    def period(self) -> seconds:
        """
        Get the configured loop period.

        Returns:
            float: The loop period in seconds (typically 0.02 for 50 Hz).
        """
        return self._period

    def start_competition(self) -> None:
        """
        Main robot control loop with integrated logging and precise timing.
        """
        exception = None
        try:
            # Execute one-time initialization
            self.robot_init()

            # Initialize simulation physics if running in simulation
            if self._is_simulation:
                self.simulation_init()

            self._init_end = RobotController.get_monotonic_time()
            Logger.periodic_after_user(self._init_end, 0)
            print("Robot startup complete!")

            Logger.start_receiver()

            try:
                self.set_watchdog_timeout(self._watchdog_timeout)

                super().start_competition()  # runs until end_competition()

            except Exception as exc:
                exception = exc
                logger.exception("Unhandled exception during robot competition")

        except Exception as exc:
            exception = exc
            logger.exception("Unhandled exception during robot initialization")

        if exception is not None:
            Logger.periodic_after_user(0, 0)
            Logger.end()
            raise exception

    def end_competition(self) -> None:
        # TODO: Anything more here
        self.clear_scheduler()

        super().end_competition()

    def before_user_loop(self) -> None:
        """
        Called from the base TimedCommandRobot just before calling the user_loop.
        """
        LogTracer.clear()  # discard blocks leaked by an exception in the previous cycle
        Logger.periodic_before_user()

    def after_user_loop(self, timing: LoopTiming) -> None:
        """
        Called from the base TimedCommandRobot just after calling the user_loop.
        """
        with contextlib.suppress(Exception):  # HACK: exception work around when in match (FMS Active)
            Logger.periodic_after_user(int(timing.user_time * 1e6), int(timing.pre_user_time * 1e6))

    def _overrun_callback(self, _overrun_info: OverrunInfo, *_args, **_kwargs) -> None:
        self._overrun_count += 1

    def report_loop_overrun(self, *_args, **_kwargs) -> None:
        pass

    def _run_command_scheduler(self):
        # Start LogTracer profiling for this cycle
        LogTracer.reset_outer("CommandScheduler")
        try:
            self._scheduler.run()
        finally:
            LogTracer.record_total()
