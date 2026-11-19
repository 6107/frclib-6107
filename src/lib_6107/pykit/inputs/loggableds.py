"""
Logged Driver Station Module for Telemetry Capture and Replay

This module provides LoggedDriverStation, a utility for capturing and replaying
Driver Station state (operator inputs, match information, mode settings) during
robot operation and log playback.

Key Responsibilities:
- Telemetry Capture: Saves all Driver Station data each cycle for logging
- Replay Support: Restores Driver Station state from logs for deterministic replay
- Joystick Input Logging: Captures all controller buttons, axes, POV values
- Match Information: Logs match type, number, time, alliance, event data
- State Synchronization: Simulates DS state during replay for consistent testing

Data Captured:
- Match Information: Event name, match number/type, replay number, match time
- Alliance Information: Alliance color (red/blue), station location (1-3)
- Mode Flags: Enabled, autonomous mode, test mode, emergency stop, FMS/DS attached
- Joystick Data: All 6 joystick ports capturing buttons, axes, POV (D-pad) values
- Joystick Metadata: Name, type (generic/Xbox), button/axis counts

Usage:
    # Logging (normal operation)
    LoggedDriverStation.save_to_table(entry.get_sub_table("DriverStation"))

    # Replay (reading from log)
    LoggedDriverStation.replay_from_log(entry.get_sub_table("DriverStation"))

Data Organization in LogTable:
    DriverStation/
        ├── AllianceStation (int): 0=unknown, 1-3=Red1-3, 4-6=Blue1-3
        ├── EventName (str)
        ├── GameSpecificMessage (str)
        ├── MatchNumber (int)
        ├── ReplayNumber (int)
        ├── MatchType (int): 0=practice, 1=qualification, 2=playoff
        ├── MatchTime (float): Seconds remaining in match
        ├── Enabled (bool)
        ├── Autonomous (bool)
        ├── Test (bool)
        ├── EmergencyStop (bool)
        ├── FMSAttached (bool)
        ├── DSAttached (bool)
        └── Joystick0-5/
            ├── Name (str): Joystick name from OS
            ├── Type (int): Joystick type identifier
            ├── Xbox (bool): Whether Xbox-compatible
            ├── ButtonCount (int)
            ├── ButtonValues (int): Bitmask of button states
            ├── POVs (int[]): D-pad angle values for each POV
            ├── AxisValues (float[]): [-1.0, 1.0] analog stick/trigger values
            └── AxisTypes (int[]): Type of each axis

Alliance Station Encoding:
    The alliance station is encoded as a single integer:
    - 0: Not connected or unknown
    - 1-3: Red 1, Red 2, Red 3
    - 4-6: Blue 1, Blue 2, Blue 3

This allows compact storage and easy serial replay.
"""

from hal import AllianceStationID, RobotMode
from wpilib import Alliance, DriverStationBackend, MatchType, POVDirection
from wpilib.simulation import DriverStationSim

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue


class LoggedDriverStation:
    """
    Utility class for capturing and replaying FRC Driver Station state.

    LoggedDriverStation provides bidirectional conversion between live Driver Station
    state and LogTable format. This enables:

    1. Telemetry Logging: Each cycle, the current Driver Station state (controller
       inputs, match info, mode flags) is captured to a LogTable for permanent storage
       in .wpilog files.

    2. Deterministic Replay: During log replay, Driver Station state is restored from
       the log file to DriverStationSim, allowing the robot to see the exact same
       operator inputs and match conditions as the original match.

    Key Features:
    - Comprehensive Logging: Captures all DS data including 6 joysticks with buttons,
      axes, and POV (D-pad) values, plus match information and mode flags.
    - Compact Encoding: Alliance station compressed to single integer (0-6).
    - Replay Fidelity: Simulates DS state precisely for deterministic test replays.
    - Robustness: Uses sensible defaults if DS data is missing during replay.

    Two Primary Use Cases:

    Case 1 - Normal Operation (REAL or SIMULATION mode):
        Called each cycle by Logger.periodic_after_user():
        ```python
        LoggedDriverStation.save_to_table(entry.get_sub_table("DriverStation"))
        ```
        Captures current DS state to LogTable for permanent logging.

    Case 2 - Replay Mode (REPLAY reading from .wpilog):
        Called each cycle by Logger.periodic_before_user():
        ```python
        LoggedDriverStation.replay_from_log(entry.get_sub_table("DriverStation"))
        ```
        Restores DS state from log so robot sees replayed operator inputs.

    Data Integrity:
    - All joystick data is compressed (buttons as bitmask, axes as compressed floats)
    - Missing joysticks default gracefully (0 buttons, 0 axes)
    - Type conversions handle null/missing values safely
    - DriverStationSim.notify_new_data() called to trigger updates

    Performance Considerations:
    - save_to_table() is called once per cycle (~50 Hz), overhead is minimal
    - Joystick iteration loops 6 times (constant time)
    - No dynamic memory allocation in the hot path
    - Suitable for regular logging without performance impact
    """

    @classmethod
    def save_to_log(cls, table: LogTable) -> None:
        """
        Capture and save the current Driver Station state to a LogTable.

        This method is called each cycle to create a permanent record of operator
        inputs, match information, and robot mode state. The saved data can later
        be replayed via replay_from_log() for deterministic testing and analysis.

        Data Captured:

        Match Information:
        - Event name, match number/type, replay number, remaining match time
        - Alliance color and alliance station (encoded 0-6)

        Robot Mode State:
        - Enabled flag (robot powered on by Driver Station)
        - Robot mode (autonomous, teleoperated or utility) and the selected OpMode
        - Emergency stop (E-stop) state
        - FMS (Field Management System) attached
        - DS (Driver Station) attached

        Joystick Data (for each of 6 ports):
        - Name from OS (e.g., "Xbox 360 Controller")
        - Type identifier and Xbox compatibility flag
        - Button count and button bitmask (all buttons encoded as a single int)
        - All POV (D-pad) hat switch values
        - All analog axes (stick, triggers, etc.) with their type identifiers

        Alliance Station Encoding:
        The alliance and location are combined into a single integer:
        - 0: No location available (not connected or validation failed)
        - 1-3: Red 1, Red 2, Red 3
        - 4-6: Blue 1, Blue 2, Blue 3

        This compact representation saves space in logs.

        Args:
            table (LogTable): The LogTable subtable to save Driver Station data to.
                Typically: entry.get_sub_table("DriverStation")
                All data is saved with hierarchical keys (Joystick0/, Joystick1/, etc.)

        Side Effects:
            - Reads from DriverStation (live or simulated)
            - Populates table with all DS entries
            - Creates subtables for each joystick (Joystick0-5)

        Typical Cycle Integration:
            Called by Logger.periodic_after_user() in normal modes:
            ```python
            #...existing code...
            LoggedDriverStation.save_to_table(cls.entry.get_sub_table("DriverStation"))
            #...existing code...
            ```
        """
        # Capture alliance and station information
        alliance = DriverStationBackend.get_alliance()
        location = DriverStationBackend.get_location()
        # Encode alliance station as single integer (0=none, 1-3=red, 4-6=blue)
        station = 0 if location is None or alliance is None else (location + (3 if alliance == Alliance.BLUE else 0))

        # Save match information
        table.put("AllianceStation", station)
        table.put("EventName", DriverStationBackend.get_event_name())
        table.put("GameSpecificMessage", DriverStationBackend.get_game_data() or "")
        table.put("MatchNumber", DriverStationBackend.get_match_number())
        table.put("ReplayNumber", DriverStationBackend.get_replay_number())
        table.put("MatchType", DriverStationBackend.get_match_type().value)
        table.put("MatchTime", DriverStationBackend.get_match_time())

        # Save robot mode state flags. 2027 replaces the autonomous/test flags with a RobotMode and an OpMode.
        robot_mode = DriverStationBackend.get_robot_mode()
        table.put("Enabled", DriverStationBackend.is_enabled())
        table.put("RobotMode", int(robot_mode.value))
        table.put("OpMode", DriverStationBackend.get_opmode())
        table.put("Autonomous", robot_mode == RobotMode.AUTONOMOUS)
        table.put("Teleop", robot_mode == RobotMode.TELEOPERATED)
        table.put("Utility", robot_mode == RobotMode.UTILITY)
        table.put("EmergencyStop", DriverStationBackend.is_e_stopped())
        table.put("FMSAttached", DriverStationBackend.is_fms_attached())
        table.put("DSAttached", DriverStationBackend.is_ds_attached())

        # Log all joystick data for each port
        for i in range(DriverStationBackend.JOYSTICK_PORTS):
            joystick_table = table.get_sub_table(f"Joystick{i}")

            # Save joystick metadata
            joystick_table.put("Name", DriverStationBackend.get_joystick_name(i).strip())
            joystick_table.put("GamepadType", int(DriverStationBackend.get_joystick_gamepad_type(i)))
            joystick_table.put("IsGamepad", DriverStationBackend.get_joystick_is_gamepad(i))

            # Buttons: availability mask, highest index and the pressed-state bitmask
            joystick_table.put("ButtonsAvailable", DriverStationBackend.get_stick_buttons_available(i))
            joystick_table.put("ButtonCount", DriverStationBackend.get_stick_buttons_maximum_index(i) + 1)
            joystick_table.put("ButtonValues", DriverStationBackend.get_stick_buttons(i))

            # POVs: availability mask plus the direction of each POV up to the highest index
            joystick_table.put("POVsAvailable", DriverStationBackend.get_stick_povs_available(i))
            pov_count = DriverStationBackend.get_stick_povs_maximum_index(i) + 1
            pov_values = [int(DriverStationBackend.get_stick_pov(i, j).value) for j in range(pov_count)]
            joystick_table.put_value("POVs", LogValue.with_type(LogValue.LoggableType.IntegerArray, pov_values))

            # Axes: availability mask plus the value of each axis up to the highest index
            joystick_table.put("AxesAvailable", DriverStationBackend.get_stick_axes_available(i))
            axis_count = DriverStationBackend.get_stick_axes_maximum_index(i) + 1
            axis_values = [DriverStationBackend.get_stick_axis(i, j) for j in range(axis_count)]
            joystick_table.put_value("AxisValues", LogValue.with_type(LogValue.LoggableType.DoubleArray, axis_values))

    @classmethod
    def replay_from_log(cls, table: LogTable) -> None:
        """
        Restore Driver Station state from a LogTable during replay.

        This method is called during log replay to populate DriverStationSim with
        the previously recorded Driver Station state. This allows the robot to see the
        exact same operator inputs, match conditions, and mode flags as during the
        original match, enabling deterministic replay for debugging and testing.

        Replay Workflow:
        1. Logger.periodic_before_user() loads the next entry from a log file
        2. replay_from_log() restores that entry's DS state to DriverStationSim
        3. Robot code executes and reads inputs (sees replayed state)
        4. Robot outputs are logged but typically not sent to hardware
        5. Repeat for the next timestamp in the log

        Data Restored:

        Match Information:
        - Alliance station (decoded from 0-6 encoding back to alliance and location)
        - Event name, match number/type, replay number, match time

        Robot Modes:
        - Enabled, autonomous, test mode flags
        - Emergency stop state
        - FMS/DS attachment status

        Joystick Data:
        - Button and axis counts
        - Button bitmask (all buttons encoded in a single integer)
        - POV hat switch angles for each joystick
        - Analog axis values and their types

        Replay Safety:
        - All values use sensible defaults if data is missing from the log
        - AllianceStationID defaults to Red1 if not recorded
        - Missing joystick data defaults to 0 buttons, 0 axes
        - Empty arrays handled gracefully

        Update Notification:
        - Calls DriverStationSim.notify_new_data() to signal DS state changed
        - Only called if ds_attached was recorded as true

        Key Design:
        - This is NOT a real-time source - data comes from a pre-recorded log file
        - Simulation time is synchronized with log timestamps
        - Enables frame-by-frame analysis with exact operator inputs

        Args:
            table (LogTable): The LogTable subtable containing saved Driver Station data.
                Typically: entry.get_sub_table("DriverStation")
                Expects hierarchical structure with Joystick0-5 subtables
                All reads use default values for missing/corrupted entries

        Side Effects:
            - Calls DriverStationSim methods to populate simulation state
            - Updates joystick button, axis, and POV states
            - May call DriverStationSim.notify_new_data() to trigger updates

        Typical Cycle Integration:
            Called by Logger.periodic_before_user() during replay mode:
            ```python
            #...existing code...
            if cls.is_replay():
                LoggedDriverStation.replay_from_log(cls.entry.get_sub_table("DriverStation"))
            #...existing code...
            ```

        Robustness:
            - Missing entries use defaults (e.g., Red1 alliance if not recorded)
            - Gracefully handles corrupted or incomplete log entries
            - Suitable for replaying logs from different versions/configurations
        """
        # Restore alliance station (decode 0-6 back to alliance + location)
        DriverStationSim.set_alliance_station_id(
            AllianceStationID(table.get("AllianceStation", AllianceStationID.RED_1.value))
        )

        # Restore match information
        DriverStationSim.set_event_name(table.get("EventName", ""))
        DriverStationSim.set_game_data(table.get("GameSpecificMessage", ""))
        DriverStationSim.set_match_number(table.get("MatchNumber", 0))
        DriverStationSim.set_replay_number(table.get("ReplayNumber", 0))
        DriverStationSim.set_match_type(MatchType(table.get("MatchType", 0)))
        DriverStationSim.set_match_time(table.get("MatchTime", -1.0))

        # Restore robot mode state flags
        DriverStationSim.set_enabled(table.get("Enabled", False))
        DriverStationSim.set_robot_mode(RobotMode(table.get("RobotMode", RobotMode.UNKNOWN.value)))
        DriverStationSim.set_e_stop(table.get("EmergencyStop", False))
        DriverStationSim.set_fms_attached(table.get("FMSAttached", False))
        ds_attached = table.get("DSAttached", False)
        DriverStationSim.set_ds_attached(ds_attached)

        # Restore joystick data for each port
        for i in range(DriverStationBackend.JOYSTICK_PORTS):
            joystick_table = table.get_sub_table(f"Joystick{i}")

            # Buttons: replay the pressed state of each available button
            button_count = joystick_table.get("ButtonCount", 0)
            button_values = joystick_table.get("ButtonValues", 0)
            DriverStationSim.set_joystick_buttons_available(i, joystick_table.get("ButtonsAvailable", 0))
            DriverStationSim.set_joystick_buttons_maximum_index(i, max(button_count - 1, 0))
            for j in range(button_count):
                DriverStationSim.set_joystick_button(i, j, bool(button_values & (1 << j)))

            # POVs
            pov_values = joystick_table.get("POVs", [])
            DriverStationSim.set_joystick_povs_available(i, joystick_table.get("POVsAvailable", 0))
            DriverStationSim.set_joystick_povs_maximum_index(i, max(len(pov_values) - 1, 0))
            for j, pov in enumerate(pov_values):
                DriverStationSim.set_joystick_pov(i, j, POVDirection(pov))

            # Axes
            axis_values = joystick_table.get("AxisValues", [])
            DriverStationSim.set_joystick_axes_available(i, joystick_table.get("AxesAvailable", 0))
            DriverStationSim.set_joystick_axes_maximum_index(i, max(len(axis_values) - 1, 0))
            for j, axis_val in enumerate(axis_values):
                DriverStationSim.set_joystick_axis(i, j, axis_val)

        # Notify DriverStationSim that data has been updated
        # This signals any listeners that DS state has changed
        if ds_attached:
            DriverStationSim.notify_new_data()
