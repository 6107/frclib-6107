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
#  NOTE: Yep, that's all there is to it. The base class from the frclib_6107
#        does all the work for you.

from pyfrc.physics.core import PhysicsInterface

from lib_6107.robot import Robot
from lib_6107.physics import PhysicsEngine as PhysicsEngineBase


class PhysicsEngine(PhysicsEngineBase):
    """
    Any objects created or manipulated in this file are for simulation purposes only.
    """
    def __init__(self, physics_controller: PhysicsInterface, robot: Robot):
        """
        Initialize the simulator.  This method is called after the container and all
        subsystems have been initialized.

        :param physics_controller: `pyfrc.physics.core.Physics` object
                                   to communicate simulation effects to
        :param robot: your robot object
        """
        super().__init__(physics_controller, robot)
