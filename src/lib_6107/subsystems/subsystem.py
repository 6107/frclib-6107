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
from copy import deepcopy
from enum import Enum, unique
from typing import Any, Callable, Optional, Tuple

from commands2 import Subsystem
from commands2.command import Command
from commands2.sysid import SysIdRoutine
from phoenix6.hardware import TalonFX
from rev import REVLibError, SparkBaseConfig, \
    SparkClosedLoopController, SparkFlex, SparkFlexSim, SparkMax, SparkMaxSim, \
    SparkRelativeEncoder
from wpilib import RobotBase
from wpilib.simulation import RoboRioSim
from wpilib.sysid import SysIdRoutineLog
from wpimath.system.plant import DCMotor
from wpimath.units import amperes, radians, radians_per_second, radiansPerSecondToRotationsPerMinute, \
    revolutions_per_minute, seconds, volts

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer
from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO

logger = logging.getLogger(__name__)


#@autologgable_output
class SubsystemBase(Subsystem):
    """
    A subsystem base class that primarily is used to add metadata at robot initialzation
    to the AdvantageScope log and maintain a minimum amount of other shared data
    """
    def __init__(self, container: 'RobotContainer', name: str, long_name: str | None) -> None:
        #
        # Set the following to True at the very end of your actual SubSystem init. This is to
        # avoid a race condition in 'pykit' where the 'periodic' and other functions may be
        # called for a subsystem 'before' full initialization. This is due to how some vendor
        # firmware routines work.
        #
        self._initialized = False   # Set to true at end of derived class __init__()
        #
        super().__init__()

        # General attributes
        self._name = name
        self.setName(name)
        self._long_name = long_name or name  # Typically for logging/smartdashboard such as "intake/indexer"
        self._container = container
        self._robot = container.robot
        self._period: seconds = container.robot.period
        self._is_simulation = RobotBase.isSimulation()

        # Simulation only (set in derived class __init__ after this call or in sim_init)
        self._physics_controller = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _check_is_connected(self, config_status: REVLibError | None) -> bool:
        """
        For Rev Robotics, the only way to check if all is well i
        """
        raise NotImplementedError("_check_is_connected: Implement in a derived class")

    @property
    def is_connected(self) -> bool:
        """
        Detect if this device is connected to the CAN Bus.  For Rev Robotics,
        the default way is based on config results. When we support CTRE, they
        have a 'isStatusOK' call that is useful.
        """
        raise NotImplementedError("is_connected: Implement in a derived class")

    def stop(self) -> None:
        """
        Called to place the subsystem in a 'stoapped' / 'safe' state
        """

    def dashboard_initialize(self) -> None:
        """
        Configure the SmartDashboard for this subsystem
        """

    def dashboard_periodic(self) -> None:
        """
        Called from periodic function to update dashboard elements for this subsystem
        """

    def fault_detection(self, state: str, clear: Optional[bool] = True, notify: Optional[bool] = True) -> None:
        """
        This routine is responsible for reading any existing faults and based
        input parameters, report them for display, and possibly clear them

        All faults detected always results in a warning log message, so please be
        aware of this if you do not clear them
        """

    ###########################################################
    # Metadata Support
    def record_metadata(self) -> None:
        """
        Called during initialization to have subsystem save of metadata information about
        itself for use in AdvantageScope. Typical things to save are.

            - Mechanism Type
            - Firmware Versions,
            - Existing Faults at startup
        """
    ###########################################################
    # Simulation Support

    def sim_init(self, physics_controller: 'PhysicsInterface') -> None:
        """
        Initialize any simulation only needed parameters
        """
        self._physics_controller = physics_controller

    def update_sim(self, _now: float, tm_diff: float) -> amperes | None:
        """
        Called when the simulation parameters for the program need to be updated.
        This function is called from the '_simulationPeriodic' function of the
        robotpy core routine and is called at a period >= 10 mS. Note that the
        CommandScheduler also has an 'simulationPeriodic' function that it calls
        into all Command2 based subsystems at its update period which has a
        default rate of 20 mS.

        This is called 'after' the CommandScheduler's 'simulationPeriodic', so if
        that function uses pykit's logging method, you should use those values in
        your simulation.

        :param _now:    The current time as a float
        :param tm_diff: The amount of time that has passed since the last
                        time that this function was called
        """
        return None
