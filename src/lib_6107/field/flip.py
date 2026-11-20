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
#  Credit for the original idea is Westwood Robotics.  Look them up...
#
"""
FlipUtil: flip wpilib geometry for the red alliance.

The mirroring rule itself lives in ``coordinates.py`` so it can change with the 2027 coordinate system.
"""

from wpilib import Alliance
from wpimath import Pose2d, Rotation2d, Translation2d

from lib_6107.field.coordinates import mirror_rotation, mirror_translation
from lib_6107.field.game_field import GameField


class FlipUtil:
    """
    Utility for flipping wpilib geometry classes based on the current alliance

    :param game_field: The ``GameField`` supplying the alliance, field size and coordinate convention
    """

    def __init__(self, game_field: GameField):
        self._game_field = game_field

    def should_flip(self) -> bool:
        """
        :return: True if geometry should be flipped (we are on the red alliance)
        """
        return self._game_field.alliance == Alliance.RED

    def field_pose(self, pose: Pose2d) -> Pose2d:
        """Flip a Pose2d based on the current alliance"""
        return Pose2d(
            self.field_translation(pose.translation()),
            self.field_rotation(pose.rotation()),
        )

    def field_translation(self, translation: Translation2d) -> Translation2d:
        """Flip a Translation2d based on the current alliance"""
        if self.should_flip():
            return mirror_translation(
                self._game_field.coordinates,
                translation,
                self._game_field.field_length,
                self._game_field.field_width,
            )
        return translation

    def field_rotation(self, rotation: Rotation2d) -> Rotation2d:
        """Flip a Rotation2d based on the current alliance"""
        if self.should_flip():
            return mirror_rotation(self._game_field.coordinates, rotation)
        return rotation
