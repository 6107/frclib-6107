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
Logged Network Boolean Module: Operator-Editable Booleans with Logging and Replay

LoggedNetworkBoolean publishes a true/false value as a tunable
(``/Tunables/<key>``) that operators toggle in Elastic. The value is logged every
cycle and can be replayed deterministically.

Typical Usage:
    intake_enabled = LoggedNetworkBoolean("Intake/Enabled", default=False)

    # In robot code
    if intake_enabled.value:
        intake.enable()

Typical Applications:
- Feature toggles and debug switches
- Subsystem enable/disable flags
- Mode selection (e.g., use vision, manual override)
- Momentary buttons (see ``NetworkTableButton``)
"""

import tunables

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue


class LoggedNetworkBoolean(LoggedNetworkValue[bool]):
    """
    Operator-editable boolean published as a tunable.

    Backed by ``tunables.add_boolean``.

    Example:
        ```python
        debug_mode = LoggedNetworkBoolean("Debug/Enabled", default=False)
        use_vision = LoggedNetworkBoolean("Config/Vision", default=True)

        if debug_mode.value:
            enable_debug_logging()
        ```

    Elastic:
        The toggle appears at ``/Tunables/<key>``. Changes made in Elastic are
        visible to robot code on the next cycle.

    Logging:
        The value is logged at ``NetworkInputs/<key>``.
    """

    def __init__(self, key: str, default: bool = False) -> None:
        """
        Create and publish a boolean tunable.

        Args:
            key (str): Tunable name shown in Elastic (e.g., "Debug/Enabled").
            default (bool): Initial value. Defaults to False.

        Example:
            ```python
            debug_enabled = LoggedNetworkBoolean("Debug/Enabled", default=False)
            use_vision = LoggedNetworkBoolean("Config/Vision", default=True)
            ```
        """
        super().__init__(key, default)

    def _publish(self, name: str, default: bool) -> tunables.Tunable:
        return tunables.add_boolean(name, default)
