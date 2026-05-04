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
"""CTRE motor controller implementation for RPM-based subsystems.

This module provides concrete implementation of RpmSubsystem for CTRE's TalonFX
motor controller paired with Kraken X60 motors. Uses Phoenix6 API for high-bandwidth
CAN communication, StatusSignal telemetry, and velocity control.

Supported Controllers:
    - KrakenX60: 80A brushless motor with TalonFX rotor + Kraken X60 stator
      (6000 RPM, 3 NM peak torque, integrated rotor temperature sensor)

Key CTRE/Phoenix6 Features:
    - StatusSignal API for efficient CAN data polling (low latency)
    - VelocityVoltage control request for direct velocity commands
    - Configurable CANivore/standard CAN bus
    - Motion Magic for smooth motion profiling
    - Integrated motor telemetry (voltage, current, position, velocity)
    - Built-in rotor position sensor (no external encoder needed)
    - Fault detection via device status API
    - High CAN update rates (up to 1kHz possible)

Configuration Flow:
    1. Subclass creates CtreRpmSubsystem instance (KrakenX60 motor)
    2. __init__ creates TalonFX on specified CAN ID
    3. __init__ registers StatusSignals for telemetry (voltage, current, velocity, position)
    4. __init__ optimizes CAN bus utilization for low latency
    5. post_init validates constants, applies TalonFXConfiguration
    6. _motor_config builds config with current limits, idle mode, PID gains
    7. _check_is_connected validates configuration and signal health
    8. Ready for velocity commands via VelocityVoltage request

StatusSignal Architecture (Key Difference from REV):
    - Replaces encoder references with native motor position/velocity
    - Update frequency tuned to robot period for synchronization
    - Signals: applied_output (voltage), velocity (RPS), supply_current, position
    - All signals registered with Phoenix6Signals for automatic logging
    - StatusSignal.is_all_good() used for connection health check

PID Configuration (Slot 0):
    - Supports kP, kI, kD gains (k_p, k_i, k_d properties)
    - Optional velocity feedforward (k_v property)
    - Note: CTRE I-zone (I_Zone) and I-max (I_Max) not exposed in base config
    - Uses CTRE's built-in velocity feedforward model
    - Slot 0 dedicated to velocity control

Velocity Control Model:
    - Commands sent as VelocityVoltage (rot/s in native units)
    - TalonFX automatically applies PID + feedforward
    - Supports continuous feedback without explicit control request re-send
    - Voltage compensation optional via k_v feedforward

Example Implementation (Kraken X60 Shooter):
    class ShooterSubsystem(CtreRpmSubsystem):
        def __init__(self, container):
            class ShooterConfig(CtreRpmConfig):
                max_rpm = 6000
                proportional_coefficient = 0.0001
                velocity_feedforward = 0.12  # Volts per RPS
                limit_current = 80

            super().__init__(
                container,
                can_device_id=10,
                inverted=False,
                name="Shooter",
                motor=DCMotor.kraken_x60(3),
                controller_type=ControllerType.KrakenX60,
                constants=ShooterConfig(),
                long_name="shooter/flywheel",
                coast=False,
                persist_config=False
            )

CAN Bus Considerations:
    - Standard CAN: 1 Mbps max, ~1kHz update rates feasible
    - CANivore: 5 Mbps potential, up to 1kHz high-frequency signals
    - optimize_bus_utilization() reduces unnecessary CAN traffic
    - Recommended: Update frequency = 1 / robot_period (synchronized with control loop)

Unit System:
    - Internal Phoenix6 units: rotations, rotations/second, volts, amperes
    - Conversion to WPILib: rotations → radians (×2π), RPS → rad/s
    - RPM input/output converted via rotationsPerMinuteToRadiansPerSecond
"""

import logging
from typing import Optional

from phoenix6 import StatusCode, StatusSignal
from phoenix6.configs import TalonFXConfiguration
from phoenix6.controls import VelocityVoltage
from phoenix6.hardware import TalonFX
from phoenix6.signals import NeutralModeValue
from phoenix6.units import ampere, rotation, rotations_per_second, volt
from wpimath.system.plant import DCMotor
from wpimath.units import amperes, radians, radians_per_second, revolutions_per_minute, \
    rotationsPerMinuteToRadiansPerSecond, rotationsToRadians

from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.rpm.rpm_subsystem import ControllerType, RpmSubsystem
from lib_6107.util.phoenix6_signals import Phoenix6Signals
from lib_6107.util.phoenix6_utils import handle_faults, try_until_ok

logger = logging.getLogger(__name__)


class CtreRpmConfig:
    """CTRE-specific configuration for RPM subsystems.

    Configuration object for CTRE/Phoenix6 TalonFX motor controllers.
    Note that some base class options (izone, imax_accum) are not exposed
    in TalonFXConfiguration.slot0 directly but can be accessed via advanced
    configuration if needed.

    Attributes:
        proportional_coefficient (float): kP gain for velocity PID. Default 0.0001.
            Controls proportional response to velocity error.

        integral_coefficient (float): kI gain for velocity PID. Default 0.
            Accumulates error over time; use conservatively to avoid oscillation.

        derivative_coefficient (float): kD gain for velocity PID. Default 0.
            Dampens response to reduce overshoot.

        izone (Optional[float]): Integral zone threshold. NOT USED in basic CTRE config.
            Note: Phoenix6 supports I_Zone via configurator but requires custom setup.

        imax_accum (Optional[float]): Max accumulated integral error. NOT USED in basic config.
            Note: Phoenix6 supports I_Max via configurator but requires custom setup.

        velocity_feedforward (Optional[float]): Feedforward gain (k_v). Default None.
            Volts per RPS. Reduces reliance on PID by providing a baseline voltage
            proportional to velocity error. e.g., 0.12 = 0.12V per RPS error.

        limit_current (amperes): Supply current limit in amperes. Default 40A.
            Typical: 40-80A for Kraken X60 (max 80A continuous).

        gear_reduction (float): Gear ratio multiplier (>1 for reduction). Default 1.0.
            Direct drive = 1.0. Affects effective RPM output.

        measurement_std_dev (List[float]): Kalman filter noise [pos_std, vel_std]. Default [0, 0].
            Experimental; typically disabled in CTRE implementations.

        max_rpm (Optional[revolutions_per_minute]): REQUIRED. Max achievable RPM.
            Must be set by subclass. For Kraken X60: typically 6000 (native).

    Note:
        CTRE's I_Zone and I_Max are available but not directly exposed here.
        Subclasses needing advanced tuning can access config.slot0.I_Zone / I_Max
        directly before applying configuration, or extend this class.
    """
    proportional_coefficient = 0.0001
    """kP - Proportional gain for velocity error response."""

    integral_coefficient = 0
    """kI - Integral gain. Use sparingly; CTRE systems often tune via feedforward instead."""

    derivative_coefficient = 0
    """kD - Derivative gain. Reduces overshoot and oscillation."""

    izone = None
    """I-zone threshold (NOT USED in basic CTRE config; see Note above)."""

    imax_accum = None
    """Max accumulated integral (NOT USED in basic CTRE config; see Note above)."""

    velocity_feedforward = None
    """Feedforward gain k_v in volts per RPS. Typical: 0.1–0.2 for brushless motors."""

    limit_current: amperes = 40
    """Current limit in amperes. Typical: 40–80A for Kraken X60."""

    gear_reduction = 1.0
    """Gear ratio multiplier (>1 for reduction). Direct drive = 1.0."""

    measurement_std_dev = [0.0, 0.0]
    """Kalman filter noise estimates [position, velocity]. Usually [0, 0]."""

    max_rpm: Optional[revolutions_per_minute] = None
    """Maximum RPM of mechanism. REQUIRED - must be set by subclass."""


class CtreRpmSubsystem(RpmSubsystem):
    """CTRE TalonFX motor controller implementation for RPM subsystems.

    Concrete implementation of RpmSubsystem using CTRE's TalonFX hardware
    (typically paired with Kraken X60 motor). Uses Phoenix6 API for low-latency
    CAN communication, StatusSignal telemetry, and VelocityVoltage control.

    Key Differences from REV (SparkMax/SparkFlex):
        - Native rotor position sensor (no external encoder)
        - StatusSignal API for efficient polling vs REV's update callbacks
        - VelocityVoltage control request abstraction
        - Higher CAN update rates possible (1 kHz vs ~200 Hz)
        - Simpler direct configuration (TalonFXConfiguration vs SparkBaseConfig)
        - CTRE fault bitmask for fault detection

    Supported Motor Controllers:
        - KrakenX60: 80A brushless, 6000 nominal RPM, integrated rotor sensor

    Initialization Sequence:
        1. __init__: Create TalonFX on specified CAN ID
        2. __init__: Create StatusSignals for motor telemetry (voltage, current, velocity, position)
        3. __init__: Set update frequency for signals (synchronized to robot period)
        4. __init__: Optimize CAN bus utilization
        5. __init__: Register signals with Phoenix6Signals logger
        6. post_init: Validate constants
        7. post_init: Build and apply TalonFXConfiguration
        8. post_init: Check connection via StatusCode and signal health
        9. Ready for velocity setpoint commands

    Motor Configuration (_motor_config):
        - Current limit (supply_current_limit)
        - Idle mode (coast/brake via motor_output.neutral_mode)
        - PID Slot 0: kP, kI, kD gains
        - Optional velocity feedforward (k_v)
        - Rotor position units: rotations (converted to radians in velocity_in_rps/position)
        - No encoder setup needed (rotor sensor built-in)

    StatusSignal Telemetry:
        Replaces external encoders with native motor signals:
        - _applied_output: Motor voltage (V)
        - _velocity: Rotor velocity (rot/s)
        - _supply_current: Motor current draw (A)
        - _position: Rotor position (rotations)

        All signals are cached and registered for automatic logging.

    Connection Validation:
        Uses StatusCode from configuration and StatusSignal.is_all_good() check.
        If config succeeds (StatusCode.OK) OR signals are healthy, considered connected.

    Attributes:
        _motor (TalonFX): CTRE TalonFX motor controller instance.
        _velocity_request (VelocityVoltage): Reusable control request object for velocity commands.
        _applied_output, _velocity, _supply_current, _position (StatusSignal): Motor telemetry.
        _is_connected (bool): True if configuration succeeded and signals are healthy.

    Example Usage:
        class ShooterSubsystem(CtreRpmSubsystem):
            def __init__(self, container):
                class ShooterConfig(CtreRpmConfig):
                    max_rpm = 6000
                    proportional_coefficient = 0.0001
                    velocity_feedforward = 0.12
                    limit_current = 80

                super().__init__(
                    container,
                    can_device_id=10,
                    inverted=False,
                    name="Shooter",
                    motor=DCMotor.kraken_x60(3),
                    controller_type=ControllerType.KrakenX60,
                    constants=ShooterConfig(),
                    long_name="shooter/flywheel",
                    coast=False,
                    persist_config=False
                )

    Note:
        Phoenix6 StatusSignals provide low-latency access to motor data. Update
        frequency is synchronized to robot period for deterministic behavior.
    """

    def __init__(self, container: 'RobotContainer', can_device_id: int, inverted: bool, name: str,
                 motor: DCMotor, controller_type: ControllerType, constants: CtreRpmConfig,
                 long_name: Optional[str] = None,
                 coast: Optional[bool] = True,
                 persist_config: Optional[bool] = False) -> None:
        """Initialize a CTRE TalonFX motor controller subsystem.

        Creates a TalonFX motor controller on the specified CAN ID, sets up
        StatusSignals for telemetry, optimizes CAN bus utilization, and validates
        connection. Calls post_init to complete configuration.

        Args:
            container (RobotContainer): Robot container for subsystem registration.
            can_device_id (int): CAN ID of the TalonFX (typically 0–62).
            inverted (bool): True to reverse motor direction.
            name (str): Subsystem name (e.g., "shooter", lowercase).
            motor (DCMotor): WPILib DCMotor model for simulation.
                Typical: DCMotor.kraken_x60(number_of_motors) for stacked Krakens.
            controller_type (ControllerType): Should be ControllerType.KrakenX60.
            constants (CtreRpmConfig): Configuration with PID tuning and limits.
            long_name (Optional[str]): Longer name for logging/dashboard.
                If None, defaults to name.
            coast (Optional[bool]): True for coast mode (coast to stop),
                False for brake mode (active stopping). Default True.
            persist_config (Optional[bool]): Unused for CTRE (kept for API compatibility
                with REV implementation). TalonFX always uses temporary config. Default False.

        Raises:
            NotImplementedError: If controller_type is not KrakenX60.

        Note:
            StatusSignals are created and update frequency is set immediately.
            post_init() is called at the end to apply motor configuration.
        """
        # Initialize base RpmSubsystem
        super().__init__(container, can_device_id, inverted, name,
                         controller_type, constants, long_name)

        # Validate and apply defaults to constants
        self._constants: CtreRpmConfig = self._validate_constants()

        # Create motor controller instance
        match controller_type:
            case ControllerType.KrakenX60:
                # Create TalonFX for Kraken X60 motor on standard CAN (CANivore device name is "")
                self._motor: TalonFX = TalonFX(self._device_id, "")

            case _:
                raise NotImplementedError(f"Unsupported controller type: {controller_type}")

        # Create reusable velocity control request object (will be updated each command)
        self._velocity_request: VelocityVoltage = VelocityVoltage(0)

        # Create StatusSignal references for efficient telemetry polling
        # These provide low-latency access to motor state without CAN round-trips
        self._applied_output: StatusSignal[volt] = self._motor.get_motor_voltage(False)
        self._velocity: StatusSignal[rotations_per_second] = self._motor.get_velocity(False)
        self._supply_current: StatusSignal[ampere] = self._motor.get_supply_current(False)
        self._position: StatusSignal[rotation] = self._motor.get_position(False)

        # Set StatusSignal update frequency to match robot period (synchronized polling)
        # Default 50 Hz for 20 mS period; higher rates possible with CANivore
        status = StatusSignal.set_update_frequency_for_all(
            1.0 / container.robot.period,
            self._applied_output,
            self._velocity,
            self._supply_current,
            self._position
        )

        # If setting frequency fails, try to optimize CAN bus utilization
        if status != StatusCode.OK:
            status = self._motor.optimize_bus_utilization()

            if status != StatusCode.OK:
                logger.warning("%s: Error during signal bus optimization: %s",
                              self.getName(), status)

        # Register signals with Phoenix6Signals for automatic logging
        Phoenix6Signals.register_signals(
            self._applied_output,
            self._velocity,
            self._supply_current,
            self._position
        )

        # Complete initialization (config, connection check)
        super().post_init(bool(coast), bool(persist_config))

    def post_init(self, coast: bool, persist_config: bool) -> None:
        """Apply motor configuration and validate CAN connection.

        Called after motor creation to:
        1. Validate constants (from base class)
        2. Build TalonFXConfiguration with PID, current limits, idle mode
        3. Apply configuration to motor with retries
        4. Check CAN connection via StatusCode and signal health

        Args:
            coast (bool): True for coast idle mode, False for brake mode.
            persist_config (bool): Unused for CTRE (kept for API compatibility).
                TalonFX uses temporary config by default.

        Note:
            If configuration fails, _is_connected is set to False but subsystem
            continues to operate (fallback mode). Check is_connected property
            before critical operations.
        """
        # Validate and apply default values to constants
        super().post_init(coast, persist_config)

        # Build motor configuration
        config = self._motor_config(coast)

        # Apply configuration with retries (try_until_ok handles exponential backoff)
        # persist_config is ignored for CTRE; config is always temporary
        config_status = try_until_ok(
            self.getName(), 5,
            lambda: self._motor.configurator.apply(config)
        )

        # Check if motor is connected and responsive
        self._is_connected = self._check_is_connected(config_status)

        # Note: TalonFX uses built-in rotor sensor; no external encoder setup needed

    def _validate_constants(self) -> CtreRpmConfig:
        """Validate CTRE-specific configuration constants.

        Currently delegates to base class validation. Provided as a template
        for future CTRE-specific validation if needed.

        Returns:
            CtreRpmConfig: Validated constants with defaults applied to None values.

        TODO:
            Remove this method if CTRE-specific validation is never implemented.
        """
        return super()._validate_constants()

    def _motor_config(self, coast: bool) -> TalonFXConfiguration:
        """Build CTRE motor configuration with PID tuning and limits.

        Creates a TalonFXConfiguration and applies:
        - Current limiting (supply_current_limit)
        - Idle mode (coast/brake)
        - PID Slot 0: kP, kI, kD gains
        - Optional velocity feedforward (k_v)
        - Rotor sensor as position feedback (no external encoder)

        Args:
            coast (bool): True for coast mode, False for brake mode.

        Returns:
            TalonFXConfiguration: Configured TalonFX config object.

        Raises:
            NotImplementedError: If controller_type is not KrakenX60.

        Note:
            TalonFXConfiguration provides direct access to slot0.k_p, k_i, k_d
            for PID tuning. Advanced options (I_Zone, I_Max) available if extended.
        """
        # Create controller-specific configuration
        match self._controller_type:
            case ControllerType.KrakenX60:
                config = TalonFXConfiguration()

            case _:
                raise NotImplementedError("CtreRpmSubsystem._motor_config: Unsupported controller type")

        # Set current limits and idle mode
        config.current_limits.supply_current_limit = self._constants.limit_current
        config.motor_output.neutral_mode = NeutralModeValue.COAST if coast else NeutralModeValue.BRAKE

        # Configure velocity PID (Slot 0)
        config.slot0.k_p = self._constants.proportional_coefficient
        config.slot0.k_i = self._constants.integral_coefficient
        config.slot0.k_d = self._constants.derivative_coefficient

        # Apply optional velocity feedforward if specified
        if self._constants.velocity_feedforward is not None:
            config.slot0.k_v = self._constants.velocity_feedforward

        return config

    def _check_is_connected(self, config_status: StatusCode | None) -> bool:
        """Validate CAN connection and motor responsiveness.

        Checks connection via:
        1. Configuration status (should be StatusCode.OK)
        2. StatusSignal health (all signals responding)

        Connection valid if either:
        - Configuration succeeded (StatusCode.OK), OR
        - Signals are all healthy even if config status is None

        Args:
            config_status (Optional[StatusCode]): Status from motor.configurator.apply().

        Returns:
            bool: True if motor is connected and responsive, False otherwise.

        Note:
            CTRE's StatusSignal.is_all_good() checks if all signals are updating.
            Combines reliability check (status code) with health check (signals).
        """
        return config_status == StatusCode.OK or (
            config_status is None and
            StatusSignal.is_all_good(
                self._applied_output,
                self._velocity,
                self._supply_current,
                self._position
            )
        )

    @property
    def is_connected(self) -> bool:
        """Check if motor is connected to CAN bus and responsive.

        Returns _is_connected flag (validated during post_init).
        For KrakenX60, returns True if configuration and signals are healthy.

        Returns:
            bool: True if connected and responsive, False if disconnected.

        Note:
            Use this to gate velocity commands or display connection status.
        """
        match self._controller_type:
            case ControllerType.KrakenX60:
                return self._is_connected
        return False

    @property
    def velocity_in_rps(self) -> radians_per_second:
        """Get current motor velocity in radians per second.

        Reads rotor velocity from StatusSignal and converts from rotations/second
        to radians/second (×2π). Applies reversal correction if needed.

        Returns:
            radians_per_second: Current angular velocity. Positive is CCW.

        Note:
            StatusSignal provides low-latency access without CAN round-trips.
        """
        rps: radians_per_second = rotationsToRadians(self._velocity.value)
        return -rps if self._inverted else rps

    @property
    def position(self) -> radians:
        """Get current rotor position in radians.

        Reads rotor position from StatusSignal and converts from rotations
        to radians (×2π).

        Returns:
            radians: Current angular position (accumulated distance).

        Note:
            Position wraps for continuous mechanisms. TalonFX tracks position
            across power cycles if configured.
        """
        return rotationsToRadians(self._position.value)

    def _set_velocity_goal(self, rpm: revolutions_per_minute,
                          rpm_tolerance: revolutions_per_minute | None) -> None:
        """Set the velocity goal and send to motor via VelocityVoltage request.

        Clamps RPM to [0, max_rpm], updates tolerance, converts to RPS, and
        sends as a VelocityVoltage control request to the motor.

        Args:
            rpm (revolutions_per_minute): Target RPM (clamped to valid range).
            rpm_tolerance (Optional[revolutions_per_minute]): Allowable error.
                If None, maintains current tolerance.

        Note:
            VelocityVoltage is a reusable control request (efficient CAN usage).
            TalonFX applies PID + feedforward autonomously once request sent.
        """
        # Store tolerance (default 0 if None)
        self._velocity_tolerance = rpm_tolerance or 0.0

        # Clamp RPM to valid range, store previous for comparison
        self._velocity_goal, previous = max(0.0, min(self._constants.max_rpm, abs(rpm))), self._velocity_goal

        # If goal or tolerance changed, send new velocity request
        if self._velocity_goal != previous or self._velocity_tolerance != self.tolerance:
            logger.info("%s: Setting goal RPM to %f. previous: %f",
                       self.getName(), self._velocity_goal, previous)
            logger.info("%s: current PID controller setpoint before command: %f",
                       self.getName(), self._pid_controller.getSetpoint())

            # Convert RPM to RPS and send velocity request
            rps: radians_per_second = rotationsPerMinuteToRadiansPerSecond(self._velocity_goal)
            self._velocity_request.with_velocity(rps)

    def updateInputs(self, inputs: RpmMechanismIO.RpmMechanismIOInputs) -> None:
        """Read motor state and populate logging struct from TalonFX.

        Called each periodic cycle to capture:
        - Connection status
        - Motor position (rotor rotations)
        - Motor velocity (rotor speed in rad/s)
        - Applied voltage (output)
        - Supply current draw (motor current)

        Args:
            inputs (RpmMechanismIOInputs): Struct to populate with current motor state.

        Note:
            Position data is logged but may not be used in replay currently (TODO).
            StatusSignals provide low-latency data without additional CAN overhead.
        """
        inputs.mechanism_connected = self.is_connected

        # Position and velocity from rotor sensor
        inputs.mechanism_position = self.position
        inputs.mechanism_velocity = self.velocity_in_rps

        # Power measurements
        inputs.mechanism_applied_voltage = self._applied_output.value
        inputs.mechanism_supply_current = self._supply_current.value

    def fault_detection(self, state: str, clear: Optional[bool] = True,
                       notify: Optional[bool] = True) -> None:
        """Detect, report, and optionally clear motor faults.

        Called at mode transitions to detect any faults in the TalonFX.
        CTRE faults are represented as a bitmask (multiple faults can coexist).

        Detected faults are logged and can trigger Elastic notifications
        for user visibility (e.g., "Motor overheated", "CAN lost").

        Args:
            state (str): Human-readable state for logging (e.g., "Autonomous-Exit").
            clear (Optional[bool]): True to clear faults after reporting,
                False to leave (sticky). Default True.
            notify (Optional[bool]): True to send Elastic notification,
                False to only log. Default True.

        Note:
            All detected faults result in a WARNING log message.
            Use state parameter to track when fault occurred (mode context).
            Sticky faults (clear=False) persist until explicitly cleared.

        Example Faults (CTRE-specific):
            - HardwareFault: Motor/controller hardware issue
            - CtreOmitFault: Firmware version mismatch or communication loss
            - OvertemperatureFault: Motor or controller overheated
            - BootloaderFault: Bootloader error (firmware issue)
        """
        # Delegate to CTRE-specific fault handler utility
        handle_faults(self.getName(), state, self._motor, clear=clear, notify=notify)