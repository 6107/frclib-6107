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
"""REV Robotics motor controller implementation for RPM-based subsystems.

This module provides concrete implementations of RpmSubsystem for REV Robotics
SparkMax and SparkFlex motor controllers. Handles CAN communication, REV-specific
configuration, firmware validation, fault detection, and simulation support.

Supported Controllers:
    - SparkMax: PWM-based 40A controller (older, less common)
    - SparkFlex: CAN-based 80A controller (recommended, modern)

Key REV-Specific Features:
    - CAN bus communication (low latency, reliable)
    - Built-in PID velocity control via ClosedLoopController
    - Firmware version checking for connection validation
    - Absolute encoder support (SparkFlex) with integrated sensors
    - Configurable coast/brake idle modes
    - Non-volatile configuration persistence option
    - Fault bitmask detection and reporting
    - REV-specific utilities (handle_faults, try_until_ok)

Configuration Flow:
    1. Subclass creates RevRpmSubsystem instance with motor type
    2. __init__ creates SparkMax/SparkFlex, initializes encoder
    3. post_init validates constants, applies motor config, checks connection
    4. _motor_config builds SparkBaseConfig with PID tuning, current limits
    5. _check_is_connected validates firmware version and CAN link
    6. Ready for periodic updates and PID setpoint commands

PID Configuration (Slot 0):
    - P, I, D gains from RevRpmConfig
    - Optional velocity feedforward coefficient
    - Optional I-zone (error band for integral application)
    - Optional I accumulator max (prevent wind-up)
    - Position wrapping enabled for continuous rotation mechanisms
    - Output range ±1.0 (normalized)
    - Encoder position units: radians (2π per rotation)

Example Implementation (SparkFlex Shooter):
    class ShooterSubsystem(RevRpmSubsystem):
        def __init__(self, container):
            class ShooterConfig(RevRpmConfig):
                max_rpm = 5600
                proportional_coefficient = 0.0001
                integral_coefficient = 0.00001

            super().__init__(container, can_device_id=2, inverted=False,
                           name="Shooter", motor=DCMotor.kraken_x60(3),
                           controller_type=ControllerType.SparkFlex,
                           constants=ShooterConfig(),
                           long_name="shooter/flywheel",
                           coast=False, persist_config=True)

Error Handling:
    - Rigid retry logic (try_until_ok) for CAN communication resilience
    - Firmware version as primary connection indicator
    - Fault detection via motor fault bitmask (REV-specific)
    - Elastic notifications for faults (optional)
    - Graceful fallback to defaults if configuration fails
"""

import logging
import math
from typing import Any, Callable, Optional

from rev import ClosedLoopSlot, PersistMode, ResetMode, REVLibError, SparkBase, SparkBaseConfig, SparkFlex, \
    SparkFlexConfig, SparkFlexSim, SparkMax, SparkMaxConfig, SparkMaxSim, SparkRelativeEncoder
from wpimath.system.plant import DCMotor
from wpimath.units import amperes, radians, radians_per_second, revolutions_per_minute

from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.rpm.rpm_subsystem import ControllerType, RpmConfig, RpmSubsystem, \
    SupportedClosedLoopControllers, SupportedEncoders
from lib_6107.util.rev_utils import handle_faults, try_until_ok

logger = logging.getLogger(__name__)


class RevRpmConfig(RpmConfig):
    """REV Robotics-specific configuration for RPM subsystems.

    Inherits from RpmConfig with REV-specific defaults. Currently equivalent
    to base class but provides a clear separation point for future REV-only
    tuning parameters (e.g., REV control panel defaults, SparkMax vs SparkFlex
    specific limits).

    Attributes:
        proportional_coefficient (float): kP gain. Default 0.0001.
        integral_coefficient (float): kI gain. Default 0.
        derivative_coefficient (float): kD gain. Default 0.
        izone (Optional[float]): Error band for integral application. Default None.
        velocity_feedforward (Optional[float]): V per RPM feedforward. Default None.
        imax_accum (Optional[float]): Max accumulated integral error. Default None.
        limit_current (amperes): Current limit in amperes. Default 40A.
        gear_reduction (float): Gear ratio multiplier. Default 1.0.
        measurement_std_dev (List[float]): Kalman filter noise [pos, vel]. Default [0, 0].
        max_rpm (Optional[revolutions_per_minute]): REQUIRED. Max achievable RPM.

    Note:
        Subclasses should override max_rpm and any tuning parameters specific
        to their mechanism. All inherited attributes apply.
    """
    proportional_coefficient = 0.0001
    """kP - Proportional gain. Increase for faster response to error."""

    integral_coefficient = 0
    """kI - Integral gain. Accumulates error over time to eliminate steady-state error."""

    derivative_coefficient = 0
    """kD - Derivative gain. Reduces overshoot by dampening response."""

    izone = None
    """I-zone threshold - integral only applied within this error band."""

    velocity_feedforward = None
    """Feedforward coefficient (V per RPM) to reduce feedback reliance."""

    imax_accum = None
    """Maximum accumulated integral error to prevent wind-up."""

    limit_current: amperes = 40
    """Current limit in amperes. Typical: 40A (SparkMax), 80A (SparkFlex)."""

    gear_reduction = 1.0
    """Gear ratio multiplier (>1 for reduction). Direct drive = 1.0."""

    measurement_std_dev = [0.0, 0.0]
    """Kalman filter noise estimates [position_std_dev, velocity_std_dev]."""

    max_rpm: Optional[revolutions_per_minute] = None
    """Maximum RPM of mechanism. REQUIRED - must be set by subclass."""


class RevRpmSubsystem(RpmSubsystem):
    """REV Robotics motor controller implementation for RPM subsystems.

    Concrete implementation of RpmSubsystem using REV SparkMax or SparkFlex
    motor controllers. Handles CAN communication, PID configuration, firmware
    validation, and fault detection.

    Supported Motor Controllers:
        - SparkMax: PWM-based, 40A continuous, older/legacy
        - SparkFlex: CAN-based, 80A continuous, recommended, faster/more reliable

    Key Features:
        - Automatic motor creation (SparkMax/SparkFlex based on ControllerType)
        - CAN connection validation via firmware version check
        - Built-in encoder support (SparkRelativeEncoder)
        - REV ClosedLoopController for velocity PID control
        - Configurable motor idle mode (coast/brake)
        - Optional configuration persistence to motor memory
        - Fault detection and reporting via REV fault bitmask
        - Simulation support via SparkMaxSim/SparkFlexSim

    Initialization Sequence:
        1. __init__: Create SparkMax/SparkFlex on specified CAN ID
        2. __init__: Set up encoder reference
        3. post_init: Validate constants, apply motor configuration
        4. post_init: Check CAN connection (firmware version)
        5. post_init: Initialize PID controller with slot 0
        6. Ready for velocity setpoint commands via _set_velocity_goal

    Motor Configuration (_motor_config):
        - Motor direction (inverted flag)
        - Current limiting
        - Idle mode (coast/brake)
        - PID gains (kP, kI, kD)
        - Optional velocity feedforward
        - Optional I-zone and accumulator limits
        - Encoder position units: radians
        - Limit switches disabled

    Attributes:
        _motor (SparkMax | SparkFlex): Motor controller object.
        _encoder (SparkRelativeEncoder): Built-in motor encoder for velocity/position.
        _pid_controller (SparkClosedLoopController): REV velocity PID controller.
        _is_connected (bool): True if motor firmware valid and CAN link OK.

    Example Usage:
        class ShooterSubsystem(RevRpmSubsystem):
            def __init__(self, container):
                class ShooterConfig(RevRpmConfig):
                    max_rpm = 5600
                    proportional_coefficient = 0.0001
                    integral_coefficient = 0.00001

                super().__init__(
                    container,
                    can_device_id=2,
                    inverted=False,
                    name="Shooter",
                    motor=DCMotor.kraken_x60(3),
                    controller_type=ControllerType.SparkFlex,
                    constants=ShooterConfig(),
                    long_name="shooter/flywheel",
                    coast=False,
                    persist_config=True
                )

    Note:
        For SparkFlex (recommended), ensure 11.x firmware is installed via
        REV Hardware Client. SparkMax is PWM-only (not CAN) and less reliable.
    """

    def __init__(self, container: 'RobotContainer', can_device_id: int, inverted: bool, name: str,
                 motor: DCMotor, controller_type: ControllerType, constants: RevRpmConfig,
                 long_name: Optional[str] = None,
                 coast: Optional[bool] = True,
                 persist_config: Optional[bool] = False) -> None:
        """Initialize a REV motor controller subsystem.

        Creates a SparkMax or SparkFlex motor controller on the specified CAN ID,
        sets up the encoder, and validates configuration. Calls post_init to complete
        configuration and connection verification.

        Args:
            container (RobotContainer): Robot container for subsystem registration.
            can_device_id (int): CAN ID of the motor controller (typically 0–62).
            inverted (bool): True to reverse motor direction relative to encoder.
            name (str): Subsystem name (e.g., "shooter", "intake", lowercase).
            motor (DCMotor): WPILib DCMotor model for simulation (e.g., DCMotor.kraken_x60(3)).
            controller_type (ControllerType): SparkMax or SparkFlex.
            constants (RevRpmConfig): Configuration object with PID tuning and limits.
            long_name (Optional[str]): Longer descriptive name for logging/dashboard.
                If None, defaults to name.
            coast (Optional[bool]): True for coast mode (coast to stop),
                False for brake mode (active stopping). Default True.
            persist_config (Optional[bool]): True to save configuration to motor
                non-volatile memory (survives power-off), False for temporary config.
                Default False (faster config apply).

        Raises:
            NotImplementedError: If controller_type is not SparkMax or SparkFlex.

        Note:
            After __init__, the motor is created but not fully configured.
            post_init() is called at the end to apply motor settings and check
            connection. No velocity commands should be issued before post_init completes.
        """
        # Initialize base RpmSubsystem
        super().__init__(container, can_device_id, inverted, name,
                         controller_type, constants, long_name)

        # Validate and apply defaults to constants
        self._constants: RevRpmConfig = self._validate_constants()
        self._encoder: SupportedEncoders | None = None

        # Create motor controller instance based on type
        match controller_type:
            case ControllerType.SparkMax:
                # PWM-based SparkMax (legacy, not recommended)
                self._motor: SparkMax = SparkMax(self._device_id, SparkMax.MotorType.kBrushless)
                if self._is_simulation:
                    self._sim_motor = SparkMaxSim(self._motor, motor)

            case ControllerType.SparkFlex:
                # CAN-based SparkFlex (recommended, modern)
                self._motor: SparkFlex = SparkFlex(self._device_id, SparkFlex.MotorType.kBrushless)
                if self._is_simulation:
                    self._sim_motor = SparkFlexSim(self._motor, motor)

            case _:
                raise NotImplementedError(f"Unsupported controller type: {controller_type}")

        # Get reference to built-in encoder
        self._encoder: SparkRelativeEncoder = self._motor.getEncoder()

        # Complete initialization (config, connection check, PID setup)
        super().post_init(bool(coast), bool(persist_config))

    def post_init(self, coast: bool, persist_config: bool) -> None:
        """Apply motor configuration and validate CAN connection.

        Called after motor creation to:
        1. Validate constants (from base class)
        2. Apply motor configuration (PID, current limit, idle mode)
        3. Check CAN connection via firmware version
        4. Initialize encoder and PID controller

        Configuration Persistence:
            - persist_config=True: Save to motor memory (survives power-off)
            - persist_config=False: Temporary config (faster, but lost on restart)

        Connection Validation:
            Checks firmware version (must be non-zero for valid motor).
            Also verifies configuration status (REVLibError.kOk).
            Falls back to True in simulation mode.

        Args:
            coast (bool): True for coast idle mode, False for brake mode.
            persist_config (bool): True to save config to motor NV memory.

        Note:
            If connection check fails, _is_connected is set to False.
            Motor can still operate, but will log warnings (not critical).
        """
        # Validate and apply default values to constants
        super().post_init(coast, persist_config)

        # Prepare configuration persistence mode
        persist = PersistMode.kPersistParameters if persist_config else PersistMode.kNoPersistParameters

        # Attempt to apply motor configuration with retries
        # try_until_ok retries up to 5 times with exponential backoff
        config_status = try_until_ok(
            self.getName(), 5,
            lambda: self._motor.configure(
                self._motor_config(coast),
                ResetMode.kResetSafeParameters,
                persist
            )
        )

        # Check if motor is connected and responsive
        self._is_connected = self._check_is_connected(config_status)

        # Set up encoder reference (should be same as motor, but explicit)
        self._encoder: SupportedEncoders = self._motor.getEncoder()

        # Initialize PID controller for velocity control
        self._pid_controller: SupportedClosedLoopControllers = self._motor.getClosedLoopController()
        # Set initial setpoint to 0 in voltage mode (will switch to velocity later)
        self._pid_controller.setSetpoint(0.0, SparkBase.ControlType.kVoltage, ClosedLoopSlot(0))

    def _validate_constants(self) -> RevRpmConfig:
        """Validate REV-specific configuration constants.

        Currently delegates to base class validation. Provided as a template
        for subclasses that may add REV-specific constant checks in the future.

        Returns:
            RevRpmConfig: Validated constants with defaults applied to None values.

        TODO:
            Remove this method if REV-specific validation is never needed,
            or implement REV-specific checks here (e.g., SparkFlex-specific limits).
        """
        return super()._validate_constants()

    def try_until_ok(self, what: str, attempts: int, command: Callable[[], Any]) -> REVLibError:
        """Retry a REV command with exponential backoff until success or max attempts.

        Wrapper around the utility function for convenient access from subclasses.

        Args:
            what (str): Description of command (for logging, e.g., "Motor config").
            attempts (int): Maximum number of attempts.
            command (Callable): Lambda or function that returns REVLibError.

        Returns:
            REVLibError: Final status code from last attempt.

        Example:
            status = self.try_until_ok("Set encoder position", 3,
                                      lambda: self._encoder.setPosition(0.0))
        """
        return try_until_ok(what, attempts, command)

    def _motor_config(self, coast: bool) -> SparkBaseConfig:
        """Build REV motor configuration with PID tuning and limits.

        Creates a SparkMaxConfig or SparkFlexConfig (depending on controller type)
        and applies:
        - Motor direction (inverted flag)
        - Current limiting
        - Idle mode (coast/brake)
        - PID slot 0: gains (kP, kI, kD), feedforward, I-zone, accumulator
        - Encoder: position units in radians
        - Limit switches: disabled
        - Position wrapping: enabled (for continuous mechanisms)
        - Output range: ±1.0 (normalized)

        Args:
            coast (bool): True for coast mode, False for brake mode.

        Returns:
            SparkBaseConfig: Configured SparkMaxConfig or SparkFlexConfig.

        Raises:
            NotImplementedError: If controller type is unsupported.

        Note:
            Uses ClosedLoopSlot(0) for velocity PID tuning. The fluent API
            allows chained configuration calls for readability.
        """
        # Create controller-specific config object
        match self._controller_type:
            case ControllerType.SparkMax:
                config = SparkMaxConfig()

            case ControllerType.SparkFlex:
                config = SparkFlexConfig()

            case _:
                raise NotImplementedError("RevRpmSubsystem._motor_config: Unsupported controller type")

        # Apply motor direction, current limit, and idle mode
        config = (config
                  .inverted(self._inverted)
                  .smartCurrentLimit(self._constants.limit_current)
                  .setIdleMode(SparkFlexConfig.IdleMode.kCoast if coast else SparkFlexConfig.IdleMode.kBrake)
                  )

        # Disable mechanical limit switches (not used in this implementation)
        config.limitSwitch.forwardLimitSwitchEnabled(False).reverseLimitSwitchEnabled(False)

        # Configure closed-loop (PID) control for slot 0 (velocity)
        slot0 = ClosedLoopSlot(ClosedLoopSlot.kSlot0)
        (
            config.closedLoop
            .pid(p=self._constants.proportional_coefficient,
                 i=self._constants.integral_coefficient,
                 d=self._constants.derivative_coefficient,
                 slot=slot0)
            .positionWrappingEnabled(True)  # Enable for continuous rotation
            .outputRange(-1, 1)  # Normalized output ±1.0
        )

        # Apply optional tuning parameters if specified
        if self._constants.velocity_feedforward is not None:
            config.closedLoop.velocityFF(self._constants.velocity_feedforward, slot=slot0)

        if self._constants.imax_accum is not None:
            config.closedLoop.IMaxAccum(self._constants.imax_accum, slot=slot0)

        if self._constants.izone is not None:
            config.closedLoop.IZone(self._constants.izone, slot=slot0)

        # Set encoder position conversion: 2π radians per motor rotation
        config.encoder.positionConversionFactor(2 * math.pi)

        return config

    def _check_is_connected(self, config_status: REVLibError | None) -> bool:
        """Validate CAN connection and motor responsiveness.

        For REV motors, connection status is determined by:
        1. Firmware version (must be non-zero, indicating motor is responding)
        2. Configuration status (should be REVLibError.kOk or None)
        3. In simulation, always returns True

        A motor is considered "connected" if:
        - Firmware version != 0 (motor is responding on CAN)
        - Config status is OK or None (configuration succeeded)
        - OR running in simulation mode

        Args:
            config_status (Optional[REVLibError]): Status from motor.configure() call.

        Returns:
            bool: True if motor is connected and responsive, False otherwise.

        Note:
            Logs firmware version at INFO level (successful).
            Logs WARNING if firmware is 0 or config status is not OK (failed connection).
        """
        match self._controller_type:
            case ControllerType.SparkFlex | ControllerType.SparkMax:
                # Read firmware version from motor (0 indicates no response)
                version = self._motor.getFirmwareVersion()
                logger.info("%s firmware version: %d", self.getName(), version)

                # Connection valid if: firmware is present AND config succeeded
                ok = (version != 0 and (config_status is None or
                                        config_status == REVLibError.kOk)) or \
                     self._is_simulation

                if not ok:
                    logger.warning("%s firmware version: %d, status: %s", self.getName(),
                                   version, str(config_status))
                return ok

            case _:
                raise NotImplementedError("Unsupported controller type")

    @property
    def is_connected(self) -> bool:
        """Check if motor is connected to CAN bus and responsive.

        Returns _is_connected flag (set during post_init by _check_is_connected).
        In simulation mode, always returns True.

        Returns:
            bool: True if connected and responsive, False if disconnected.

        Note:
            Use this to gate velocity commands or display connection status.
            Even if disconnected, the subsystem may still function (fallback modes).
        """
        return self._is_connected or self._is_simulation

    @property
    def velocity_in_rps(self) -> radians_per_second:
        """Get current motor velocity in radians per second.

        Reads encoder velocity and applies reversal correction if needed.

        Returns:
            radians_per_second: Current angular velocity. Positive is CCW (left turn).
        """
        rps = self._encoder.getVelocity()
        return -rps if self._inverted else rps

    @property
    def position(self) -> radians:
        """Get current motor position in radians.

        Reads encoder position. Position wraps for continuous rotation mechanisms.

        Returns:
            radians: Current angular position relative to encoder home.
        """
        return self._encoder.getPosition()

    def _set_velocity_goal(self, rpm: revolutions_per_minute,
                          rpm_tolerance: revolutions_per_minute | None) -> None:
        """Set the velocity goal and tolerance for PID control.

        Clamps RPM to [0, max_rpm], updates tolerance, and sends setpoint
        to the SparkFlex/SparkMax PID controller.

        Args:
            rpm (revolutions_per_minute): Target RPM (clamped to valid range).
            rpm_tolerance (Optional[revolutions_per_minute]): Error tolerance.
                If None, maintains current tolerance. If 0, sets to 0 (strict).

        Note:
            Takes absolute value of RPM (reversal handled via motor inversion).
            Logs goal changes and current PID setpoint for debugging.
        """
        # Store tolerance (default 0 if None)
        self._velocity_tolerance = rpm_tolerance or 0.0

        # Clamp RPM to [0, max_rpm], store previous for comparison
        self._velocity_goal, previous = max(0.0, min(self._constants.max_rpm, abs(rpm))), self._velocity_goal

        # If goal or tolerance changed, update PID setpoint
        if self._velocity_goal != previous or self._velocity_tolerance != self.tolerance:
            logger.info("%s: Setting goal RPM to %f. previous:%f",
                       self.getName(), self._velocity_goal, previous)
            logger.info("%s: current PID controller setpoint before command: %f",
                       self.getName(), self._pid_controller.getSetpoint())

            # Set PID setpoint in velocity (RPM) mode
            self._pid_controller.setSetpoint(self._velocity_goal, SparkBase.ControlType.kVelocity)

    def updateInputs(self, inputs: RpmMechanismIO.RpmMechanismIOInputs) -> None:
        """Read motor state and populate logging struct from REV hardware.

        Called each periodic cycle to capture:
        - Connection status
        - Motor position (encoder rotations)
        - Motor velocity (encoder speed in rad/s)
        - Applied voltage (output)
        - Supply current draw (motor current)

        Args:
            inputs (RpmMechanismIOInputs): Struct to populate with current motor state.

        Note:
            Position is logged but may not be used in log replay (TODO).
            All values are read directly from REV API (no filtering applied here).
        """
        inputs.mechanism_connected = self.is_connected

        # Position and velocity from encoder
        inputs.mechanism_position = self.position
        inputs.mechanism_velocity = self.velocity_in_rps

        # Power measurements
        inputs.mechanism_applied_voltage = self._motor.getAppliedOutput()
        inputs.mechanism_supply_current = self._motor.getOutputCurrent()

    def fault_detection(self, state: str, clear: Optional[bool] = True,
                       notify: Optional[bool] = True) -> None:
        """Detect, report, and optionally clear motor faults.

        Called at mode transitions (disabled, autonomous, teleop init/exit) to
        detect any faults in the motor controller. REV faults are represented
        as a bitmask (multiple faults can occur simultaneously).

        Faults are logged as warnings and can trigger Elastic notifications
        for user awareness (e.g., "Motor overheated", "CAN fault").

        Args:
            state (str): Human-readable state for logging (e.g., "Autonomous-Exit",
                "Disabled-Init").
            clear (Optional[bool]): True to clear faults after reporting.
                False to leave faults (sticky, visible in next check). Default True.
            notify (Optional[bool]): True to send Elastic notification for critical
                faults. False to only log. Default True.

        Note:
            All detected faults result in a WARNING log message.
            Use state parameter to understand when fault occurred (during which mode).
            Sticky faults (if clear=False) persist until explicitly cleared.

        Example Faults (REV-specific):
            - MotorFault: Motor hardware issue
            - SensorFault: Encoder or Hall-effect sensor issue
            - OvercurrentFault: Current limit exceeded
            - OvertemperatureFault: Motor or controller overheated
        """
        # Delegate to REV-specific fault handler utility
        handle_faults(self.getName(), state, self._motor, clear=clear, notify=notify)