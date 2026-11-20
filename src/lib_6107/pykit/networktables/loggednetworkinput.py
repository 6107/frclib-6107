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
Logged Network Input Module for Tunable Input Integration

This module provides LoggedNetworkInput, a base class for integrating tunable-backed
inputs (choosers, numbers, booleans, strings, buttons) with the pykit logging and
replay system.

LoggedNetworkInput serves as the foundation for:
- Elastic selectors (autonomous modes, test options)
- Operator-editable values and buttons published as tunables
- Other operator interface elements that need telemetry capture

Key Features:
- Periodic Updates: Syncs with the tunables registry each cycle
- Logging Integration: Input state automatically logged for telemetry
- Replay Support: Inputs can be replayed from logs for deterministic testing
- Hierarchical Namespacing: Configurable prefix for log organization
- Key Normalization: Utilities for consistent key path management

Inheritance Hierarchy:
    LoggedNetworkInput (base class)
        ↓
        ├── LoggedDashboardChooser (autonomous mode, test selector)
        ├── LoggedNetworkValue (LoggedNetworkNumber / Boolean / String)
        │       ↓
        │   NetworkTableButton wraps a LoggedNetworkBoolean
        └── [Other tunable input types]

All tunable inputs follow this lifecycle:
    1. periodic() called by Logger each cycle (~50 Hz)
    2. Read the tunable (or the log in replay mode)
    3. Detect changes and fire callbacks if needed
    4. Log input state via Logger.process_inputs()
"""


class LoggedNetworkInput:
    """
    Abstract base class for tunable-backed inputs integrated with logging/replay.

    LoggedNetworkInput defines the interface and common functionality for all
    operator inputs (edited in Elastic and published through ``tunables``) that
    need to be logged and replayed. It provides a framework for:

    1. Periodic Synchronization: Update input state each robot cycle
    2. Logging Integration: Automatically capture input changes to telemetry
    3. Replay Support: Restore input state from logs during replay
    4. Hierarchical Organization: Organize inputs in log namespace via prefix

    Design Pattern:

    Subclasses implement this pattern:
    1. Inherit from LoggedNetworkInput
    2. Publish a tunable in __init__ (e.g., tunables.add_double or a Selectable)
    3. Override periodic() to read the tunable (or the log) each cycle
    4. Implement to_log() and from_log() for logging integration
    5. Register with Logger via Logger.register_tunable_input()

    The Logger calls periodic() on all registered inputs during each robot cycle,
    ensuring synchronized updates across all tunable inputs.

    Namespace Organization:

    The prefix attribute organizes logged inputs hierarchically:
    ```
    Default prefix: "NetworkInputs"

    Logged paths using Logger.process_inputs():
        /NetworkInputs/Tunables/Auto          (LoggedDashboardChooser)
        /NetworkInputs/Shooter/Speed          (LoggedNetworkNumber)
        /NetworkInputs/Debug/Enabled          (LoggedNetworkBoolean)
    ```

    This keeps all tunable inputs organized under a common namespace in logs.

    Integration with Logger:

    Typical usage flow:
    ```python
    # Create input (it registers itself with the Logger)
    chooser = LoggedDashboardChooser("Auto")
    chooser.add_option("Score", "score")

    # Each cycle:
    Logger.periodic_before_user() calls chooser.periodic()
        ↓
    periodic() reads the tunable (or the log during replay)
        ↓
    Logger.process_inputs() calls to_log() / from_log()
        ↓
    Input state persisted to telemetry
    ```

    Logging and Replay:

    Normal Mode (Live Operation):
    - periodic() reads state from the tunable (updated by Elastic)
    - to_log() saves state to log table
    - State visible in Elastic in real-time

    Replay Mode (Log Analysis):
    - periodic() still called (via Logger.periodic_before_user)
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

    Used by subclasses when calling Logger.process_inputs():
        Logger.process_inputs(self.prefix, self)

    This places inputs under "/NetworkInputs/*" in logs.

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
        3. Subclass should register with Logger via Logger.register_tunable_input()

        Subclass Responsibility:
        Subclasses should:
        - Call super().__init__() first to initialize base state
        - Publish their tunable (tunables.add_* or tunables.publish)
        - Register with Logger if not auto-registered
        - Override periodic() and logging methods

        Example:
        ```python
        class MyInput(LoggedNetworkInput):
            def __init__(self, key):
                super().__init__()

                # Publish the tunable shown in Elastic
                self.tunable = tunables.add_double(key, 0.0)

                # Register with logging system
                Logger.register_tunable_input(self)
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
        1. Logger.periodic_before_user() calls this periodic() method
        2. Subclass implementation reads the tunable (or the log in replay mode)
        3. Robot code executes and may read input state via getter methods
        4. Logger.process_inputs() (invoked from periodic()) calls:
           - to_log() in normal mode (save input)
           - from_log() in replay mode (restore input from log)

        Typical Implementation (subclass example):

        ```python
        class CustomChooser(LoggedNetworkInput):
            def periodic(self) -> None:
                # In normal mode, read the tunable
                if not Logger.is_replay():
                    self.selected = self.tunable.get()

                # Trigger logging via Logger.process_inputs()
                # This calls to_log() or from_log() depending on mode
                Logger.process_inputs(self.prefix, self)

                # Fire change callbacks if value changed
                if self.selected != self.previous:
                    self.on_change_callback(self.selected)
                    self.previous = self.selected
        ```

        Synchronization Modes:

        Normal Mode (Robot Operation):
        - Read from the tunable (operator changes made in Elastic)
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
        - Tunables must only be touched from the main thread

        Required Override:
        All subclasses MUST override this method. The base class provides
        no implementation (intentionally empty).

        Subclass Contract:
        When overriding, your implementation should:
        1. Update internal state from the tunable (or log during replay)
        2. Call Logger.process_inputs() to integrate with logging
        3. Detect changes and fire change callbacks
        4. Handle both normal and replay modes appropriately
        """

    @staticmethod
    def remove_slash(key: str) -> str:
        """
        Remove a leading forward slash from a key string if present.

        Utility method for normalizing tunable names. Tunable names are relative
        (e.g., "Shooter/Speed" is published at "/Tunables/Shooter/Speed"), but
        callers migrating from NetworkTables often pass keys with a leading "/".
        This method accepts both forms.

        This method provides idempotent slash removal - safe to call on keys
        that may or may not have leading slashes.

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
                - "/Shooter/Speed" → "Shooter/Speed"
                - "Shooter/Speed" → "Shooter/Speed" (unchanged)
                - "/Single" → "Single"
                - "" → "" (empty string returns empty)

        Returns:
            str: The key with leading slash removed if present, or the original
                key unchanged if no leading slash. Returns the same string type
                (never produces None).

        Use Cases:

        1. Path Composition:
        ```python
        base = "NetworkInputs"
        key = "/Subsystem"
        full_path = base + "/" + remove_slash(key)  # "NetworkInputs/Subsystem"
        ```

        2. Defensive Programming:
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
