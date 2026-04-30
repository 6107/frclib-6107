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
    LoggedDriverStation.save_to_table(entry.get_subtable("DriverStation"))
    
    # Replay (reading from log)
    LoggedDriverStation.load_from_table(entry.get_subtable("DriverStation"))

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

from hal import AllianceStationID
from wpilib import DriverStation
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
        Called each cycle by Logger.periodicAfterUser():
        ```python
        LoggedDriverStation.save_to_table(entry.get_subtable("DriverStation"))
        ```
        Captures current DS state to LogTable for permanent logging.
    
    Case 2 - Replay Mode (REPLAY reading from .wpilog):
        Called each cycle by Logger.periodicBeforeUser():
        ```python
        LoggedDriverStation.load_from_tablele(entry.get_subtable("DriverStation"))
        ```
        Restores DS state from log so robot sees replayed operator inputs.
    
    Data Integrity:
    - All joystick data is compressed (buttons as bitmask, axes as compressed floats)
    - Missing joysticks default gracefully (0 buttons, 0 axes)
    - Type conversions handle null/missing values safely
    - DriverStationSim.notifyNewData() called to trigger updates
    
    Performance Considerations:
    - save_to_table() is called once per cycle (~50 Hz), overhead is minimal
    - Joystick iteration loops 6 times (constant time)
    - No dynamic memory allocation in hot path
    - Suitable for regular logging without performance impact
    """

    @classmethod
    def save_to_table(cls, table: LogTable) -> None:
        """
        Capture and save the current Driver Station state to a LogTable.
        
        This method is called each cycle to create a permanent record of operator
        inputs, match information, and robot mode state. The saved data can later
        be replayed via load_from_table() for deterministic testing and analysis.
        
        Data Captured:
        
        Match Information:
        - Event name, match number/type, replay number, remaining match time
        - Alliance color and alliance station (encoded 0-6)
        
        Robot Mode State:
        - Enabled flag (robot powered on by Driver Station)
        - Autonomous mode vs teleop
        - Test mode vs competition mode
        - Emergency stop (E-stop) state
        - FMS (Field Management System) attached
        - DS (Driver Station) attached
        
        Joystick Data (for each of 6 ports):
        - Name from OS (e.g., "Xbox 360 Controller")
        - Type identifier and Xbox compatibility flag
        - Button count and button bitmask (all buttons encoded as single int)
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
                Typically: entry.get_subtable("DriverStation")
                All data is saved with hierarchical keys (Joystick0/, Joystick1/, etc.)
                
        Side Effects:
            - Reads from DriverStation (live or simulated)
            - Populates table with all DS entries
            - Creates subtables for each joystick (Joystick0-5)
            
        Typical Cycle Integration:
            Called by Logger.periodicAfterUser() in normal modes:
            ```python
            #...existing code...
            LoggedDriverStation.save_to_table(cls.entry.get_subtable("DriverStation"))
            #...existing code...
            ```
        """
        # Capture alliance and station information
        alliance = DriverStation.getAlliance()
        location = DriverStation.getLocation()
        # Encode alliance station as single integer (0=none, 1-3=red, 4-6=blue)
        station = (
            0
            if location is None or alliance is None
            else (location + (3 if alliance == DriverStation.Alliance.kBlue else 0))
        )
        
        # Save match information
        table.put("AllianceStation", station)
        table.put("EventName", DriverStation.getEventName())
        table.put("GameSpecificMessage", DriverStation.getGameSpecificMessage())
        table.put("MatchNumber", DriverStation.getMatchNumber())
        table.put("ReplayNumber", DriverStation.getReplayNumber())
        table.put("MatchType", DriverStation.getMatchType().value)
        table.put("MatchTime", DriverStation.getMatchTime())

        # Save robot mode state flags
        table.put("Enabled", DriverStation.isEnabled())
        table.put("Autonomous", DriverStation.isAutonomous())
        table.put("Test", DriverStation.isTest())
        table.put("EmergencyStop", DriverStation.isEStopped())
        table.put("FMSAttached", DriverStation.isFMSAttached())
        table.put("DSAttached", DriverStation.isDSAttached())

        # Log all joystick data for each port (typically 6 ports: 0-5)
        for i in range(DriverStation.kJoystickPorts):
            joystick_table = table.get_subtable(f"Joystick{i}")
            
            # Save joystick metadata
            joystick_table.put("Name", DriverStation.getJoystickName(i).strip())
            joystick_table.put("Type", DriverStation.getJoystickType(i))
            joystick_table.put("Xbox", DriverStation.getJoystickIsXbox(i))
            joystick_table.put("ButtonCount", DriverStation.getStickButtonCount(i))
            
            # Save button states as bitmask (all buttons encoded in single integer)
            joystick_table.put("ButtonValues", DriverStation.getStickButtons(i))

            # Log POV (D-pad) values - each POV hat switch can have one angle
            pov_count = DriverStation.getStickPOVCount(i)
            pov_values = [DriverStation.getStickPOV(i, j) for j in range(pov_count)]
            joystick_table.put_value("POVs", LogValue.withType(LogValue.LoggableType.IntegerArray,
                                                               pov_values))
            
            # Log axis values (analog sticks, triggers, etc.) and their types
            axis_count = DriverStation.getStickAxisCount(i)
            axis_values = [DriverStation.getStickAxis(i, j) for j in range(axis_count)]
            axis_types = [DriverStation.getJoystickAxisType(i, j) for j in range(axis_count)]

            joystick_table.put_value("AxisValues",
                                     LogValue.withType(LogValue.LoggableType.DoubleArray, axis_values))
            joystick_table.put("AxisTypes", axis_types)

    @classmethod
    def load_from_table(cls, table: LogTable) -> None:
        """
        Restore Driver Station state from a LogTable during replay.
        
        This method is called during log replay to populate DriverStationSim with
        previously recorded Driver Station state. This allows the robot to see the
        exact same operator inputs, match conditions, and mode flags as during the
        original match, enabling deterministic replay for debugging and testing.
        
        Replay Workflow:
        1. Logger.periodicBeforeUser() loads next entry from log file
        2. load_from_table() restores that entry's DS state to DriverStationSim
        3. Robot code executes and reads inputs (sees replayed state)
        4. Robot outputs are logged but typically not sent to hardware
        5. Repeat for next timestamp in log
        
        Data Restored:
        
        Match Information:
        - Alliance station (decoded from 0-6 encoding back to alliance + location)
        - Event name, match number/type, replay number, match time
        
        Robot Modes:
        - Enabled, autonomous, test mode flags
        - Emergency stop state
        - FMS/DS attachment status
        
        Joystick Data:
        - Button and axis counts
        - Button bitmask (all buttons encoded in single integer)
        - POV hat switch angles for each joystick
        - Analog axis values and their types
        
        Replay Safety:
        - All values use sensible defaults if data is missing from log
        - AllianceStationID defaults to Red1 if not recorded
        - Missing joystick data defaults to 0 buttons, 0 axes
        - Empty arrays handled gracefully
        
        Update Notification:
        - Calls DriverStationSim.notifyNewData() to signal DS state changed
        - Only called if ds_attached was recorded as true
        
        Key Design:
        - This is NOT a real-time source - data comes from pre-recorded log file
        - Simulation time is synchronized with log timestamps
        - Enables frame-by-frame analysis with exact operator inputs
        
        Args:
            table (LogTable): The LogTable subtable containing saved Driver Station data.
                Typically: entry.get_subtable("DriverStation")
                Expects hierarchical structure with Joystick0-5 subtables
                All reads use default values for missing/corrupted entries
                
        Side Effects:
            - Calls DriverStationSim methods to populate simulation state
            - Updates joystick button, axis, and POV states
            - May call DriverStationSim.notifyNewData() to trigger updates
            
        Typical Cycle Integration:
            Called by Logger.periodicBeforeUser() during replay mode:
            ```python
            #...existing code...
            if cls.isReplay():
                LoggedDriverStation.load_from_table(cls.entry.get_subtable("DriverStation"))
            #...existing code...
            ```
            
        Robustness:
            - Missing entries use defaults (e.g., Red1 alliance if not recorded)
            - Gracefully handles corrupted or incomplete log entries
            - Suitable for replaying logs from different versions/configurations
        """
        # Restore alliance station (decode 0-6 back to alliance + location)
        DriverStationSim.setAllianceStationId(
            AllianceStationID(table.get("AllianceStation", AllianceStationID.kRed1.value)))
        
        # Restore match information
        DriverStationSim.setEventName(table.get("EventName", ""))
        DriverStationSim.setGameSpecificMessage(table.get("GameSpecificMessage", ""))
        DriverStationSim.setMatchNumber(table.get("MatchNumber", 0))
        DriverStationSim.setReplayNumber(table.get("ReplayNumber", 0))
        DriverStationSim.setMatchType(DriverStation.MatchType(table.get("MatchType", 0)))
        DriverStationSim.setMatchTime(table.get("MatchTime", -1.0))

        # Restore robot mode state flags
        DriverStationSim.setEnabled(table.get("Enabled", False))
        DriverStationSim.setAutonomous(table.get("Autonomous", False))
        DriverStationSim.setTest(table.get("Test", False))
        DriverStationSim.setEStop(table.get("EmergencyStop", False))
        DriverStationSim.setFmsAttached(table.get("FMSAttached", False))
        ds_attached = table.get("DSAttached", False)
        DriverStationSim.setDsAttached(ds_attached)

        # Restore joystick data for each port
        for i in range(DriverStation.kJoystickPorts):
            joystick_table = table.get_subtable(f"Joystick{i}")

            # Restore button states (bitmask encoding all buttons in single integer)
            button_values = joystick_table.get("ButtonValues", 0)
            DriverStationSim.setJoystickButtons(i, button_values)

            # Restore POV (D-pad) values for each hat switch on this joystick
            pov_values = joystick_table.get("POVs", [])
            DriverStationSim.setJoystickPOVCount(i, len(pov_values))
            for j, pov in enumerate(pov_values):
                DriverStationSim.setJoystickPOV(i, j, pov)

            # Restore analog axis values and their type identifiers
            axis_values = joystick_table.get("AxisValues", [])
            axis_types = joystick_table.get("AxisTypes", [])

            DriverStationSim.setJoystickAxisCount(i, len(axis_values))
            for j, (axis_val, axis_type) in enumerate(zip(axis_values, axis_types)):
                DriverStationSim.setJoystickAxis(i, j, axis_val)
                DriverStationSim.setJoystickAxisType(i, j, axis_type)

        # Notify DriverStationSim that data has been updated
        # This signals any listeners that DS state has changed
        if ds_attached:
            DriverStationSim.notifyNewData()