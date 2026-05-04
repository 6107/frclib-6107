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
"""Robot physics simulation engine for pyfrc.

This module implements the physics simulation for the frclib-6107 library using pyfrc.
It provides a framework for simulating robot mechanisms and subsystems during desktop
testing without hardware.

The physics engine integrates with all subsystems in the robot container that implement
the optional sim_init() and update_sim() hooks. Each subsystem can provide its own
simulation physics, which are aggregated to calculate overall battery draw and update
the WPILib simulation state.

Key Features:
    - Automatic subsystem simulation initialization via sim_init() hook
    - Centralized battery voltage simulation using BatterySim
    - Performance profiling via LogTracer for simulation update cycles
    - Alliance color and starting position management
    - Field visualization synchronization

Usage:
    This class is instantiated automatically by pyfrc when running in simulation mode.
    Team implementations typically override specific subsystem sim_init() and update_sim()
    methods to model mechanism physics (motor dynamics, pneumatics, etc.).

References:
    - pyfrc documentation: https://robotpy.readthedocs.io/projects/pyfrc/en/latest/physics.html
    - pyfrc examples: https://github.com/robotpy/examples
"""

import logging
from typing import List

from pyfrc.physics.core import PhysicsInterface
from wpilib.simulation import BatterySim, RoboRioSim
from wpimath.units import amperes

from lib_6107.robot import Robot

from lib_6107.pykit.logtracer import LogTracer

logger = logging.getLogger(__name__)


class PhysicsEngine:
    """Physics simulation engine for the frclib robot.

    Manages the overall simulation lifecycle and coordinates physics updates across all
    subsystems. Acts as the central hub for robot-wide simulation, including battery
    voltage simulation, field visualization, and alliance management.

    This engine is instantiated after the RobotContainer and all subsystems are
    initialized. It recursively calls sim_init() on every subsystem that implements it,
    allowing each subsystem to configure its own physics simulation.

    During each simulation update (called at ≥10 mS intervals by pyfrc), the engine:
    1. Collects current draw from each subsystem's update_sim() method
    2. Calculates total battery voltage draw using WPILib's BatterySim
    3. Updates the simulated RoboRIO voltage
    4. Profiles performance using LogTracer

    Attributes:
        _physics_controller (PhysicsInterface): Reference to pyfrc's physics interface
            for updating simulation state and field visualization.
        _robot (Robot): Reference to the main Robot object for accessing the container
            and its subsystems.
        field: The field visualization object from the physics controller. Used for
            updating robot pose for visualization in simulation tools.

    Note:
        Teams typically do not modify this class directly. Instead, implement
        sim_init() and update_sim() methods in subsystems to define custom physics.
    """

    def __init__(self, physics_controller: PhysicsInterface, robot: "Robot"):
        """Initialize the physics simulation engine.

        Called once at the start of simulation after all subsystems have been
        initialized. This method:
        1. Stores references to the physics controller and robot
        2. Calls sim_init() on all subsystems that implement it
        3. Sets up the field visualization
        4. Registers for alliance color changes
        5. Sets the initial robot pose based on alliance and location

        Args:
            physics_controller (PhysicsInterface): The pyfrc physics controller
                used to update simulation state and field visualization.
            robot (Robot): The main Robot instance containing RobotContainer
                and all subsystems.

        Raises:
            Exception: Any exception raised by subsystem sim_init() is propagated
                after logging.

        Note:
            The field reference is used for all subsequent pose updates. Alliance
            changes trigger automatic field reorientation and pose updates.
        """
        logger.info("PhysicsEngine.__init__: entry")

        self._physics_controller = physics_controller
        self._robot: Robot = robot

        # Initialize simulated subsystems by calling their optional sim_init() hook
        for subsystem in robot.container.subsystems:
            if hasattr(subsystem, "sim_init") and callable(getattr(subsystem, "sim_init")):
                subsystem.sim_init(physics_controller)

        # Set up field visualization from the physics controller
        # The field is pre-configured in the physics controller's simulation setup
        # and provides real-time visualization of the robot's pose
        self.field = physics_controller.field

        # Register for alliance color changes before match starts
        # TODO: If vision odometry is supported in simulation, this may need to be
        #       changed to the robot's field view (first-person) instead of the
        #       overhead field view to better simulate vision processing.
        robot.container.register_alliance_change_callback(self._alliance_change)
        self._alliance_change(self._robot.container.is_red_alliance,
                              self._robot.container.alliance_location)

        logger.info("PhysicsEngine.__init__: exit")

    def update_sim(self, now: float, tm_diff: float) -> None:
        """Update robot physics simulation for the current time step.

        Called periodically (at intervals ≥10 mS) by pyfrc during simulation.
        This is the main physics update loop and is responsible for:
        1. Calling update_sim() on all subsystems that implement it
        2. Collecting current draw estimates from each subsystem
        3. Simulating battery voltage depletion using BatterySim
        4. Profiling update performance with LogTracer

        Subsystem update_sim() methods are called after CommandScheduler's own
        simulationPeriodic (default 20 mS), so they can use values logged by
        subsystem commands in the same cycle.

        This method includes error handling: if any subsystem's update_sim() raises
        an exception, it is logged and re-raised to prevent silent failures.

        Args:
            now (float): Current simulation time in seconds since the start of the
                simulation.
            tm_diff (float): Time delta since the last update_sim() call, in seconds.
                Typical value: 0.010 (10 mS) or 0.020 (20 mS).

        Raises:
            Exception: Any exception raised by a subsystem's update_sim() is caught,
                logged with subsystem name, and re-raised.

        Note:
            Performance profiling is done for each subsystem's update_sim() call
            and logged to LogTracer under the key "{subsystem_name}-UpdateSim".
            Total update time is recorded as "UpdateSimTotal".
        """
        LogTracer.resetOuter("UpdateSim")

        current_used: List[amperes] = []
        for subsystem in self._robot.container.subsystems:
            try:
                # Call update_sim() on subsystems that have implemented it
                if hasattr(subsystem, "update_sim") and callable(getattr(subsystem, "update_sim")):
                    # Subsystems return current draw in amperes or None if not applicable
                    amps: amperes | None = subsystem.update_sim(now, tm_diff)
                    if amps is not None:
                        current_used.append(amps)

                    # Profile each subsystem's update performance
                    LogTracer.record(f"{subsystem.getName()}-UpdateSim")

            except Exception as e:
                # Log subsystem exceptions with full context before re-raising
                logger.exception("Subsystem %s threw an exception during update_sim: %s",
                                 subsystem.getName(), str(e))
                raise

        # Calculate and update battery voltage based on total current draw
        if current_used:
            # BatterySim.calculate() uses 12V battery model with internal resistance
            # Returns the voltage under load based on the list of currents drawn
            RoboRioSim.setVInVoltage(BatterySim.calculate(current_used))
            # TODO: Consider adding SmartDashboard telemetry for simulated battery state
            #       or RoboRIO voltage for debugging battery-related issues in simulation

        # Record total time spent in this update cycle for performance analysis
        LogTracer.recordTotal()

    def _alliance_change(self, is_red: bool, location: int) -> None:
        """Handle alliance color or starting location changes.

        Called when the robot's alliance is selected (typically before the match
        starts). Updates the field visualization to show the correct starting pose
        and field orientation based on the selected alliance and starting location.

        The starting pose is retrieved from the SimulationConstants using the
        alliance color and location index.

        Args:
            is_red (bool): True if the robot is on the red alliance, False for blue.
            location (int): Starting location index (typically 0, 1, or 2 representing
                left, center, right starting positions).

        Note:
            This method is called automatically during initialization to set up the
            initial pose. It can also be called during simulation if the user
            changes the alliance selection in the simulator UI.
        """
        const = self._robot.simulation_constants

        # Retrieve the appropriate starting pose based on alliance and location
        initial_pose = const.RED_TEST_POSE[location] if is_red else const.BLUE_TEST_POSE[location]

        # Update the field visualization with the new robot pose
        self._physics_controller.field.setRobotPose(initial_pose)