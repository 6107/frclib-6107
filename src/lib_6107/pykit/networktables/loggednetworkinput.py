"""
Logged Network Input Module for Dashboard Input Integration

This module provides LoggedNetworkInput, a base class for integrating dashboard
inputs (choosers, buttons, etc.) with the pykit logging and replay system.

LoggedNetworkInput serves as the foundation for:
- Dashboard selectors (autonomous modes, test options)
- Network buttons and controls
- Other operator interface elements that need telemetry capture

Key Features:
- Periodic Updates: Syncs with NetworkTables/dashboards each cycle
- Logging Integration: Input state automatically logged for telemetry
- Replay Support: Inputs can be replayed from logs for deterministic testing
- Hierarchical Namespacing: Configurable prefix for log organization
- Key Normalization: Utilities for consistent key path management

Inheritance Hierarchy:
    LoggedNetworkInput (base class)
        ↓
        ├── LoggedDashboardChooser (autonomous mode, test selector)
        ├── NetworkTableButton (operator trigger button)
        └── [Other dashboard input types]

All dashboard inputs follow this lifecycle:
    1. periodic() called by Logger each cycle (~50 Hz)
    2. Sync with NetworkTables (or log in replay mode)
    3. Detect changes and fire callbacks if needed
    4. Log input state via Logger.processInputs()
"""


class LoggedNetworkInput:
    """
    Abstract base class for NetworkTables inputs integrated with logging/replay.
    
    LoggedNetworkInput defines the interface and common functionality for all
    dashboard inputs that need to be logged and replayed. It provides a framework
    for:
    
    1. Periodic Synchronization: Update input state each robot cycle
    2. Logging Integration: Automatically capture input changes to telemetry
    3. Replay Support: Restore input state from logs during replay
    4. Hierarchical Organization: Organize inputs in log namespace via prefix
    
    Design Pattern:
    
    Subclasses implement this pattern:
    1. Inherit from LoggedNetworkInput
    2. Override periodic() to sync with NT/log each cycle
    3. Implement to_log() and from_log() for logging integration
    4. Register with Logger via Logger.registerDashboardInput()
    
    The Logger calls periodic() on all registered inputs during each robot cycle,
    ensuring synchronized updates across all dashboard elements.
    
    Namespace Organization:
    
    The prefix attribute organizes logged inputs hierarchically:
    ```
    Default prefix: "NetworkInputs"
    
    Logged paths using Logger.processInputs():
        /SmartDashboard/NetworkInputs/Auto/Selected
        /SmartDashboard/NetworkInputs/Test/Mode
        /SmartDashboard/NetworkInputs/Debug/Enabled
    ```
    
    This keeps all dashboard inputs organized under a common namespace in logs.
    
    Integration with Logger:
    
    Typical usage flow:
    ```python
    # Create input
    chooser = LoggedDashboardChooser("Auto")
    chooser.addOption("Score", "score")
    
    # Logger automatically registers on creation
    Logger.registerDashboardInput(chooser)
    
    # Each cycle:
    Logger.periodicBeforeUser() calls chooser.periodic()
        ↓
    periodic() syncs with NT (or log during replay)
        ↓
    Logger.processInputs() calls to_log() / from_log()
        ↓
    Input state persisted to telemetry
    ```
    
    Logging and Replay:
    
    Normal Mode (Live Operation):
    - periodic() reads state from NetworkTables
    - to_log() saves state to log table
    - State visible on dashboard in real-time
    
    Replay Mode (Log Analysis):
    - periodic() still called (via Logger.periodicBeforeUser)
    - from_log() restores state from log file
    - Robot sees exact same inputs as during original match
    - Enables deterministic playback for analysis
    
    Attributes:
        prefix (str): Namespace prefix for logging (default: "NetworkInputs").
            Can be overridden by subclasses or modified before logging.
    """

    prefix: str = "NetworkInputs"
    """
    Namespace prefix for organizing logged inputs in the telemetry hierarchy.
    
    Used by subclasses when calling Logger.processInputs():
        Logger.processInputs(self.prefix + "/SmartDashboard", self)
    
    This places inputs under "/SmartDashboard/NetworkInputs/*" in logs.
    
    Can be customized by subclasses or individual instances:
    ```python
    class CustomInput(LoggedNetworkInput):
        prefix = "CustomInputs"  # Override class-level prefix
    
    input1 = LoggedDashboardChooser("Auto")
    input1.prefix = "AnotherNamespace"  # Override instance prefix
    ```
    """

    def __init__(self) -> None:
        """
        Initialize a LoggedNetworkInput base instance.
        
        This is typically called by subclass __init__ via super().__init__().
        The base class initialization is minimal since most functionality is
        deferred to subclasses.
        
        Initialization Steps:
        1. Base class state initialized (empty, minimal)
        2. Subclass-specific initialization follows
        3. Subclass should register with Logger via Logger.registerDashboardInput()
        
        Subclass Responsibility:
        Subclasses should:
        - Call super().__init__() first to initialize base state
        - Set up their specific NetworkTables entries or widgets
        - Register with Logger if not auto-registered
        - Override periodic() and logging methods
        
        Example:
        ```python
        class MyInput(LoggedNetworkInput):
            def __init__(self, key):
                # Initialize specific to this input type
                self.entry = NetworkTableInstance.getDefault().getEntry(key)
                
                # Call base class initialization
                super().__init__()
                
                # Register with logging system
                Logger.registerDashboardInput(self)
        ```
        
        Note:
            This base constructor does nothing by design, allowing subclasses
            full flexibility in initialization. All meaningful work happens in
            subclass __init__ implementations.
        """

    def periodic(self) -> None:
        """
        Update the input's state each robot cycle.
        
        Called by Logger approximately 50 times per second (every 20 ms) during
        the robot periodic execution. Subclasses MUST override this method to
        implement their specific synchronization logic.
        
        Execution Cycle:
        
        Each robot periodic cycle (~50 Hz):
        1. Logger.periodicBeforeUser() calls this periodic() method
        2. Subclass implementation syncs state with NetworkTables or log
        3. Robot code executes and may read input state via getter methods
        4. Logger.periodicAfterUser() calls Logger.processInputs() which:
           - Calls to_log() in normal mode (save input)
           - Calls from_log() in replay mode (restore input from log)
        
        Typical Implementation (subclass example):
        
        ```python
        class CustomChooser(LoggedNetworkInput):
            def periodic(self) -> None:
                # In normal mode, sync with NetworkTables
                if not Logger.isReplay():
                    self.selected = self.nt_entry.get()
                
                # Trigger logging via Logger.processInputs()
                # This calls to_log() or from_log() depending on mode
                Logger.processInputs(self.prefix + "/SmartDashboard", self)
                
                # Fire change callbacks if value changed
                if self.selected != self.previous:
                    self.on_change_callback(self.selected)
                    self.previous = self.selected
        ```
        
        Synchronization Modes:
        
        Normal Mode (Robot Operation):
        - Read from NetworkTables (operator/dashboard changes)
        - Publish state to log via to_log()
        - Detect changes and fire callbacks
        
        Replay Mode (Log Playback):
        - Load state from log via from_log()
        - Robot sees exact state as during original match
        - Enables deterministic testing
        
        Performance Considerations:
        - Called every 20 ms in typical 50 Hz robot loop
        - Should be fast (<1 ms typically)
        - Avoid blocking I/O or expensive computations
        - Suitable for NetworkTables reads/writes (cached/efficient)
        
        Required Override:
        All subclasses MUST override this method. The base class provides
        no implementation (intentionally empty).
        
        Subclass Contract:
        When overriding, your implementation should:
        1. Update internal state from NetworkTables (or log during replay)
        2. Call Logger.processInputs() to integrate with logging
        3. Detect changes and fire change callbacks
        4. Handle both normal and replay modes appropriately
        """

    @staticmethod
    def remove_slash(key: str) -> str:
        """
        Remove a leading forward slash from a key string if present.
        
        Utility method for normalizing NetworkTables keys. NetworkTables keys
        conventionally start with "/" (e.g., "/SmartDashboard/Auto"), but some
        contexts require the leading slash removed (e.g., when composing paths).
        
        This method provides idempotent slash removal - safe to call on keys
        that may or may not have leading slashes.
        
        Key Path Conventions:
        
        NetworkTables:
        - Full paths include leading slash: "/SmartDashboard/Subsystem/Value"
        - Root table: "/SmartDashboard", "/Limelight", etc.
        
        Some APIs:
        - Require slash-less paths: "SmartDashboard/Subsystem/Value"
        - Used when composing paths or in specific NT contexts
        
        This method bridges those conventions.
        
        Idempotent Behavior:
        ```python
        # Safe to call multiple times
        remove_slash("/Key")      # Returns "Key"
        remove_slash("Key")       # Returns "Key"
        remove_slash("/Key/Sub")  # Returns "Key/Sub"
        remove_slash("Key/Sub")   # Returns "Key/Sub"
        ```
        
        Args:
            key (str): The key string, potentially with leading slash.
                Examples:
                - "/SmartDashboard/Auto" → "SmartDashboard/Auto"
                - "SmartDashboard/Auto" → "SmartDashboard/Auto" (unchanged)
                - "/Single" → "Single"
                - "" → "" (empty string returns empty)
                
        Returns:
            str: The key with leading slash removed if present, or the original
                key unchanged if no leading slash. Returns the same string type
                (never produces None).
                
        Use Cases:
        
        1. Path Composition:
        ```python
        base = "/SmartDashboard"
        key = "/Subsystem"
        composed = remove_slash(key)  # "Subsystem"
        full_path = base + "/" + composed  # "/SmartDashboard/Subsystem"
        ```
        
        2. API Compatibility:
        ```python
        # Some APIs require slash-less paths
        nt_key = "/SmartDashboard/Value"
        api_key = remove_slash(nt_key)
        some_api.configure(api_key)
        ```
        
        3. Defensive Programming:
        ```python
        # Don't know if key has leading slash, remove_slash handles both
        user_key = get_from_config()  # User may provide with or without /
        normalized = remove_slash(user_key)
        ```
        
        Performance:
        - O(1) time complexity (single string comparison and slicing)
        - Safe for frequent calls in loops
        - No memory allocation if no slash (string is returned unchanged)
        
        Note:
            Only removes the *leading* slash. Trailing slashes or internal
            slashes are preserved:
            ```python
            remove_slash("/A/B/C")  # Returns "A/B/C" (only front slash removed)
            remove_slash("/A/")     # Returns "A/" (trailing slash preserved)
            ```
        """
        if key.startswith("/"):
            return key[1:]
        return key