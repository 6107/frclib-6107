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
import traceback

import hal
from wpilib import IterativeRobotBase, RobotBase, RobotController, Watchdog
from wpimath.units import seconds
from wpiutil import report_usage
from wpiutil.sync import wait_for_object

from lib_6107.pykit.logger import Logger

#: Default main loop period in seconds (20 ms = 50 Hz)
DEFAULT_PERIOD: seconds = 0.02

# Multiplier from the loop period to the default loop overrun timeout.
DEFAULT_OVERRUN_MULTIPLIER: float = 2.0

HAL_kInvalidHandle: int = 0  #: HAL invalid handle constant (used for notifier and other HAL resources)


class LoggedRobot(IterativeRobotBase):
    """
    Robot base class providing integrated logging and precise loop timing.

    LoggedRobot extends WPILib's IterativeRobotBase to provide:
    - Deterministic loop timing using HAL notifier for accurate synchronization
    - Integration with pykit Logger for telemetry capture at each timestamp
    - Overrun detection when user code exceeds the periodic deadline
    - Simulation support via simulation_init() callback
    - Automatic resource cleanup via watchdog and notifier patterns

    Teams should subclass this instead of IterativeRobotBase to get logging and
    precise timing. The logging setup (mode detection, receiver initialization)
    should happen in robot_init() via Robot.container_init() callback (see Robot class).

    Attributes:
        default_period (float): Class-level default loop period in seconds (20 ms).
        _use_timing (bool): Whether to enforce timing via HAL notifier. Can be set to
            False for testing to disable timing enforcement.
        period (float): Property returning the configured loop period in seconds.

    Usage:
        ```python
        class MyRobot(LoggedRobot):
            def robot_init(self):
                # Initialize Logger here via Robot.container_init() callback
                self.container = RobotContainer(self)

            def robot_periodic(self):
                # User periodic code - automatically wrapped by logging
                pass

        if __name__ == "__main__":
            hal.main(lambda: MyRobot(period=0.02))
        ```
    """

    #: Class-level default loop period in seconds (20 ms for FRC standard 50 Hz loop)
    default_period = DEFAULT_PERIOD  # seconds
    # overrun_multiplier = DEFAULT_OVERRUN_MULTIPLIER  # Multiplier for watchdog timeout relative to loop period

    def _print_overrun_message(self) -> None:
        """
        Callback invoked when the main loop overruns its deadline.

        This method is registered with the Watchdog to alert developers when
        user code or subsystem updates exceeded the target loop period. Override
        to customize overrun handling (e.g., log to dashboard, increment counter).

        Default behavior: Print warning to console.
        """
        print("Loop overrun detected!")

    def __init__(
        self, period: seconds = DEFAULT_PERIOD, overrun_multiplier: float = DEFAULT_OVERRUN_MULTIPLIER
    ) -> None:
        """
        Initialize the LoggedRobot with precise timing infrastructure.

        Sets up:
        - HAL notifier for deterministic timing synchronization
        - Watchdog for loop overrun detection
        - DSControlWord for Driver Station communication
        - Conversion of period to microseconds for HAL operations
        - Detection of simulation mode

        Args:
            period (seconds): The target loop period in seconds. Typical value is 0.02 (50 Hz).
                Must be positive. Default: 0.02 seconds (20 ms).

        Note:
            - The first periodic cycle is delayed by one period to ensure the HAL
              notifier's time base is properly initialized (handles robotpy test edge case)
            - The initializer does not start the Logger (that happens in startCompetition)
        """
        super().__init__(period)

        self._use_timing = True  # Control flag to enable/disable timing enforcement via HAL notifier.

        self._period: seconds = period  # Configured loop period in seconds
        self._period_ns: int = int(
            period * 1_000_000_000
        )  # Loop period converted to nanoseconds for HAL notifier operations

        self._is_simulation = RobotBase.is_simulation()  # True if running in simulation mode (SIMULATION or REPLAY)

        # Because in "robotpy test" this code starts at time 0
        # and hal.waitForNotifierAlarm returns (current_time_or_stopped, status)
        # with current_time_or_stopped assigned to 0 when hal.stopNotifier is called
        # or when the current time is 0, and hal.stopNotifier is signal to
        # exit the infinite loop, the stop is prematurely detected at time 0.
        # Force the program to wait until self._period_ns for the first periodic loop
        # so that current_time_or_stopped will contain a non-zero current time and the
        # infinite loop does not end prematurely.
        #
        # "Next cycle wake-up time in microseconds (initialized to first period boundary)
        self._next_cycle_ns: int = 0 + self._period_ns

        # The primary wrapper around the HAL notifier system for scheduling periodic or single-shot
        # timer callbacks. wpilib.Notifier executes callbacks on a separate background thread driven
        # by HAL timer alarms. Because Python uses the Global Interpreter Lock (GIL), Notifier
        # loops in Python are best suited for I/O-bound tasks or moderate-rate control loops
        # rather than strict hard-real-time microsecond execution
        notifier, status = hal.create_notifier()
        if status != 0:
            raise RuntimeError(f"Error creating notifier: status {status}")

        self._notifier: int = notifier

        # HAL notifier handle for precise timing interrupt
        hal.set_notifier_name(self._notifier, "LoggedRobot")

        # Watchdog timer to detect loop overruns and invoke print_overrun_message.
        #
        # This functionality is similar to what the TimedRobot class provides internally to print out
        # warnings when the robot's periodic loops take longer than the configured period. Since we derive
        # directly from IterativeRobotBase, we need to implement our own watchdog to detect overruns and
        # log them appropriately.
        #
        # wpilib.Watchdog wraps a timer that tracks how long a specific block of code takes to run. WPILib
        # uses it internally (such as in TimedRobot and MotorSafety), and teams can instantiate it directly
        # to profile their own periodic loops.
        #
        #  • Overrun Detection. You configure the watchdog with a timeout duration (in seconds) and an
        #    optional callback function. If the timer is not reset (reset()) before the timeout expires,
        #    it prints a warning message to the Driver Station console and triggers your callback.
        #
        #  • Epoch Tracking. You can call add_epoch("name") at different milestones inside your robot
        #    loop. When an overrun happens, print_epochs() outputs the exact breakdown of how long each
        #    section took. This helps you pinpoint which subsystem or sensor read is slowing down your robot.
        #
        #  • Manual Activation. A newly created Watchdog starts disabled by default. You must call enable()
        #    or reset() to start monitoring, and disable() when you want it to stop.
        #
        self._watchdog = Watchdog(LoggedRobot.default_period, self._print_overrun_message)
        self._overrun_multiplier = overrun_multiplier
        self._watchdog.set_timeout(period * self._overrun_multiplier)

        report_usage("Framework", "PyKit_LoggedRobot")
        report_usage("LoggingFramework", "PyKit")

        self._init_end: int = 0  # FPGA timestamp (nanoseconds) when robot_init() completes

    def robot_init(self) -> None:
        """One-time initialization hook, called by start_competition() before the main loop.

        WPILib 2027 removed ``robotInit``; this hook is provided by LoggedRobot so subclasses can
        keep a single place for deferred startup work. Override in subclasses (e.g. Robot).
        """
        pass

    def _nop_callback(self) -> None:
        """
        No-op callback for HAL notifier.

        This method is registered with the HAL notifier to wake the main loop
        at precise intervals. It does not perform any action itself; the main
        loop handles user code execution and logging.
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

    @property
    def overrun_multiplier(self) -> float:
        """
        Get the configured loop overrun multiplier.

        Returns:
            float: The multiplier applied to the loop period to determine the watchdog timeout.
        """
        return self._overrun_multiplier

    @overrun_multiplier.setter
    def overrun_multiplier(self, value: float) -> None:
        """
        Set the loop overrun multiplier.

        Args:
            value (float): The new multiplier to apply to the loop period for watchdog timeout.
        """
        if value > 1.0 and value != self._overrun_multiplier:
            self._overrun_multiplier = value
            self._watchdog.set_timeout(self._period * self._overrun_multiplier)

    def set_loop_overrun_warning_timeout(self, timeout: seconds) -> None:
        """
        Set the watchdog timeout for loop overrun warnings. This is a more direct
        way to configure the watchdog timeout than using overrun_multiplier.

        Args:
            timeout (seconds): The new timeout duration in seconds. Must be at least the loop period.
        """
        if timeout >= self._period:
            self._watchdog.set_timeout(timeout)

    def start_competition(self) -> None:
        """
        Main robot control loop with integrated logging and precise timing.

        This method overrides IterativeRobotBase.start_competition() to replace
        the standard loop with one that:
        1. Executes robot_init() for initialization
        2. Initializes simulation physics if in simulation mode
        3. Starts the Logger with detected mode (REAL/SIMULATION/REPLAY)
        4. Enters an infinite loop that:
           a. Waits for the next cycle deadline using HAL notifier timing
           b. Detects and handles loop overruns (user code exceeds deadline)
           c. Calls Logger.periodic_before_user() to load sensor inputs
           d. Executes user periodic code (_loop_func)
           e. Calls Logger.periodic_after_user() to log outputs and measure performance
           f. Exits when stopNotifier signals (notifier returns 0)

        Timing is deterministic and precise, achieving ±0.1ms jitter on real roboRIO.

        The loop continues until hal.waitForNotifierAlarm returns 0 (signal to exit)
        or an error occurs in notifier synchronization.

        Note:
            - User code must complete within the loop period to avoid overruns
            - Overruns print a warning but the loop continues at the next deadline
            - Performance metrics are logged automatically by Logger
            - The initial robot_init() timing is captured and logged
        """
        try:
            # Execute one-time initialization
            self.robot_init()

            # Initialize simulation physics if running in simulation
            if self._is_simulation:
                self.simulation_init()

            # Log completion of initialization and notify observation starts
            self._init_end = RobotController.get_monotonic_time()

            # TODO: AdvantageKit has an AutoLogOutputManager that is referenced here. Look into its purpose and implementation.

            # Save data from the init sequence
            Logger.periodic_after_user(self._init_end, 0)

            print("Robot startup complete!")
            hal.observe_user_program_starting()  # Tell the DS that the robot is ready to be enabled

            # Start the Logger's receiver threads for telemetry output
            Logger.start_receiver()

            # Main robot loop: iterate until notifier signals stop (returns 0)
            while True:
                # Synchronize to the next deadline using HAL notifier for precise timing
                if self._use_timing:
                    self._watchdog.reset()  # Reset watchdog timer to avoid false overrun detection

                    current_time = RobotController.get_monotonic_time()

                    if self._next_cycle_ns < current_time:
                        # Loop overrun detected: user code took longer than period
                        # Skip wait and run immediately, then advance to next deadline
                        self._next_cycle_ns = current_time
                    else:
                        # Schedule the notifier to wake at the next deadline (absolute time, nanoseconds)
                        notifier = self._notifier

                        if notifier is HAL_kInvalidHandle:
                            break

                        status = hal.set_notifier_alarm(notifier, self._next_cycle_ns, 0, True, True)
                        if status != 0:
                            raise RuntimeError(f"Error setting notifier alarm: status {status}")

                        # Block until the notifier alarm fires; False means it was destroyed (end of main loop)
                        if not wait_for_object(notifier):
                            break

                    # Advance the next cycle deadline by one period
                    self._next_cycle_ns += self._period_ns

                # Run logger pre-user code (load inputs from sensors or log file)
                periodic_before_start = RobotController.get_monotonic_time()
                Logger.periodic_before_user()

                # Execute user periodic code and measure its duration
                user_code_start = RobotController.get_monotonic_time()
                self._loop_func()
                user_code_end = RobotController.get_monotonic_time()

                # Note: Logger.periodic_after_user() is commented out due to FMS (Driver Station)
                # compatibility issues during matches. It could raise exceptions when the FPGA
                # time overflows or during specific FMS states. This functionality should be
                # uncommented and tested once a reliable fix is implemented.

                with contextlib.suppress(Exception):  # HACK: Exception work around when in match (FMS Active)
                    # Run logger post-user code (save outputs to log)
                    Logger.periodic_after_user(user_code_end - user_code_start, user_code_start - periodic_before_start)

        except Exception as exc:
            msg = "\n".join(traceback.format_exception(exc))
            Logger.periodic_after_user(0, 0, msg)
            Logger.end()
            raise

    def end_competition(self) -> None:
        """
        Clean up HAL resources at robot shutdown.

        Called by WPILib when the robot transitions to disabled or exits.
        Properly stops and cleans the HAL notifier to release system resources.

        Override in subclasses to add custom shutdown logic, but call super().end_competition() at the end.
        """
        self._watchdog.disable()

        notifier, self._notifier = self._notifier, HAL_kInvalidHandle
        if notifier is not None:
            hal.destroy_notifier(notifier)  # Wakes the main loop, which sees the wait return False
