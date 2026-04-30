"""
Logged Dashboard Chooser Module for Operator Selection with Replay

This module provides LoggedDashboardChooser, a type-safe wrapper around WPILib's
SendableChooser that integrates with the pykit logging system for deterministic
replay and analysis.

Key Features:
- Dashboard Selector: Displays enumerated options on SmartDashboard for operator use
- Auto-Logging: Selection is automatically logged each cycle for telemetry
- Deterministic Replay: Selections can be replayed from logs for analysis
- Type-Safe: Generic[T] ensures type safety for selection values
- Change Detection: Optional callbacks fire when selection changes
- Normal/Replay Modes: Seamlessly switches between live and replay operation

Typical Usage:
    # Create a typed chooser (e.g., for autonomous modes)
    auto_chooser = LoggedDashboardChooser[str]("Autonomous")
    auto_chooser.setDefaultOption("None", "none")
    auto_chooser.addOption("Drive Forward", "forward")
    auto_chooser.addOption("Score", "score")
    
    # Register callback for selection changes
    auto_chooser.onChange(lambda mode: print(f"Selected: {mode}"))
    
    # In robot code, get the selected value
    selected = auto_chooser.get_selected()

Data Flow:
    Normal Mode:
        SmartDashboard Selection → periodic() → LoggedDashboardChooser → Logger
    
    Replay Mode:
        Log File → Logger → periodic() → LoggedDashboardChooser (updates from log)

The selected value is logged automatically each cycle, enabling operators to see
what mode was selected at each point in a match during analysis.
"""

from typing import Callable, Generic, Optional, TypeVar

from wpilib import SendableChooser, SmartDashboard

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput

#: Type variable for generic chooser values (e.g., str, int, enum, custom objects)
T = TypeVar("T")


class LoggedDashboardChooser(LoggedNetworkInput, Generic[T]):
    """
    Type-safe dashboard chooser with integrated logging and replay support.
    
    LoggedDashboardChooser wraps WPILib's SendableChooser and integrates with the
    pykit logging system, enabling:
    
    1. Live Operation: Displays selectable options on SmartDashboard for operators
    2. Automatic Logging: Selection logged each cycle for permanent telemetry record
    3. Deterministic Replay: Selection can be replayed from logs for testing/analysis
    4. Type Safety: Generic[T] ensures selected values have consistent type
    5. Event Handling: Optional callbacks fire when selection changes
    
    Architecture:
    
    Inheritance Chain:
        LoggedDashboardChooser → LoggedNetworkInput → Interface for logging integration
    
    Key Data Structures:
    - sendable_chooser: WPILib chooser displayed on SmartDashboard
    - options: dict[str, T] mapping display names to typed values
    - selected_value: str (key tracking current selection)
    - listener: Optional callback invoked when selection changes
    
    Operating Modes:
    
    Normal Mode (Robot Operation):
    1. periodic() called each cycle by Logger
    2. Reads selected_value from sendable_chooser.getSelected()
    3. Logs selection to telemetry via Logger.processInputs()
    4. Fires change callback if selection differs from previous cycle
    5. Operators can change selection on SmartDashboard in real-time
    
    Replay Mode (Log Analysis):
    1. periodic() called each cycle during replay
    2. Selection restored from log via Logger.processInputs() → from_log()
    3. Robot sees exact same selection as during original match
    4. Allows deterministic replay with recorded operator inputs
    5. Change callbacks fire when selection changes during replay
    
    Change Detection:
    
    Each cycle, compares currentValue with previous_value:
    - If equal: callback not invoked
    - If different: callback invoked once with new selection
    - This prevents repeated callbacks for same selection
    
    Usage Pattern:
    
    ```python
    # Autonomous mode selector with enum values
    class AutoMode(Enum):
        NONE = 0
        SCORE = 1
        CROSS = 2
    
    auto_chooser = LoggedDashboardChooser[AutoMode]("Auto")
    auto_chooser.setDefaultOption("None", AutoMode.NONE)
    auto_chooser.addOption("Score", AutoMode.SCORE)
    auto_chooser.addOption("Cross", AutoMode.CROSS)
    
    # Register handler for mode changes
    def on_mode_change(mode: AutoMode):
        print(f"Autonomous mode: {mode}")
        if mode == AutoMode.SCORE:
            command_scheduler.schedule(score_command())
    
    auto_chooser.onChange(on_mode_change)
    
    # In autonomousInit()
    selected = auto_chooser.get_selected()
    
    # Rest of operation is automatic:
    # - periodic() called by Logger each cycle
    # - Selection logged automatically
    # - Callbacks invoked on changes
    # - Replay reads selection from log
    ```
    
    Generic Type Parameter:
    
    The Generic[T] enables type-safe selections:
    ```python
    # String values
    chooser_str = LoggedDashboardChooser[str]("String")
    value: str = chooser_str.get_selected()
    
    # Enum values
    chooser_enum = LoggedDashboardChooser[AutoMode]("Mode")
    value: AutoMode = chooser_enum.get_selected()
    
    # Custom objects
    chooser_obj = LoggedDashboardChooser[Config]("Config")
    value: Config = chooser_obj.get_selected()
    ```
    
    Attributes:
        key (str): The dashboard selector key (displayed on SmartDashboard)
        selected_value (str): The current selection key (maps to value in options dict)
        previous_value (Optional[str]): Previous cycle's selection for change detection
        listener (Optional[Callable[[T], None]]): Callback invoked on selection change
        sendable_chooser (SendableChooser): WPILib chooser widget
        options (dict[str, T]): Mapping from display keys to typed values
        prefix (str): Inherited from LoggedNetworkInput, base path for logging
    """

    key: str
    """The SmartDashboard key for this chooser (display name)."""
    
    selected_value: str = ""
    """Current selection key (String). Maps to value via options dict."""
    
    previous_value: Optional[str]
    """Previous cycle's selection. Used for change detection."""
    
    listener: Optional[Callable[[T], None]]
    """Optional callback fired when selection changes. Receives selected value."""

    sendable_chooser: SendableChooser
    """WPILib SendableChooser widget displayed on SmartDashboard."""

    options: dict[str, T] = {}
    """Mapping from display keys (str) to typed values (T)."""

    def __init__(self, key: str) -> None:
        """
        Initialize a LoggedDashboardChooser with display key.
        
        Creates a new dashboard chooser that will display on SmartDashboard and
        automatically log selections to telemetry. After construction, call
        setDefaultOption() and addOption() to populate available choices.
        
        Initialization Steps:
        1. Create WPILib SendableChooser widget
        2. Publish to SmartDashboard (made visible to operators)
        3. Register with Logger as a dashboard input
        4. Initialize internal state (previous_value, listener)
        5. Call periodic() to trigger initial synchronization

        Args:
            key (str): The SmartDashboard display key. This string appears as the
                selector title on the dashboard. Examples:
                - "Autonomous Mode"
                - "Drive Mode"
                - "Test Selector"
                
        Attributes Initialized:
            self.key: Stores the dashboard key
            self.sendable_chooser: Creates new WPILib SendableChooser
            self.previous_value: Set to None
            self.listener: Set to None (no callback initially)
            self.options: Empty dict (populated via addOption/setDefaultOption)
            self.selected_value: Empty string (set by first periodic call)
            
        Side Effects:
            - Displays chooser on SmartDashboard (becomes visible to operators)
            - Registers with Logger for automatic periodic updates
            - Inherits self.prefix from LoggedNetworkInput base class
            - Calls initial periodic() to load any pre-existing selection
            
        Note:
            After construction, use addOption() and setDefaultOption() to populate
            the chooser with selectable values before robot initialization completes.
            
        Example:
            ```python
            # Create the chooser
            chooser = LoggedDashboardChooser[str]("Test Mode")
            
            # Add options
            chooser.setDefaultOption("None", "none")
            chooser.addOption("Test 1", "test1")
            chooser.addOption("Test 2", "test2")
            
            # Now operators see the selector on their dashboard
            ```
        """
        self.key = key
        self.sendable_chooser = SendableChooser()
        self.previous_value = None
        self.listener = None
        
        # Publish the chooser to SmartDashboard so operators can see/interact with it
        SmartDashboard.putData(key, self.sendable_chooser)
        
        # Perform initial synchronization
        self.periodic()

        # Register with Logger so periodic() is called each robot cycle
        Logger.registerDashboardInput(self)

    def addOption(self, key: str, value: T):
        """
        Add a selectable option to the chooser.
        
        Adds an entry to the chooser that operators can select from the dashboard.
        Once added, the option appears as a button/radio option on SmartDashboard.
        
        Implementation Note:
        The key is stored in the SendableChooser for display, and also used as
        the lookup key in the options dict. This means the display name and the
        dict key must match exactly.

        Args:
            key (str): Display name for this option (shown on dashboard).
                Should be descriptive for operators, e.g., "Score Ball", "Cross Line"
            value (T): The typed value returned by get_selected() when this option
                is chosen. Can be any type matching the chooser's Generic[T] parameter.
                Examples: AutoMode.SCORE, "drive_forward", 42, etc.
                
        Side Effects:
            - Adds option to internal SendableChooser (displayed on dashboard)
            - Stores mapping in self.options dict for retrieval
            - Option becomes selectable by operators in real-time
            
        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.addOption("Score", AutoMode.SCORE)
            chooser.addOption("Cross", AutoMode.CROSS)
            
            # Operators now see "Score" and "Cross" buttons on their dashboard
            # Selecting "Score" makes get_selected() return AutoMode.SCORE
            ```
        """
        self.sendable_chooser.addOption(key, key)
        self.options[key] = value

    def setDefaultOption(self, key: str, value: T):
        """
        Set the default option for the chooser.
        
        Specifies which option is pre-selected if the operator hasn't made a
        selection yet. On SmartDashboard, the default option is highlighted or
        pre-checked.
        
        There should be exactly one default option. Calling this multiple times
        overwrites the previous default.

        Args:
            key (str): Display name for the default option.
                Should match one of the addOption() display names if that option
                should be overwritten with this default behavior.
            value (T): The default typed value returned by get_selected() if no
                operator selection has been made. Typically, the safest/no-op mode
                (e.g., AutoMode.NONE, "do_nothing", etc.).
                
        Side Effects:
            - Sets default in internal SendableChooser
            - Stores mapping in self.options dict
            - This option appears pre-selected on SmartDashboard
            - get_selected() returns this value until operator changes selection
            
        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.setDefaultOption("None", AutoMode.NONE)  # Safe default
            chooser.addOption("Score", AutoMode.SCORE)
            
            # If operators don't select anything, they get AutoMode.NONE
            ```
        """
        self.sendable_chooser.setDefaultOption(key, key)
        self.options[key] = value

    def get_selected(self) -> Optional[T]:
        """
        Get the currently selected typed value.
        
        Returns the value associated with the current selection. The selection
        can come from:
        - Operator on SmartDashboard (normal mode)
        - Log file (replay mode)
        
        The return type is T (the generic type parameter), providing type safety.
        If no selection is found in the options dict, returns None.

        Returns:
            T | None: The typed value for the current selection, or None if the
                selection key is not found in the options dict.
                
        Raises:
            ValueError: If selected_value is None (internal error condition)
            
        Side Effects:
            Queries the internal options dict for the selected key.
            
        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.setDefaultOption("None", AutoMode.NONE)
            chooser.addOption("Score", AutoMode.SCORE)
            
            selected: AutoMode | None = chooser.get_selected()
            if selected == AutoMode.SCORE:
                print("Scoring autonomous mode selected")
            
            # Type checker knows selected is AutoMode | None
            ```
        """
        if self.selected_value is None:
            raise ValueError("Selected value is None")

        return self.options.get(self.selected_value)

    def periodic(self) -> None:
        """
        Update chooser state each robot cycle.
        
        Called automatically by Logger approximately 50 times per second. This
        method synchronizes the chooser between SmartDashboard (normal mode) or
        log file (replay mode), detects changes, and invokes callbacks.
        
        Execution Flow:
        
        1. Update selected_value:
           - Normal mode: Read from SmartDashboard SendableChooser
           - Replay mode: Skip (will be set by subsequent from_log call)
        
        2. Normalize selection:
           - If selected_value is None, set to empty string (default)
        
        3. Log synchronization:
           - Calls Logger.processInputs() which:
             - In normal mode: Calls self.to_log() to save selection
             - In replay mode: Calls self.from_log() to load selection from log
        
        4. Change detection:
           - Compare selected_value with previous_value
           - If different, invoke listener callback with new value
        
        5. Update state:
           - Store selected_value in previous_value for next cycle
        
        This enables:
        - Selection changes to be logged automatically each cycle
        - Callbacks to fire at the right time (after log sync)
        - Deterministic replay where same selection appears at same time
        
        Timing Note:
        The periodic frequency is controlled by Logger and robot loop rate,
        typically 50 Hz (20 ms between calls).

        Side Effects:
            - May read SmartDashboard (normal mode)
            - May write to Logger for logging
            - May invoke listener callback if selection changed
            - Updates previous_value
            
        Call Sequence Per Cycle:
            Logger.periodicBeforeUser()  # Invokes this periodic()
                ↓
            periodic() executes
                ↓
            [Robot code executes, possibly calls get_selected()]
                ↓
            Logger.periodicAfterUser()  # Logs output (including self.to_log call)
        """
        # In normal mode, read from NetworkTables; in replay mode, read from log
        if not Logger.isReplay():
            self.selected_value = self.sendable_chooser.getSelected()

        # Normalize: convert None to empty string for consistency
        if self.selected_value is None:
            self.selected_value = ""
        
        # Sync with logger (saves to log in normal mode, loads from log in replay mode)
        Logger.processInputs(self.prefix + "/SmartDashboard", self)
        
        # Fire callback if selection changed
        if self.selected_value != self.previous_value and self.listener is not None:
            selected = self.get_selected()
            if selected is not None:
                self.listener(selected)
        
        # Update previous state for next cycle's comparison
        self.previous_value = self.selected_value

    def on_change(self, callback: Callable[[T], None]) -> None:
        """
        Register a callback to invoke when selection changes.
        
        The callback is invoked exactly once per selection change, receiving the
        new selected value as its argument. This enables robot code to react to
        operator selections on the dashboard or during replay.
        
        Callback Timing:
        Invoked during periodic() when the current selected_value differs from the
        previous cycle's value. This occurs once per transition, not repeatedly
        for the same selection.
        
        Typical Use Cases:
        - Trigger autonomous commands when mode is selected
        - Update robot state based on selected configuration
        - Log events when operator changes selection
        
        Callback Execution Order:
        The callback is called after the selection has been synchronized with the
        log (or SmartDashboard), so get_selected() will return the new value if
        called from within the callback.

        Args:
            callback (Callable[[T], None]): Function to invoke on selection change.
                Receives the new selected value (type T) as its only argument.
                Return value is ignored.
                
        Type Signature:
            callback: (T) -> None
            
        Side Effects:
            - Stores callback in self.listener
            - Replaces any previously registered callback
            - Callback invoked during periodic() on each selection change
            
        Example:
            ```python
            chooser = LoggedDashboardChooser[str]("Mode")
            chooser.setDefaultOption("Normal", "normal")
            chooser.addOption("Test", "test")
            
            def on_mode_change(mode: str):
                if mode == "test":
                    print("TEST MODE ACTIVATED!")
                    # Trigger test-specific setup
            
            chooser.onChange(on_mode_change)
            
            # When operator changes to "Test" or during replay at that point,
            # on_mode_change("test") is called automatically
            ```
        """
        self.listener = callback

    def to_log(self, table: LogTable, prefix: str) -> None:
        """
        Save the current selection to the log table.
        
        Called by Logger.processInputs() during normal operation (not replay) to
        record the current selection into the telemetry log. This creates a
        permanent record of what selection was active at each moment in time.
        
        The selection key (not the value) is logged, allowing deterministic replay
        by restoring the same key string later.

        Args:
            table (LogTable): The log table to write selection to
            prefix (str): The prefix path within the log table
                Combined with self.key to form the logged entry name
                Example: "/SmartDashboard/Auto" + "/Autonomous" 
                         → logs at "/SmartDashboard/Auto/Autonomous"
                
        Side Effects:
            - Writes selected_value to the log table at the composed key path
            - Contributes to the permanent telemetry record
            - Enables replay to reproduce this selection
            
        Typical Logging Path:
            prefix: "/SmartDashboard"
            self.key: "Autonomous"
            composed key: "/SmartDashboard/Autonomous"
            
        Note:
            This method is automatically called by Logger during normal operation.
            It's typically not called directly by user code.
        """
        table.put(f"{prefix}/{self.key}", self.selected_value)

    def from_log(self, table: LogTable, prefix: str) -> None:
        """
        Load the selection from the log table.
        
        Called by Logger.processInputs() during replay mode to restore the
        selection from the previously recorded log. This allows the robot to see
        the exact same selection during replay as during the original match,
        enabling deterministic testing and analysis.
        
        If the log entry doesn't exist (e.g., corrupt log or different version),
        falls back to keeping the current selected_value unchanged.

        Args:
            table (LogTable): The log table to read selection from
            prefix (str): The prefix path within the log table
                Combined with self.key to form the log entry name to read
                Example: "/SmartDashboard/Auto" + "/Autonomous" 
                         → reads from "/SmartDashboard/Auto/Autonomous"
                
        Side Effects:
            - Reads from the log table at the composed key path
            - Updates self.selected_value with the logged value
            - Falls back to current selected_value if log entry not found
            - On next periodic(), change detection triggers callback if different
            
        Fallback Behavior:
            If the log entry doesn't exist:
            ```python
            self.selected_value = table.get(key, self.selected_value)
            # Use current value as default if log entry missing
            ```
            This gracefully handles logs from different code versions or incomplete logs.
            
        Replay Timing:
            Called during Logger.periodicBeforeUser(), before user code executes.
            Guarantees that get_selected() returns the correct replayed value when
            robot periodic code runs.
            
        Note:
            This method is automatically called by Logger during replay mode.
            It's typically not called directly by user code.
        """
        self.selected_value = table.get(f"{prefix}/{self.key}", self.selected_value)