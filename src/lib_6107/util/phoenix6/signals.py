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
import logging
from enum import Enum

from wpilib import RobotBase

logger = logging.getLogger(__name__)

try:
    from phoenix6 import StatusCode, StatusSignal

except ImportError:

    class StatusCode(Enum):
        OK = 0

    class StatusSignal:
        name = "Not Supported"

        @staticmethod
        def refresh_all() -> StatusCode:
            return StatusCode.OK


class Phoenix6Signals:
    """
    Optimizer for CTRE devices
    """

    _signals: set[StatusSignal] = set()

    @classmethod
    def register_signal(cls, signal: StatusSignal) -> None:
        if signal not in cls._signals:
            cls._signals.add(signal)
        else:
            logging.warning(f"Signal {signal.name} already registered")

    @classmethod
    def register_signals(cls, *signals: StatusSignal) -> None:
        for signal in signals:
            cls.register_signal(signal)

    @classmethod
    def unregister_signal(cls, signal: StatusSignal) -> None:
        cls._signals.discard(signal)

    @classmethod
    def clear(cls) -> None:
        """Remove every registered signal (used by tests and when subsystems are rebuilt)"""
        cls._signals.clear()

    @classmethod
    def refresh(cls) -> StatusCode:
        """
        In robot.robot_periodic, call this to request all status to be updated at once. Documentation
        says it is faster
        """
        if not cls._signals:
            return StatusCode.OK

        # In simulation the CTRE sim does not publish status frames on a real CAN schedule, so the
        # periodic "stale" (Warning 1000) reports from refresh_all are spurious; keep them on a real robot.
        return StatusSignal.refresh_all(*list(cls._signals), report_error=not RobotBase.is_simulation())
