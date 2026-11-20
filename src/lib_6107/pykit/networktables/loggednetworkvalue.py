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
Logged Network Value Module: Base Class for Operator-Editable Tunable Values

This module provides LoggedNetworkValue, the generic base class behind
LoggedNetworkNumber, LoggedNetworkBoolean and LoggedNetworkString. Each instance
publishes a value as a tunable (``/Tunables/<key>``) that operators edit in Elastic,
reads it each robot cycle, and records it through the pykit Logger so the exact
operator-supplied value can be replayed later.

Key Features:
- Elastic Editing: The value is a ``tunables`` entry shown (and editable) in Elastic
- Type Safe: A single PEP 695 type parameter ``T`` types the value
- Auto-Logging: The value is logged each cycle at ``NetworkInputs/<key>``
- Deterministic Replay: In replay mode the value comes from the log, not the tunable
- Simple Subclassing: A subclass only implements ``_publish`` (and optionally
  ``_coerce``) to say which kind of tunable backs the value

Architecture:

    Normal Mode:
        Elastic → tunable → TunableRegistry.update() → periodic() → value → Logger

    Replay Mode:
        Log File → Logger.process_inputs() → from_log() → value

Subclassing:

    class LoggedNetworkBoolean(LoggedNetworkValue[bool]):
        def _publish(self, name: str, default: bool) -> tunables.Tunable:
            return tunables.add_boolean(name, default)

Threading:
    Tunables must only be accessed from the main thread. periodic() is called by the
    Logger from the robot's main loop, which satisfies this requirement.
"""

import tunables

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput


class LoggedNetworkValue[T](LoggedNetworkInput):
    """
    Generic base class for a tunable value that is logged and replayable.

    LoggedNetworkValue publishes a single value as a tunable so an operator can
    edit it in Elastic, keeps a cached copy that robot code reads through
    ``value`` (or by calling the instance), and logs the cached value every cycle.

    Type Parameter:
        T: The Python type of the value (bool, float, str, ...)

    Subclass Contract:
        Subclasses implement ``_publish`` to create the backing tunable, and may
        override ``_coerce`` to normalize values before they are stored or written
        (for example, converting ``int`` to ``float``).

    Lifecycle:
        1. __init__ publishes the tunable with the default value and registers the
           instance with Logger.register_tunable_input()
        2. Each cycle, Logger calls periodic(), which (outside replay) copies the
           tunable's current value into the cache and then calls
           Logger.process_inputs() so the value is logged (or restored in replay)
        3. Robot code reads ``value`` and may assign to it to write the value back
           to Elastic

    Usage:

    ```python
    max_speed = LoggedNetworkNumber("Drive/MaxSpeed", default=3.0)

    speed = max_speed.value      # Cached value from the latest cycle
    speed = max_speed()          # Same as above

    max_speed.value = 2.5        # Writes through to the tunable (visible in Elastic)
    ```

    Attributes:
        _key (str): The tunable name (a leading "/" is accepted and removed)
        _default (T): Fallback value used when a log entry is missing in replay
        _value (T): Cached value, updated each cycle
        _tunable (tunables.Tunable): The backing tunable
    """

    _key: str
    """The tunable name for this value."""

    _default: T
    """Fallback used when a log entry is missing during replay."""

    _value: T
    """Cached value, refreshed from the tunable each cycle (or from the log in replay)."""

    _tunable: tunables.Tunable
    """The backing ``tunables.Tunable`` handle."""

    def __init__(self, key: str, default: T) -> None:
        """
        Publish the tunable and register with the Logger.

        Args:
            key (str): The tunable name, shown in Elastic under ``/Tunables``.
                Hierarchical names use "/" (e.g., "Drive/MaxSpeed"). A leading "/"
                is removed for compatibility with older NetworkTables-style keys.
            default (T): The initial value, published to Elastic immediately and
                used as the replay fallback.

        Side Effects:
            - Publishes a tunable at ``/Tunables/<key>``. If the name is already
              published, tunables logs a warning and this instance works on a
              private (unpublished) value.
            - Registers with Logger so periodic() runs every cycle.

        Raises:
            NotImplementedError: If the subclass did not implement ``_publish``.
        """
        self._key = key
        self._default = self._coerce(default)
        self._value = self._default
        self._tunable = self._publish(LoggedNetworkInput.remove_slash(key), self._default)

        Logger.register_tunable_input(self)

    def _publish(self, name: str, default: T) -> tunables.Tunable:
        """
        Create the backing tunable. Implemented by subclasses.

        Args:
            name (str): The relative tunable name (no leading "/")
            default (T): The initial value

        Returns:
            tunables.Tunable: A handle with ``get()`` and ``set()`` methods
        """
        raise NotImplementedError

    def _coerce(self, value: T) -> T:
        """
        Normalize a value before it is stored or written. Identity by default.

        Args:
            value (T): The value supplied by robot code

        Returns:
            T: The value to store
        """
        return value

    def __call__(self) -> T:
        """
        Return the current value; shorthand for the ``value`` property.

        Example:
            ```python
            enabled = LoggedNetworkBoolean("Enabled", default=False)

            if enabled():  # Compact syntax in conditionals
                do_something()
            ```
        """
        return self.value

    @property
    def value(self) -> T:
        """
        The current value as of the latest periodic() call.

        In normal operation this is the value last read from the tunable (what the
        operator set in Elastic). During replay it is the value restored from the log.
        """
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        """
        Set the value and write it through to the tunable.

        The new value is stored immediately and written to the tunable so Elastic
        shows it. If an operator edits the value in Elastic afterwards, the next
        periodic() call picks up the operator's value.

        Args:
            value (T): The new value (normalized by ``_coerce``)
        """
        self._value = self._coerce(value)
        self._tunable.set(self._value)

    def set_default(self, default: T) -> None:
        """
        Change the fallback value used when a log entry is missing in replay.

        This does not change the value currently shown in Elastic; assign to
        ``value`` to do that.

        Args:
            default (T): The new fallback value
        """
        self._default = self._coerce(default)

    def to_log(self, table: LogTable, prefix: str) -> None:
        """
        Record the cached value in the log table (normal mode).

        Called by Logger.process_inputs(). The entry key is
        ``{prefix}/{key}`` with any leading "/" removed from the key, e.g.
        prefix ``NetworkInputs`` and key ``Drive/MaxSpeed`` log at
        ``NetworkInputs/Drive/MaxSpeed``.

        Args:
            table (LogTable): The log table to write to
            prefix (str): Namespace prefix (normally ``NetworkInputs``)
        """
        table.put(f"{prefix}/{LoggedNetworkInput.remove_slash(self._key)}", self._value)

    def from_log(self, table: LogTable, prefix: str) -> None:
        """
        Restore the cached value from the log table (replay mode).

        Called by Logger.process_inputs() during replay. If the entry is missing
        the default is used, which keeps incomplete logs from breaking replay.

        Args:
            table (LogTable): The log table to read from
            prefix (str): Namespace prefix (normally ``NetworkInputs``)
        """
        self._value = table.get(
            f"{prefix}/{LoggedNetworkInput.remove_slash(self._key)}",
            self._default,
        )

    def periodic(self) -> None:
        """
        Refresh the cached value and log it; called by Logger every cycle (~50 Hz).

        - Normal mode: copies the tunable's current value (updated by Elastic via
          TunableRegistry.update()) into the cache, then logs it.
        - Replay mode: leaves the tunable alone; Logger.process_inputs() restores the
          cached value from the log.

        Users should not call this directly.
        """
        if not Logger.is_replay():
            self._value = self._tunable.get()

        Logger.process_inputs(self.prefix, self)
