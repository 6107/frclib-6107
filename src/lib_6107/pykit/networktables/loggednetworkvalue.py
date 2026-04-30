"""
Logged Network Value Module for Generic NetworkTables Integration

This module provides LoggedNetworkValue, a generic base class for all NetworkTables
values that need to be logged and replayed. It serves as the foundation for type-safe
wrappers around NetworkTables entries (booleans, numbers, strings, etc.).

Architecture:
The module uses Python generics to provide compile-time type safety while allowing
a single implementation to handle multiple NetworkTables entry types:
- T: The Python value type (bool, float, str, int)
- V: The NetworkTables entry type (BooleanEntry, DoubleEntry, StringEntry, IntegerEntry)

Subclass Pattern:
All NetworkTables value wrappers inherit from LoggedNetworkValue:
    LoggedNetworkValue[bool, BooleanEntry] → LoggedNetworkBoolean
    LoggedNetworkValue[float, DoubleEntry] → LoggedNetworkNumber
    LoggedNetworkValue[str, StringEntry] → LoggedNetworkString
    LoggedNetworkValue[int, IntegerEntry] → LoggedNetworkInteger (hypothetical)

Key Features:
- Type Safety: Uses Python generics for compile-time type checking
- Automatic Logging: Values logged each cycle for telemetry
- Deterministic Replay: Values can be replayed from logs
- Property-Based Access: value property for easy read/write
- Callable Interface: Objects can be called to get value (obj() returns obj.value)
- Default Values: Graceful fallback when NT unavailable

Lifecycle Integration:
    periodic() called by Logger each cycle
        ↓
    Sync with NetworkTables (normal mode) or Log (replay mode)
        ↓
    Logger.processInputs() → calls to_log() or from_log()
        ↓
    Value persisted to telemetry
        ↓
    repeat next cycle

Data Flow:
Normal Mode: NetworkTables → periodic() → to_log() → Logger → .wpilog
Replay Mode: .wpilog → from_log() → periodic() → Robot Code → Analysis Tools
"""

from typing import Generic, TypeVar, Union

from ntcore import (
    BooleanEntry,
    DoubleEntry,
    IntegerEntry,
    StringEntry,
)

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput

#: Type alias for all supported NetworkTables entry types
#: - DoubleEntry: 64-bit floating point numbers
#: - BooleanEntry: Boolean true/false values
#: - StringEntry: Unicode text strings
#: - IntegerEntry: 64-bit signed integers
NTEntry = Union[
    DoubleEntry,
    BooleanEntry,
    StringEntry,
    IntegerEntry,
]

#: Type alias for all supported Python value types
#: - float: Corresponds to DoubleEntry (64-bit IEEE 754)
#: - bool: Corresponds to BooleanEntry
#: - str: Corresponds to StringEntry (UTF-8 encoded)
#: - int: Corresponds to IntegerEntry (64-bit signed)
PyNTValue = Union[float, bool, str, int]

#: Type variable T: Represents the Python value type
#: Constrained to PyNTValue types (float, bool, str, int)
#: Used in Generic[T, V] to ensure type safety
T = TypeVar("T", bound=PyNTValue)

#: Type variable V: Represents the NetworkTables entry type
#: Constrained to NTEntry types (DoubleEntry, BooleanEntry, etc.)
#: Used in Generic[T, V] to ensure type safety
#: V must be the entry type corresponding to T
V = TypeVar("V", bound=NTEntry)


class LoggedNetworkValue(LoggedNetworkInput, Generic[T, V]):
    """
    Generic base class for type-safe loggable NetworkTables values.
    
    LoggedNetworkValue provides the framework for all NetworkTables values that need
    to be integrated with the pykit logging system. It handles:
    
    1. Type Safety: Uses Python generics [T, V] to enforce type consistency
       - T: The Python value type (bool, float, str, int)
       - V: The NetworkTables entry type (BooleanEntry, DoubleEntry, etc.)
    
    2. NetworkTables Synchronization:
       - Reads from NT each cycle (normal mode)
       - Writes to NT when value property is set
       - Publishing to dashboards via NT protocol
    
    3. Logging Integration:
       - Automatic logging of all values via to_log()
       - Deterministic replay via from_log()
       - Integration with Logger for periodic updates
    
    4. Default Value Management:
       - Fallback when NT entry unavailable
       - Graceful degradation if system offline
       - Customizable default behavior
    
    Inheritance Hierarchy:
    ```
    LoggedNetworkInput (abstract base)
            ↑
            |
    LoggedNetworkValue[T, V] (generic framework)
            ↑
            |
            ├── LoggedNetworkBoolean[bool, BooleanEntry]
            ├── LoggedNetworkNumber[float, DoubleEntry]
            ├── LoggedNetworkString[str, StringEntry]
            └── [Other typed wrappers...]
    ```
    
    Generic Type Usage:
    
    The class uses two type parameters to enforce type safety:
    
    - T (first parameter): The Python value type
      - Must be one of: float, bool, str, int
      - Represents what the robot code actually uses
      - Examples: bool for LoggedNetworkBoolean, float for LoggedNetworkNumber
    
    - V (second parameter): The NetworkTables entry type
      - Must be one of: DoubleEntry, BooleanEntry, StringEntry, IntegerEntry
      - Represents the NT backend storage
      - Examples: BooleanEntry for bool, DoubleEntry for float
    
    Type Correspondence:
    ```
    T (Python)          V (NetworkTables)       Subclass
    ─────────────────────────────────────────────────────
    bool                BooleanEntry            LoggedNetworkBoolean
    float               DoubleEntry             LoggedNetworkNumber
    str                 StringEntry             LoggedNetworkString
    int                 IntegerEntry            LoggedNetworkInteger (if existed)
    ```
    
    Usage Pattern (Subclass Implementation):
    
    ```python
    class LoggedNetworkBoolean(LoggedNetworkValue[bool, BooleanEntry]):
        def __init__(self, key: str, default: bool = False):
            # Create the NT entry (subclass responsibility)
            self._entry = (
                NetworkTableInstance.getDefault()
                .get_booleanTopic(key)
                .get_entry(default)
            )
            # Initialize base class
            super().__init__(key, default)
    ```
    
    Lifecycle During Robot Operation:
    
    Each cycle (~50 Hz):
    1. Logger.periodicBeforeUser() calls periodic() on all registered inputs
    2. periodic() checks if in replay mode:
       - Normal: Reads _entry from NT, updates self._value
       - Replay: Skips (value will be set by from_log())
    3. Logger.processInputs() calls to_log() or from_log():
       - Normal: to_log() saves value to log table
       - Replay: from_log() restores value from log table
    4. Robot periodic code executes (can read self.value)
    5. Value published to NetworkTables (if NT connected)
    6. Value persisted to .wpilog file for later analysis
    
    Thread Safety:
    - NetworkTables entries are thread-safe
    - Python property access (self.value) is atomic
    - Multiple threads can safely read/write same value
    - No synchronization required by user code
    
    Performance:
    - Getting value: ~1-2 microseconds (property access)
    - Setting value: ~0.1-0.5 milliseconds (NT sync + network)
    - Suitable for 50 Hz robot loop with hundreds of values
    
    Attributes:
        _key (str): The NetworkTables entry key
        _value (T): Current cached value
        _default (T): Fallback value if NT unavailable
        _entry (V): The actual NetworkTables entry for hardware access
        prefix (str): Inherited from LoggedNetworkInput (default: "NetworkInputs")
    """

    _value: T
    """Current cached value of type T. Updated from NT each cycle."""
    
    _default: T
    """Default/fallback value used when NT entry unavailable."""
    
    _entry: V
    """The NetworkTables entry (V type) for hardware synchronization."""

    def __init__(self, key: str, default: T) -> None:
        """
        Initialize a LoggedNetworkValue with NetworkTables integration.
        
        This is the base class initializer called by all subclasses (after they
        create the _entry object). It sets up:
        1. Internal state (key, value, default)
        2. Logger integration (registers for periodic updates)
        3. NetworkTables synchronization (sets initial NT value)
        4. Default fallback configuration
        
        Call Sequence by Subclass:
        ```python
        class LoggedNetworkBoolean(LoggedNetworkValue[bool, BooleanEntry]):
            def __init__(self, key, default=False):
                # Step 1: Create the NT entry
                self._entry = NetworkTableInstance.getDefault()\\
                    .getBooleanTopic(key)\\
                    .getEntry(default)
                
                # Step 2: Call base class init
                super().__init__(key, default)  # THIS METHOD
        ```
        
        Initialization Steps:
        1. Store key for later logging/replay
        2. Initialize value to default
        3. Register with Logger for periodic() calls
        4. Set the NT entry to the default value
        5. Configure default fallback behavior

        Args:
            key (str): The NetworkTables entry key (e.g., "/SmartDashboard/MaxSpeed")
                Must match the key used when creating self._entry in subclass
                Used for logging and identifying the entry
                
            default (T): The initial/fallback value of type T
                Used when:
                - First connecting (NT entry doesn't exist yet)
                - During testing/offline operation
                - Log replay with missing entries
                - System unavailability
                
                Type T depends on subclass:
                - LoggedNetworkBoolean: bool (e.g., False)
                - LoggedNetworkNumber: float (e.g., 0.0)
                - LoggedNetworkString: str (e.g., "")
                
        Attributes Initialized:
            self._key: Stores the NT key
            self._value: Set to default
            self._default: Set to default (can be changed via setDefault)
            
        Side Effects:
            - Registers with Logger via Logger.registerDashboardInput(self)
            - Publishes default to NT via self._entry.set()
            - Configures NT default behavior via self.setDefault()
            - Makes periodic() callable by Logger
            
        Note:
            Subclasses MUST create self._entry before calling super().__init__().
            The entry is used by setDefault() and during periodic() calls.
            
        Example:
            ```python
            # Subclass pattern
            self._entry = NetworkTableInstance.getDefault()\\
                .getBooleanTopic(key)\\
                .getEntry(default)
            super().__init__(key, default)  # Call this to finish initialization
            ```
        """
        # Store the key for later use in logging/replay
        self._key = key
        
        # Initialize the cached value to the default
        self._value = default
        
        # Store the default for fallback usage
        self._default = default
        
        # Register with Logger so periodic() is called each cycle
        Logger.registerDashboardInput(self)

        # Set the initial value in NetworkTables
        # This makes the value visible to dashboards immediately
        self._entry.set(default)
        
        # Configure NT default behavior (fallback if entry unavailable)
        self.set_default(default)

    def __call__(self) -> T:
        """
        Make the object callable to retrieve its value.
        
        This allows convenient syntax for getting the current value:
        ```python
        max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
        speed = max_speed()  # Same as max_speed.value
        ```
        
        Useful in contexts where a callable is expected or for compact syntax.
        Equivalent to accessing the value property.

        Returns:
            T: The current value of the same type as initialized
            
        Example:
            ```python
            enabled = LoggedNetworkBoolean("Enabled", default=False)
            
            # These are equivalent:
            is_enabled = enabled.value
            is_enabled = enabled()
            
            if enabled():  # Compact syntax in conditionals
                do_something()
            ```
        """
        return self.value

    @property
    def value(self) -> T:
        """
        Get the current value of this NetworkTables entry.
        
        Returns the cached value. In normal mode, this is updated from NT each
        cycle during periodic(). In replay mode, this is updated from the log
        file via from_log().
        
        Type Safety:
        The return type is T (the Python value type), guaranteed by the generic
        type parameter. No type conversion needed - type checker knows the type.
        
        Performance:
        Getting value is O(1) - simple attribute access (~1-2 microseconds).
        Safe to call frequently (50+ times per cycle if needed).

        Returns:
            T: The current value with guaranteed type:
               - bool if LoggedNetworkBoolean
               - float if LoggedNetworkNumber
               - str if LoggedNetworkString
               - int if LoggedNetworkInteger
               
        Example:
            ```python
            max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
            current = max_speed.value  # Returns float
            
            enabled = LoggedNetworkBoolean("Enabled", default=False)
            is_on = enabled.value  # Returns bool
            ```
        """
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        """
        Set the value of this NetworkTables entry.
        
        Updates the cached value immediately. Note that setting the value does NOT
        automatically publish to NetworkTables - that happens during the next
        periodic() cycle when periodic() reads from _entry.
        
        The value is logged automatically during to_log() in the next logging cycle.
        
        Type Safety:
        The setter enforces the correct type T. Passing the wrong type will fail:
        ```python
        max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
        max_speed.value = 5.0  # OK - float matches T
        max_speed.value = "5"  # Type error - str doesn't match float
        ```

        Args:
            value (T): The new value, must match the expected type T:
                - bool for LoggedNetworkBoolean
                - float for LoggedNetworkNumber
                - str for LoggedNetworkString
                - int for LoggedNetworkInteger
                
        Side Effects:
            - Updates self._value immediately
            - Value will be published to NT in next cycle (during periodic)
            - Value will be logged in next logging cycle (during to_log)
            - Change may trigger NT event listeners
            
        Note:
            Setting the value does NOT immediately write to NT. Writing happens
            asynchronously during periodic(), ensuring non-blocking behavior.
            
        Example:
            ```python
            max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
            
            max_speed.value = 5.5  # Update immediately
            # Value published to NT in ~1-20ms
            # Value logged in ~20ms (next cycle)
            
            enabled = LoggedNetworkBoolean("Enabled", default=False)
            enabled.value = True  # Boolean state updated
            ```
        """
        self._value = value

    def set_default(self, default: T) -> None:
        """
        Update the default/fallback value for this entry.
        
        The default value is used when the NetworkTables entry is unavailable
        (robot offline, NT server not running, etc.). Changing this allows
        updating fallback behavior during runtime.
        
        This affects behavior during:
        - Robot startup (if NT not yet initialized)
        - Offline/simulation scenarios
        - Log replay if entry missing from log
        - NT connection loss
        
        The default is also set in NetworkTables (via _entry) for other clients
        to see the preferred fallback value.

        Args:
            default (T): The new default/fallback value of type T
                Should be a safe/neutral value:
                - False for booleans (safest is off/disabled)
                - 0.0 for numbers (neutral/no-op)
                - "" for strings (empty default)
                
        Side Effects:
            - Updates self._defaultValue
            - Updates _entry's default (via NetworkTables)
            - Affects fallback behavior during NT unavailability
            
        Typical Usage:
            ```python
            # Create with one default, change later if needed
            max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
            
            # Use default value...
            
            # Update default mid-match if behavior changes
            max_speed.setDefault(2.0)  # Reduced default
            
            # Now if NT becomes unavailable, fallback is 2.0 instead of 3.0
            ```
            
        Note:
            This is typically called during initialization, but can be changed
            during runtime if needed. Does not affect current value, only the
            fallback.
        """
        self._default = default

    def to_log(self, table: LogTable, prefix: str) -> None:
        """
        Save the current value to the log table.
        
        Called by Logger.processInputs() during normal operation to record the
        current value into the telemetry log. This creates a permanent record
        of what the value was at this moment in time.
        
        The value is stored at: {prefix}/{key_without_leading_slash}
        
        Logging in Normal Mode:
        During normal robot operation, to_log() is called each cycle to save
        the current state. This enables:
        - Replay: Exact state can be reproduced
        - Analysis: See how values changed throughout match
        - Debugging: Correlate value changes with events

        Args:
            table (LogTable): The log table to write the value to
                Typically passed from Logger.processInputs()
                
            prefix (str): The prefix path within the log (e.g., "/SmartDashboard")
                Combined with the key to form the full log path
                Leading slash in key is removed before combining
                
        Side Effects:
            - Writes self._value to the log table
            - Entry persisted to .wpilog file
            - Value visible in AdvantageScope and other log analyzers
            
        Log Path:
            Full log key = "{prefix}/{remove_slash(self._key)}"
            Example:
            ```
            prefix = "/SmartDashboard"
            self._key = "/MaxSpeed"
            final_key = "/SmartDashboard/MaxSpeed"
            ```
            
        Note:
            This method is called automatically by Logger. It's not typically
            called directly by user code.
            
        Replay Compatibility:
            The value logged here is restored via from_log() during replay,
            ensuring deterministic playback.
        """
        table.put(f"{prefix}/{LoggedNetworkInput.remove_slash(self._key)}", self._value)

    def from_log(self, table: LogTable, prefix: str) -> None:
        """
        Load the value from the log table.
        
        Called by Logger.processInputs() during replay mode to restore the
        value from a previously recorded log file. This allows the robot to
        see the exact same values it saw during the original match, enabling
        deterministic replay for testing and analysis.
        
        The value is loaded from: {prefix}/{key_without_leading_slash}
        
        Logging in Replay Mode:
        During log replay, from_log() is called each cycle to restore the state
        that was recorded. This enables:
        - Deterministic Testing: Exact same inputs as original match
        - Bug Reproduction: See exactly what happened
        - Algorithm Development: Test new algorithms with real match data
        - What-If Analysis: Change code and replay with same match data

        Args:
            table (LogTable): The log table to read the value from
                Contains all data from one timestamp of the original log
                
            prefix (str): The prefix path within the log (e.g., "/SmartDashboard")
                Combined with the key to form the full log path
                Leading slash in key is removed before combining
                
        Side Effects:
            - Reads value from log table at combined key path
            - Updates self._value (replaces current value)
            - Fallback to self._defaultValue if log entry missing
            - Change may trigger value setter side effects
            
        Log Path:
            Full log key = "{prefix}/{remove_slash(self._key)}"
            Example (same as to_log):
            ```
            prefix = "/SmartDashboard"
            self._key = "/MaxSpeed"
            final_key = "/SmartDashboard/MaxSpeed"
            ```
            
        Fallback Behavior:
            If the log entry doesn't exist (corrupt log, different code version):
            ```python
            self._value = table.get(key, self._defaultValue)
            # Uses default if key not found
            ```
            This gracefully handles incomplete logs.
            
        Note:
            This method is called automatically by Logger only in replay mode.
            In normal operation, this is never called.
            
        Replay Determinism:
            The value restored here is the same value that was logged via to_log(),
            ensuring exact replay of the original execution.
        """
        self._value = table.get(
            f"{prefix}/{LoggedNetworkInput.remove_slash(self._key)}",
            self._default,
        )

    def periodic(self) -> None:
        """
        Update the value each robot cycle (~50 Hz).
        
        Called by Logger.periodicBeforeUser() approximately 50 times per second.
        This method handles the mode-specific synchronization:
        - Normal Mode: Reads from NetworkTables, publishes to dashboards
        - Replay Mode: Loads from LOG file via Logger.processInputs()
        
        Execution Flow:
        
        1. Check robot mode:
           - Not replay: Read from NetworkTables (_entry.get())
           - Is replay: Skip (value will be set by from_log())
        
        2. Call Logger.processInputs() to trigger logging:
           - Normal: Calls self.to_log() to save value
           - Replay: Calls self.from_log() to restore value from log
        
        The mode is determined by Logger.isReplay() which checks if a replay
        source was set via Logger.setReplaySource(). If set, we're replaying.
        
        Cycle Timing (Typical):
        
        ```
        t=0ms    Logger.periodicBeforeUser()
                 └─→ periodic() [this method]
                     ├─→ Read from NT (normal) or skip (replay)
                     └─→ Logger.processInputs()
                         ├─→ to_log() [normal]
                         └─→ from_log() [replay]
        
        t=5ms    Robot periodic code executes
                 └─→ Robot code reads self.value
        
        t=15ms   Logger.periodicAfterUser()
                 └─→ Receivers publish to NT/files
        
        t=20ms   Repeat (50 Hz = 20ms cycle)
        ```
        
        Mode Selection:
        
        Normal Mode (REAL or SIMULATION):
        - Logger.isReplay() returns False
        - periodic() reads from NT: self._value = self._entry.get()
        - Logger.processInputs() calls to_log()
        - Value saved to log and published to dashboards
        
        Replay Mode (REPLAY):
        - Logger.isReplay() returns True
        - periodic() skips NT read (stay offline)
        - Logger.processInputs() calls from_log()
        - Value restored from log file for deterministic replay
        
        Performance:
        - Typical execution: <1ms (NT read + logging overhead)
        - Safe for 50+ values per cycle with no performance issues
        
        Side Effects:
            - May update self._value from NT or log
            - Triggers to_log() or from_log() via Logger.processInputs()
            - May publish changes to NT server
            - May trigger logging/replay system
            
        Note:
            This method is called automatically by Logger. Users should not
            call this directly - it's called as part of the robot control loop.
            
        Example (How Logger Uses This):
            ```python
            # In Logger.periodicBeforeUser():
            for input in dashboard_inputs:
                input.periodic()  # Calls THIS METHOD
            
            # Result: Values synced with NT and/or log
            # Robot code then reads the values
            ```
        """
        # In normal mode, read from NetworkTables to stay synchronized
        # In replay mode, skip (value will be set by Logger.processInputs → from_log)
        if not Logger.isReplay():
            self._value = self._entry.get(self._default)
        
        # Trigger logging integration:
        # - Normal: Calls our to_log() method to save value
        # - Replay: Calls our from_log() method to restore value from log
        Logger.processInputs(self.prefix, self)