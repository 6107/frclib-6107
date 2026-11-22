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

from dataclasses import dataclass

from wpimath.units import amperes, celsius, radians, radians_per_second, volts

from lib_6107.pykit.autolog import autolog


class RpmMechanismIO:
    """
    Drive I/O for a mechanism that has an RPM Goal
    """

    @autolog
    @dataclass(slots=True)
    class RpmMechanismIOInputs:
        mechanism_connected: bool = False

        mechanism_position: radians = 0.0
        mechanism_velocity: radians_per_second = 0.0
        mechanism_applied_voltage: volts = 0.0
        mechanism_supply_current: amperes = 0.0

        # Appended fields keep existing keys stable for log replay
        mechanism_temperature: celsius = 0.0
        mechanism_faults_raw: int = 0
        mechanism_warnings_raw: int = 0
        mechanism_last_error: int = 0

    def __init__(self, name: str) -> None:
        self.name = name

    def update_inputs(self, inputs: RpmMechanismIOInputs) -> None:
        """Update the drive I/O inputs.

        Args:
            inputs (RpmMechanismIOInputs): The drive I/O inputs to update.
        """
        pass
