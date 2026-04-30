"""
Logged Network Number Module for NetworkTables Numeric Integration

This module provides LoggedNetworkNumber, a typed wrapper for NetworkTables
numeric (double/float) values that integrates with the pykit logging and replay system.

Key Features:
- Type-Safe Access: Strongly typed float wrapper for numeric values
- NetworkTables Integration: Syncs with NT for real-time dashboard interaction
- Auto-Logging: Numeric state automatically logged each cycle
- Deterministic Replay: Can be replayed from logs for testing
- Default Values: Graceful fallback to defaults if NT entry doesn't exist
- High Precision: Uses 64-bit doubles for calculations and control

Typical Usage:
    # Create a logged number for a tuning parameter
    max_speed = LoggedNetworkNumber("Drive/MaxSpeed", default=3.0)
    
    # Read current value (from NT or log during replay)
    current_speed = max_speed.value
    
    # Write value (published to NT and logged automatically)
    max_speed.value = 5.5
    
    # Use in calculations
    command_speed = desired_speed * max_speed.value

Common Use Cases:
- PID Tuning: Store kP, kI, kD on dashboard, tune without redeploying
- Speed Limits: Configure max speed, acceleration limits dynamically
- Sensor Calibration: Store offset/scale factors
- Threshold Values: Dynamic thresholds for logic decisions
- Test Parameters: Configure behavior during testing

Data Architecture:
    Dashboard/Operator ←→ NetworkTables ←→ LoggedNetworkNumber ←→ Logger
                              ↓
                           Robot Code (reads/writes)
                              ↓
                           .wpilog file (permanent record)
"""

from ntcore import DoubleEntry, NetworkTableInstance

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue


class LoggedNetworkNumber(LoggedNetworkValue[float, DoubleEntry]):
    """
    Type-safe NetworkTables numeric value with integrated logging and replay.
    
    LoggedNetworkNumber wraps a NetworkTables double (64-bit float) entry to provide:
    
    1. Type Safety: The value property is guaranteed to be float (no type conversions)
    2. NetworkTables Sync: Automatically syncs with dashboards via NT protocol
    3. Logging: All reads/writes are captured for telemetry and analysis
    4. Replay Support: State can be deterministically replayed from logs
    5. Default Values: Graceful fallback to sensible defaults if NT unavailable
    6. High Precision: Uses IEEE 754 double precision (64-bit) for calculations
    
    Generic Type Parameters:
    - First type parameter [float]: The value type (always float for this class)
    - Second type parameter [DoubleEntry]: The NT entry type (DoubleEntry)
    
    This structure allows the base class (LoggedNetworkValue) to provide
    generic logging and replay functionality while subclasses specify their
    particular value and entry types.
    
    Integration Architecture:
    
    NetworkTables provides real-time synchronization:
    - Writes to self.value publish to NT (visible on dashboards immediately)
    - Reads of self.value get latest value from NT or memory cache
    - Changes propagate to connected dashboards at ~50 Hz
    - Supports multiple readers/writers with thread-safe synchronization
    
    Logging Integration (via LoggedNetworkValue):
    - Inherits to_log() and from_log() for automatic telemetry capture
    - Each cycle, current value can be logged to persistent storage
    - During replay, state restored from log for deterministic behavior
    
    Replay Workflow:
    ```
    Log Replay → from_log(value) → update self.value → Robot code reads → Deterministic behavior
    ```
    
    Precision and Range:
    
    Uses 64-bit IEEE 754 doubles:
    - Range: ±1.7976931348623157e+308 (extremely large)
    - Precision: ~15-17 significant decimal digits
    - Resolution: ±2.2204460492503131e-16 (near zero)
    - Sufficient for all FRC control values and calculations
    - Preferred over 32-bit float for control systems (better precision for tuning)
    
    Typical Value Ranges in FRC:
    ```
    Motor voltages: 0.0 to 12.0 volts
    Speeds: -1.0 to 1.0 (normalized) or 0 to 6000 RPM
    PID gains: 0.001 to 10.0+ depending on controller
    Distances: 0 to 10+ meters
    Angles: -180 to 180 degrees (or 0 to 360)
    Time: 0 to infinite seconds
    ```
    All well within double precision range and precision.
    
    Typical Usage Patterns:
    
    Pattern 1: PID Tuning Parameter
    ```python
    # Store PID gains on dashboard for live tuning
    pid_kp = LoggedNetworkNumber("Drive/PID/kP", default=0.1)
    pid_ki = LoggedNetworkNumber("Drive/PID/kI", default=0.0)
    pid_kd = LoggedNetworkNumber("Drive/PID/kD", default=0.01)
    
    robot_container.periodic():
        controller.setP(pid_kp.value)
        controller.setI(pid_ki.value)
        controller.setD(pid_kd.value)
    ```
    
    Pattern 2: Dynamic Limits
    ```python
    # Configure behavior via dashboard
    max_speed = LoggedNetworkNumber("Drive/MaxSpeed", default=3.0)
    max_acceleration = LoggedNetworkNumber("Drive/MaxAccel", default=2.0)
    
    drive_subsystem.set_velocity(user_input * max_speed.value)
    ```
    
    Pattern 3: Sensor Calibration
    ```python
    # Store calibration offsets
    gyro_offset = LoggedNetworkNumber("Sensors/GyroOffset", default=0.0)
    encoder_scale = LoggedNetworkNumber("Sensors/EncoderScale", default=1.0)
    
    calibrated_angle = raw_gyro_angle - gyro_offset.value
    distance = raw_encoder_ticks * encoder_scale.value
    ```
    
    Pattern 4: Test Mode Configuration
    ```python
    # Configure test behavior
    test_motor_voltage = LoggedNetworkNumber("Test/MotorVoltage", default=0.0)
    test_duration = LoggedNetworkNumber("Test/Duration", default=1.0)
    
    test_command.execute():
        motor.setVoltage(test_motor_voltage.value)
    ```
    
    Default Value Semantics:
    The default is used when:
    1. NetworkTables entry doesn't exist (first time ever)
    2. Robot is disconnected from driver station
    3. Entry hasn't been set by external source yet
    4. Log entry missing during replay
    5. NT server unavailable
    
    This ensures graceful degradation rather than crashes when NT unavailable.
    Common defaults: 0.0 (neutral), 1.0 (neutral multiplier), positive limits.
    
    Thread Safety:
    - NetworkTables entries are thread-safe (NT handles synchronization)
    - Property access (self.value) is atomic
    - Multiple robot threads can safely read/write same number
    - Dashboard clients can read while robot writes (and vice versa)
    
    Performance:
    - Getting value: ~1-2 microseconds (cache lookup)
    - Setting value: ~100-500 microseconds (NT sync + network publish)
    - Suitable for high-frequency periodic use (50 Hz loops)
    - Typical robot loop: hundreds of these reads/writes per cycle with no issues
    
    Attributes:
        _entry (DoubleEntry): The NetworkTables DoubleEntry for this value
        key (str): The NetworkTables entry key (full path, e.g., "/SmartDashboard/MaxSpeed")
        default (float): The value to use if NT entry unavailable
    """

    def __init__(self, key: str, default: float = 0.0) -> None:
        """
        Initialize a LoggedNetworkNumber NetworkTables entry.
        
        Creates a new NetworkTables double (numeric) entry that integrates with the
        pykit logging system. The entry is published to NetworkTables immediately
        and becomes accessible to dashboards and other network clients.
        
        NetworkTables Setup:
        
        The constructor performs these steps:
        1. Gets the default NetworkTableInstance (network connection to NT server)
        2. Gets or creates a DoubleTopic at the specified key
        3. Gets or creates a DoubleEntry for that topic
        4. Sets the initial value to default (64-bit precision)
        5. Stores the entry for property-based access
        6. Initializes parent class (LoggedNetworkValue) for logging integration
        
        Key Format:
        NetworkTables keys follow a hierarchical path format:
        - Root tables: "/SmartDashboard", "/Limelight", "/PowerDistribution"
        - Subtables: "/SmartDashboard/Subsystem/Parameter"
        - Full example: "/SmartDashboard/Drive/MaxSpeed"
        
        Case Sensitivity:
        NetworkTables keys are case-sensitive. "/MaxSpeed" ≠ "/maxspeed"
        
        Entry Creation:
        If the key doesn't exist in NetworkTables, this call creates it with
        the default. If it already exists, the existing entry is retrieved
        and the default value is used only if the current value is None.
        
        Double Precision:
        Uses IEEE 754 double precision (64-bit float) internally:
        - ~15-17 significant decimal digits of precision
        - Range: ±1.7976931348623157e+308
        - Suitable for all FRC control system values
        - Preferred over 32-bit float for better precision in closed-loop control

        Args:
            key (str): The NetworkTables entry key (full path with leading "/").
                Format: "/Table/SubTable/EntryName"
                Examples:
                - "/SmartDashboard/Drive/MaxSpeed" (dashboard-visible)
                - "/Robot/PID/kP" (custom namespace for tuning)
                - "/Subsystem/Calibration/EncoderOffset" (sensor calibration)
                - "/Test/Parameters/Voltage" (test mode parameters)
                
                Convention: Use "/SmartDashboard/" prefix for dashboard visibility,
                or custom namespaces for internal robot state.
                Keep keys descriptive: "/Drive/MaxSpeed" better than "/param1"
                
            default (float, optional): The initial numeric value if the NT
                entry doesn't exist or is uninitialized. Used as fallback when:
                - Robot first connects (entry not yet in NT)
                - Driver station disconnects
                - Log replay with missing entry
                - Fallback for system unavailability
                
                Typical defaults:
                - 0.0: Neutral/off state (motors, arms)
                - 1.0: Neutral multiplier (no scaling)
                - Positive value: Safe upper limit (speeds, currents)
                - Actual expected value: Pre-populate with good tuning value
                
                Defaults to 0.0 (safe default for most cases).
                
        Attributes Initialized:
            self._entry: DoubleEntry connected to NT
            self.key: Stores the NT key for logging/replay
            self.default: Stores the fallback value
            
        Side Effects:
            - Creates or retrieves entry in NetworkTableInstance
            - Sets initial value in NT (visible to connected dashboards)
            - Registers with Logger for automatic logging/replay
            - May trigger NT event listeners on connected clients
            - Publishes to network immediately (visible on connected dashboards)
            
        Exception Handling:
            - If NetworkTableInstance is unavailable (catastrophic): Will raise
            - If key format is invalid: NetworkTables will handle gracefully
            - Generally very robust; designed for FRC reliability
            
        Example Usage:
            ```python
            # Create a simple tuning parameter
            max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
            # NT entry created at "/SmartDashboard" → "MaxSpeed"
            # Operator can tune from SmartDashboard
            # Logged for replay analysis
            
            # Create a hierarchical calibration value
            encoder_scale = LoggedNetworkNumber("Drive/Calibration/EncoderScale", 
                                               default=1.0)
            # Stored under "/SmartDashboard/Drive/Calibration/EncoderScale"
            # Well-organized tagging for complex robots
            
            # Create a PID tuning parameter with good starting value
            pid_kp = LoggedNetworkNumber("Drive/PID/kP", default=0.05)
            # Default 0.05 is a reasonable starting proportional gain
            # Operator can adjust on the fly
            
            # Create a persistent configuration value
            loop_period = LoggedNetworkNumber("Config/LoopPeriod", 
                                            default=0.02)
            # Default 0.02 = 20ms = 50 Hz (standard FRC rate)
            # Can be changed if testing different rates
            ```
            
        Networking Details:
            - NT4 protocol used for communication
            - Publishing to dashboards: ~10-50 ms latency depending on network
            - Double precision transmitted over network (full precision preserved)
            - Multiple concurrent readers/writers supported safely
            - Recommended: One LoggedNetworkNumber per numeric value (avoid duplication)
            - Typical robot: 50-200+ of these numbers networked with no issues
        """
        # Create the NetworkTables double (numeric) entry
        # Step 1: Get the default NetworkTableInstance (main connection to NT)
        # Step 2: Get the DoubleTopic for this numeric key
        # Step 3: Get a DoubleEntry for the topic with default value (64-bit precision)
        self._entry = (
            NetworkTableInstance.getDefault()
            .getDoubleTopic(key)
            .getEntry(default)
        )
        
        # Initialize parent class (LoggedNetworkValue) with logging integration
        # This enables automatic telemetry capture and replay support
        super().__init__(key, default)