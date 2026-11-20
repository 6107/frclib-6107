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
Logged Chooser Module for Operator Selection with Replay

This module provides LoggedDashboardChooser, a type-safe wrapper around the
``tunables.Selectable`` chooser that integrates with the pykit logging system for
deterministic replay and analysis. The class name is kept for compatibility; the
operator interacts with it in Elastic and it is transported as a tunable.

Key Features:
- Elastic Selector: Displays enumerated options in Elastic for operator use
  (published at ``/Tunables/<key>`` with ``default``, ``options`` and ``selected``)
- Auto-Logging: Selection is automatically logged each cycle for telemetry
- Deterministic Replay: Selections can be replayed from logs for analysis
- Type-Safe: A PEP 695 type parameter ``T`` types the selection values
- Change Detection: Optional callbacks fire when selection changes
- Normal/Replay Modes: Seamlessly switches between live and replay operation

Typical Usage:
    # Create a typed chooser (e.g., for autonomous modes)
    auto_chooser = LoggedDashboardChooser[str]("Autonomous")
    auto_chooser.set_default_option("None", "none")
    auto_chooser.add_option("Drive Forward", "forward")
    auto_chooser.add_option("Score", "score")

    # Register callback for selection changes
    auto_chooser.on_change(lambda mode: print(f"Selected: {mode}"))

    # In robot code, get the selected value
    selected = auto_chooser.get_selected()

Data Flow:
    Normal Mode:
        Elastic → tunables Selectable → periodic() → LoggedDashboardChooser → Logger

    Replay Mode:
        Log File → Logger → periodic() → LoggedDashboardChooser (updates from log)

The selected option name is logged automatically each cycle at
``NetworkInputs/Tunables/<key>``, enabling operators to see what mode was selected
at each point in a match during analysis.
"""

from collections.abc import Callable

import tunables
from tunables import Selectable

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput


class LoggedDashboardChooser[T](LoggedNetworkInput):
    """
    Type-safe Elastic chooser with integrated logging and replay support.

    LoggedDashboardChooser wraps a ``tunables.Selectable`` and integrates with the
    pykit logging system, enabling:

    1. Live Operation: Displays selectable options in Elastic for operators
    2. Automatic Logging: Selection logged each cycle for a permanent telemetry record
    3. Deterministic Replay: Selection can be replayed from logs for testing/analysis
    4. Type Safety: The type parameter T gives selected values a consistent type
    5. Event Handling: Optional callbacks fire when selection changes

    Architecture:

    Inheritance Chain:
        LoggedDashboardChooser → LoggedNetworkInput → Interface for logging integration

    Key Data Structures:
    - selectable: tunables.Selectable[str] published to Elastic. It stores option
      *names* only, because the log (and replay) must record the name chosen by
      the operator, and Selectable has no public getter for the selected name.
    - options: dict[str, T] mapping option names to typed values
    - selected_value: str (name of the current selection)
    - listener: Optional callback invoked when selection changes

    Operating Modes:

    Normal Mode (Robot Operation):
    1. periodic() called each cycle by Logger
    2. Reads selected_value from selectable.get_selected()
    3. Logs selection to telemetry via Logger.process_inputs()
    4. Fires change callback if selection differs from the previous cycle
    5. Operators can change the selection in Elastic in real-time

    Replay Mode (Log Analysis):
    1. periodic() called each cycle during replay
    2. Selection restored from the log via Logger.process_inputs() → from_log()
    3. Robot sees the exact same selection as during the original match
    4. Allows deterministic replay with recorded operator inputs
    5. Change callbacks fire when selection changes during replay

    Change Detection:

    Each cycle compares selected_value with previous_value:
    - If equal: callback not invoked
    - If different: callback invoked once with the new selection
    - This prevents repeated callbacks for the same selection

    Usage Pattern:

    ```python
    # Autonomous mode selector with enum values
    class AutoMode(Enum):
        NONE = 0
        SCORE = 1
        CROSS = 2

    auto_chooser = LoggedDashboardChooser[AutoMode]("Auto")
    auto_chooser.set_default_option("None", AutoMode.NONE)
    auto_chooser.add_option("Score", AutoMode.SCORE)
    auto_chooser.add_option("Cross", AutoMode.CROSS)

    # Register handler for mode changes
    def on_mode_change(mode: AutoMode):
        print(f"Autonomous mode: {mode}")
        if mode == AutoMode.SCORE:
            command_scheduler.schedule(score_command())

    auto_chooser.on_change(on_mode_change)

    # In autonomous_init()
    selected = auto_chooser.get_selected()

    # Rest of operation is automatic:
    # - periodic() called by Logger each cycle
    # - Selection logged automatically
    # - Callbacks invoked on changes
    # - Replay reads selection from log
    ```

    Generic Type Parameter:

    The type parameter T enables type-safe selections:
    ```python
    # String values
    chooser_str = LoggedDashboardChooser[str]("String")
    value: str | None = chooser_str.get_selected()

    # Enum values
    chooser_enum = LoggedDashboardChooser[AutoMode]("Mode")
    value: AutoMode | None = chooser_enum.get_selected()

    # Custom objects
    chooser_obj = LoggedDashboardChooser[Config]("Config")
    value: Config | None = chooser_obj.get_selected()
    ```

    Attributes:
        key (str): The tunable name of the chooser (shown in Elastic)
        selected_value (str): The current selection name (maps to a value in options)
        previous_value (str | None): Previous cycle's selection for change detection
        listener (Callable[[T], None] | None): Callback invoked on selection change
        selectable (Selectable[str]): The tunables chooser published to Elastic
        options (dict[str, T]): Mapping from option names to typed values
        prefix (str): Inherited from LoggedNetworkInput, base path for logging
    """

    key: str
    """The tunable name for this chooser (shown in Elastic)."""

    selected_value: str = ""
    """Current selection name (String). Maps to a value via the options dict."""

    previous_value: str | None
    """Previous cycle's selection. Used for change detection."""

    listener: Callable[[T], None] | None
    """Optional callback fired when selection changes. Receives selected value."""

    selectable: Selectable[str]
    """The tunables chooser published to Elastic (stores option names)."""

    options: dict[str, T]
    """Mapping from option names (str) to typed values (T)."""

    def __init__(self, key: str) -> None:
        """
        Initialize a LoggedDashboardChooser with a tunable name.

        Creates a new chooser that is published as a tunable for Elastic and
        automatically logs selections to telemetry. After construction, call
        set_default_option() and add_option() to populate available choices.

        Initialization Steps:
        1. Create the tunables Selectable
        2. Publish it as a tunable (visible to operators in Elastic)
        3. Initialize internal state (previous_value, listener, options)
        4. Call periodic() to trigger initial synchronization
        5. Register with Logger as a tunable input

        Args:
            key (str): The tunable name. This string appears as the selector
                title in Elastic. Examples:
                - "Autonomous Mode"
                - "Drive Mode"
                - "Test Selector"

        Attributes Initialized:
            self.key: Stores the tunable name
            self.selectable: Creates a new tunables Selectable
            self.previous_value: Set to None
            self.listener: Set to None (no callback initially)
            self.options: Empty dict (populated via add_option/set_default_option)
            self.selected_value: Empty string (set by the first periodic call)

        Side Effects:
            - Publishes the chooser under /Tunables/<key> (visible in Elastic)
            - Registers with Logger for automatic periodic updates
            - Inherits self.prefix from LoggedNetworkInput base class
            - Calls initial periodic() to load any pre-existing selection
            - If the name is already published, tunables logs a warning and this
              chooser is not shown in Elastic

        Note:
            After construction, use add_option() and set_default_option() to populate
            the chooser with selectable values before robot initialization completes.

        Example:
            ```python
            # Create the chooser
            chooser = LoggedDashboardChooser[str]("Test Mode")

            # Add options
            chooser.set_default_option("None", "none")
            chooser.add_option("Test 1", "test1")
            chooser.add_option("Test 2", "test2")

            # Now operators see the selector in Elastic
            ```
        """
        self.key = key
        self.selectable = Selectable()
        self.previous_value = None
        self.listener = None
        self.selected_value = ""
        self.options = {}

        # Publish the chooser as a tunable so Elastic can see/interact with it
        tunables.publish(key, self.selectable)

        # Perform initial synchronization
        self.periodic()

        # Register with Logger so periodic() is called each robot cycle
        Logger.register_tunable_input(self)

    def add_option(self, key: str, value: T):
        """
        Add a selectable option to the chooser.

        Adds an entry to the chooser that operators can select in Elastic.
        Once added, the option appears in the chooser's drop-down in Elastic.

        Implementation Note:
        The name is stored in the Selectable for display, and also used as
        the lookup key in the options dict. This means the display name and the
        dict key always match exactly.

        Args:
            key (str): Display name for this option (shown in Elastic).
                Should be descriptive for operators, e.g., "Score Ball", "Cross Line"
            value (T): The typed value returned by get_selected() when this option
                is chosen. Can be any type matching the chooser's type parameter.
                Examples: AutoMode.SCORE, "drive_forward", 42, etc.

        Side Effects:
            - Adds option to the internal Selectable (displayed in Elastic)
            - Stores mapping in self.options dict for retrieval
            - Option becomes selectable by operators in real-time

        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.add_option("Score", AutoMode.SCORE)
            chooser.add_option("Cross", AutoMode.CROSS)

            # Operators now see "Score" and "Cross" in Elastic
            # Selecting "Score" makes get_selected() return AutoMode.SCORE
            ```
        """
        self.selectable.add(key, key)
        self.options[key] = value

    def set_default_option(self, key: str, value: T):
        """
        Set the default option for the chooser.

        Specifies which option is pre-selected if the operator hasn't made a
        selection yet. In Elastic, the default option is shown as selected.

        There should be exactly one default option. Calling this multiple times
        overwrites the previous default.

        Args:
            key (str): Display name for the default option.
            value (T): The default typed value returned by get_selected() if no
                operator selection has been made. Typically, the safest/no-op mode
                (e.g., AutoMode.NONE, "do_nothing", etc.).

        Side Effects:
            - Sets the default in the internal Selectable
            - Stores mapping in self.options dict
            - This option appears pre-selected in Elastic
            - get_selected() returns this value until the operator changes selection

        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.set_default_option("None", AutoMode.NONE)  # Safe default
            chooser.add_option("Score", AutoMode.SCORE)

            # If operators don't select anything, they get AutoMode.NONE
            ```
        """
        self.selectable.add_default(key, key)
        self.options[key] = value

    def get_selected(self) -> T | None:
        """
        Get the currently selected typed value.

        Returns the value associated with the current selection. The selection
        can come from:
        - Operator in Elastic (normal mode)
        - Log file (replay mode)

        The return type is T (the type parameter), providing type safety.
        If no selection is found in the options dict, returns None.

        Returns:
            T | None: The typed value for the current selection, or None if the
                selection name is not found in the options dict.

        Raises:
            ValueError: If selected_value is None (internal error condition)

        Side Effects:
            Queries the internal options dict for the selected name.

        Example:
            ```python
            chooser = LoggedDashboardChooser[AutoMode]("Auto")
            chooser.set_default_option("None", AutoMode.NONE)
            chooser.add_option("Score", AutoMode.SCORE)

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
        Update the chooser state each robot cycle.

        Called automatically by Logger approximately 50 times per second. This
        method synchronizes the chooser with the tunables Selectable (normal mode)
        or the log file (replay mode), detects changes, and invokes callbacks.

        Execution Flow:

        1. Update selected_value:
           - Normal mode: Read from the Selectable
           - Replay mode: Skip (will be set by the subsequent from_log call)

        2. Normalize selection:
           - If selected_value is None, set to empty string (default)

        3. Log synchronization:
           - Calls Logger.process_inputs() which:
             - In normal mode: Calls self.to_log() to save selection
             - In replay mode: Calls self.from_log() to load selection from log

        4. Change detection:
           - Compare selected_value with previous_value
           - If different, invoke the listener callback with the new value

        5. Update state:
           - Store selected_value in previous_value for the next cycle

        This enables:
        - Selection changes to be logged automatically each cycle
        - Callbacks to fire at the right time (after log sync)
        - Deterministic replay where the same selection appears at the same time

        Timing Note:
        The periodic frequency is controlled by Logger and robot loop rate,
        typically 50 Hz (20 ms between calls).

        Side Effects:
            - Reads the tunables Selectable (normal mode)
            - Writes to Logger for logging
            - May invoke listener callback if the selection changed
            - Updates previous_value

        Call Sequence Per Cycle:
            Logger.periodic_before_user()  # Invokes this periodic()
                ↓
            periodic() executes
                ↓
            [Robot code executes, possibly calls get_selected()]
                ↓
            Logger.periodic_after_user()  # Logs output
        """
        # In normal mode, read from the Selectable; in replay mode, read from log
        if not Logger.is_replay():
            self.selected_value = self.selectable.get_selected()

        # Normalize: convert None to empty string for consistency
        if self.selected_value is None:
            self.selected_value = ""

        # Sync with logger (saves to log in normal mode, loads from log in replay mode)
        Logger.process_inputs(self.prefix + "/Tunables", self)

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
        operator selections in Elastic or during replay.

        Callback Timing:
        Invoked during periodic() when the current selected_value differs from the
        previous cycle's value. This occurs once per transition, not repeatedly
        for the same selection.

        Typical Use Cases:
        - Trigger autonomous commands when a mode is selected
        - Update robot state based on the selected configuration
        - Log events when the operator changes selection

        Callback Execution Order:
        The callback is called after the selection has been synchronized with the
        log (or the Selectable), so get_selected() will return the new value if
        called from within the callback.

        Args:
            callback (Callable[[T], None]): Function to invoke on selection change.
                Receives the new selected value (type T) as its only argument.
                Return value is ignored.

        Side Effects:
            - Stores callback in self.listener
            - Replaces any previously registered callback
            - Callback invoked during periodic() on each selection change

        Example:
            ```python
            chooser = LoggedDashboardChooser[str]("Mode")
            chooser.set_default_option("Normal", "normal")
            chooser.add_option("Test", "test")

            def on_mode_change(mode: str):
                if mode == "test":
                    print("TEST MODE ACTIVATED!")
                    # Trigger test-specific setup

            chooser.on_change(on_mode_change)

            # When operator changes to "Test" or during replay at that point,
            # on_mode_change("test") is called automatically
            ```
        """
        self.listener = callback

    def to_log(self, table: LogTable, prefix: str) -> None:
        """
        Save the current selection to the log table.

        Called by Logger.process_inputs() during normal operation (not replay) to
        record the current selection into the telemetry log. This creates a
        permanent record of what selection was active at each moment in time.

        The selection name (not the value) is logged, allowing deterministic replay
        by restoring the same name string later.

        Args:
            table (LogTable): The log table to write the selection to
            prefix (str): The prefix path within the log table
                Combined with self.key to form the logged entry name
                Example: "NetworkInputs/Tunables" + "Autonomous"
                         → logs at "NetworkInputs/Tunables/Autonomous"

        Side Effects:
            - Writes selected_value to the log table at the composed key path
            - Contributes to the permanent telemetry record
            - Enables replay to reproduce this selection

        Note:
            Logger automatically calls this method during normal operation.
            It's typically not called directly by user code.
        """
        table.put(f"{prefix}/{self.key}", self.selected_value)

    def from_log(self, table: LogTable, prefix: str) -> None:
        """
        Load the selection from the log table.

        Called by Logger.process_inputs() during replay mode to restore the
        selection from the previously recorded log. This allows the robot to see
        the exact same selection during replay as during the original match,
        enabling deterministic testing and analysis.

        If the log entry doesn't exist (e.g., corrupt log or different version),
        falls back to keeping the current selected_value unchanged.

        Args:
            table (LogTable): The log table to read the selection from
            prefix (str): The prefix path within the log table
                Combined with self.key to form the log entry name to read
                Example: "NetworkInputs/Tunables" + "Autonomous"
                         → reads from "NetworkInputs/Tunables/Autonomous"

        Side Effects:
            - Reads from the log table at the composed key path
            - Updates self.selected_value with the logged value
            - Falls back to the current selected_value if the log entry is not found
            - On next periodic(), change detection triggers callback if different

        Fallback Behavior:
            If the log entry doesn't exist:
            ```python
            self.selected_value = table.get(key, self.selected_value)
            # Use current value as default if log entry missing
            ```
            This gracefully handles logs from different code versions or incomplete logs.
            Logs recorded before the move to tunables used a different log path and
            are not read.

        Replay Timing:
            Called during Logger.periodic_before_user(), before user code executes.
            Guarantees that get_selected() returns the correct replayed value when
            robot periodic code runs.

        Note:
            Logger automatically calls this method during replay mode.
            It's typically not called directly by user code.
        """
        self.selected_value = table.get(f"{prefix}/{self.key}", self.selected_value)
