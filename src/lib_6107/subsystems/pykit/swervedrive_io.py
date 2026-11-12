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

from wpimath import Rotation2d
from wpimath.units import amperes, radians, radians_per_second, volts

from lib_6107.pykit.autolog import autolog


class SwerveModuleIO:
    """
    SwerveDriveIO provides drive I/O to provide log information for AdvantageScope
    replay and simulation.
    """

    @autolog
    @dataclass(slots=True)
    class SwerveModuleIOInputs:
        drive_connected: bool = False
        steer_connected: bool = False
        encoder_connected: bool = False

        drive_position: radians = 0.0  # rad
        drive_velocity: radians_per_second = 0.0  # rad / sec
        drive_applied: volts = 0.0  # volts
        drive_supply_current: amperes = 0.0  # amps
        drive_torque_current: amperes = 0.0  # amps

        turn_position: radians = 0.0  # rad
        turn_velocity: radians_per_second = 0.0  # rad / sec
        turn_applied: volts = 0.0  # volts
        turn_supply_current: amperes = 0.0  # amps
        turn_torque_current: amperes = 0.0  # amps

        turn_absolute_position: float = 0.0  # rad

    def __init__(self, name: str) -> None:
        self.name = name

    def update_inputs(self, inputs: SwerveModuleIOInputs) -> None:
        """
        Update the swerve module I/O inputs.

        Args:
            inputs (SwerveModuleIOInputs): The swerve module I/O inputs to update.
        """

    def set_swerve_angle(self, swerveAngle: Rotation2d) -> None:
        """
        Set the swerve module angle.

        Args:
            swerveAngle (Rotation2d): The desired swerve module angle.
        """

    def set_wheel_linear_velocity_target(self, wheelLinearVelocityTarget: float) -> None:
        """
        Set the swerve module wheel linear velocity.

        Args:
            wheelLinearVelocity_m_per_s (float): The desired wheel linear velocity in meters per second.
        """

    def set_swerve_angle_target(self, swerveAngleTarget: Rotation2d) -> None:
        """
        Set the swerve module angle target.

        Args:
            swerveAngleTarget (Rotation2d): The desired swerve module angle target.
        """
