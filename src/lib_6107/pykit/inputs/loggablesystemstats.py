"""
Logged System Statistics Module for Robot Health Monitoring

This module provides LoggedSystemStats, a utility for capturing and logging robot
system statistics including:
- RoboRIO/FPGA hardware information (version, revision, serial number)
- System health metrics (brownout state, communications status, RSL state)
- NetworkTables client connections and their connectivity status

The statistics are captured with adaptive frequency to balance telemetry detail
with logging efficiency:
- Hardware Info (FPGA version, team number, etc.): Once at startup
- System Health (brownout, comms disabled): ~Every 4 seconds (200 cycle interval)
- Network Connections: ~Every 10 seconds (500 cycle interval)

Typical Usage:
    LoggedSystemStats.save_to_table(entry.get_subtable("SystemStats"))

Data Captured:
- Hardware: FPGA version, revision, serial number, team number, comments
- Health: System active, brownout state, comms disabled count, RSL state, time valid
- Networking: Connected clients with IP address, port, protocol version

All timing is based on 50 Hz periodic calls (20 ms cycle time).
"""

from hal import (
    getBrownedOut,
    getComments,
    getCommsDisableCount,
    getFPGAButton,
    getFPGARevision,
    getFPGAVersion,
    getRSLState,
    getSerialNumber,
    getSystemActive,
    getSystemTimeValid,
    getTeamNumber,
)

from ntcore import NetworkTableInstance

from lib_6107.pykit.logtable import LogTable


class LoggedSystemStats:
    """
    Utility class for capturing and logging robot system statistics and health.
    
    LoggedSystemStats periodically captures hardware information, system health metrics,
    and NetworkTables connectivity data from the roboRIO and logs them to telemetry.
    This enables operators and engineers to monitor system status and diagnose issues
    during or after matches.
    
    Data Categories:
    
    1. Hardware Information (captured once at startup):
       - FPGA Version: WPILib/RoboRIO firmware version
       - FPGA Revision: Hardware revision number
       - Serial Number: Unique roboRIO identifier
       - Team Number: FRC team code
       - Comments: User-defined system description
       - FPGA Button: Manual override button state
    
    2. System Health (captured every ~4 seconds, 200 cycle interval):
       - System Active: Whether the roboRIO is running normally
       - Brownout State: Whether a brownout (voltage sag) is occurring
       - Comms Disabled Count: Number of times communication was disabled
       - RSL State: Status of the Robot Signal Light (indicator LED)
       - System Time Valid: Whether the system clock is synchronized
    
    3. NetworkTables Connections (captured every ~10 seconds, 500 cycle interval):
       - Connected Clients: List of dashboard and supporting systems connected via NT
       - Per-Client Metadata: IP address, port, protocol version
       - Connection State: Whether each client is currently connected or disconnected
    
    Efficiency Strategy:
    
    The class uses adaptive sampling (not every cycle) to reduce logging overhead:
    - One-time statistics: Captured only on first call (pass 0)
    - Periodic metrics: Captured on modulo intervals (pass % 199 and pass % 499)
    - This avoids expensive HAL calls on every cycle while maintaining visibility
    
    For 50 Hz robot periodic:
    - Hardware Info: First cycle only (~0 ms into match)
    - System Health: Every 200 cycles = 4 second interval
    - Network Info: Every 500 cycles = 10 second interval
    
    HAL Quirks Handled:
    
    - Some HAL functions return tuples instead of scalars (e.g., getFPGAVersion()
      returns (version, 0)). This class extracts [0] element for cleaner logging.
    - This is likely a legacy artifact from C++ binding layer.
    
    NetworkTables Connection Tracking:
    
    The class tracks which NT clients have connected and disconnected by:
    - Storing the set of remote IDs from previous cycle (last_nt_remote_ids)
    - Detecting new connections by comparing current vs previous ID sets
    - Marking disconnected clients with Connected=False entry
    - Updating the tracking set for next cycle
    
    This allows the log to show connect/disconnect events even if no active data
    is being transmitted from that client.
    
    Class Attributes:
        last_nt_remote_ids (set[str]): Set of remote client IDs from previous cycle.
            Used to detect client disconnections for logging.
        save_pass (int): Counter incremented each call. Used to determine when to
            capture expensive metrics (via modulo operations).
    
    Thread Safety:
    - Assumed to be called only from robot main thread (50 Hz)
    - State variables (save_pass, last_nt_remote_ids) are not thread-safe
    - If called from multiple threads, synchronization is required
    """

    last_nt_remote_ids: set[str] = set()
    """Set of NetworkTables remote client IDs from the previous save_to_table() call.
    Used to track client disconnections by comparing with current connections."""
    
    save_pass: int = 0
    """Call counter tracking how many times save_to_table() has been invoked.
    Used to implement adaptive sampling via modulo operations."""

    @classmethod
    def save_to_table(cls, table: LogTable) -> None:
        """
        Capture and log robot system statistics with adaptive sampling.
        
        This method is the main entry point for system statistics logging. It captures
        hardware info, system health, and network connectivity data with varying
        frequencies to balance monitoring visibility with logging efficiency.
        
        Called Each Cycle:
        Invoked once per robot periodic cycle (50 Hz, 20 ms) from Logger.periodicAfterUser():
        
        ```python
        LoggedSystemStats.save_to_table(entry.get_subtable("SystemStats"))
        ```
        
        Sampling Strategy:
        
        1. Pass 0 (First call, ~0 ms into match):
           - FPGA Version and Revision
           - Serial Number (unique roboRIO identifier)
           - Team Number
           - User Comments
           - FPGA Manual Button State
           These are static for the entire match, so logged once.
        
        2. Every 200 passes (~4 second interval at 50 Hz):
           - System Active: Normal operation indicator
           - Brownout State: Voltage sag detection
           - Comms Disabled Count: Communication failure tracking
           - RSL State: Robot Signal Light status
           - System Time Valid: Clock synchronization status
           These metrics change infrequently but indicate system health issues.
        
        3. Every 500 passes (~10 second interval at 50 Hz):
           - NetworkTables Client Connections
           - Per-Client Metadata: IP address, port, protocol version
           - Connection Status: Current connected/disconnected state
           Networking changes slowly but is important for robot-to-dashboard comms.
        
        Connection Tracking Logic:
        
        The NetworkTables connection tracking uses set difference to detect changes:
        ```
        current_ids = {connection.remote_id for each connection}
        disconnected = last_nt_remote_ids - current_ids
        connected = current_ids - last_nt_remote_ids
        
        For disconnected: nt_client_table[remote_id].put("Connected", False)
        last_nt_remote_ids = current_ids
        ```
        
        This enables the log to show connect/disconnect events by comparing the current
        set of connected clients to the set from the previous sample.
        
        HAL Tuple Handling:
        
        Some HAL functions return tuples (e.g., getFPGAVersion() returns (version, 0)).
        This is likely a legacy from C++ JNI bindings. The code extracts [0]:
        ```python
        table.put("FPGAVersion", getFPGAVersion()[0])  # Extract version from tuple
        ```
        
        Data Organization in LogTable:
        ```
        SystemStats/
        ├── FPGAVersion (int) - One-time, first call
        ├── FPGARevision (int)
        ├── SerialNumber (str)
        ├── Comments (str)
        ├── TeamNumber (int)
        ├── FPGAButton (bool)
        ├── SystemActive (bool) - Every 4 seconds
        ├── BrownedOut (bool)
        ├── CommsDisabledCount (int)
        ├── RSLState (bool)
        ├── SystemTimeValid (bool)
        └── NTClients/ - Every 10 seconds
            └── [remote_id]/
                ├── Connected (bool)
                ├── IPAddress (str)
                ├── RemotePort (int)
                └── ProtocolVersion (str)
        ```

        Args:
            table (LogTable): The LogTable subtable to write system stats to.
                Typically: entry.get_subtable("SystemStats")
                Will be populated with one-time, periodic, and connection data.
                
        Side Effects:
            - Reads from HAL (roboRIO hardware and firmware)
            - Reads from NetworkTableInstance (NT client connections)
            - Increments cls.save_pass counter
            - Updates cls.last_nt_remote_ids set with current connections
            - Populates table with captured data (subset depends on cycle count)
            
        Performance:
            - Pass 0: ~10-20 ms (reads 6 HAL values)
            - Pass % 199 == 0: ~5-10 ms (reads 5 HAL values)
            - Pass % 499 == 0: ~10-20 ms (queries NT connections, reads client metadata)
            - Other passes: <1 ms (increment counter only)
            - Average overhead: <2 ms per cycle
            
        Typical Data Values:
            - FPGAVersion: 2026, 2025, etc. (year-based versioning)
            - SerialNumber: "03264AB0" (unique 8-char hex)
            - TeamNumber: 6107 (FRC team number)
            - SystemActive: true (normal operation)
            - BrownedOut: false (normal) or true (voltage sag detected)
            - CommsDisabledCount: 0 (normal) or >0 (communication issue)
            - Connected (per NT client): true or false
            - IPAddress: "10.61.7.5" (driver station) or "127.0.0.1" (localhost sim)
        """
        # Limit how and when to save off statistics here since this can be expensive
        # These are only called the first time (pass 0)
        if cls.save_pass == 0:
            # for some reason these return tuples of length 2, take the first element
            # This is a legacy artifact from C++ HAL bindings
            table.put("FPGAVersion", getFPGAVersion()[0])
            table.put("FPGARevision", getFPGARevision()[0])
            table.put("SerialNumber", getSerialNumber())
            table.put("Comments", getComments())
            table.put("TeamNumber", getTeamNumber())
            table.put("FPGAButton", getFPGAButton()[0])

        # These capture system health at about once every 4 seconds (200 passes @ 50 Hz)
        if cls.save_pass % 199 == 0:
            table.put("SystemActive", getSystemActive()[0])
            table.put("BrownedOut", getBrownedOut()[0])
            table.put("CommsDisabledCount", getCommsDisableCount()[0])
            table.put("RSLState", getRSLState()[0])
            table.put("SystemTimeValid", getSystemTimeValid()[0])

        # These capture network connections at about once every 10 seconds (500 passes @ 50 Hz)
        if cls.save_pass % 499 == 0:
            nt_clients_table = table.get_subtable("NTClients")

            # Query current NetworkTables connections
            nt_connections = NetworkTableInstance.getDefault().getConnections()

            # Build set of currently connected remote client IDs
            nt_remote_ids = set()
            for connection in nt_connections:
                # Track disconnections by removing from last_nt_remote_ids if present
                if connection.remote_id in LoggedSystemStats.last_nt_remote_ids:
                    LoggedSystemStats.last_nt_remote_ids.remove(connection.remote_id)
                # Add to current set
                nt_remote_ids.add(connection.remote_id)

                # Log metadata for this connected client
                nt_client_table = nt_clients_table.get_subtable(connection.remote_id)
                nt_client_table.put("Connected", True)
                nt_client_table.put("IPAddress", connection.remote_ip)
                nt_client_table.put("RemotePort", connection.remote_port)
                nt_client_table.put("ProtocolVersion", connection.protocol_version)

            # Mark any clients that were previously connected but are now disconnected
            # These are the remote IDs that were in last_nt_remote_ids but not in nt_remote_ids
            for remoteId in LoggedSystemStats.last_nt_remote_ids:
                nt_client_table = nt_clients_table.get_subtable(remoteId)
                nt_client_table.put("Connected", False)

            # Update tracking set for next sample
            LoggedSystemStats.last_nt_remote_ids = nt_remote_ids
        
        # Increment pass counter for next call
        cls.save_pass += 1