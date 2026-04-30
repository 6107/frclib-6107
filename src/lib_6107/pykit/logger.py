"""
Logger Module for Centralized Robot Telemetry Management

This module provides the Logger singleton, which manages all robot telemetry during
operation (real, simulation, and replay modes). It orchestrates the complete logging
pipeline: capturing sensor data, recording user outputs, publishing to dashboards,
and enabling deterministic log replay for analysis.

Key Responsibilities:
- Lifecycle Management: Coordinates start/end of logging across all backends
- Dual-Mode Operation: Handles both real-time logging and log replay scenarios
- Console Capture: Intercepts print() statements and logs them as telemetry
- Pipeline Orchestration: Manages periodic input loading and output publishing
- Performance Tracking: Measures and logs timing metrics for each subsystem
- Dashboard Control: Enables dynamic dashboard inputs during operation

The Logger operates in two distinct modes:
1. NORMAL: Captures live robot data and publishes to receivers (files, NT4, etc.)
2. REPLAY: Loads pre-recorded data from a log file and replays it deterministically

Data Flow (Normal Mode):
    Robot Hardware → periodicBeforeUser() → User Code → periodicAfterUser() → Receivers

Data Flow (Replay Mode):
    Log File → periodicBeforeUser() → User Code (reads replayed inputs) → periodicAfterUser()

All logging is timestamp-synchronized via FPGA clock, enabling precise temporal analysis
and frame-by-frame replay in AdvantageScope or custom analysis tools.
"""

import sys
import threading
import traceback
from typing import Any, Optional

from wpilib import RobotController

from lib_6107.pykit.alertlogger import AlertLogger
from lib_6107.pykit.autolog import AutoLogInputManager, AutoLogOutputManager
from lib_6107.pykit.inputs.loggableds import LoggedDriverStation
from lib_6107.pykit.inputs.loggablepowerdistribution import LoggedPowerDistribution
from lib_6107.pykit.inputs.loggablesystemstats import LoggedSystemStats
from lib_6107.pykit.logdatareceiver import LogDataReceiver
from lib_6107.pykit.logreplaysource import LogReplaySource
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput


class _ConsoleRecorder:
    """
    Internal helper class that intercepts and logs print/error output.
    
    This class acts as a stream wrapper (implementing the file-like interface)
    that captures all output written to stdout/stderr (via print() and sys.stdout/stderr).
    It buffers output until a newline is encountered, then logs each complete line
    as a telemetry entry under "Console/*" for visibility in dashboards.
    
    Design:
    - Dual-stream: Wraps both stdout and stderr independently
    - Non-blocking: Passes through to original stream immediately (doesn't delay)
    - Thread-safe: Uses lock to prevent interleaved writes from multiple threads
    - Graceful degradation: Catches exceptions to prevent logging errors from breaking I/O
    
    Attributes:
        orig: The original stdout/stderr stream to pass writes through to
        lock: Threading lock for synchronizing access to shared buffer
        buffer: Accumulator for characters until newline is encountered
    """
    
    def __init__(self, orig):
        """
        Initialize the console recorder wrapping an original stream.
        
        Args:
            orig: The original stdout or stderr file object to wrap
        """
        self.orig = orig
        self.lock = threading.Lock()
        self.buffer = ""

    def write(self, s):
        """
        Write a string, capturing it for logging while passing through to original stream.
        
        This method implements the file-like write() interface. It:
        1. Acquires a lock for thread safety
        2. Writes immediately to the original stream (non-blocking)
        3. Buffers the string locally
        4. When a newline is encountered, logs each complete line separately
        5. Gracefully handles any I/O or logging errors
        
        Args:
            s (str): The string to write. May contain zero or more newlines.
            
        Side Effects:
            - Writes to self.orig stream immediately
            - Logs lines to Logger.recordOutput("Console", line) when complete
            - Updates self.buffer with incomplete lines
        """
        try:
            with self.lock:
                # always write through to original stream
                self.orig.write(s)
                try:
                    self.orig.flush()
                except (OSError, ValueError):
                    # I/O errors or writing to a closed stream
                    pass
                # buffer until newline then record each line
                self.buffer += s
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    try:
                        # Logger may not yet be initialized when class is defined; reference at runtime
                        Logger.recordOutput("Console", line)
                    except (AttributeError, RuntimeError, ValueError):
                        # Logger may not be ready or the logging backend raised an error
                        pass
        except (OSError, ValueError, RuntimeError):
            # Locking errors, I/O errors, or value errors from stream operations
            pass

    def flush(self):
        """
        Flush any buffered output and the underlying stream.
        
        Ensures that any partial lines in the buffer are logged before flushing
        the underlying stream. This is called by Python's I/O layer at appropriate
        times (e.g., when sys.stdout.flush() is explicitly called).
        
        Side Effects:
            - Logs any buffered partial line
            - Calls flush() on the original stream
        """
        if self.buffer:
            Logger.recordOutput("Console", self.buffer)
            self.buffer = ""
        try:
            self.orig.flush()
        except (OSError, ValueError):
            # I/O errors or writing to a closed stream
            pass


class Logger:
    """
    Centralized singleton for managing robot telemetry in all operating modes.
    
    Logger orchestrates the complete telemetry pipeline: capturing inputs from
    hardware/logs, executing user code, publishing outputs, and coordinating
    all data receivers (file writers, NetworkTables publishers, etc.).
    
    The Logger operates in two primary modes:
    - NORMAL: Live logging of real robot during operation
    - REPLAY: Deterministic playback of pre-recorded log file
    
    Mode Detection:
    If Logger.replaySource is set (non-None), replay mode is active. Otherwise,
    normal logging mode is active.
    
    Data Architecture:
    - entry: The current log table (master timestamp + all sensor inputs)
    - outputTable: Writable subtable for user code to log outputs (RealOutputs/ReplayOutputs)
    - data_receivers: List of backends to publish each complete entry to
    
    Lifecycle:
    1. start() - Initialize logging, set up receivers, begin capture
    2. periodicBeforeUser() - Load inputs, update dashboard controls (50 Hz)
    3. [User Code Executes] - Robot code reads inputs, updates subsystems
    4. periodicAfterUser() - Publish outputs, measure timing, send to receivers
    5. end() - Flush remaining data, shutdown receivers, cleanup
    
    Performance Metrics (logged automatically):
    - Logger/EntryUpdateMS: Time to load/update sensor inputs
    - Logger/DriverStationMS: Time to sync Driver Station state
    - Logger/DashboardInputsMS: Time to update dashboard choosers
    - Logger/AutoLogOutputMS: Time to publish auto-logged members
    - Logger/AlertLoggerMS: Time to process alert system
    - LoggedRobot/UserCodeMS: Time for user periodic methods
    - LoggedRobot/LogPeriodicMS: Total time in logger periodic methods
    - LoggedRobot/FullCycleMS: Total time for entire cycle
    
    Thread Safety:
    - Not thread-safe; all methods assume single-threaded access from robot main loop
    - Console recorder uses internal locking only
    
    Class Attributes:
        replaySource (LogReplaySource | None): Source of replay data. None = normal mode.
        running (bool): True when logging is active (between start() and end())
        cycleCount (int): Number of robot periodic cycles executed
        entry (LogTable): Root log table for current timestamp
        outputTable (LogTable): Subtable where user code logs outputs
        metadata (dict): Static metadata entries (robot version, team ID, etc.)
        checkConsole (bool): Whether to capture console output (default True)
        data_receivers (list[LogDataReceiver]): Backends for publishing entries
        dashboardInputs (list[LoggedNetworkInput]): Dashboard choosers/inputs
    """

    replaySource: Optional[LogReplaySource] = None
    """
    The replay source providing pre-recorded log data.
    - None (default): Normal logging mode
    - LogReplaySource: Replay mode with data from log file
    """
    
    running: bool = False
    """True when logging is active (Logger.start() has been called and not yet end())."""
    
    cycleCount: int = 0
    """Count of robot periodic cycles executed. Incremented in periodicBeforeUser()."""
    
    entry: LogTable = LogTable(0)
    """Root LogTable for the current timestamp. Contains all inputs and outputs."""
    
    outputTable: LogTable = LogTable(0)
    """Subtable where user code logs outputs. Points to RealOutputs or ReplayOutputs."""
    
    metadata: dict[str, str] = {}
    """Static metadata entries (e.g., robot version, team number, match info)."""
    
    checkConsole: bool = True
    """Enable/disable console output capture. Set before Logger.start() to control."""

    # Internal fields for console capturing
    _orig_stdout: Optional[Any] = None
    _orig_stderr: Optional[Any] = None
    _console_wrapped: bool = False
    _console_recorder_stdout: Optional[Any] = None
    _console_recorder_stderr: Optional[Any] = None

    data_receivers: list[LogDataReceiver] = []
    """List of data receivers that process each LogTable entry."""
    
    dashboardInputs: list[LoggedNetworkInput] = []
    """List of dashboard inputs (choosers, etc.) updated periodically."""

    @classmethod
    def setReplaySource(cls, replaySource: LogReplaySource):
        """
        Set the replay source to enable replay mode.
        
        Call this before Logger.start() to activate replay mode. The provided
        source will be used to load pre-recorded log data for deterministic playback.

        Args:
            replaySource (LogReplaySource): Source of pre-recorded log data.
                If None, replay mode is disabled.
        """
        cls.replaySource = replaySource

    @classmethod
    def isReplay(cls) -> bool:
        """
        Check if the logger is in replay mode.
        
        Returns:
            bool: True if replaying from a log file, False if logging normal operation.
        """
        return cls.replaySource is not None

    @classmethod
    def recordOutput(cls, key: str, value: Any, unit: Optional[str] = None):
        """
        Record an output value to the log table.
        
        This is the primary method subsystems and user code use to publish telemetry.
        Values are stored in the outputTable and sent to receivers each cycle.
        
        No-op in replay mode (outputs are replayed from log file, not recorded).
        Exceptions during logging are silently caught to prevent logging errors from
        crashing robot code.

        Args:
            key (str): The logging key (e.g., "Drivetrain/speed"). Supports hierarchical
                paths with "/" separators. Ideally PascalCase for consistency.
            value (Any): The value to log. Supported types: bool, int, float, str,
                bytes, and lists of primitives. Type is inferred from value.
            unit (str, optional): Physical unit string (e.g., "m/s", "RPM", "degrees").
                Used for dashboard visualization. Defaults to None.
        """
        if cls.running:
            try:
                cls.outputTable.put(key, value, unit=unit)
            except Exception as _e:
                pass

    @classmethod
    def recordMetadata(cls, key: str, value: str):
        """
        Record static metadata for this logging session.
        
        Metadata is logged once at startup and is useful for session context:
        robot version, team number, match type/number, game data, etc.
        
        No-op in replay mode (metadata is from the replayed log, not updated).
        
        Call before Logger.start() for best results.

        Args:
            key (str): Metadata key (e.g., "RobotVersion", "TeamNumber")
            value (str): Metadata value as string
        """
        if not cls.isReplay():
            cls.metadata[key] = value

    @classmethod
    def processInputs(cls, prefix: str, inputs):
        """
        Process an I/O object, handling both logging and replay scenarios.
        
        This utility method provides a simple way to handle inputs uniformly:
        - Normal mode: Calls inputs.to_log() to save input state to log table
        - Replay mode: Calls inputs.from_log() to restore input state from log table
        
        This reduces code duplication in subsystems that need to log I/O state
        (e.g., motors, sensors, PDP reads).

        Args:
            prefix (str): Prefix for log entries (e.g., "/Drivetrain")
            inputs: An input object with to_log(table, prefix) and from_log(table, prefix) methods
        """
        if cls.running:
            if cls.isReplay():
                inputs.from_log(cls.entry, prefix)
            else:
                inputs.to_log(cls.entry, prefix)

    @classmethod
    def addDataReciever(cls, reciever: LogDataReceiver):
        """
        Register a data receiver to process log entries each cycle.
        
        Data receivers are backends that consume LogTable entries and handle them
        according to their specific needs (file writing, network streaming, etc.).
        
        Examples: WPILOGWriter (USB drive), NT4Publisher (NetworkTables), etc.
        
        Call before Logger.start() so receivers are initialized at startup.

        Args:
            reciever (LogDataReceiver): A receiver implementing the LogDataReceiver interface
        """
        cls.data_receivers.append(reciever)

    @classmethod
    def registerDashboardInput(cls, dashboardInput: LoggedNetworkInput):
        """
        Register a dashboard input (chooser, button, etc.) for periodic updates.
        
        Dashboard inputs are updated each cycle to reflect changes made by operators
        on the driver station or dashboard. Examples: auto mode chooser, test selector.

        Args:
            dashboardInput (LoggedNetworkInput): A dashboard input with periodic() method
        """
        cls.dashboardInputs.append(dashboardInput)

    @classmethod
    def start(cls):
        """
        Initialize and start the logging system.
        
        This method:
        1. Activates the running flag
        2. Initializes replay source if in replay mode
        3. Sets up output subtables (RealOutputs or ReplayOutputs)
        4. Records metadata entries
        5. Wraps console output for capture (optional)
        6. Redirects FPGA timestamp source to Logger.getTimestamp()
        7. Performs initial input loading via periodicBeforeUser()
        
        Call this once during robotInit() or equivalent startup routine.
        Should be called before any recordOutput() calls.
        
        Side Effects:
            - Sets cls.running = True
            - May wrap sys.stdout/sys.stderr (if checkConsole=True)
            - Calls start() on all registered data receivers
            - Loads initial sensor inputs
        """
        if not cls.running:
            cls.running = True
            cls.cycleCount = 0
            print("Logger started")

            if cls.isReplay():
                rs = cls.replaySource
                if rs is not None:
                    rs.start()

            if not cls.isReplay():
                print("Logger in normal logging mode")
                cls.outputTable = cls.entry.get_subtable("RealOutputs")
            else:
                print("Logger in replay mode")
                cls.outputTable = cls.entry.get_subtable("ReplayOutputs")

            metadataTable = cls.entry.get_subtable(
                "ReplayMetadata" if cls.isReplay() else "RealMetadata"
            )

            for key, value in cls.metadata.items():
                metadataTable.put(key, value)

            # Setup console capture to record prints under "Console"
            if cls.checkConsole and not cls._console_wrapped:
                try:
                    cls._orig_stdout = sys.stdout
                    cls._orig_stderr = sys.stderr
                    cls._console_recorder_stdout = _ConsoleRecorder(cls._orig_stdout)
                    cls._console_recorder_stderr = _ConsoleRecorder(cls._orig_stderr)
                    sys.stdout = cls._console_recorder_stdout
                    sys.stderr = cls._console_recorder_stderr
                    cls._console_wrapped = True
                except (AttributeError, RuntimeError, TypeError):
                    # If sys streams are missing or recorder construction failed
                    pass

            RobotController.setTimeSource(cls.getTimestamp)
            cls.periodicBeforeUser()

    @classmethod
    def start_receiver(cls):
        """
        Start all registered data receivers.
        
        This method is called by LoggedRobot after the main loop starts running.
        It allows receivers to prepare for accepting log entries (e.g., open files,
        establish network connections, allocate buffers).
        
        Exceptions during receiver startup are logged but don't crash the robot.
        """
        for receiver in cls.data_receivers:
            try:
                receiver.start()

            except (AttributeError, RuntimeError) as e:
                print(f"pykit.logger.startReciever: Failed to start receiver '{receiver}' {e}")
                error_msg = traceback.format_exc()
                print(f"pykit.logger.startReciever: {error_msg}")

    @classmethod
    def end(cls):
        """
        Shutdown the logging system and all data receivers.
        
        This method:
        1. Stops live logging (sets running=False)
        2. Restores console streams if wrapped (sys.stdout/stderr)
        3. Ends replay source if active
        4. Restores RobotController time source to FPGA clock
        5. Calls end() on all data receivers for cleanup/flushing
        
        Call this during robot shutdown or when transitioning out of teleop.
        Ensures all buffered data is flushed before shutdown completes.
        """
        if cls.running:
            cls.running = False
            print("Logger ended")

            # Restore console if we wrapped it
            if cls._console_wrapped:
                try:
                    if cls._orig_stdout is not None:
                        sys.stdout = cls._orig_stdout
                    if cls._orig_stderr is not None:
                        sys.stderr = cls._orig_stderr
                except (AttributeError, RuntimeError):
                    # Restoring original streams failed
                    pass
                cls._console_wrapped = False
                cls._console_recorder_stdout = None
                cls._console_recorder_stderr = None
                cls._orig_stdout = None
                cls._orig_stderr = None

            if cls.isReplay():
                rs = cls.replaySource
                if rs is not None:
                    rs.end()

            RobotController.setTimeSource(RobotController.getFPGATime)
            for reciever in cls.data_receivers:
                reciever.end()

    @classmethod
    def getTimestamp(cls) -> int:
        """
        Get the current timestamp for the logging system.
        
        In normal mode: Returns current FPGA time (microseconds since roboRIO boot).
        In replay mode: Returns the timestamp of the current log entry being played back.
        
        This method is set as the time source for RobotController during Logger.start(),
        so all FPGA timestamps reflect the replay time during log playback.

        Returns:
            int: Timestamp in microseconds. In FPGA units after roboRIO boot,
                or the log entry timestamp during replay.
        """
        if cls.isReplay():
            return cls.entry.getTimestamp()
        # RobotController.getFPGATime may be untyped; ensure int
        return int(RobotController.getFPGATime())

    @classmethod
    def periodicBeforeUser(cls):
        """
        Load inputs and prepare for user code execution (called before robotPeriodic).
        
        This method is called at the beginning of each robot periodic cycle (~50 Hz):
        1. Increments the cycle counter
        2. Updates the timestamp (from FPGA clock or replay log)
        3. In replay mode: loads next timestamped entry from log
        4. Simulates Driver Station state (in replay mode)
        5. Updates dashboard inputs (choosers, buttons, etc.)
        6. Logs performance metrics (timing for each phase)
        
        In normal mode: Reads current FPGA time and prepares for sensor input capture.
        In replay mode: Loads next pre-recorded entry from log file and aborts if log ends.
        
        Called automatically by Logger.start() and by LoggedRobot each cycle.
        
        Side Effects:
            - Increments cls.cycleCount
            - Updates cls.entry timestamp
            - Loads new data from replay source (if in replay mode)
            - Logs performance timing metrics
            - May call SystemExit(0) if end of replay is reached
        """
        cls.cycleCount += 1
        if cls.running:
            entryUpdateStart = RobotController.getFPGATime()
            if not cls.isReplay():
                # Normal mode: set current timestamp
                cls.entry.setTimestamp(RobotController.getFPGATime())
            else:
                # Replay mode: load next timestamped data from log
                rs = cls.replaySource
                if rs is None or not rs.updateTable(cls.entry):
                    print("End of replay reached")
                    if cls.cycleCount == 1:
                        print(
                            "[ERROR] This robot did not start properly, is the replay logfile from PyKit?"
                        )
                    else:
                        cls.end()
                    raise SystemExit(0)

            dsStart = RobotController.getFPGATime()
            # In replay mode, simulate driver station inputs from log
            if cls.isReplay():
                LoggedDriverStation.load_from_table(
                    cls.entry.get_subtable("DriverStation")
                )
            dashboardInputStart = RobotController.getFPGATime()

            # Update dashboard inputs (choosers, etc.)
            for dashInput in cls.dashboardInputs:
                dashInput.periodic()

            dashboardInputEnd = RobotController.getFPGATime()

            cls.recordOutput(
                "Logger/EntryUpdateMS", (dsStart - entryUpdateStart) / 1000.0
            )
            if cls.isReplay():
                cls.recordOutput(
                    "Logger/DriverStationMS", (dashboardInputStart - dsStart) / 1000.0
                )
            cls.recordOutput(
                "Logger/DashboardInputsMS",
                (dashboardInputEnd - dashboardInputStart) / 1000.0,
            )

    @classmethod
    def periodicAfterUser(cls, userCodeLength: int, periodicBeforeLength: int):
        """
        Finalize log entry and send to receivers (called after robotPeriodic).
        
        This method completes the logging cycle by:
        1. Saving Driver Station state (normal mode only)
        2. Saving system stats (battery voltage, brownout, etc.)
        3. Publishing all auto-logged members via AutoLogOutputManager
        4. Processing alerts via AlertLogger
        5. Publishing all auto-logged inputs via AutoLogInputManager (normal mode)
        6. Logging detailed performance metrics for analysis
        7. Sending the complete LogTable to all registered data receivers
        
        Performance Metrics Recorded:
        - Logger/DriverStationMS: Time to save/load DS state
        - Logger/SystemStatsMS: Time to capture battery/system info
        - Logger/AutoLogOutputMS: Time for auto-logged output publishing
        - Logger/AlertLoggerMS: Time for alert processing
        - LoggedRobot/UserCodeMS: User periodic execution time
        - LoggedRobot/LogPeriodicMS: Total logging overhead
        - LoggedRobot/FullCycleMS: Total cycle time (overhead + user code)
        
        Called automatically by LoggedRobot after each periodic cycle.

        Args:
            userCodeLength (int): Execution time of user code in microseconds
                (from periodicBeforeUser start to end of _loopFunc)
            periodicBeforeLength (int): Execution time of periodicBeforeUser
                in microseconds
                
        Side Effects:
            - Records performance metrics to outputTable
            - Sends complete LogTable to all data receivers
            - Updates internal timing state
        """
        if cls.running:
            dsStart = RobotController.getFPGATime()
            # In normal mode, save driver station state to log
            if not cls.isReplay():
                LoggedDriverStation.save_to_table(cls.entry.get_subtable("DriverStation"))
            systemStart = RobotController.getFPGATime()
            if not cls.isReplay():
                LoggedSystemStats.save_to_table(cls.entry.get_subtable("SystemStats"))
                LoggedPowerDistribution.get_instance().save_to_table(
                    cls.entry.get_subtable("PowerDistribution")
                )
            autoLogStart = RobotController.getFPGATime()
            # Publish all auto-logged outputs
            AutoLogOutputManager.publish_all(cls.outputTable)
            alertLogStart = RobotController.getFPGATime()
            AlertLogger.periodic(cls.outputTable)
            alertLogEnd = RobotController.getFPGATime()
            if not cls.isReplay():
                cls.recordOutput(
                    "Logger/DriverStationMS", (systemStart - dsStart) / 1000.0
                )
                cls.recordOutput(
                    "Logger/SystemStatsMS", (autoLogStart - systemStart) / 1000.0
                )
                # Log all auto-logged inputs
                for logged_input in AutoLogInputManager.getInputs():
                    logged_input.to_log(
                        cls.entry.get_subtable("/"),
                        "/" + logged_input.__class__.__name__,
                    )

            cls.recordOutput(
                "Logger/AutoLogOutputMS", (alertLogStart - autoLogStart) / 1000.0
            )
            cls.recordOutput(
                "Logger/AlertLoggerMS", (alertLogEnd - alertLogStart) / 1000.0
            )
            cls.recordOutput("LoggedRobot/UserCodeMS", userCodeLength / 1000.0)
            periodicAfterLength = alertLogEnd - dsStart
            cls.recordOutput(
                "LoggedRobot/LogPeriodicMS",
                (periodicBeforeLength + periodicAfterLength) / 1000.0,
            )
            cls.recordOutput(
                "LoggedRobot/FullCycleMS",
                (periodicBeforeLength + userCodeLength + periodicAfterLength) / 1000.0,
            )

            # Send log table to all receivers (file writer, NetworkTables, etc.)
            for reciever in cls.data_receivers:
                reciever.put_table(LogTable.clone(cls.entry))