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
"""NavX3 IMU implementation for frclib-6107.

This module implements the Gyro interface for the Studica NavX3 (robotpy-navx 2027, ``navx.Navx``), a
9-DOF inertial measurement unit (IMU) that provides gyroscope, accelerometer, and magnetometer data
over the Systemcore CAN/CAN FD bus or USB.

NavX-Specific Behavior:
    - Requires initialization/calibration period at startup (~10-15 seconds)
    - Cannot be zeroed while calibrating; must wait for completion
    - Provides full 6-DOF orientation (yaw, pitch, roll)
    - Connected state and sample timestamps come from the NavX3 itself

Calibration Lifecycle:
    1. Robot boots; NavX init begins (is_calibrating = True)
    2. Call initialize() → detects calibration in progress, sets _calibrated = False
    3. periodic() waits for calibration to complete (is_calibrating → False)
    4. periodic() detects completion → calls zero_yaw() and sets _calibrated = True
    5. Normal operation: calibrated = True, angle/yaw available

Connection Options:
    - CAN (default): navx.Navx(can_id, CANPort.CAN_S0) - NavX3 on the Systemcore CAN bus
    - USB: navx.Navx.usb(navx.UsbPort.USB0) - Systemcore USB port

Real vs Simulation:
    - REAL mode: Reads from the physical NavX3
    - SIMULATION: ``navx.Navx`` registers a SimDevice named ``NavX3[<can_id>]`` with the values Yaw,
      Angle, Pitch, Roll, Angular Velocity X/Y/Z, etc. Reads go through the normal ``navx.Navx`` API
      and ``sim_yaw`` writes the SimDevice. ``resetYaw()`` does not change simulated values, so
      ``zero_yaw()`` zeroes them directly.
    - Calibration skipped in simulation (is_calibrating always False in sim)

Usage:
    # Create NavX3 on CAN (default device ID)
    navx = NavX(is_reversed=False)
    navx.initialize()

    # In periodic:
    navx.periodic()  # Wait for calibration, then zero_yaw()

    # Use in commands:
    heading = navx.heading  # Rotation2d object
    turn_rate = navx.turn_rate  # rad/s for PID

    # Reset heading during match
    navx.zero_yaw()  # Zero only yaw (keeps pitch/roll)
"""

import math
from typing import TYPE_CHECKING, Any

import navx
from wpilib import RobotBase, Timer
from wpilib.simulation import SimDeviceSim
from wpimath import Rotation2d
from wpimath.units import degrees, degrees_per_second, radians_per_second

from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.pykit.gyro_io import GyroIO

if TYPE_CHECKING:
    from lib_6107.physics import PhysicsEngine


class NavX(Gyro):
    """Studica NavX3 IMU gyro implementation (``navx.Navx``).

    Concrete implementation of the Gyro base class for the NavX3 inertial
    measurement unit. Provides 6-DOF orientation (yaw, pitch, roll) sensor data
    with calibration handling and hardware/simulation support.

    Key Differences from Pigeon2:
        - Requires explicit calibration wait at startup (10-15 seconds)
        - Calibration cannot be interrupted; zero_yaw() fails if calibrating
        - Provides separate yaw and angle properties (see Gyro base class)
        - Calibration status must be monitored in periodic() for initialization

    Attributes:
        gyro_type (str): Set to "navX" for identification.
        _gyro (navx.Navx): Underlying NavX3 hardware object (CAN or USB).
        _is_simulation (bool): True if robot is in simulation mode (set at init).
        _calibrated (bool): Internal flag tracking calibration completion.
            Set False at startup, True after calibration finishes and zero_yaw() called.
        _sim_gyro (Optional[SimDeviceSim]): The ``NavX3[<can_id>]`` SimDevice (set by ``sim_init``).

    Calibration State Machine:
        Initialize() Call → Check is_calibrating:
            - If True: _calibrated = False (wait for hardware)
            - If False: zero_yaw() → _calibrated = True (ready now)

        periodic() Call → If not calibrated and not calibrating:
            - Calibration complete! Call zero_yaw()
            - Set _calibrated = True

    Example - Full Initialization:
        navx = Gyro.create("navx", is_reversed=False)
        if navx:
            navx.initialize()  # Starts waiting for calibration

        # In robot_periodic or container periodic:
        while not navx.calibrated:
            navx.periodic()  # Will complete calibration and zero_yaw()
            # Optionally display calibration status on dashboard

        # Now ready to use for navigation, targeting, etc.
    """

    gyro_type = "navX"

    DEFAULT_CAN_ID = 0

    def __init__(self, is_reversed: bool, inst: Any | None = None, can_id: int | None = None):
        """Initialize the NavX gyro.

        Creates a NavX instance and detects simulation vs real hardware mode.
        By default uses a CAN connection (``can_id``, or DEFAULT_CAN_ID); can override with a custom navx.Navx instance.

        Args:
            is_reversed (bool): True if gyro rotation direction is reversed
                (e.g., for upside-down NavX mounting). All angle measurements
                will be negated if True.
            inst (Optional[Any]): Optional navx.Navx instance to use (e.g.,
                navx.Navx(5) for CAN ID 5, navx.Navx.usb(navx.UsbPort.USB0) for USB).
                If None, a navx.Navx is created on ``can_id`` on the default CAN bus.
            can_id (Optional[int]): CAN device ID set on the NavX3. Defaults to DEFAULT_CAN_ID.
                Also selects the simulation device name ``NavX3[<can_id>]`` when ``inst`` is None.

        Note:
            If inst is provided, it bypasses the default CAN creation. This allows
            teams to use the USB connection.

        Example:
            # CAN (default)
            navx = NavX(is_reversed=False)

            # Custom: CAN device ID 5
            navx = NavX(is_reversed=False, can_id=5)
        """
        super().__init__(is_reversed)

        self._can_id = self.DEFAULT_CAN_ID if can_id is None else can_id
        self._gyro = inst if inst is not None else navx.Navx(self._can_id)
        self._sim_gyro: SimDeviceSim | None = None
        self._is_simulation = RobotBase.is_simulation()
        self._calibrated = False

    def initialize(self) -> None:
        """Initialize the NavX and wait for calibration to complete.

        Called once at robot startup. Performs initial checks:
        - If NavX is calibrating: Sets _calibrated = False to trigger waiting in periodic()
        - If NavX is already calibrated (e.g., SIM mode): Calls zero_yaw() and sets _calibrated = True

        CRITICAL NOTE: zero_yaw() will NOT work while NavX is calibrating.
        Always wait for calibration to finish before zeroing yaw. The periodic()
        method handles this automatically.

        Real Robot Flow:
            1. initialize() called → detects is_calibrating = True
            2. Sets _calibrated = False (will be handled in periodic)
            3. periodic() called repeatedly while is_calibrating = True
            4. When is_calibrating becomes False, periodic() calls zero_yaw()
                and sets _calibrated = True

        Simulation Flow:
            1. initialize() called → is_calibrating is always False in SIM mode
            2. Immediately calls zero_yaw() and sets _calibrated = True
            3. Ready to use immediately

        See Also:
            calibrated property: Check if initialization complete
            is_calibrating property: Check if hardware still calibrating
            periodic(): Completes calibration initialization automatically
        """
        if self.is_calibrating:
            # Hardware is calibrating; don't try to zero yet
            # periodic() will handle completion
            self._calibrated = False
        else:
            # Already calibrated (e.g., in simulation), safe to zero now
            self.zero_yaw()
            self._calibrated = True

    @property
    def calibrated(self) -> bool:
        """Check if NavX is fully calibrated and ready for use.

        Returns False until initialize() plus periodic() have completed the
        calibration cycle. Used to gate access to gyro data during startup.

        Returns:
            bool: True if initialization is complete and zero_yaw() has been called.
                False while NavX is calibrating or waiting for initialization.

        Note:
            In REAL mode, calibration typically takes 10-15 seconds at startup.
            In SIMULATION mode, this is immediate.

        Example:
            if navx.calibrated:
                # Safe to use heading in commands
                target_rotation = Rotation2d.from_degrees(90)
            else:
                # Display "Calibrating..." message
                Logger.record_output("Status", "Calibrating NavX...")
        """
        return self._calibrated

    @property
    def is_calibrating(self) -> bool:
        """Check if NavX is currently in calibration process.

        Returns True while the NavX is internally calibrating its sensors.
        During calibration, gyro measurements may be unreliable and zero_yaw()
        operations should not be attempted.

        Return Logic:
            - REAL: Returns not self._gyro.isConnected() (hardware state)
            - SIMULATION: Returns False (calibration skipped in sim)

        Returns:
            bool: True if NavX is actively calibrating, False otherwise.

        Note:
            Calibration typically takes 10-15 seconds at power-on. Calibration
            completes faster if the robot is kept stationary during startup.

        See Also:
            calibrated property: Tracks overall initialization completion
            periodic(): Automatically detects when calibration finishes
        """
        return not self._is_simulation and not self._gyro.isConnected()

    def reset(self) -> None:
        """Perform a full reset of the NavX hardware.

        Attempts a hard reset via zeroYaw() if available, otherwise calls
        the full reset() method. After reset, all angles are zeroed and
        calibration state is reset.

        Note:
            This is a full hardware reset, which may take a brief moment to
            complete. Prefer zero_yaw() for just zeroing heading without
            disrupting pitch/roll calibration.

        See Also:
            zero_yaw(): Soft reset of yaw only (preferred for mid-match)
        """
        # NavX3 has no separate full reset; resetting yaw is the only supported operation
        self.zero_yaw()

    def zero_yaw(self) -> None:
        """Zero the yaw angle (heading) without affecting pitch or roll.

        Soft reset that sets current heading to 0 degrees. Safe to call
        mid-match to re-anchor the coordinate system. In REAL mode, this
        updates hardware state; in SIMULATION mode, sets sim_yaw = 0.

        Mode-Specific Behavior:
            - REAL: Calls self._gyro.resetYaw() on hardware
            - SIMULATION: Sets self.sim_yaw property to 0.0

        WARNING: Do NOT call while is_calibrating is True. Wait for calibration
        to complete first. initialize() and periodic() handle this automatically.

        Example:
            # At match start, after calibration is complete
            if navx.calibrated:
                navx.zero_yaw()  # Set heading to 0

            # Mid-match realignment
            navx.zero_yaw()  # Now current heading is 0 degrees

        See Also:
            reset(): Full hardware reset (less common)
            calibrated property: Check before calling zero_yaw()
        """
        if self._is_simulation:
            self.sim_yaw = 0.0
        else:
            self._gyro.resetYaw()

    @property
    def yaw(self) -> degrees:
        """Get the robot's yaw angle (Z-axis rotation) in degrees.

        Returns the raw yaw measurement without offset correction. This is the
        fundamental angle from the NavX IMU before any mathematical adjustments.

        Mode-Specific Behavior:
            - REAL: Reads self._gyro.getYaw() from hardware
            - SIMULATION: Reads self._gyro.getYaw() (the simulated device; set via sim_yaw)

        Reversal:
            If is_reversed is True, the returned value is negated to account
            for upside-down or reversed mounting.

        Returns:
            degrees: Current yaw angle in degrees. Positive is counterclockwise
                (left turn) when viewed from above.

        Note:
            Unlike angle property, yaw does NOT include the offset from zero_yaw().
            Both yaw and angle reference the same hardware measurement, but
            angle applies an internal offset for easier use in commands.

        See Also:
            angle property: Same data but with zero_yaw() offset applied
        """
        yaw = self._gyro.getYaw() or 0.0
        return -yaw if self._reversed else yaw

    @property
    def pitch(self) -> degrees:
        """Get the robot's pitch angle (Y-axis rotation) in degrees.

        Pitch is forward/backward tilt: positive is forward (nose down),
        negative is backward (nose up). Used to detect ramp incline or
        wheelie state.

        Mode-Specific Behavior:
            - REAL: Reads self._gyro.getPitch() with optional offset correction
            - SIMULATION: Reads the simulated device's Pitch value (0.0 unless a test sets it)

        Note:
            Pitch measurement typically requires NavX calibration and mounting
            angle compensation. The pitch_offset (currently 0) can be adjusted
            if NavX is mounted at an angle.

        TODO:
            Determine if pitch_offset should ever be non-zero or remove if unused.
        """
        pitch_offset = 0  # TODO: Always zero?

        return (self._gyro.getPitch() or 0.0) - pitch_offset

    @property
    def roll(self) -> degrees:
        """Get the robot's roll angle (X-axis rotation) in degrees.

        Roll is left/right tilt: positive is right tilt (right side down),
        negative is left tilt (left side down). Used to detect tipover risk
        or sloped terrain.

        Mode-Specific Behavior:
            - REAL: Reads self._gyro.getRoll() with optional offset correction
            - SIMULATION: Reads the simulated device's Roll value (0.0 unless a test sets it)

        Note:
            Roll measurement typically requires NavX calibration and mounting
            angle compensation. The roll_offset (currently 0) can be adjusted
            if NavX is mounted at an angle.

        TODO:
            Determine if roll_offset should ever be non-zero or remove if unused.
        """
        roll_offset = 0  # TODO: Always zero?

        return (self._gyro.getRoll() or 0.0) - roll_offset

    @property
    def raw_angle(self) -> degrees:
        """Get the unfiltered raw yaw angle directly from NavX hardware.

        Returns the raw hardware measurement before any filtering, offset,
        or reversal adjustments. Used for diagnostics and data analysis.

        Mode-Specific Behavior:
            - REAL: Returns self._gyro.getYaw() (no adjustments)
            - SIMULATION: Returns the simulated device's Yaw

        Returns:
            degrees: Raw yaw angle in degrees (no reversal applied).

        Note:
            Prefer using angle or yaw properties for normal operations.
            raw_angle is primarily for debugging hardware issues.
        """
        return self._gyro.getYaw() or 0.0

    @property
    def angle(self) -> degrees:
        """Get the robot's heading with zero_yaw() offset applied.

        Returns the yaw angle with any offset from zero_yaw() calls incorporated.
        This is the primary angle property for use in commands and trajectory
        following.

        Mode-Specific Behavior:
            - REAL: Reads self._gyro.getAngle() (continuous, does not wrap)
            - SIMULATION: Reads the simulated device's Angle (kept in step with Yaw by sim_yaw)

        Reversal:
            If is_reversed is True, the returned value is negated.

        Returns:
            degrees: Current heading in degrees relative to last zero_yaw() call.
                Positive is counterclockwise (left turn).

        Note:
            angle == yaw if zero_yaw() was never called or called at hardware
            reset. After zero_yaw(), angle maintains the offset internally.

        Example:
            navx.zero_yaw()
            # Now: angle = 0, some yaw value = X

            # After robot turns 45 degrees:
            # angle = 45, yaw = X + 45
        """
        angle = self._gyro.getAngle() or 0.0

        return -angle if self._reversed else angle

    @property
    def turn_rate(self) -> radians_per_second:
        """Get the robot's turn rate (angular velocity) in radians per second.

        Converts turn_rate_degrees_per_second to radians for use with WPILib
        motion profiling and PID controllers.

        Returns:
            radians_per_second: Current angular velocity in rad/s. Positive is
                counterclockwise (left turn).

        See Also:
            turn_rate_degrees_per_second property: Same data in deg/s
        """
        return math.radians(self.turn_rate_degrees_per_second)

    @property
    def turn_rate_degrees_per_second(self) -> degrees_per_second:
        """Get the robot's turn rate (angular velocity) in degrees per second.

        Returns the Z-axis angular velocity from the NavX gyroscope. Used to
        feed velocity into PID control loops for heading commands.

        Mode-Specific Behavior:
            - REAL: Reads self._gyro.getAngularVelocity().z from hardware
            - SIMULATION: Reads the simulated device's "Angular Velocity Z" (0.0 unless set)

        Reversal:
            If is_reversed is True, the returned value is negated.

        Returns:
            degrees_per_second: Current turn rate. Positive is counterclockwise
                (left turn).

        Example:
            pidController.calculate(target - navx.angle, navx.turn_rate_degrees_per_second)
        """
        velocity = self._gyro.getAngularVelocity()
        rate = velocity.z if velocity is not None else 0.0

        return -rate if self._reversed else rate

    def periodic(self) -> None:
        """Handle NavX calibration completion during periodic updates.

        Monitors the calibration state and auto-completes initialization when
        hardware finished calibrating. Call this every periodic cycle (typically
        from drivetrain or container periodic) until calibrated property becomes True.

        Calibration Completion Logic:
            If not self.calibrated and not self.is_calibrating:
                - Calibration just finished!
                - Call zero_yaw() to set heading to 0
                - Set _calibrated = True (initialization complete)

        This method allows calibration initialization to happen automatically
        in the background without blocking the main loop.

        Example - Container periodic:
            def robot_periodic(self):
                if hasattr(self.gyro, 'periodic'):
                    self.gyro.periodic()  # Auto-complete calibration when ready
                # Rest of periodic code...

        Note:
            Does NOT update GyroIOInputs or log telemetry; that's handled by
            the parent Gyro.periodic() via the base class. This method only
            manages the calibration state machine.
        """
        if not self.calibrated and not self.is_calibrating:
            # Calibration has just finished; zero the yaw and mark as calibrated
            self.zero_yaw()
            self._calibrated = True

    # ====================================================================
    # AdvantageKit IO Pattern Support (pykit / AdvantageScope logging)
    # ====================================================================

    def update_inputs(self, inputs: GyroIO.GyroIOInputs) -> None:
        """Populate sensor inputs struct from NavX hardware for logging.

        Called by the base Gyro.periodic() method to read all NavX measurements
        and pack them into the GyroIO.GyroIOInputs struct for pykit Logger.
        This data is then logged to .wpilog files and displayed in AdvantageScope.

        Data Populated (radians, matching the Pigeon2 implementation):
            - connected: ``isConnected()`` (data arrived recently)
            - yaw, yaw_rate, roll, pitch
            - *_timestamp: the NavX3 sample time (``getTimestamp()``), falling back to the
              current time when the device is not streaming

        Args:
            inputs (GyroIO.GyroIOInputs): Struct to populate with current sensor data.

        Note:
            This method is part of the AdvantageKit hardware abstraction layer.
            All values are logged automatically after update_inputs() returns.
        """
        inputs.connected = self._gyro.isConnected()
        inputs.yaw = Rotation2d.from_degrees(self.angle).radians()
        inputs.yaw_rate = self.turn_rate
        inputs.roll = math.radians(self.roll)
        inputs.pitch = math.radians(self.pitch)

        timestamp = self._gyro.getTimestamp()
        if timestamp is None:
            timestamp = Timer.get_timestamp()
        inputs.yaw_timestamp = inputs.yaw_rate_timestamp = timestamp
        inputs.roll_timestamp = inputs.pitch_timestamp = timestamp

    # ====================================================================
    # Simulation Support
    # ====================================================================

    def _sim_device(self) -> SimDeviceSim:
        """Return the NavX3 SimDevice (``NavX3[<can_id>]``), looking it up on first use."""
        if self._sim_gyro is None:
            names = SimDeviceSim.enumerate_devices("NavX3")
            name = f"NavX3[{self._can_id}]"
            if name not in names and len(names) == 1:
                name = names[0]
            self._sim_gyro = SimDeviceSim(name)
        return self._sim_gyro

    def sim_init(self, physics_controller: PhysicsEngine) -> None:
        """Connect to the simulated NavX3 device so ``sim_yaw`` can be read/written.

        Args:
            physics_controller (PhysicsEngine): library physics engine (unused, kept for API consistency).

        Note:
            ``navx.Navx`` registers a SimDevice named ``NavX3[<can_id>]``. If the NavX was injected with a
            different CAN ID and exactly one NavX3 device exists, that device is used.
        """
        super().sim_init(physics_controller)
        self._sim_device()

    @property
    def sim_yaw(self) -> degrees:
        """Simulated NavX3 yaw in degrees, read from the SimDevice's ``Yaw`` value."""
        return self._sim_device().get_double("Yaw").get()

    @sim_yaw.setter
    def sim_yaw(self, value: degrees) -> None:
        """Set the simulated NavX3 yaw (``Yaw`` and ``Angle`` SimDevice values) in degrees.

        Updated by the physics engine. If the gyro is reversed the value is negated before
        writing, so that ``yaw``/``angle`` read back ``value``.
        """
        if self._reversed:
            value = -value

        sim = self._sim_device()
        sim.get_double("Yaw").set(value)
        sim.get_double("Angle").set(value)
