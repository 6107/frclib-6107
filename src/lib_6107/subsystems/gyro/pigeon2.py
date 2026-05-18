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
"""CTRE Pigeon 2.0 IMU implementation for frclib-6107.

This module implements the Gyro interface for the CTRE Pigeon 2.0, a full 9-DOF
inertial measurement unit (IMU) that communicates over CAN bus with low latency.

Pigeon2-Specific Advantages:
    - Auto-calibrates at startup (~1-2 seconds, much faster than NavX)
    - No explicit calibration wait needed; ready almost immediately
    - CAN bus communication (typically faster and more reliable than SPI)
    - Dense integration with Phoenix6 ecosystem
    - Automatic temperature compensation
    - Compass disabled by default (optional, often disabled for reliability)
    - StatusSignal timestamp support for cycle-accurate log replay
    - Direct access to raw sensor data via get_* methods

Calibration:
    - Pigeon2 auto-calibrates internally; calibrated property always True
    - is_calibrating property always False (no explicit wait needed)
    - Safe to zero_yaw() immediately after initialization
    - No 10-15 second startup delay like NavX

Configuration:
    - Compass disabled by default (to avoid magnetic interference)
    - Update frequency configurable via constructor
    - CAN bus automatically optimized for latency during initialize()
    - Multiple StatusSignals (yaw, pitch, roll, rates) cached for efficiency

Orientation Methods:
    - Pigeon2 uses CTRE Tuner X Calibration Tool to set mount orientation
    - If custom instance provided, is_reversed forced to False (orientation set in hardware)
    - Reversal only used for CTRE-created instances without custom calibration

Real vs Simulation:
    - REAL: Uses Phoenix6 StatusSignal to read CAN data with timestamps
    - SIMULATION: Uses Pigeon2SimState to read/write simulated IMU values
    - Timestamps preserved through logging for precise replay

Usage:
    # Create Pigeon2 on CAN ID 0, update at 50 Hz
    pigeon2 = Gyro.create("pigeon2", is_reversed=False, device_id=0, update_frequency=50)
    pigeon2.initialize()

    # Immediately ready to use (no calibration wait)
    heading = pigeon2.heading  # Rotation2d object

    # In simulation:
    pigeon2.sim_yaw = new_angle  # PhysicsEngine updates this
"""

import logging
import math
from typing import Optional

from phoenix6 import StatusCode, StatusSignal
from phoenix6.configs import Pigeon2Configuration
from phoenix6.hardware import pigeon2
from phoenix6.sim.pigeon2_sim_state import Pigeon2SimState
from wpilib import RobotBase
from wpimath.units import degrees, degrees_per_second, hertz, radians, radians_per_second

from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.pykit.gyro_io import GyroIO
from lib_6107.util.phoenix6_signals import Phoenix6Signals
from lib_6107.util.phoenix6_utils import try_until_ok

logger = logging.getLogger(__name__)


class Pigeon2(Gyro):
    """CTRE Pigeon 2.0 IMU gyro implementation.

    Concrete implementation of the Gyro base class for the Pigeon 2.0 inertial
    measurement unit. Provides fast CAN-based 6-DOF orientation (yaw, pitch, roll)
    with automatic temperature compensation and StatusSignal timestamp support for
    precise log replay.

    Key Differences from NavX:
        - Auto-calibrates internally (~1-2 sec) vs explicit NavX calibration wait
        - CAN bus (faster, more reliable) vs SPI/I2C
        - Always calibrated; no explicit wait in periodic() required
        - Can zero yaw immediately after initialize()
        - Orientation set via CTRE Tuner X (hardware) vs is_reversed (software)
        - StatusSignal timestamps for exact replay timing

    Attributes:
        gyro_type (str): Set to "Pigeon2" for identification.
        _gyro (pigeon2.Pigeon2): CTRE Pigeon2 hardware object (created or injected).
        _update_hz (hertz): CAN update frequency for sensor reads. Default typically 50 Hz.
            Higher values reduce latency but increase CAN bus load.
        _instance_supplied (bool): True if custom Pigeon2 instance was injected at init.
            If False, this class handles initialization; if True, assumes pre-configured.
        _sim_gyro (Optional[pigeon2.Pigeon2]): Reference to simulated Pigeon2 (SIM mode only).
        _sim_gyro_state (Optional[Pigeon2SimState]): Simulation state object for updating yaw.
        _yaw, _yaw_velocity, _roll, _pitch (StatusSignal): Cached hardware signal handles.
            Used for efficient CAN communication and timestamp tracking.

    Important Configuration Notes:
        - Compass disabled at startup to avoid magnetic interference
        - Orientation should be set in CTRE Tuner X Calibration Tool, not via is_reversed
        - If custom instance provided, is_reversed is forced to False (orient in hardware instead)
        - StatusSignal update frequencies automatically optimized to reduce CAN load
        - Bus utilization optimized in initialize() via optimize_bus_utilization()

    Example - Basic Setup:
        pigeon2 = Gyro.create("pigeon2", is_reversed=False, device_id=0, update_frequency=50)
        pigeon2.initialize()

        # Immediately ready (no calibration wait like NavX)
        angle = pigeon2.angle  # In degrees
        turn_rate = pigeon2.turn_rate  # In rad/s for PID
    """

    gyro_type = "Pigeon2"

    def __init__(self, device_id: int, is_reversed: bool, update_frequency: hertz,
                 inst: Optional[pigeon2.Pigeon2] = None) -> None:
        """Initialize the Pigeon2 gyro.

        Sets up CTRE Pigeon2 IMU on CAN bus. Supports both automatic creation
        (from device_id) and injection of a pre-configured Pigeon2 instance.

        If a custom instance is provided, it's assumed to have proper orientation
        already configured via CTRE Tuner X, so is_reversed is forced to False
        and the instance is validated.

        Args:
            device_id (int): CAN ID of the Pigeon2 device. Only used if inst is None.
                Typically 0, 1, or 2 depending on other CAN devices.
            is_reversed (bool): True if gyro rotation should be negated (for upside-down
                or reversed mounting). Only used if inst is None. If custom instance
                provided, this is ignored and set to False (orientation configured in
                CTRE Tuner X instead).
            update_frequency (hertz): CAN update rate for sensor reads in Hz. Typical
                values: 50 Hz (balanced), 100 Hz (higher bandwidth), 200 Hz (max update
                rate of some sensors). Higher values reduce latency but increase CAN traffic.
            inst (Optional[pigeon2.Pigeon2]): Optional pre-configured Pigeon2 instance.
                If provided, bypasses device_id and is_reversed, assumes the instance
                is already configured with correct orientation in CTRE Tuner X.

        Raises:
            ValueError: If inst is provided but is not a pigeon2.Pigeon2 instance.

        Note:
            Compass is disabled at startup to prevent magnetic interference.
            If compass is needed, set it in a custom pre-initialization step or
            enable it in a subclass before calling super().__init__().

        Example:
            # Automatic Pigeon2 on CAN ID 0
            pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

            # Custom: Pre-configured instance (orientation set in CTRE Tuner X)
            custom_pigeon2 = pigeon2.Pigeon2(0)
            # ... configure custom_pigeon2 via CTRE Tuner ...
            gyro = Pigeon2(device_id=0, is_reversed=False, update_frequency=50,
                          inst=custom_pigeon2)
        """
        if inst is not None:
            is_reversed = False

            # Validate custom instance type
            if not isinstance(inst, pigeon2.Pigeon2):
                raise ValueError(f"Invalid object type past in as gyro instance: {type(inst)}")

        # Initialize base class with reversal (or False if custom instance)
        super().__init__(is_reversed)

        # Create or use provided Pigeon2 instance
        self._gyro: pigeon2.Pigeon2 = inst or pigeon2.Pigeon2(device_id)
        self._sim_gyro: Optional[pigeon2.Pigeon2] = None
        self._sim_gyro_state: Optional[Pigeon2SimState] = None
        self._instance_supplied = inst is not None

        # Configure Pigeon2 with default settings (compass disabled)
        config: Pigeon2Configuration = Pigeon2Configuration()
        config.pigeon2_features.enable_compass = False

        try_until_ok("Pigeon2", 5,
                     lambda: self._gyro.configurator.apply(config, timeout_seconds=0.2))

        # Store update frequency for initialize() to apply to StatusSignals
        self._update_hz: hertz = update_frequency

        # TODO: Simulation may need higher rate (1000 Hz) for physics accuracy

        # Cache StatusSignal handles for efficient polling and timestamp tracking
        self._yaw: StatusSignal = self._gyro.get_yaw()
        self._yaw_velocity: StatusSignal = self._gyro.get_angular_velocity_z_world()
        self._roll: StatusSignal = self._gyro.get_roll()
        self._pitch: StatusSignal = self._gyro.get_pitch()

    def initialize(self) -> None:
        """Configure Pigeon2 update rates and optimize CAN bus utilization.

        Called once at robot startup after all subsystems are created. Handles:
        1. Optional reset if this class created the Pigeon2 (not a custom instance)
        2. Sets update frequency on all StatusSignals to reduce CAN overhead
        3. Optimizes CAN bus utilization to minimize latency
        4. Registers signals with Phoenix6Signals telemetry system

        Unlike NavX, Pigeon2 auto-calibrates internally from power-on, so no
        explicit calibration wait is needed. Initialization is about optimizing
        CAN bus performance, not waiting for calibration.

        StatusSignal Update Frequency:
            Applied to yaw, yaw_velocity (turn rate), roll, and pitch. Higher
            frequencies provide fresher data but increase CAN load. Common values:
            - 50 Hz: Conservative, good for competition
            - 100 Hz: Balanced bandwidth/load
            - 200 Hz: Maximum update rate if CAN load permits

        Bus Optimization:
            Calls optimize_bus_utilization() to reduce unnecessary CAN traffic
            and minimize latency. Should be called after all signal configuration.

        Warnings:
            Logs warnings if StatusSignal frequency updates or bus optimization fail,
            but does not block initialization. Gyro will still function with warnings.
        """
        # Only reset if we created the Pigeon2; custom instances come pre-configured
        if not self._instance_supplied:
            self.reset()

        # Set update frequency on all StatusSignals
        status = StatusSignal.set_update_frequency_for_all(
            self._update_hz,
            self._yaw,
            self._yaw_velocity,
            self._roll,
            self._pitch
        )
        if status != StatusCode.OK:
            logger.warning("%s: Error during gyro frequency update: %s",
                          self.gyro_type, status)

        # Fine-tune yaw update frequency if needed
        if self._update_hz > 0.0:
            status = self._yaw.set_update_frequency(self._update_hz)

            if status != StatusCode.OK:
                logger.warning("%s: Error during gyro yaw frequency update: %s",
                              self.gyro_type, status)

        # Optimize CAN bus utilization for lower latency
        status = self._gyro.optimize_bus_utilization()

        if status != StatusCode.OK:
            logger.warning("%s: Error during gyro bus optimization: %s",
                          self.gyro_type, status)

        # Register signals for Phoenix6 telemetry system
        Phoenix6Signals.register_signals(self._yaw, self._yaw_velocity,
                                        self._roll, self._pitch)

    @property
    def calibrated(self) -> bool:
        """Check if Pigeon2 is calibrated and ready to use.

        Always returns True for Pigeon2 (auto-calibrates internally). Unlike NavX,
        which requires an explicit calibration wait, Pigeon2 is ready immediately
        after power-on (~1-2 seconds for internal gyro biasing).

        Returns:
            bool: Always True. Pigeon2 auto-calibrates in background.

        Note:
            Safe to call zero_yaw() and use gyro immediately after initialize().
            No need for periodic calibration checks like with NavX.
        """
        return True

    @property
    def is_calibrating(self) -> bool:
        """Check if Pigeon2 is currently calibrating.

        Always returns False for Pigeon2 (auto-calibration is internal and
        non-blocking). Provided for API compatibility with NavX.

        Returns:
            bool: Always False. Pigeon2 never reports active calibration.

        Note:
            Unlike NavX, which blocks zero_yaw() during calibration, Pigeon2
            can be zeroed immediately after power-on.
        """
        return False

    def reset(self) -> None:
        """Perform a full reset of the Pigeon2 hardware.

        Calls zero_yaw() to reset yaw to 0 degrees. This is the primary reset
        method for Pigeon2. A full hardware reset (via CTRE reset pin) can be
        done externally if needed.

        Note:
            Unlike NavX, safe to call anytime; doesn't block during calibration.
        """
        self.zero_yaw()

    def zero_yaw(self) -> None:
        """Zero the yaw angle (heading) to 0 degrees.

        Sets current heading to 0 degrees. Safe to call immediately after
        power-on (no calibration wait needed like NavX). Also zeros simulated
        gyro in SIM mode.

        Implementation:
            - REAL: Calls self._gyro.set_yaw(0.0) to update hardware
            - SIMULATION: Prints TODO message (needs fixed; should update sim_yaw)

        Example:
            gyro.zero_yaw()  # Set current heading to 0
            # Now: yaw == angle == 0

        TODO in SIM mode:
            Need to properly zero the simulation gyro; currently just prints TODO.
        """
        self._gyro.set_yaw(0.0)

        if RobotBase.isSimulation():
            print("TODO: Need to zero simulation gyro")  # TODO

    @property
    def yaw(self) -> degrees:
        """Get the robot's yaw angle (Z-axis rotation) in degrees.

        Returns the current heading from Pigeon2 hardware. For Pigeon2, yaw == angle
        (there's no separate offset like NavX). Reads via cached _yaw StatusSignal.

        Reversal:
            If is_reversed is True, the value is negated.

        Returns:
            degrees: Current yaw angle. Positive is counterclockwise (left turn).

        Note:
            For Pigeon2, yaw and angle are equivalent. NavX uses yaw for raw
            and angle for offset-corrected; Pigeon2 doesn't distinguish.

        TODO:
            Verify distinction between yaw and angle; may be NavX-specific
            and not relevant to Pigeon2.
        """
        yaw = self._gyro.get_yaw().value

        return -yaw if self._reversed else yaw

    @yaw.setter
    def yaw(self, value: degrees) -> None:
        """Set the yaw angle directly (used by zero_yaw and custom resets).

        Args:
            value (degrees): New yaw angle to set.
        """
        self._gyro.set_yaw(value)

    @property
    def pitch(self) -> degrees:
        """Get the robot's pitch angle (Y-axis forward/backward tilt) in degrees.

        Positive is forward tilt (nose down), negative is backward (nose up).
        Reads from cached _pitch StatusSignal.

        Returns:
            degrees: Current pitch angle.

        Note:
            Pitch typically needs calibration for accuracy if Pigeon2 is mounted
            at an angle. Offset (currently 0) can be adjusted if needed.

        TODO:
            Determine if pitch_offset should ever be non-zero.
        """
        pitch_offset = 0  # TODO: Always zero?

        return self._pitch.value - pitch_offset

    @property
    def roll(self) -> degrees:
        """Get the robot's roll angle (X-axis left/right tilt) in degrees.

        Positive is right tilt (right side down), negative is left tilt.
        Reads from cached _roll StatusSignal.

        Returns:
            degrees: Current roll angle.

        Note:
            Roll typically needs calibration for accuracy if Pigeon2 is mounted
            at an angle. Offset (currently 0) can be adjusted if needed.

        TODO:
            Determine if roll_offset should ever be non-zero.
        """
        roll_offset = 0  # TODO: Always zero?

        return self._roll.value - roll_offset

    @property
    def raw_angle(self) -> degrees:
        """Get the unfiltered raw angle from Pigeon2.

        For Pigeon2, raw_angle == angle (no separate filtering).
        Returns yaw via angle property.

        Returns:
            degrees: Current raw angle (same as angle for Pigeon2).
        """
        return self.angle

    @property
    def angle(self) -> degrees:
        """Get the robot's heading angle in degrees.

        For Pigeon2, angle == yaw (no separate offset like NavX).

        Returns:
            degrees: Current heading angle. Positive is counterclockwise.
        """
        return self.yaw

    @property
    def turn_rate(self) -> radians_per_second:
        """Get the robot's turn rate (angular velocity) in radians per second.

        Converts turn_rate_degrees_per_second to radians for use with WPILib
        motion profiling and PID controllers.

        Returns:
            radians_per_second: Current angular velocity in rad/s.
        """
        return math.radians(self.turn_rate_degrees_per_second)

    @property
    def turn_rate_degrees_per_second(self) -> degrees_per_second:
        """Get the robot's turn rate (angular velocity) in degrees per second.

        Returns the Z-axis angular velocity from Pigeon2 gyroscope. Used to
        feed velocity feedforward into turn PID controllers. Reads from cached
        _yaw_velocity StatusSignal.

        Reversal:
            If is_reversed is True, the value is negated.

        Returns:
            degrees_per_second: Current angular velocity. Positive is counterclockwise.

        Example:
            pidController.calculate(target - gyro.angle,
                                   gyro.turn_rate_degrees_per_second)
        """
        rate = self._gyro.get_angular_velocity_z_world().value

        return -rate if self._reversed else rate

    # ========================================================================
    # AdvantageKit IO Pattern Support (pykit / AdvantageScope logging)
    # ========================================================================

    def updateInputs(self, inputs: GyroIO.GyroIOInputs) -> None:
        """Populate sensor inputs struct from Pigeon2 for logging and replay.

        Called by base Gyro.periodic() to read all Pigeon2 measurements and
        pack into GyroIO.GyroIOInputs struct for pykit Logger. This data is
        logged to .wpilog files for AdvantageScope visualization and analysis.

        Data Populated:
            - connected: CAN communication status
            - yaw/yaw_timestamp: Heading and timestamp from hardware
            - yaw_rate/yaw_rate_timestamp: Angular velocity and timestamp
            - roll/roll_timestamp: Roll angle and timestamp
            - pitch/pitch_timestamp: Pitch angle and timestamp

        Timestamps:
            StatusSignal timestamps provide exact cycle when each measurement was
            captured, enabling precise replay and synchronization with drive motor data.

        Args:
            inputs (GyroIO.GyroIOInputs): Struct to populate with current sensor data.
                Will be logged by pykit Logger after this method returns.

        Implementation:
            1. Checks CAN connection health via StatusSignal.is_all_good()
            2. Reads cached StatusSignal values
            3. Converts degrees to radians for consistency with WPILib
            4. Stores timestamps for replay correlation
        """
        # Check CAN connection status
        inputs.connected = StatusSignal.is_all_good(self._yaw,
                                                    self._yaw_velocity)

        # Yaw (heading) in radians with timestamp
        inputs.yaw = math.radians(self._yaw.value_as_double)
        inputs.yaw_timestamp = self._yaw.timestamp.time

        # Yaw rate (angular velocity) in radians/sec with timestamp
        inputs.yaw_rate = math.radians(self._yaw_velocity.value_as_double)
        inputs.yaw_rate_timestamp = self._yaw.timestamp.time

        # Roll (left/right tilt) in radians with timestamp
        inputs.roll = math.radians(self._roll.value_as_double)
        inputs.roll_timestamp = self._roll.timestamp.time

        # Pitch (forward/back tilt) in radians with timestamp
        inputs.pitch = math.radians(self._pitch.value_as_double)
        inputs.pitch_timestamp = self._pitch.timestamp.time

    def set_yaw(self, yaw_rad: radians) -> None:
        """Set the gyro yaw angle from radians.

        Convenience method for setting yaw angle in radians (converts to degrees
        for hardware). Used by autonomous commands that work in radians.

        Args:
            yaw_rad (radians): New yaw angle in radians to set.

        Example:
            gyro.set_yaw(0.0)  # Set heading to 0 radians
            gyro.set_yaw(math.pi)  # Set heading to 180 degrees
        """
        self.yaw = math.degrees(yaw_rad)

    # ========================================================================
    # Simulation Support
    # ========================================================================

    def sim_init(self, physics_controller: 'PhysicsInterface') -> None:
        """Initialize simulation support for Pigeon2.

        Called once during simulation startup to connect to the simulated Pigeon2
        device state in WPILib. After this call, sim_yaw can be updated by
        PhysicsEngine during physics simulation.

        Args:
            physics_controller (PhysicsInterface): pyfrc physics interface (stored
                but not actively used; kept for API consistency).

        Implementation:
            Stores references to both the simulated Pigeon2 object and its
            SimDeviceSim state, allowing physics updates to flow through.

        Note:
            Only called in SIMULATION mode; REAL and REPLAY modes skip this.

        Example:
            def sim_init(self, physics):
                self._sim_gyro = self._gyro  # Use real Pigeon2 object in sim
                self._sim_gyro_state = self._gyro.sim_state  # Access state for updates
        """
        super().sim_init(physics_controller)

        # In simulation, use the real Pigeon2 object with sim_state
        self._sim_gyro = self._gyro
        self._sim_gyro_state = self._gyro.sim_state

    @property
    def sim_yaw(self) -> degrees:
        """Get the simulated Pigeon2 yaw angle.

        Reads the current simulated heading from Pigeon2SimState.
        Updated by PhysicsEngine during physics loop.

        Returns:
            degrees: Current simulated yaw angle.

        Note:
            Only valid after sim_init() has been called. Returns via
            self._sim_gyro.get_yaw().value.
        """
        return self._sim_gyro.get_yaw().value

    @sim_yaw.setter
    def sim_yaw(self, value: degrees) -> None:
        """Set the simulated Pigeon2 yaw angle.

        Called by PhysicsEngine to update simulated gyro state based on robot
        rotation calculated from drive motor physics. Updates via
        Pigeon2SimState.set_raw_yaw().

        Args:
            value (degrees): New yaw angle to simulate in degrees.

        Reversal:
            If is_reversed is True, the value is negated before writing to
            match reversed hardware behavior.

        Implementation:
            Applies reversal correction, then writes to SimState via
            self._sim_gyro_state.set_raw_yaw(value).

        Example:
            # PhysicsEngine updates simulated gyro each physics step
            robot_rotation = physics.get_robot_rotation_from_drive()
            gyro.sim_yaw = robot_rotation

        TODO:
            Reconcile with physics.py gyro update logic to avoid duplication.
        """
        # TODO: Reconcile with physics.py gyro update functions

        # Apply reversal to match hardware orientation
        if self._reversed:
            value = -value

        # Update simulation state
        self._sim_gyro_state.set_raw_yaw(value)