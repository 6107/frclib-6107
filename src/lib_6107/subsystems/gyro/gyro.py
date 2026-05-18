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
"""Abstract base class for gyro/IMU sensors in frclib-6107.

This module provides a hardware-agnostic gyroscope interface following the
AdvantageKit IO pattern. Allows seamless switching between different gyro
implementations (Pigeon2, NavX, etc.) with automatic logging to pykit/AdvantageScope
and simulation support.

Key Features:
    - Factory method for easy gyro instantiation
    - AdvantageKit IO abstraction for inputs/outputs
    - Automatic telemetry logging via pykit Logger
    - Simulation support with settable sim_yaw
    - SmartDashboard integration for debugging
    - Calibration state tracking
    - Support for reversed gyro orientation

Supported Gyro Types:
    - "pigeon2": CTRE Pigeon 2.0 IMU (on CAN bus)
    - "navx": Kauai Labs NavX-MXP (on I2C, SPI, or USB)

Angle vs Yaw:
    - yaw: Raw gyro output without offset; use for consistency with angle property
    - angle: Offset-corrected heading after reset(); preferred for most use cases
    - Use angle property unless you specifically need raw yaw

Usage:
    # Create a gyro using factory method
    gyro = Gyro.create("pigeon2", is_reversed=False, device_id=0)
    if gyro:
        gyro.initialize()
        # Use gyro.angle, gyro.turn_rate, gyro.heading in commands/subsystems

    # In subsystem periodic:
    gyro.periodic()  # Updates inputs and logs telemetry

    # In simulation:
    gyro.sim_init(physics_controller)  # Set up simulation state
    gyro.sim_yaw = new_angle  # Update simulated orientation
"""

import math
from typing import Any, Optional

from pyfrc.physics.core import PhysicsInterface
from wpilib import SmartDashboard
from wpimath.geometry import Rotation2d
from wpimath.units import degrees, degrees_per_second, hertz, radians_per_second

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer
from lib_6107.subsystems.pykit.gyro_io import GyroIO


class Gyro(GyroIO):
    """Abstract base class for gyroscope/IMU sensors on the robot.

    Provides a hardware-agnostic interface to various gyro implementations.
    Follows the AdvantageKit IO pattern: a Gyro instance wraps hardware-specific
    code, while GyroIO.GyroIOInputs holds all sensor measurements for logging
    and replay. This separation allows the same gyro code to work in REAL,
    SIMULATION, and REPLAY modes.

    Subclasses (Pigeon2, NavX) implement hardware-specific initialization,
    calibration, and input reading. All angle measurements are logged to
    pykit Logger and can be replayed for analysis or testing.

    Important Methods to Implement in Subclasses:
        - reset(): Hard reset of gyro; zero out accumulated angle
        - zero_yaw(): Zero only the yaw angle (offset-based)
        - yaw, pitch, roll, angle: Angle getters (degrees)
        - raw_angle: Unfiltered angle before any corrections
        - turn_rate_degrees_per_second: Angular velocity in deg/s
        - updateInputs(inputs): Populate GyroIO.GyroIOInputs from hardware

    Example:
        gyro = Gyro.create("pigeon2", is_reversed=False, device_id=0)
        if gyro:
            gyro.initialize()
            while True:
                gyro.periodic()
                print(f"Heading: {gyro.heading}")
                print(f"Turn rate: {gyro.turn_rate} rad/s")

    Attributes:
        gyro_type (str): String identifier for gyro type (e.g., "pigeon2", "navx").
            Set in subclasses.
        _gyro (Any): Reference to underlying vendor gyro/IMU object (e.g.,
            Pigeon2, NavX instance).
        _reversed (bool): True if gyro rotation direction is reversed (positive
            becomes negative). Applied to yaw/angle/roll measurements.
        _inputs (GyroIO.GyroIOInputs): Current sensor inputs struct for logging.
        _sim_gyro (Optional[Gyro]): Reference to simulation gyro instance
            (for dual-mode hardware/sim).
        _physics_controller (Optional[PhysicsInterface]): pyfrc physics interface
            for simulation updates.
    """

    gyro_type = "unknown"
    """Gyro type identifier (override in subclass)."""

    def __init__(self, is_reversed: bool) -> None:
        """Initialize the gyro base class.

        Args:
            is_reversed (bool): True if the gyro measurement direction should be
                negated (for reversed mounting). Applied to all angle measurements.
        """
        super().__init__()

        self._gyro = None
        self._reversed = is_reversed
        self._sim_gyro: Optional[Gyro] = None
        self._physics_controller: Optional[PhysicsInterface] = None
        self._inputs = GyroIO.GyroIOInputs()

    @property
    def gyro(self) -> Any:
        """Get the underlying hardware gyro/IMU object.

        Returns:
            Any: The vendor gyro object (e.g., Pigeon2, NavX) or None if not
                initialized.

        Note:
            Direct access to vendor-specific APIs should be minimized; prefer
            using Gyro properties (yaw, angle, turn_rate) for consistency.
        """
        return self._gyro

    @property
    def inputs(self) -> GyroIO.GyroIOInputs:
        """Get the current sensor inputs struct for logging/replay.

        Returns:
            GyroIO.GyroIOInputs: Struct containing all gyro measurements
                (angles, rates, calibration status) for telemetry logging.
        """
        return self._inputs

    @staticmethod
    def create(gyro_type: str, is_reversed: bool,
               device_id: int = -1,
               update_frequency: hertz = -1,
               inst: Optional[Any] = None) -> Optional[Gyro]:
        """Factory method to create a gyro instance by type name.

        Supports multiple gyro implementations and returns the appropriate
        subclass instance. If the requested type is not supported or fails
        to initialize, returns None.

        Args:
            gyro_type (str): Type of gyro to create. Supported values:
                - "pigeon2": CTRE Pigeon 2.0 IMU (requires device_id, update_frequency)
                - "navx": Kauai Labs NavX-MXP (I2C, SPI, or USB; inst can override port)
            is_reversed (bool): True if gyro rotation is reversed.
            device_id (int): CAN device ID for Pigeon2. Ignored for NavX.
                Default -1 (use vendor default).
            update_frequency (hertz): Update frequency for Pigeon2 in Hz.
                Default -1 (use vendor default, typically 50 Hz).
            inst (Optional[Any]): Vendor-specific instance (e.g., NavX port).
                If provided, used instead of default. Default None.

        Returns:
            Optional[Gyro]: Instance of requested gyro type, or None if type
                not supported or creation failed.

        Example:
            # Create a Pigeon2 on CAN device 0 with 50 Hz updates
            gyro = Gyro.create("pigeon2", is_reversed=False, device_id=0, update_frequency=50)

            # Create a NavX on default SPI port
            gyro = Gyro.create("navx", is_reversed=False)
        """
        match gyro_type.lower():
            case "pigeon2":
                from lib_6107.subsystems.gyro.pigeon2 import Pigeon2
                return Pigeon2(device_id, is_reversed, update_frequency, inst=inst)

            case "navx":
                from lib_6107.subsystems.gyro.navx_imu import NavX
                return NavX(is_reversed, inst=inst)

        return None

    def initialize(self) -> None:
        """Perform initialization steps to prepare the gyro for operation.

        Calls reset() to zero out accumulated angles and prepare the gyro
        for use. Override in subclasses if additional setup is needed
        (e.g., calibration, LED configuration, update rate configuration).
        """
        self.reset()

    @property
    def is_reversed(self) -> bool:
        """Check if gyro rotation direction is reversed.

        Returns:
            bool: True if gyro measurements are negated (reversed mount).
        """
        return self._reversed

    @property
    def calibrated(self) -> bool:
        """Check if the gyro is fully calibrated.

        Default returns True (most modern gyros auto-calibrate). Override
        in subclasses if your gyro requires manual calibration (e.g., NavX).

        Returns:
            bool: True if gyro is calibrated and ready for use.
        """
        return True

    @property
    def is_calibrating(self) -> bool:
        """Check if the gyro is currently calibrating.

        Default returns False. Override in subclasses that have a calibration
        phase (e.g., NavX requires initialization time).

        Returns:
            bool: True if gyro is in calibration process.

        Note:
            Don't use gyro measurements while is_calibrating is True.
            Wait for calibrated property to become True.
        """
        return False

    def reset(self) -> None:
        """Reset the gyro to zero angle and clear accumulated measurements.

        Implement in subclass to perform hardware-specific reset. Typically:
        - Zero out yaw/pitch/roll angles
        - Clear any accumulated angle offsets
        - Reset internal calibration state if needed

        Called automatically by initialize(). Also call manually when you need
        to re-zero the robot (e.g., at match start).

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    def zero_yaw(self) -> None:
        """Zero only the yaw angle (heading).

        Unlike reset(), this is an offset-based zero that doesn't affect
        pitch or roll. Used for re-zeroing robot heading mid-match without
        disturbing orientation calibration. Implement in subclass.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.

        Example:
            gyro.zero_yaw()  # Now gyro.yaw == 0, but pitch/roll unchanged
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def yaw(self) -> degrees:
        """Get the robot's yaw angle (heading around Z axis) in degrees.

        Yaw is the Z-axis rotation (left/right turn). This is the raw gyro
        output without incorporating the offset applied by reset(). Use this
        for consistency when angle property is also available.

        Prefer using angle property unless you specifically need raw yaw for
        alignment algorithms or debugging.

        Returns:
            degrees: Current yaw angle in degrees. Positive is counterclockwise
                when viewed from above (right turn). Negated if is_reversed.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.

        Note:
            Yaw != angle. Yaw is raw; angle includes reset offset.
            Use get_angle() for most commands; use yaw when you need consistency.
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def pitch(self) -> degrees:
        """Get the robot's pitch angle (rotation around Y axis) in degrees.

        Pitch is front/back tilt. Positive is forward tilt (nose down).

        Returns:
            degrees: Current pitch angle in degrees.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def roll(self) -> degrees:
        """Get the robot's roll angle (rotation around X axis) in degrees.

        Roll is left/right tilt. Positive is right tilt (right side down).

        Returns:
            degrees: Current roll angle in degrees.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def angle(self) -> degrees:
        """Get the robot's heading angle with reset offset applied.

        Combined angle measurement (typically from yaw) that incorporates
        the offset set by reset() calls. This is the primary angle property
        for most use cases (commands, trajectory following, etc.).

        Returns:
            degrees: Current heading angle in degrees, with reset offset.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.

        Example:
            gyro.reset()  # Set angle to 0
            # After some rotation...
            print(gyro.angle)  # Returns angle relative to reset point
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def raw_angle(self) -> degrees:
        """Get the unfiltered, uncorrected gyro angle.

        Raw angle directly from hardware before any processing, filtering,
        or offset application. Used for diagnostics and data analysis, not
        for normal commands.

        Returns:
            degrees: Raw, unprocessed gyro angle.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    @property
    def heading(self) -> Rotation2d:
        """Get the robot's heading as a Rotation2d object.

        Combines yaw angle with WPILib Rotation2d for integration with
        trajectory and pose estimation code.

        Returns:
            Rotation2d: Robot heading as a Rotation2d constructed from yaw.
        """
        return Rotation2d.fromDegrees(self.yaw)

    @property
    def turn_rate(self) -> radians_per_second:
        """Get the robot's turn rate (angular velocity) in radians per second.

        Derived from turn_rate_degrees_per_second property. Used in PID
        controllers and velocity-based heading commands.

        Returns:
            radians_per_second: Current turn rate in rad/s. Positive is
                counterclockwise (left turn).
        """
        return math.radians(self.turn_rate_degrees_per_second)

    @property
    def turn_rate_degrees_per_second(self) -> degrees_per_second:
        """Get the robot's turn rate (angular velocity) in degrees per second.

        Raw angular velocity measurement from gyro. Implement in subclass.

        Returns:
            degrees_per_second: Current turn rate in deg/s. Positive is
                counterclockwise rotation (left turn).

        Raises:
            NotImplementedError: Always in base class; implement in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    def periodic(self) -> None:
        """Update gyro inputs and log telemetry data.

        Called during the main robot loop (typically from drivetrain periodic
        or container periodic). Updates the GyroIO.GyroIOInputs struct from
        hardware, logs to pykit Logger, and records performance metrics.

        Execution Order:
        1. Call updateInputs(self._inputs) to read hardware
        2. Log all inputs to pykit Logger under "Drive/Gyro"
        3. Record IO update time via LogTracer for performance profiling

        This method is called within the subsystem's periodic, so LogTracer
        outer reset is not needed (already reset by parent).

        Note:
            For most use cases, you don't call this directly; the drivetrain
            or another parent subsystem calls it during their periodic(). Only
            override if you need custom logging or preprocessing.
        """
        # updateInputs reads hardware into self._inputs
        self.updateInputs(self._inputs)

        # Log all gyro measurements to pykit for AdvantageScope
        Logger.processInputs("Drive/Gyro", self._inputs)

        # Profile IO update duration for performance analysis
        LogTracer.record("IOUpdate")

    # ====================================================================
    # SmartDashboard support
    # ====================================================================

    def dashboard_initialize(self) -> None:
        """Initialize SmartDashboard widgets for this gyro.

        Called once at startup to set up dashboard display entries for gyro
        debugging and monitoring. Logs static gyro type information.

        Override in subclasses to add type-specific entries (e.g., calibration
        status, device ID, firmware version).
        """
        SmartDashboard.putString('Gyro/type', self.gyro_type)

    def dashboard_periodic(self) -> None:
        """Update SmartDashboard widgets with current gyro state.

        Called each periodic cycle to refresh dashboard displays with live
        gyro measurements (yaw, pitch, roll). Allows real-time monitoring
        during development and match.

        Commented-out entries show alternative values that can be enabled for
        debugging (angle, pitch, roll). Yaw is logged by default for consistency.

        Override to add type-specific metrics (e.g., temperature, calibration
        progress, device health).
        """
        # Log current yaw heading (primary measurement)
        SmartDashboard.putNumber('Gyro/yaw', self.yaw)

        # Optional: uncomment to also log angle, pitch, roll
        # SmartDashboard.putNumber('Gyro/angle', self.angle)
        # SmartDashboard.putNumber('Gyro/pitch', self.pitch)
        # SmartDashboard.putNumber('Gyro/roll', self.roll)

    # ====================================================================
    # Simulation support
    # ====================================================================

    def sim_init(self, physics_controller: 'PhysicsInterface') -> None:
        """Initialize simulation support for this gyro.

        Called once during simulation initialization to set up simulated
        gyro state. Override in subclasses to create and configure a sim
        gyro instance, then store it in self._sim_gyro.

        Args:
            physics_controller (PhysicsInterface): pyfrc physics interface
                for accessing simulated robot state and physics updates.

        Example:
            def sim_init(self, physics_controller):
                self._physics_controller = physics_controller
                self._sim_gyro = SimulatedGyro()

        Note:
            Only called in SIMULATION mode; REAL and REPLAY modes skip this.
        """
        # Override in subclass to initialize simulated gyro object

    @property
    def sim_yaw(self) -> degrees:
        """Get the simulated gyro yaw angle.

        Used during simulation to read the current simulated heading from
        either PhysicsEngine or an internal sim model.

        Returns:
            degrees: Current simulated yaw angle.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.
        """
        raise NotImplementedError("Implement in derived class")

    @sim_yaw.setter
    def sim_yaw(self, value: degrees) -> None:
        """Set the simulated gyro yaw angle.

        Called by PhysicsEngine to update the simulated gyro state based on
        robot's rotation from drive motor physics simulation. Updates internal
        sim_gyro or offset as needed.

        Args:
            value (degrees): New simulated yaw angle in degrees.

        Raises:
            NotImplementedError: Always in base class; implement in subclass.

        Example:
            # PhysicsEngine updates sim gyro during physics simulation
            gyro.sim_yaw = robot_rotation_from_physics
        """
        raise NotImplementedError("Implement in derived class")