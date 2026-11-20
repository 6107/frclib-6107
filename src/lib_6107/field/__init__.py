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
Field and AprilTag support. See ``README.md`` in this directory.
"""

from lib_6107.field.coordinates import DEFAULT_COORDINATES, FieldCoordinates, mirror_rotation, mirror_translation
from lib_6107.field.flip import FlipUtil
from lib_6107.field.game_field import FieldCallback, FieldChange, GameField
from lib_6107.field.layout import FieldLayout, FieldTag
from lib_6107.field.selector import FieldSelector
from lib_6107.field.sources import FieldSource, load_layout

__all__ = [
    "DEFAULT_COORDINATES",
    "FieldCallback",
    "FieldChange",
    "FieldCoordinates",
    "FieldLayout",
    "FieldSelector",
    "FieldSource",
    "FieldTag",
    "FlipUtil",
    "GameField",
    "load_layout",
    "mirror_rotation",
    "mirror_translation",
]
