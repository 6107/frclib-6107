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
Logged Network Number Module: Operator-Editable Numbers with Logging and Replay

LoggedNetworkNumber publishes a floating point value as a tunable
(``/Tunables/<key>``) that operators edit in Elastic. The value is logged every
cycle and can be replayed deterministically.

Typical Usage:
    max_speed = LoggedNetworkNumber("Drive/MaxSpeed", default=3.0)

    # In robot code
    command_speed = desired_speed * max_speed.value

Typical Applications:
- PID gains tuned live (``Drive/PID/kP``)
- Speed and acceleration limits
- Sensor calibration offsets and scale factors
- Test durations and voltages

For validated numeric entry (minimum/maximum bounds), use ``FloatEditBox`` or
``IntegerEditBox`` from ``lib_6107.util.numerical_chooser`` instead.
"""

import tunables

from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue


class LoggedNetworkNumber(LoggedNetworkValue[float]):
    """
    Operator-editable floating point number published as a tunable.

    Backed by ``tunables.add_double``. Integer defaults and assigned integers are
    converted to ``float``.

    Example:
        ```python
        pid_kp = LoggedNetworkNumber("Drive/PID/kP", default=0.1)
        pid_ki = LoggedNetworkNumber("Drive/PID/kI", default=0.0)

        controller.set_p(pid_kp.value)
        controller.set_i(pid_ki())  # Calling the instance returns the value too
        ```

    Elastic:
        The number appears at ``/Tunables/<key>``. Edits made in Elastic are visible
        to robot code on the next cycle.

    Logging:
        The value is logged at ``NetworkInputs/<key>``.
    """

    def __init__(self, key: str, default: float = 0.0) -> None:
        """
        Create and publish a number tunable.

        Args:
            key (str): Tunable name shown in Elastic (e.g., "Drive/MaxSpeed").
            default (float): Initial value. Integers are converted to float.
                Defaults to 0.0.

        Example:
            ```python
            max_speed = LoggedNetworkNumber("MaxSpeed", default=3.0)
            encoder_scale = LoggedNetworkNumber("Drive/Calibration/EncoderScale", default=1.0)
            ```
        """
        super().__init__(key, default)

    def _publish(self, name: str, default: float) -> tunables.Tunable:
        return tunables.add_double(name, default)

    def _coerce(self, value: float) -> float:
        return float(value)
