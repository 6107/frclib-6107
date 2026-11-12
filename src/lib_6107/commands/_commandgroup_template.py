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
#  This file originated from aesatchien's FRC2429_2025 project on github:
#       https://github.com/aesatchien/FRC2429_2025
#
#  It provides a starting place to define a Command Group. Just copy it to
#  a new filename and change the class name and implementation to suite what you
#  may need in your project.
#

from commands2 import PrintCommand, SequentialCommandGroup


class CommandGroupTemplate(SequentialCommandGroup):
    """
    TODO: Describe this class here
    """

    def __init__(self, container, indent: int | None = 0) -> None:
        super().__init__()

        self._name = self.__class__.__name__
        self.set_name(self._name)
        self.container = container
        self.add_commands(PrintCommand(f"{'    ' * indent}** Started {self._name} **"))

        # self.add_commands(... your stuff here, call other commands with indent=indent+1 ...)

        self.add_commands(PrintCommand(f"{'    ' * indent}** Finished {self._name} **"))

        raise NotImplementedError("Remember to remove this line as well")  # TODO: work here
