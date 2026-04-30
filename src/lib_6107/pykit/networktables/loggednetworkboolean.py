"""
Logged Network Boolean Module for NetworkTables Boolean Integration

This module provides LoggedNetworkBoolean, a typed wrapper for NetworkTables
boolean values that integrates with the pykit logging and replay system.

Key Features:
- Type-Safe Access: Strongly typed boolean wrapper (no runtime type confusion)
- NetworkTables Integration: Syncs with NT for real-time dashboard interaction
- Auto-Logging: Boolean state automatically logged each cycle
- Deterministic Replay: Can be replayed from logs for testing
- Default Values: Graceful fallback to defaults if NT entry doesn't exist

Typical Usage:
    # Create a logged boolean for a subsystem state
    intake_enabled = LoggedNetworkBoolean("Intake/Enabled", default=False)
    
    # Read current state (from NT or log during replay)
    if intake_enabled.value:
        intake.enable()
    
    # Write state (published to NT and logged automatically)
    intake_enabled.value = True

Data Architecture:
    Dashboard/Operator ←→ NetworkTables ←→ LoggedNetworkBoolean ←→ Logger
                                              ↓
                                           Robot Code
                                              ↓
                                          .wpilog file
"""

from ntcore import BooleanEntry, NetworkTableInstance

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue


class LoggedNetworkBoolean(LoggedNetworkValue[bool, BooleanEntry]):
    """
    Type-safe NetworkTables boolean with integrated logging and replay.
    
    LoggedNetworkBoolean wraps a NetworkTables boolean entry to provide:
    
    1. Type Safety: The value property is guaranteed to be bool (no type conversions)
    2. NetworkTables Sync: Automatically syncs with dashboards via NT protocol
    3. Logging: All reads/writes are captured for telemetry and analysis
    4. Replay Support: State can be deterministically replayed from logs
    5. Default Values: Graceful fallback to sensible defaults if NT unavailable
    
    Generic Type Parameters:
    - First type parameter [bool]: The value type (always bool for this class)
    - Second type parameter [BooleanEntry]: The NT entry type (BooleanEntry)
    
    This structure allows the base class (LoggedNetworkValue) to provide
    generic logging and replay functionality while subclasses specify their
    particular value and entry types.
    
    Integration Architecture:
    
    NetworkTables provides real-time synchronization:
    - Writes to self.value publish to NT (visible on dashboards immediately)
    - Reads of self.value get latest value from NT or memory cache
    - Changes propagate to connected dashboards at ~50 Hz
    
    Logging Integration (via LoggedNetworkValue):
    - Inherits to_log() and from_log() for automatic telemetry capture
    - Each cycle, current value can be logged to persistent storage
    - During replay, state restored from log for deterministic behavior
    
    Replay Workflow:
    ```
    Log Replay → from_log(value) → update self.value → Robot code reads → Deterministic behavior
    ```
    
    Typical Usage Patterns:
    
    Pattern 1: Dashboard Toggle
    ```python
    # Operator controls via SmartDashboard checkbox
    debug_mode = LoggedNetworkBoolean("Debug/Enabled", default=False)
    
    robot_container.periodic():
        if debug_mode.value:
            enable_debug_logging()
    ```
    
    Pattern 2: Subsystem State Indicator
    ```python
    # Subsystem publishes its enabled state for telemetry
    intake_running = LoggedNetworkBoolean("Intake/Running", default=False)
    
    intake_subsystem.periodic():
        intake_running.value = self.is_running()  # Publish state
    ```
    
    Pattern 3: Robot Configuration
    ```python
    # Persistent configuration that survives reboots via NT persistence
    use_vision = LoggedNetworkBoolean("Config/Vision", default=True)
    
    robotInit():
        if use_vision.value:
            enable_vision_processor()
    ```
    
    Default Value Semantics:
    The default is used when:
    1. NetworkTables entry doesn't exist (first time ever)
    2. Robot is disconnected from driver station
    3. Entry hasn't been set by external source yet
    4. Log entry missing during replay
    
    This ensures graceful degradation rather than crashes when NT unavailable.
    
    Thread Safety:
    - NetworkTables entries are thread-safe (NT handles synchronization)
    - Property access (self.value) is atomic
    - Multiple robot threads can safely read/write same boolean
    - Dashboard clients can read while robot writes (and vice versa)
    
    Performance:
    - Getting value: ~1-2 microseconds (cache lookup)
    - Setting value: ~100-500 microseconds (NT sync + network publish)
    - Suitable for high-frequency periodic use (50 Hz loops)
    - Avoid spamming writes in tight loops if many booleans networked
    
    Attributes:
        _entry (BooleanEntry): The NetworkTables BooleanEntry for this value
        key (str): The NetworkTables entry key (full path, e.g., "/SmartDashboard/Debug")
        default (bool): The value to use if NT entry unavailable
    """

    def __init__(self, key: str, default: bool = False) -> None:
        """
        Initialize a LoggedNetworkBoolean NetworkTables entry.
        
        Creates a new NetworkTables boolean entry that integrates with the pykit
        logging system. The entry is published to NetworkTables immediately and
        becomes accessible to dashboards and other network clients.
        
        NetworkTables Setup:
        
        The constructor performs these steps:
        1. Gets the default NetworkTableInstance (network connection to NT server)
        2. Gets or creates a BooleanTopic at the specified key
        3. Gets or creates a BooleanEntry for that topic
        4. Sets the initial value to default
        5. Stores the entry for property-based access
        6. Initializes parent class (LoggedNetworkValue) for logging integration
        
        Key Format:
        NetworkTables keys follow a hierarchical path format:
        - Root tables: "/SmartDashboard", "/Limelight", "/PowerDistribution"
        - Subtables: "/SmartDashboard/Subsystem/Feature"
        - Full example: "/SmartDashboard/Intake/RunEnabled"
        
        Case Sensitivity:
        NetworkTables keys are case-sensitive. "/Debug" ≠ "/debug"
        
        Entry Creation:
        If the key doesn't exist in NetworkTables, this call creates it with
        the default. If it already exists, the existing entry is retrieved
        and the default value is used only if the current value is None.

        Args:
            key (str): The NetworkTables entry key (full path with leading "/").
                Format: "/Table/SubTable/EntryName"
                Examples:
                - "/SmartDashboard/Debug/Enabled" (dashboard-visible)
                - "/Robot/Intake/Running" (custom namespace)
                - "/Subsystem/State/HasBall" (hierarchical subsystem state)
                
                Convention: Use "/SmartDashboard/" prefix for dashboard visibility,
                or custom namespaces for internal robot state.
                
            default (bool, optional): The initial boolean value if the NT
                entry doesn't exist or is uninitialized. Used as fallback when:
                - Robot first connects (entry not yet in NT)
                - Driver station disconnects
                - Log replay with missing entry
                - Fallback for system unavailability
                Defaults to False (recommended for safety-critical features).
                
        Attributes Initialized:
            self._entry: BooleanEntry connected to NT
            self.key: Stores the NT key for logging/replay
            self.default: Stores the fallback value
            
        Side Effects:
            - Creates or retrieves entry in NetworkTableInstance
            - Sets initial value in NT (visible to connected dashboards)
            - Registers with Logger for automatic logging/replay
            - May trigger NT event listeners on connected clients
            
        Exception Handling:
            - If NetworkTableInstance is unavailable (catastrophic): Will raise
            - If key format is invalid: NetworkTables will handle gracefully
            - Generally very robust; designed for FRC reliability
            
        Example Usage:
            ```python
            # Create a simple boolean for debugging
            debug_enabled = LoggedNetworkBoolean("Debug/Enabled", default=False)
            # NT entry created at "/SmartDashboard" → "Debug" → "Enabled"
            # Operator can toggle from SmartDashboard
            
            # Create a subsystem state indicator
            intake_has_note = LoggedNetworkBoolean("Intake/HasNote", default=False)
            # Subsystem updates this each cycle: intake_has_note.value = has_note()
            # Visible on dashboard and logged for later analysis
            
            # Create a persistent configuration value
            use_vision = LoggedNetworkBoolean("Config/Vision", default=True)
            # If set via NT Persistent module, survives robot reboots
            # Robot reads this during initialization
            ```
            
        Networking Details:
            - NT4 protocol used for communication
            - Publishing to dashboards: ~10-50 ms latency depending on network
            - Multiple concurrent readers/writers supported safely
            - Recommended: One LoggedNetworkBoolean per boolean value (avoid duplication)
        """
        # Create the NetworkTables boolean entry
        # Step 1: Get the default NetworkTableInstance (main connection to NT)
        # Step 2: Get the BooleanTopic for this key
        # Step 3: Get a BooleanEntry for the topic with default value
        self._entry = (
            NetworkTableInstance.getDefault()
            .getBooleanTopic(key)
            .getEntry(default)
        )
        
        # Initialize parent class (LoggedNetworkValue) with logging integration
        # This enables automatic telemetry capture and replay support
        super().__init__(key, default)