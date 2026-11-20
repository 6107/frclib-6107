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
Log Tracer Module for Performance Profiling

This module provides LogTracer, a hierarchical performance profiler for measuring
execution time of code blocks and subsystems. It captures timing at multiple levels:

- Outer level: Total time for a major operation (e.g., "robot_periodic")
- Inner level: Time for individual phases within that operation (e.g., "subsystemUpdate")

Timings are logged to NetworkTables/disk via the pykit Logger for visualization
in SmartDashboard, AdvantageScope, or other dashboards. This enables operators to
identify performance bottlenecks during competition or testing.

Typical Usage Pattern:
    ```python
    # At the start of a large operation (e.g., robot_periodic)
    LogTracer.reset_outer("RobotPeriodic")

    # After each significant phase
    subsystem1.update()
    LogTracer.record("Subsystem1Update")

    subsystem2.update()
    LogTracer.record("Subsystem2Update")

    # At the end
    LogTracer.record_total()  # Logs total time and all phase times
    ```

This creates LogTable entries like:
    - LogTracer/RobotPeriodic/Subsystem1UpdateMS: milliseconds for subsystem1
    - LogTracer/RobotPeriodic/Subsystem2UpdateMS: milliseconds for subsystem2
    - LogTracer/RobotPeriodic/TotalMS: total time for robot_periodic

Credit: Adapted from 1757-Westwood Robotics
(https://github.com/1757WestwoodRobotics/2026-Rebuilt)
"""

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
# From 1757-Westwood Robotics: https://github.com/1757WestwoodRobotics/2026-Rebuilt

from wpilib import RobotController

from lib_6107.pykit.logger import Logger


class LogTracer:
    """
    Hierarchical performance profiler for measuring and logging code execution time.

    LogTracer uses a two-level timing system to measure performance of code blocks
    and their sub-phases. This is useful for identifying bottlenecks in robot code
    and ensuring loop timing requirements are met during competition.

    Two-Level Timing Architecture:
    - Outer Level: Marks the start of a major operation (e.g., robot_periodic) via reset_outer()
    - Inner Level: Marks the completion of sub-phases within that operation via record()
    - The time for each phase is calculated since the previous record() or reset_outer()
    - record_total() logs the total time from reset_outer() to the current point

    Class Attributes:
        _inner_start (float): timestamp (nanoseconds) of the last reset() or record() call.
            Used to measure the duration of individual phases.
        _outer_start (float): timestamp (nanoseconds) of the last reset_outer() call.
            Used to measure total time for the entire operation block.
        _prefix (str): Namespace prefix for all logged metrics (e.g., "RobotPeriodic").
            Forms the path "LogTracer/{_prefix}/*MS" for each logged value.

    Output Format:
        All timings are logged via Logger.record_output() in milliseconds with keys:
        - "LogTracer/{prefix}/{action}MS" for each record() call
        - "LogTracer/{prefix}/TotalMS" for record_total()

        Example: "LogTracer/RobotPeriodic/Subsystem1UpdateMS" = 2.5

    Typical Workflow:
        ```python
        # In robot_periodic()
        LogTracer.reset_outer("RobotPeriodic")

        # Execute and profile subsystems
        drivetrain.update()
        LogTracer.record("DrivetrainUpdate")

        arms.update()
        LogTracer.record("ArmUpdate")

        # Log total time for this cycle
        LogTracer.record_total()

        # Output logged to LogTracer/RobotPeriodic/DrivetrainUpdateMS, etc.
        ```

    Performance Considerations:
    - LogTracer adds negligible overhead (~10-50 microseconds per call)
    - Suitable for profiling at any level from microseconds to seconds
    - Can be called multiple times per robot cycle for fine-grained analysis

    Thread Safety:
    - Not thread-safe; assume single-threaded use in robot main loop
    - If used from multiple threads, synchronization is required
    """

    _inner_start: int = 0
    """timestamp (nanoseconds) of the last reset() or record() call.
    Used to measure the duration of individual phases."""

    _outer_start: int = 0
    """timestamp (nanoseconds) of the last reset_outer() call.
    Used to measure the total duration from the start of the operation block."""

    _prefix: str = ""
    """Namespace prefix for logged metrics (e.g., 'RobotPeriodic', 'AutonCommand').
    Forms the path 'LogTracer/{_prefix}/*MS' for all logged values."""

    @classmethod
    def reset_outer(cls, prefix: str) -> None:
        """
        Start a new profiling block and reset both outer and inner timers.

        Call this method at the beginning of a major operation (e.g., robot_periodic,
        autonomous_init, teleop_periodic) to define a new block of code to profile.
        This captures the current monotonic time as the reference point for the entire
        operation and resets the inner timer for the first phase.

        The prefix is used to organize logged metrics in the telemetry namespace.
        For example, reset_outer("RobotPeriodic") will result in logged keys like:
        - LogTracer/RobotPeriodic/Subsystem1UpdateMS
        - LogTracer/RobotPeriodic/TotalMS

        Args:
            prefix (str): The namespace prefix for this profiling block (e.g., "RobotPeriodic",
                "AutonCommand", "VisionUpdate"). Should be descriptive and consistent
                for the same operation. No leading "/" required.

        Side Effects:
            - Sets cls._outer_start to the current monotonic time
            - Sets cls._prefix to the provided prefix
            - Calls reset() to initialize cls._inner_start to the current monotonic time
            - Clears any previous timing state

        Example:
            ```python
            LogTracer.reset_outer("RobotPeriodic")
            # Subsequent record() calls will log to LogTracer/RobotPeriodic/*MS
            ```
        """
        cls._outer_start = RobotController.get_monotonic_time()
        cls.reset()
        cls._prefix = prefix

    @classmethod
    def reset(cls) -> None:
        """
        Reset the inner timer without changing the outer timer or prefix.

        Call this method to start measuring a new phase within the current operation
        block. This updates the inner timer to the current time without affecting
        the outer timer (which continues measuring from reset_outer()).

        This is less commonly used than record(), but is useful when you want to
        adjust the starting point of phase measurement without logging an intermediate
        result.

        Side Effects:
            - Sets cls._inner_start to the current monotonic time
            - Does not affect cls._outer_start or cls._prefix
            - The next record() call will measure time from this new starting point

        Note:
            Most code should call record() instead, which both captures the previous
            phase duration and resets the inner timer for the next phase in one call.
        """
        cls._inner_start = RobotController.get_monotonic_time()

    @classmethod
    def record(cls, action: str) -> None:
        """
        Record the execution time of the current phase and prepare for the next phase.

        Call this method after each significant operation to log how long that
        operation took. The time is calculated as the duration from the previous
        record() call (or from reset_outer() if this is the first record()).

        Each call immediately logs the phase duration to the Logger and resets the
        inner timer to prepare for measuring the next phase.

        Logged Key Format: "LogTracer/{prefix}/{action}MS"
        Examples:
        - "LogTracer/RobotPeriodic/Subsystem1UpdateMS"
        - "LogTracer/RobotPeriodic/PathfindingMS"
        - "LogTracer/AutonInit/ConfigurationMS"

        Args:
            action (str): A descriptive name for the phase that just completed.
                Should be concise but meaningful (e.g., "Subsystem1Update", "PathPlanning").
                Best practice: Use PascalCase or camelCase. The suffix "MS" is added
                automatically by this method.

        Side Effects:
            - Logs one entry to the Logger with key "LogTracer/{_prefix}/{action}MS"
            - Resets cls._inner_start to the current monotonic time
            - Does not affect cls._outer_start or cls._prefix

        Returns:
            None

        Example:
            ```python
            LogTracer.reset_outer("RobotPeriodic")

            drivetrain.update()
            LogTracer.record("DrivetrainUpdate")  # Logs time for drivetrain update

            vision.update()
            LogTracer.record("VisionUpdate")  # Logs time for vision update

            LogTracer.record_total()  # Logs total time
            ```

        Note:
            - Time is converted from nanoseconds to milliseconds for readability
            - Use record() frequently to get fine-grained performance metrics
            - Recommended to record() after each subsystem update for full visibility
        """
        now = RobotController.get_monotonic_time()
        Logger.record_output(f"LogTracer/{cls._prefix}/{action}MS", (now - cls._inner_start) / 1_000_000.0)
        cls._inner_start = now

    @classmethod
    def record_total(cls) -> None:
        """
        Record the total execution time from the start of the current operation block.

        Call this method at the end of the operation block to log the total time
        from the reset_outer() call to this point. This gives a high-level view of
        overall performance and helps verify that the entire operation completed
        within the required time (e.g., within 20 ms for a robot periodic cycle).

        The total time includes all phases measured by record() calls plus any
        unmeasured portions that occurred after the last record().

        Logged Key Format: "LogTracer/{prefix}/TotalMS"
        Example: "LogTracer/RobotPeriodic/TotalMS" = 18.5 ms

        Side Effects:
            - Logs one entry to the Logger with key "LogTracer/{_prefix}/TotalMS"
            - Does not reset any timers (they remain available for inspection)

        Returns:
            None

        Example:
            ```python
            LogTracer.reset_outer("RobotPeriodic")

            # ... perform multiple record() calls ...

            LogTracer.record_total()  # Logs total time for robot_periodic
            ```

        Typical Usage Pattern:
            ```python
            def robot_periodic(self):
                LogTracer.reset_outer("RobotPeriodic")

                self.subsystems.update()
                LogTracer.record("SubsystemsUpdate")

                self.commands.execute()
                LogTracer.record("CommandsExecute")

                LogTracer.record_total()  # Final metric: total cycle time
            ```

        Note:
            - Time is converted from nanoseconds to milliseconds
            - Typically called once per operation block (e.g., once per robot_periodic)
            - Useful for verifying loop timing requirements are met
            - Recommended to use in conjunction with record() for best insights
        """
        now = RobotController.get_monotonic_time()
        Logger.record_output(f"LogTracer/{cls._prefix}/TotalMS", (now - cls._outer_start) / 1_000_000.0)
