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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from commands2 import Command, Subsystem
from wpilib import RobotBase

from lib_6107.pykit.logger import Logger

if TYPE_CHECKING:
    from subsystems.drivetrain.drivesubsystem import DriveSubsystem

    from lib_6107.robotcontainer import RobotContainer

logger = logging.getLogger(__name__)


class BaseCommand(Command):
    """
    Base Command class for Team 6107 robotics
    """

    def __init__(self, target):
        super().__init__()
        self._name = self.get_class_name()  # TODO: Work on how to best set the name in all existing derived classes
        self.set_name(self._name)

        # if not isinstance(target, ('RobotContainer', 'DriveSubsystem')):
        #     raise ValueError(f"target must be a subclass of RobotContainer or DriveSubsystem")

        self._target: DriveSubsystem | RobotContainer = target
        self._drivetrain: DriveSubsystem | None = None
        self._container: RobotContainer | None = None

        if isinstance(self._target, Subsystem):
            self.add_requirements(target)  # commandsV2 version of requirements'

        self._resolve_target()

        self._start_time: float = 0
        self._log_level = logging.INFO if RobotBase.is_simulation() else logging.DEBUG

    def _resolve_target(self) -> None:
        """
        Determine the container and drivetrain from the target. A RobotContainer target exposes
        ``robot_drive``; a drivetrain target exposes ``container``.
        """
        if hasattr(self._target, "robot_drive"):
            self._container = self._target
            self._drivetrain = self._target.robot_drive

        elif hasattr(self._target, "container"):
            self._drivetrain = self._target
            self._container = self._target.container

    @property
    def name(self) -> str:
        return self._name

    @classmethod
    def get_class_name(cls) -> str:
        return cls.__name__

    def initialize(self) -> None:
        """
        Called just before this Command runs the first time
        """
        self._resolve_target()

        self._start_time = round(self._container.get_elapsed_time(), 2)
        logging.info("%s: Started at %s", self._name, self._start_time)

        Logger.record_output(f"Commands/{self._name}/State", "running")

    def record_status(self, status: str) -> None:
        """
        Record a human-readable progress status for this command (replaces the 2026
        ``SmartDashboard.putString("command/<name>", status)`` pattern).

        Args:
            status: Short description of what the command is currently doing.
        """
        Logger.record_output(f"Commands/{self._name}/Status", status)

    def end(self, interrupted: bool) -> None:
        """
        The action to take when the command ends. Called when either the command finishes normally, or
        when it interrupted/canceled.

        Do not schedule commands here that share requirements with this command. Use :meth:`.and_then` instead.

        :param interrupted: whether the command was interrupted/canceled
        """
        end_time = self._container.get_elapsed_time()
        message = (
            f"{self._name}: {'Interrupted' if interrupted else 'Ended'} at {end_time:.1f} s"
            f" after {end_time - self._start_time:.1f} s"
        )
        logging.info(message)  # pylint: disable=logging-fstring-interpolation

        Logger.record_output(f"Commands/{self._name}/State", "interrupted" if interrupted else "ended")
