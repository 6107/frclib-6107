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
from collections.abc import Callable
from math import copysign

from commands2 import Command, cmd
from commands2.button import CommandDualShock4Controller, CommandXboxController
from wpilib import GenericHID

AnalogInput = Callable[[], float]

kXboxJoystickDeadband = 0.1
"""dimensionless"""

kKeyboardJoystickDeadband = 0.0
"""dimensionless"""

kXboxTriggerActivationThreshold = 0.5


def deadband(input_fn: AnalogInput, deadband_limit: float) -> AnalogInput:
    def _with_deadband() -> float:
        value = input_fn()
        return 0 if abs(value) <= deadband_limit else value

    return _with_deadband


def invert(input_fn: AnalogInput) -> AnalogInput:
    def _invert() -> float:
        return -1 * input_fn()

    return _invert


def sign_square(input_fn: AnalogInput) -> AnalogInput:
    def square() -> float:
        val = input_fn()
        return copysign(val * val, val)

    return square


class OperatorInterface:
    """
    The controls that the operator(s)/driver(s) interact with
    """

    driverController: CommandDualShock4Controller | CommandXboxController
    operatorController: CommandDualShock4Controller | CommandXboxController

    def __init__(self) -> None:
        # if kRobotMode == RobotModes.SIMULATION:
        #     self.driverController = CommandXboxController(0)
        # else:
        self.driverController = CommandXboxController(0)
        self.operatorController = CommandXboxController(1)

        self.driverX = sign_square(invert(deadband(self.driverController.get_left_x, kXboxJoystickDeadband)))
        self.driverY = sign_square(invert(deadband(self.driverController.get_left_y, kXboxJoystickDeadband)))
        self.driverRotationX = invert(deadband(self.driverController.get_right_x, kXboxJoystickDeadband))
        self.driverRotationY = invert(deadband(self.driverController.get_right_y, kXboxJoystickDeadband))

    def rumble_controllers(self, amount: float = 1.0) -> None:
        for controller in (self.driverController, self.operatorController):
            controller.get_hid().set_rumble(GenericHID.RumbleType.LEFT_RUMBLE, amount)
            controller.get_hid().set_rumble(GenericHID.RumbleType.RIGHT_RUMBLE, amount)

    def rumble_controllers_command(self, amount: float = 1.0) -> Command:
        return cmd.start_end(lambda: self.rumble_controllers(amount), lambda: self.rumble_controllers(0.0))
