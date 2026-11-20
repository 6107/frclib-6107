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
FieldCoordinates: the single place that describes *how* field coordinates are laid out and how a pose is mirrored
for the other alliance.

The coordinate system changes in 2027. Until the 2027 field data is released we only know the 2026 convention, so
that is the only member below. When 2027 data is available:

1. Add a new ``FieldCoordinates`` member (for example ``BLUE_ORIGIN_2027``) and describe it in its comment.
2. Teach ``mirror_translation`` / ``mirror_rotation`` about it (one ``match`` arm each).
3. Pass it to the year's ``GameField`` subclass (``coordinates=...``) and to the ``FieldLayout`` factories.

Nothing else in lib_6107 should hard-code the origin, axis directions or the red-alliance mirroring rule. Always
go through ``GameField.coordinates`` / ``FlipUtil``.
"""

from enum import Enum
from math import pi

from wpimath import Rotation2d, Translation2d
from wpimath.units import meters


class FieldCoordinates(Enum):
    """Known field coordinate conventions"""

    # 2026 (and earlier) WPILib "always blue origin" convention (units are meters):
    #   * Origin (0, 0) is the corner at the right side of the blue alliance wall, seen from the blue driver station
    #   * +X points from the blue alliance wall toward the red alliance wall (along the field length)
    #   * +Y points to the left, as seen from the blue driver station (along the field width)
    #   * Rotation is counter-clockwise positive; 0 degrees faces +X (toward red)
    #   * Mirroring a pose for the red alliance rotates it 180 degrees about the field center
    #     (x -> length - x, y -> width - y, heading + 180 degrees)
    BLUE_ORIGIN_2026 = "blue-origin-2026"


# TODO: Revisit when the 2027 field/coordinate data is released
DEFAULT_COORDINATES = FieldCoordinates.BLUE_ORIGIN_2026


def mirror_translation(
    coordinates: FieldCoordinates, translation: Translation2d, length: meters, width: meters
) -> Translation2d:
    """
    Mirror a translation to the other alliance's side of the field.

    :param coordinates: Coordinate convention in use
    :param translation: Translation to mirror
    :param length: Field length in meters
    :param width: Field width in meters
    """
    match coordinates:
        case FieldCoordinates.BLUE_ORIGIN_2026:
            return Translation2d(length, width) - translation

    raise NotImplementedError(f"mirror_translation: unsupported coordinates {coordinates}")


def mirror_rotation(coordinates: FieldCoordinates, rotation: Rotation2d) -> Rotation2d:
    """
    Mirror a heading to the other alliance's side of the field.

    :param coordinates: Coordinate convention in use
    :param rotation: Rotation to mirror
    """
    match coordinates:
        case FieldCoordinates.BLUE_ORIGIN_2026:
            return rotation - Rotation2d(pi)

    raise NotImplementedError(f"mirror_rotation: unsupported coordinates {coordinates}")
