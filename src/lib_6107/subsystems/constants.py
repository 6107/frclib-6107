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
#
# Constants for source in this subdirectory will go here

import math

from dataclasses import dataclass
from enum import Enum, unique

from wpimath.units import meters, radians

@unique
class VisionSubsystemType(Enum):
    """
    Supported vision subsystem types.
    """
    NONE         = ""
    LIMELIGHT    = "Limelight"  # Currently Limelight 2 only
    PHOTONVISION = "PhotonVision"


@dataclass(slots=True)
class VisionConstants:
    """
    Various constants often used in vision calls (LimeLight and/or PhotonVision).
    """
    # TODO: Look into the april tag heights and how Z_ERROR is actually used and obtained and
    #       see if we can calculate it from the field data on startup to be 1/2 meter above the
    #       maximum
    MAX_VISION_AMBIGUITY: float = 0.3
    MAX_VISION_Z_ERROR: meters = 1.5  # 0.75

    # Adjusted automatically based on distance and # of tags
    LINEAR_STD_DEV_BASELINE: meters = 0.02
    ANGULAR_STD_DEV_BASELINE: radians = 0.06

    # Multipliers to apply for MegaTag 2 observations
    LINEAR_STD_DEV_MEGATAG2_FACTOR: float = 0.5  # More stable than full 3D solve
    ANGULAR_STD_DEV_MEGATAG2_FACTOR: float = math.inf  # No rotation data available

    # Vision Pipeline for April tags. The pipelines need to be manually
    # set up in the camera and should use the following pipeline number. [0..9]
    APRILTAGS_PIPELINE: int = 0  # TODO: Need to set this up in all our cameras
