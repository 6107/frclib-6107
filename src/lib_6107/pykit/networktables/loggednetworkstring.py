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
Logged Network String Module: Operator-Editable Text with Logging and Replay

LoggedNetworkString publishes a text value as a tunable (``/Tunables/<key>``) that
operators edit in Elastic. The value is logged every cycle and can be replayed
deterministically.

Typical Usage:
    strategy = LoggedNetworkString("Config/SelectedStrategy", default="Default")

    # In robot code
    if strategy.value == "Aggressive":
        schedule(aggressive_auto())

Typical Applications:
- Free-form configuration (strategy names, team labels)
- Match notes entered by the drive team
- Diagnostics text shown to the operator
"""

import tunables

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue


class LoggedNetworkString(LoggedNetworkValue[str]):
    """
    Operator-editable string published as a tunable.

    Backed by ``tunables.add``, which infers a string tunable from the default.
    Unicode text is supported.

    Example:
        ```python
        robot_state = LoggedNetworkString("Robot/State", default="Idle")
        team_name = LoggedNetworkString("Config/TeamName", default="Team 6107 ロボット")

        robot_state.value = "Running"   # Writes through to Elastic
        ```

    Elastic:
        The text box appears at ``/Tunables/<key>``. Edits made in Elastic are
        visible to robot code on the next cycle.

    Logging:
        The value is logged at ``NetworkInputs/<key>``.
    """

    def __init__(self, key: str, default: str = "") -> None:
        """
        Create and publish a string tunable.

        Args:
            key (str): Tunable name shown in Elastic (e.g., "Match/GameData").
            default (str): Initial value. Defaults to the empty string.

        Example:
            ```python
            game_data = LoggedNetworkString("Match/GameData", default="")
            last_error = LoggedNetworkString("Diagnostics/LastError", default="No Errors")
            ```
        """
        super().__init__(key, default)

    def _publish(self, name: str, default: str) -> tunables.Tunable:
        return tunables.add(name, default)
