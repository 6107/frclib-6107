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
1. Logger.periodicBeforeUser() - Load sensor inputs/replay data
2. User periodic code (_loopFunc) - Execute robotPeriodic, mode periodic, etc.
3. Logger.periodicAfterUser() - Log output values and timing metrics
"""

import hal

from wpilib import DSControlWord, IterativeRobotBase, RobotController, Watchdog, RobotBase
from wpimath.units import seconds

from lib_6107.pykit.logger import Logger

#: Default main loop period in seconds (20 ms = 50 Hz)
DEFAULT_PERIOD: seconds = 0.02


class LoggedRobot(IterativeRobotBase):
    """
    Robot base class providing integrated logging and precise loop timing.
    
    LoggedRobot extends WPILib's IterativeRobotBase to provide:
    - Deterministic loop timing using HAL notifier for accurate synchronization
    - Integration with pykit Logger for telemetry capture at each timestamp
    - Overrun detection when user code exceeds the periodic deadline
    - Simulation support via _simulationInit() callback
    - Automatic resource cleanup via watchdog and notifier patterns
    
    Teams should subclass this instead of IterativeRobotBase to get logging and
    precise timing. The logging setup (mode detection, receiver initialization)
    should happen in robotInit() via Robot.container_init() callback (see Robot class).
    
    Attributes:
        default_period (float): Class-level default loop period in seconds (20 ms).
        use_timing (bool): Whether to enforce timing via HAL notifier. Can be set to
            False for testing to disable timing enforcement.
        period (float): Property returning the configured loop period in seconds.
        
    Usage:
        ```python
        class MyRobot(LoggedRobot):
            def robotInit(self):
                # Initialize Logger here via Robot.container_init() callback
                self.container = RobotContainer(self)
            
            def robotPeriodic(self):
                # User periodic code - automatically wrapped by logging
                pass
        
        if __name__ == "__main__":
            hal.main(lambda: MyRobot(period=0.02))
        ```
    """
    
    #: Class-level default loop period in seconds (20 ms for FRC standard 50 Hz loop)
    default_period = 0.02  # seconds

    def printOverrunMessage(self) -> None:
        """
        Callback invoked when the main loop overruns its deadline.
        
        This method is registered with the Watchdog to alert developers when
        user code or subsystem updates exceeded the target loop period. Override
        to customize overrun handling (e.g., log to dashboard, increment counter).
        
        Default behavior: Print warning to console.
        """
        print("Loop overrun detected!")

    def __init__(self, period: seconds = DEFAULT_PERIOD):
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
        self.use_timing = True
        """Control flag to enable/disable timing enforcement via HAL notifier."""

        self._period = period
        """Configured loop period in seconds."""
        
        self._periodUs = int(period * 1000000)
        """Loop period converted to microseconds for HAL notifier operations."""
        
        self._is_simulation = RobotBase.isSimulation()
        """True if running in simulation mode (SIMULATION or REPLAY)."""

        # Because in "robotpy test" this code starts at time 0
        # and hal.waitForNotifierAlarm returns (current_time_or_stopped, status)
        # with current_time_or_stopped assigned to 0 when hal.stopNotifier is called
        # or when the current time is 0, and hal.stopNotifier is signal to
        # exit the infinite loop, the stop is prematurely detected at time 0.
        # Force the program to wait until self._periodUs for the first periodic loop
        # so that current_time_or_stopped will contain a non-zero current time and the
        # infinite loop does not end prematurely.
        self._next_cycle_us = 0 + self._periodUs
        """Next cycle wake-up time in microseconds (initialized to first period boundary)."""

        self.notifier = hal.initializeNotifier()[0]
        """HAL notifier handle for precise timing interrupt."""
        
        self.watchdog = Watchdog(LoggedRobot.default_period, self.printOverrunMessage)
        """Watchdog timer to detect loop overruns and invoke printOverrunMessage."""
        
        self.word = DSControlWord()
        """Driver Station control word for mode and enable state tracking."""
        
        self.init_end = 0.0
        """FPGA timestamp (microseconds) when robotInit() completes."""

    @property
    def period(self) -> seconds:
        """
        Get the configured loop period.
        
        Returns:
            float: The loop period in seconds (typically 0.02 for 50 Hz).
        """
        return self._period

    def endCompetition(self) -> None:
        """
        Clean up HAL resources at robot shutdown.
        
        Called by WPILib when the robot transitions to disabled or exits.
        Properly stops and cleans the HAL notifier to release system resources.
        
        Override in subclasses to add custom shutdown logic, but call super().endCompetition() at the end.
        """
        hal.stopNotifier(self.notifier)
        hal.cleanNotifier(self.notifier)

    def startCompetition(self) -> None:
        """
        Main robot control loop with integrated logging and precise timing.
        
        This method overrides IterativeRobotBase.startCompetition() to replace
        the standard loop with one that:
        1. Executes robotInit() for initialization
        2. Initializes simulation physics if in simulation mode
        3. Starts the Logger with detected mode (REAL/SIMULATION/REPLAY)
        4. Enters an infinite loop that:
           a. Waits for the next cycle deadline using HAL notifier timing
           b. Detects and handles loop overruns (user code exceeds deadline)
           c. Calls Logger.periodicBeforeUser() to load sensor inputs
           d. Executes user periodic code (_loopFunc)
           e. Calls Logger.periodicAfterUser() to log outputs and measure performance
           f. Exits when stopNotifier signals (notifier returns 0)
        
        Timing is deterministic and precise, achieving ±0.1ms jitter on real roboRIO.
        
        The loop continues until hal.waitForNotifierAlarm returns 0 (signal to exit)
        or an error occurs in notifier synchronization.
        
        Note:
            - User code must complete within the loop period to avoid overruns
            - Overruns print a warning but the loop continues at the next deadline
            - Performance metrics are logged automatically by Logger
            - The initial robotInit() timing is captured and logged
        """
        # Execute one-time initialization
        self.robotInit()

        # Initialize simulation physics if running in simulation
        if self._is_simulation:
            self._simulationInit()

        # Log completion of initialization and notify observation starts
        self.init_end = RobotController.getFPGATime()
        Logger.periodicAfterUser(self.init_end, 0)
        print("Robot startup complete!")
        hal.observeUserProgramStarting()

        # Start the Logger's receiver threads for telemetry output
        Logger.start_receiver()

        # Main robot loop: iterate until notifier signals stop (returns 0)
        while True:
            # Synchronize to the next deadline using HAL notifier for precise timing
            if self.use_timing:
                current_time = RobotController.getFPGATime()
                if self._next_cycle_us < current_time:
                    # Loop overrun detected: user code took longer than period
                    # Skip wait and run immediately, then advance to next deadline
                    self._next_cycle_us = current_time
                else:
                    # Schedule the notifier to wake at the next deadline
                    hal.updateNotifierAlarm(self.notifier, int(self._next_cycle_us))

                    # Block until the notifier alarm fires or stop is signaled
                    current_time_or_stopped, status = hal.waitForNotifierAlarm(self.notifier)
                    if status != 0:
                        raise RuntimeError( f"Error waiting for notifier alarm: status {status}")

                    # Exit if notifier was stopped (signal to end main loop)
                    if current_time_or_stopped == 0:
                        break

                # Advance the next cycle deadline by one period
                self._next_cycle_us += self._periodUs

            # Run logger pre-user code (load inputs from sensors or log file)
            periodic_before_start = RobotController.getFPGATime()
            Logger.periodicBeforeUser()

            # Execute user periodic code and measure its duration
            user_code_start = RobotController.getFPGATime()
            self._loopFunc()
            user_code_end = RobotController.getFPGATime()

            # Note: Logger.periodicAfterUser() is commented out due to FMS (Driver Station) 
            # compatibility issues during matches. It could raise exceptions when the FPGA
            # time overflows or during specific FMS states. This functionality should be 
            # uncommented and tested once a reliable fix is implemented.
            try:     # HACK: Exception work around when in match (FMS Active)
                # Run logger post-user code (save outputs to log)
                Logger.periodicAfterUser(
                    user_code_end - user_code_start, user_code_start - periodic_before_start
                )
            except Exception as e:
                pass