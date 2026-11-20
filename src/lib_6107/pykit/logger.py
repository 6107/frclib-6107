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
Logger Module for Centralized Robot Telemetry Management

This module provides the Logger singleton, which manages all robot telemetry during
operation (real, simulation, and replay modes). It orchestrates the complete logging
pipeline: capturing sensor data, recording user outputs, publishing to Elastic and AdvantageScope,
and enabling deterministic log replay for analysis.

Key Responsibilities:
- Lifecycle Management: Coordinates start/end of logging across all backends
- Dual-Mode Operation: Handles both real-time logging and log replay scenarios
- Console Capture: Intercepts print() statements and logs them as telemetry
- Pipeline Orchestration: Manages periodic input loading and output publishing
- Performance Tracking: Measures and logs timing metrics for each subsystem
- Tunable Inputs: Enables operator-editable tunable inputs (set from Elastic) during operation

The Logger operates in two distinct modes:
1. NORMAL: Captures live robot data and publishes to receivers (files, NT4, etc.)
2. REPLAY: Loads pre-recorded data from a log file and replays it deterministically

Data Flow (Normal Mode):
    Robot Hardware → periodic_before_user() → User Code → periodic_after_user() → Receivers

Data Flow (Replay Mode):
    Log File → periodic_before_user() → User Code (reads replayed inputs) → periodic_after_user()

All logging is timestamp-synchronized via the monotonic robot clock (nanoseconds), enabling precise temporal analysis
and frame-by-frame replay in AdvantageScope or custom analysis tools.
"""

import atexit
import contextlib
import sys
import threading
import traceback
from typing import Any

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
    as a telemetry entry under "Console/*" for visibility in Elastic and AdvantageScope.

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
            - Logs lines to Logger.record_output("Console", line) when complete
            - Updates self.buffer with incomplete lines
        """
        try:
            with self.lock:
                # always write through to original stream
                self.orig.write(s)
                with contextlib.suppress(OSError, ValueError):
                    self.orig.flush()

                # buffer until newline then record each line
                self.buffer += s
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    with contextlib.suppress(AttributeError, RuntimeError, ValueError):
                        # Logger may not yet be initialized when class is defined; reference at runtime
                        Logger.record_output("Console", line)

        except OSError, ValueError, RuntimeError:
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
            Logger.record_output("Console", self.buffer)
            self.buffer = ""

        with contextlib.suppress(OSError, ValueError):
            self.orig.flush()


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
    If Logger.replay_source is set (non-None), replay mode is active. Otherwise,
    normal logging mode is active.

    Data Architecture:
    - entry: The current log table (master timestamp + all sensor inputs)
    - output_table: Writable subtable for user code to log outputs (RealOutputs/ReplayOutputs)
    - data_receivers: List of backends to publish each complete entry to

    Lifecycle:
    1. start() - Initialize logging, set up receivers, begin capture
    2. periodic_before_user() - Load inputs, update tunable inputs (50 Hz)
    3. [User Code Executes] - Robot code reads inputs, updates subsystems
    4. periodic_after_user() - Publish outputs, measure timing, send to receivers
    5. end() - Flush remaining data, shutdown receivers, cleanup

    Performance Metrics (logged automatically):
    - Logger/EntryUpdateMS: Time to load/update sensor inputs
    - Logger/DriverStationMS: Time to sync Driver Station state
    - Logger/TunableInputsMS: Time to update tunable inputs (choosers, edit boxes, etc.)
    - Logger/AutoLogOutputMS: Time to publish auto-logged members
    - Logger/AlertLoggerMS: Time to process alert system
    - LoggedRobot/UserCodeMS: Time for user periodic methods
    - LoggedRobot/LogPeriodicMS: Total time in logger periodic methods
    - LoggedRobot/FullCycleMS: Total time for entire cycle

    Thread Safety:
    - Not thread-safe; all methods assume single-threaded access from robot main loop
    - Console recorder uses internal locking only

    Class Attributes:
        replay_source (LogReplaySource | None): Source of replay data. None = normal mode.
        running (bool): True when logging is active (between start() and end())
        cycle_count (int): Number of robot periodic cycles executed
        entry (LogTable): Root log table for current timestamp
        output_table (LogTable): Subtable where user code logs outputs
        metadata (dict): Static metadata entries (robot version, team ID, etc.)
        check_console (bool): Whether to capture console output (default True)
        data_receivers (list[LogDataReceiver]): Backends for publishing entries
        tunable_inputs (list[LoggedNetworkInput]): Tunable-backed choosers/inputs
    """

    replay_source: LogReplaySource | None = None
    """
    The replay source providing pre-recorded log data.
    - None (default): Normal logging mode
    - LogReplaySource: Replay mode with data from log file
    """

    running: bool = False
    """True when logging is active (Logger.start() has been called and not yet end())."""

    cycle_count: int = 0
    """Count of robot periodic cycles executed. Incremented in periodic_before_user()."""

    entry: LogTable = LogTable(0)
    """Root LogTable for the current timestamp. Contains all inputs and outputs."""

    output_table: LogTable = LogTable(0)
    """Subtable where user code logs outputs. Points to RealOutputs or ReplayOutputs."""

    metadata: dict[str, str] = {}
    """Static metadata entries (e.g., robot version, team number, match info)."""

    check_console: bool = True
    """Enable/disable console output capture. Set before Logger.start() to control."""

    # Internal fields for console capturing
    _orig_stdout: Any | None = None
    _orig_stderr: Any | None = None
    _console_wrapped: bool = False
    _console_recorder_stdout: Any | None = None
    _console_recorder_stderr: Any | None = None

    data_receivers: list[LogDataReceiver] = []
    """List of data receivers that process each LogTable entry."""

    tunable_inputs: list[LoggedNetworkInput] = []
    """List of tunable inputs (choosers, etc.) updated periodically."""

    @classmethod
    def set_replay_source(cls, replay_source: LogReplaySource):
        """
        Set the replay source to enable replay mode.

        Call this before Logger.start() to activate replay mode. The provided
        source will be used to load pre-recorded log data for deterministic playback.

        Args:
            replay_source (LogReplaySource): Source of pre-recorded log data.
                If None, replay mode is disabled.
        """
        cls.replay_source = replay_source

    @classmethod
    def is_replay(cls) -> bool:
        """
        Check if the logger is in replay mode.

        Returns:
            bool: True if replaying from a log file, False if logging normal operation.
        """
        return cls.replay_source is not None

    @classmethod
    def record_output(cls, key: str, value: Any, unit: str | None = None):
        """
        Record an output value to the log table.

        This is the primary method subsystems and user code use to publish telemetry.
        Values are stored in the output_table and sent to receivers each cycle.

        No-op in replay mode (outputs are replayed from log file, not recorded).
        Exceptions during logging are silently caught to prevent logging errors from
        crashing robot code.

        Args:
            key (str): The logging key (e.g., "Drivetrain/speed"). Supports hierarchical
                paths with "/" separators. Ideally PascalCase for consistency.
            value (Any): The value to log. Supported types: bool, int, float, str,
                bytes, and lists of primitives. Type is inferred from value.
            unit (str, optional): Physical unit string (e.g., "m/s", "RPM", "degrees").
                Used for Elastic visualization. Defaults to None.
        """
        if cls.running:
            with contextlib.suppress(AttributeError, RuntimeError, ValueError):
                cls.output_table.put(key, value, unit=unit)

    @classmethod
    def record_metadata(cls, key: str, value: str):
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
        if not cls.is_replay():
            cls.metadata[key] = value

    @classmethod
    def process_inputs(cls, key: str, inputs):
        """
        Process an I/O object, handling both logging and replay scenarios.

        This utility method provides a simple way to handle inputs uniformly:
        - Normal mode: Calls inputs.to_log() to save input state to log table
        - Replay mode: Calls inputs.from_log() to restore input state from log table

        This reduces code duplication in subsystems that need to log I/O state
        (e.g., motors, sensors, PDP reads).

        Args:
            key (str): Prefix for log entries (e.g., "/Drivetrain")
            inputs: An input object with to_log(table, key) and from_log(table, key) methods
        """
        if cls.running:
            if cls.is_replay():
                inputs.from_log(cls.entry, key)
            else:
                inputs.to_log(cls.entry, key)

    @classmethod
    def add_data_receiver(cls, receiver: LogDataReceiver):
        """
        Register a data receiver to process log entries each cycle.

        Data receivers are backends that consume LogTable entries and handle them
        according to their specific needs (file writing, network streaming, etc.).

        Examples: WPILOGWriter (USB drive), NT4Publisher (NetworkTables), etc.

        Call before Logger.start() so receivers are initialized at startup.

        Args:
            receiver (LogDataReceiver): A receiver implementing the LogDataReceiver interface
        """
        cls.data_receivers.append(receiver)

    @classmethod
    def register_tunable_input(cls, tunable_input: LoggedNetworkInput):
        """
        Register a tunable-backed input (chooser, edit box, button, etc.) for periodic updates.

        Tunable inputs are updated each cycle to reflect changes made by operators in
        Elastic (published through ``tunables`` under ``/Tunables``). Examples: auto mode
        chooser, test selector.

        Args:
            tunable_input (LoggedNetworkInput): A tunable input with a periodic() method
        """
        cls.tunable_inputs.append(tunable_input)

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
        6. Sets the RobotController time source (Logger.get_timestamp() in replay mode,\n           RobotController.get_monotonic_time() otherwise)
        7. Performs initial input loading via periodic_before_user()

        Call this once during robot_init() or equivalent startup routine.
        Should be called before any record_output() calls.

        Side Effects:
            - Sets cls.running = True
            - May wrap sys.stdout/sys.stderr (if check_console=True)
            - Calls start() on all registered data receivers
            - Loads initial sensor inputs
        """
        if not cls.running:
            cls.running = True
            cls.cycle_count = 0

            if cls.is_replay():
                rs = cls.replay_source
                if rs is not None:
                    rs.start()

            if not cls.is_replay():
                print("Logger in normal logging mode")
                cls.output_table = cls.entry.get_sub_table("RealOutputs")
            else:
                print("Logger in replay mode")
                cls.output_table = cls.entry.get_sub_table("ReplayOutputs")

            metadata_table = cls.entry.get_sub_table("ReplayMetadata" if cls.is_replay() else "RealMetadata")

            for key, value in cls.metadata.items():
                metadata_table.put(key, value)

            # Setup console capture to record prints under "Console"
            if cls.check_console and not cls._console_wrapped:
                try:
                    cls._orig_stdout = sys.stdout
                    cls._orig_stderr = sys.stderr
                    cls._console_recorder_stdout = _ConsoleRecorder(cls._orig_stdout)
                    cls._console_recorder_stderr = _ConsoleRecorder(cls._orig_stderr)
                    sys.stdout = cls._console_recorder_stdout
                    sys.stderr = cls._console_recorder_stderr
                    cls._console_wrapped = True
                except AttributeError, RuntimeError, TypeError:
                    # If sys streams are missing or recorder construction failed
                    pass

            # Update controller to use our timestamp. Needed as part of playback control
            RobotController.set_time_source(
                cls.get_timestamp if cls.is_replay() else RobotController.get_monotonic_time
            )
            # Start first periodic cycle
            cls.periodic_before_user()

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
        4. Restores RobotController time source to RobotController.get_monotonic_time
        5. Calls end() on all data receivers for cleanup/flushing

        Call this during robot shutdown or when transitioning out of teleop.
        Ensures all buffered data is flushed before shutdown completes.
        """
        running, cls.running = cls.running, False
        if running:
            print("Logger ended")

            # Restore console if we wrapped it
            if cls._console_wrapped:
                try:
                    if cls._orig_stdout is not None:
                        sys.stdout = cls._orig_stdout
                    if cls._orig_stderr is not None:
                        sys.stderr = cls._orig_stderr
                except AttributeError, RuntimeError:
                    # Restoring original streams failed
                    pass
                cls._console_wrapped = False
                cls._console_recorder_stdout = None
                cls._console_recorder_stderr = None
                cls._orig_stdout = None
                cls._orig_stderr = None

            if cls.is_replay():
                rs = cls.replay_source
                if rs is not None:
                    rs.end()

            RobotController.set_time_source(RobotController.get_monotonic_time)
            for receiver in cls.data_receivers:
                receiver.end()

    @classmethod
    def get_timestamp(cls) -> int:
        """
        Get the current timestamp for the logging system.

        In normal mode: Returns RobotController.get_monotonic_time() (nanoseconds).
        In replay mode: Returns the timestamp of the current log entry being played back.

        This method is set as the time source for RobotController during Logger.start() in replay mode,
        so robot timestamps reflect the replay time during log playback.

        Returns:
            int: Timestamp in nanoseconds: the monotonic robot time in normal mode,
                or the log entry timestamp during replay.
        """
        if cls.is_replay():
            return cls.entry.get_timestamp()

        return RobotController.get_monotonic_time()

    @classmethod
    def periodic_before_user(cls):
        """
        Load inputs and prepare for user code execution (called before robot_periodic).

        This method is called at the beginning of each robot periodic cycle (~50 Hz):
        1. Increments the cycle counter
        2. Updates the timestamp (from the monotonic robot clock or replay log)
        3. In replay mode: loads next timestamped entry from log
        4. Simulates Driver Station state (in replay mode)
        5. Updates tunable inputs (choosers, buttons, etc.)
        6. Logs performance metrics (timing for each phase)

        In normal mode: Reads the current monotonic time and prepares for sensor input capture.
        In replay mode: Loads next pre-recorded entry from log file and aborts if log ends.

        Called automatically by Logger.start() and by LoggedRobot each cycle.

        Side Effects:
            - Increments cls.cycle_count
            - Updates cls.entry timestamp
            - Loads new data from replay source (if in replay mode)
            - Logs performance timing metrics
            - May call SystemExit(0) if end of replay is reached
        """
        cls.cycle_count += 1
        if cls.running:
            entry_update_start = RobotController.get_monotonic_time()

            rs = cls.replay_source
            ds_start = RobotController.get_monotonic_time()

            if not cls.is_replay() or rs is None:
                # Normal mode: set current timestamp
                cls.entry.timestamp = ds_start

            elif not rs.update_table(cls.entry):
                print("End of replay reached")

                if cls.cycle_count == 1:
                    print("[ERROR] This robot did not start properly, is the replay logfile from PyKit?")
                else:
                    cls.end()

                raise SystemExit(0)

            # In replay mode, simulate driver station inputs from log
            if cls.is_replay():
                LoggedDriverStation.replay_from_log(cls.entry.get_sub_table("DriverStation"))

            tunable_input_start = RobotController.get_monotonic_time()

            # Update tunable inputs (choosers, etc.)
            for tunable_input in cls.tunable_inputs:
                tunable_input.periodic()

            tunable_input_end = RobotController.get_monotonic_time()

            cls.record_output("Logger/EntryUpdateMS", (ds_start - entry_update_start) / 1_000_000.0)

            if cls.is_replay():
                cls.record_output("Logger/DriverStationMS", (tunable_input_start - ds_start) / 1_000_000.0)

            cls.record_output("Logger/TunableInputsMS", (tunable_input_end - tunable_input_start) / 1_000_000.0)

    @classmethod
    def periodic_after_user(cls, user_code_length: int, periodic_before_length: int):
        """
        Finalize log entry and send to receivers (called after robot_periodic).

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
            user_code_length (int): Execution time of user code in nanoseconds
                (from periodic_before_user start to end of _loop_func)
            periodic_before_length (int): Execution time of periodic_before_user
                in nanoseconds

        Side Effects:
            - Records performance metrics to output_table
            - Sends complete LogTable to all data receivers
            - Updates internal timing state
        """
        if cls.running:
            # TODO: If we support an akit type 'ConduitAPI', need to grab it here..  See akit Logger() for more info

            ds_start = RobotController.get_monotonic_time()

            # In normal mode, save driver station state to log
            if not cls.is_replay():
                LoggedDriverStation.save_to_log(cls.entry.get_sub_table("DriverStation"))

            system_start = RobotController.get_monotonic_time()

            if not cls.is_replay():
                LoggedSystemStats.save_to_table(cls.entry.get_sub_table("SystemStats"))
                logged_power = LoggedPowerDistribution.get_instance()
                if logged_power is not None:
                    logged_power.save_to_table(cls.entry.get_sub_table("PowerDistribution"))

            # TODO: If we have 3rd party loggers (Rev/CTRE) save them here.  See akit for an example

            # Update automatic outputs from user code
            auto_log_start = RobotController.get_monotonic_time()
            AutoLogOutputManager.publish_all(cls.output_table)

            alert_log_start = RobotController.get_monotonic_time()
            AlertLogger.periodic(cls.output_table)
            alert_log_end = RobotController.get_monotonic_time()

            # TODO: If we have a radio logger, get info. See akit for an example
            # TODO: If we support a different console loggers, get info. See akit for an example
            # TODO: If we support a python GC statistics logger, get info. See akit for an example

            # Now record timing data
            if not cls.is_replay():
                cls.record_output("Logger/DriverStationMS", (system_start - ds_start) / 1_000_000.0)
                cls.record_output("Logger/SystemStatsMS", (auto_log_start - system_start) / 1_000_000.0)
                # Log all auto-logged inputs
                for logged_input in AutoLogInputManager.get_inputs():
                    logged_input.to_log(
                        cls.entry.get_sub_table("/"),
                        "/" + logged_input.__class__.__name__,
                    )

            cls.record_output("Logger/AutoLogOutputMS", (alert_log_start - auto_log_start) / 1_000_000.0)
            cls.record_output("Logger/AlertLoggerMS", (alert_log_end - alert_log_start) / 1_000_000.0)

            # TODO: See the TODO's above...
            # recordOutput("Logger/RadioLogMS", (consoleCaptureStart - radioLogStart) / 1_000_000.0);
            # recordOutput("Logger/ConsoleMS", (gcStatsStart - consoleCaptureStart) / 1_000_000.0);
            # ecordOutput("Logger/GCStatsMS", (gcStatsEnd - gcStatsStart) / 1_000_000.0);

            cls.record_output("LoggedRobot/UserCodeMS", user_code_length / 1_000_000.0)
            periodic_after_length = alert_log_end - ds_start
            cls.record_output(
                "LoggedRobot/LogPeriodicMS",
                (periodic_before_length + periodic_after_length) / 1_000_000.0,
            )
            cls.record_output(
                "LoggedRobot/FullCycleMS",
                (periodic_before_length + user_code_length + periodic_after_length) / 1_000_000.0,
            )
            # Send log table to all receivers (file writer, NetworkTables, etc.)
            # TODO: Akit has a ReceiverThread. Can we support that as wel
            for receiver in cls.data_receivers:
                receiver.put_table(LogTable.clone(cls.entry))


@atexit.register
def atexit_end():
    """
    Ensure Logger.end() is called on program exit.

    This method is registered with the atexit module to guarantee that
    the logging system is properly shut down when the robot program exits,
    even if end() was not explicitly called. It prevents data loss and ensures
    all receivers flush their buffers.
    """
    Logger.end()
