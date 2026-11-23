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
"""Base subsystem class for PID-controlled single-motor mechanisms in frclib-6107.

This module provides a reusable subsystem for mechanisms driven by a single motor
with a PID velocity (RPM) control goal. Supports REV SparkMax/SparkFlex and CTRE
TalonFX motors with integrated logging, simulation, and SysID characterization.

Key Features:
    - PID velocity control with configurable kP, kI, kD, I-zone
    - Multi-motor support (SparkMax, SparkFlex, TalonFX)
    - Goal tracking with tolerance checking for command readiness
    - Automatic logging via AdvantageKit IO pattern (replay support)
    - SysID integration for system characterization
    - Simulation support via REV/CTRE sim motors
    - Current limiting and configurable motor behavior (coast/brake)
    - Logger-based dashboard telemetry for real-time debugging

Typical Use Cases:
    - Intake/ejection wheels
    - Shooter flywheels
    - Indexer belts/wheels
    - Climber spools
    - Any other single-motor RPM-based mechanisms

PID Tuning Guide:
    - Start with kP only (proportional) to reach setpoint roughly
    - Add kD (derivative) to reduce overshoot
    - Add kI (integral) if steady-state error remains
    - Use I-zone to limit integral wind-up at large errors
    - Velocity feedforward can reduce tuning effort

Example Implementation (Shooter Flywheel):
    class ShooterSubsystem(RpmSubsystem):
        def __init__(self, container):
            class ShooterConfig(RpmConfig):
                max_rpm = 5600
                proportional_coefficient = 0.0001
                integral_coefficient = 0.00001
                derivative_coefficient = 0
                limit_current = 40

            super().__init__(container, can_device_id=2, inverted=False,
                           name="Shooter", controller_type=ControllerType.SparkFlex,
                           constants=ShooterConfig(), long_name="shooter/flywheel")

            # Create motor post-init
            self.post_init(coast=False, persist_config=True)
"""

from __future__ import annotations

import logging
from copy import deepcopy
from enum import Enum, unique
from typing import TYPE_CHECKING, Any

from commands2.command import Command
from commands2.sysid import SysIdRoutine
from phoenix6.hardware import TalonFX
from rev import (
    SparkBaseConfig,
    SparkClosedLoopController,
    SparkFlex,
    SparkFlexSim,
    SparkMax,
    SparkMaxSim,
    SparkRelativeEncoder,
)
from wpilib.simulation import RoboRioSim
from wpilib.sysid import SysIdRoutineLog
from wpimath import DCMotor
from wpimath.units import (
    amperes,
    radians,
    radians_per_second,
    radians_per_second_to_rotations_per_minute,
    revolutions_per_minute,
    volts,
)

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer
from lib_6107.subsystems.pykit.rpm_mechanism_io import RpmMechanismIO
from lib_6107.subsystems.subsystem import SubsystemBase

if TYPE_CHECKING:
    from lib_6107.robotcontainer import RobotContainer

logger = logging.getLogger(__name__)

# Type aliases for supported motor/encoder/controller combinations
SupportedMotors = SparkMax | SparkFlex | TalonFX
"""Union type for all supported real (non-simulation) motor controllers."""

SupportedSimMotors = SparkMaxSim | SparkFlexSim
"""Union type for supported simulated motor classes."""

SupportedEncoders = SparkRelativeEncoder
"""Union type for supported encoder implementations."""

SupportedClosedLoopControllers = SparkClosedLoopController
"""Union type for supported closed-loop PID controller implementations."""


@unique
class ControllerType(Enum):
    """Enumeration of supported motor controller types.

    Used to identify which motor/controller combination is being configured.
    This determines hardware-specific initialization, configuration, and
    communication protocols.

    Attributes:
        SparkMax (str): REV Robotics SparkMax PWM motor controller.
            - 40A continuous (60A peak)
            - Used for smaller motors (up to ~2.2 kW)
            - PWM interface

        SparkFlex (str): REV Robotics SparkFlex CAN motor controller
            - 80A continuous (120A peak)
            - Used for larger motors (up to ~4.5 kW)
            - CAN bus interface

        KrakenX60 (str): CTRE Kraken X60 motor with TalonFX controller
            - 80A continuous (150A peak)
            - 6000 RPM motor
            - CAN bus interface
            - Note: Imported as TalonFX from phoenix6
    """

    SparkMax = "SparkMax"  # Rev Robotics PWM controller
    SparkFlex = "SparkFlex"  # Rev Robotics CAN controller
    KrakenX60 = "KrakenX60"  # CTRE TalonFX + Kraken X60 motor


def _default_max_rpm(controller_type: ControllerType, motor: DCMotor) -> revolutions_per_minute:
    """Calculate default maximum RPM based on controller and motor characteristics.

    Placeholder for future automatic RPM calculation. Currently returns 0.0.
    Teams should explicitly set max_rpm in RpmConfig rather than relying on this.

    Args:
        controller_type (ControllerType): Motor controller type.
        motor (DCMotor): WPILib DCMotor model for motor characteristics.

    Returns:
        revolutions_per_minute: Calculated maximum RPM (currently 0.0).

    TODO:
        Implement automatic max RPM calculation from motor model and
        gearing. Currently requires explicit configuration.
    """
    # TODO: Future, for when None passed in for MAX_RPM
    return 0.0


class RpmConfig:
    """Configuration constants for RPM-based subsystems.

    Teams create a subclass and override these values to configure their specific
    mechanism. Any attributes set to None will use the defaults shown here.

    Required Attributes (must be set by subclass):
        - max_rpm: Maximum achievable RPM (motor + gearing)
        - limit_current: Current limit in amperes
        - proportional_coefficient (kP): PID proportional gain
        - integral_coefficient (kI): PID integral gain
        - derivative_coefficient (kD): PID derivative gain

    Optional Attributes (inherit defaults if not set):
        - gear_reduction: Gear ratio multiplier (> 1 for reduction)
        - measurement_std_dev: [position_std_dev, velocity_std_dev] for Kalman filtering
        - velocity_feedforward: Voltage/RPM feedforward coefficient
        - izone: Error band under which integral gain applies
        - imax_accum: Maximum accumulated integral error

    Attributes:
        proportional_coefficient (float): Gain applied proportionally to error.
            Typical range: 0.0001–0.001. Larger values = stronger response to error.
            Controls how quickly the mechanism reaches setpoint.

        integral_coefficient (float): Gain applied to accumulated error over time.
            Typical range: 0–0.00001. Eliminates steady-state error. Too high
            causes overshoot and oscillation. Use I-zone to limit application.

        derivative_coefficient (float): Gain applied to error rate of change.
            Typical range: 0–0.001. Reduces overshoot by dampening response.
            Can amplify noise if set too high.

        izone (Optional[float]): Error threshold below which integral accumulates.
            Outside this zone, kI is not applied. Prevents integral wind-up when
            far from setpoint. None means I-zone is effectively infinite.

        velocity_feedforward (Optional[float]): Voltage per RPM to reduce steady-state error.
            Feedforward voltage = velocity_feedforward * velocity_goal. Reduces
            reliance on feedback control. None means no feedforward.

        imax_accum (Optional[float]): Maximum accumulated integral error value.
            Caps the integral term to prevent large overshoot-causing spikes.
            None means no accumulation limit.

        limit_current (amperes): Current limit for motor in amperes.
            Typical: 40A (SparkMax), 80A (SparkFlex). Default 40A.

        gear_reduction (float): Gear ratio multiplier (> 1 for reduction).
            Example: 4.0 means 4:1 reduction (wheel slower than motor).
            Used to convert motor RPM to mechanism RPM. Default 1.0 (no reduction).

        measurement_std_dev (List[float]): [position_std_dev, velocity_std_dev].
            Kalman filter noise estimates. [0.0, 0.0] disables filtering.

        max_rpm (Optional[revolutions_per_minute]): Maximum RPM of the mechanism.
            MUST be set by subclass. Used for command validation and log scaling.
    """

    proportional_coefficient = 0.0001
    """kP - Proportional gain. Increase to reach goal faster; decrease to reduce overshoot."""

    integral_coefficient = 0
    """kI - Integral gain. Adds effort over time to eliminate steady-state error."""

    derivative_coefficient = 0
    """kD - Derivative gain. Slows down as approaching goal to reduce overshoot."""

    izone = None
    """I-zone threshold - integral only applied within this error band from goal."""

    velocity_feedforward = None
    """Feedforward voltage multiplier (V per RPM) to reduce feedback reliance."""

    imax_accum = None
    """Maximum accumulated integral error magnitude to prevent wind-up."""

    limit_current: amperes = 40
    """Current limit in amperes. Typical: 40A (SparkMax), 80A (SparkFlex)."""

    # Optional configuration
    gear_reduction = 1.0
    """Gear ratio (> 1 for reduction). Default 1.0 means direct drive."""

    measurement_std_dev = [0.0, 0.0]
    """[position_std_dev, velocity_std_dev] for Kalman filtering. [0,0] disables."""

    max_rpm: revolutions_per_minute | None = None
    """Maximum RPM of mechanism. REQUIRED - must be set by subclass."""

    # Private class variable for required fields
    __rpm_required_attributes = (
        "max_rpm",
        "limit_current",
        "proportional_coefficient",
        "integral_coefficient",
        "derivative_coefficient",
    )

    @property
    def required_attributes(self) -> tuple[str, ...]:
        """Get tuple of required attribute names that must exist in subclass.

        Returns:
            Tuple[str, ...]: Attribute names that must be present in configuration.
                Each can be None (will use defaults), but must exist as an attribute.
        """
        return self.__rpm_required_attributes


class RpmSubsystem(SubsystemBase, RpmMechanismIO):
    """Base subsystem for PID-controlled single-motor mechanisms.

    Provides a reusable framework for mechanisms with a single motor that maintains
    a velocity (RPM) goal. Integrates PID control, telemetry logging, simulation,
    and SysID characterization. Teams subclass this and implement abstract methods
    to create specific mechanisms (shooter, intake, indexer, etc.).

    Inherited from SubsystemBase:
        - Name tracking and hierarchy
        - Periodic and dashboard callbacks
        - Initialization status tracking
        - Robot reference

    Inherited from RpmMechanismIO:
        - AdvantageKit IO abstraction for logging/replay
        - Hardware abstraction layer pattern

    Motor Support:
        - REV SparkMax (40A PWM)
        - REV SparkFlex (80A CAN)
        - CTRE TalonFX/Kraken X60 (80A CAN)

    Key Responsibilities:
        1. PID velocity control with configurable gains
        2. Current limiting for motor protection
        3. Goal tracking and readiness checking
        4. Motor motion profiling and voltage commands
        5. Telemetry logging for replay analysis
        6. Simulation physics updates
        7. SysID system identification support

    Abstract Methods (required implementation):
        - velocity_in_rps: Return current motor velocity in rad/s
        - position: Return motor position in radians
        - _set_velocity_goal: Set PID target RPM and tolerance
        - _motor_config: Return SparkBaseConfig for motor setup
        - update_inputs: Populate RpmMechanismIOInputs from hardware

    Attributes:
        _motor (SupportedMotors): Motor controller object (SparkMax/SparkFlex/TalonFX).
        _encoder (SupportedEncoders): Motor encoder for position/velocity feedback.
        _pid_controller (SupportedClosedLoopControllers): Closed-loop velocity controller.
        _velocity_goal (revolutions_per_minute): Target RPM for PID controller.
        _velocity_tolerance (revolutions_per_minute): Allowable RPM error for readiness.
        _sim_motor (SupportedSimMotors): Simulated motor (SIMULATION mode only).
        _constants (RpmConfig): Configuration values (validated at post_init).
        _sysid_routine (SysIdRoutine): System identification characterization routine.

    Periodic Flow:
        1. periodic() called each cycle (20 mS)
        2. update_inputs() reads motor state into RpmMechanismIOInputs
        3. Logger records goal, current velocity, tolerance
        4. dashboard_periodic() records telemetry at throttled rate

    Example Implementation:
        class ShooterSubsystem(RpmSubsystem):
            def __init__(self, container):
                class ShooterConfig(RpmConfig):
                    max_rpm = 5600
                    proportional_coefficient = 0.0001
                    ...

                super().__init__(container, can_device_id=2, inverted=False,
                               name="Shooter", controller_type=ControllerType.SparkFlex,
                               constants=ShooterConfig(), long_name="shooter/flywheel")

            def velocity_in_rps(self):
                return self._encoder.get_velocity()

            def _set_velocity_goal(self, rpm, tolerance):
                # Set PID setpoint
                pass
    """

    def __init__(
        self,
        container: RobotContainer,
        can_device_id: int,
        inverted: bool,
        name: str,
        controller_type: ControllerType,
        constants: RpmConfig,
        long_name: str | None,
    ) -> None:
        """Initialize the RPM subsystem base class.

        Called by subclass to set up subsystem infrastructure. Subclass must create
        the motor, encoder, and PID controller after calling this (typically in
        post_init() or a custom init method).

        Args:
            container (RobotContainer): Robot container reference for subsystem registration.
            can_device_id (int): CAN bus ID for the motor (ignored for non-CAN motors).
            inverted (bool): True if motor direction should be reversed.
            name (str): Subsystem name (lowercase, e.g., "shooter" or "intake").
            controller_type (ControllerType): Motor controller type (SparkMax, SparkFlex, KrakenX60).
            constants (RpmConfig): Configuration object with PID and Current limits.
            long_name (str | None): Longer name for logging/dashboard (e.g., "shooter/flywheel").
                If None, defaults to name.

        Note:
            - Subclass must initialize _motor, _encoder, _pid_controller in post_init()
            - Constants are validated in post_init() via _validate_constants()
            - SysIdRoutine is created automatically; subclass can expose it via methods
        """
        # Initialize both base classes
        SubsystemBase.__init__(self, container, name, long_name)
        RpmMechanismIO.__init__(self, name)

        # Store configuration
        self._controller_type = controller_type
        self._long_name = long_name or name
        self._device_id = can_device_id
        self._inverted = inverted
        self._inputs = RpmMechanismIO.RpmMechanismIOInputs()

        # Simulation only (set in derived class or sim_init)
        self._sim_motor: SupportedSimMotors | None = None

        # Motor/encoder/controller (set by derived class after super().__init__)
        self._motor: SupportedMotors | None = None
        self._encoder: SupportedEncoders | None = None
        self._constants: RpmConfig = constants

        # Defined in post_init
        self._is_connected: bool = False
        self._pid_controller: SupportedClosedLoopControllers | None = None

        # Control state
        self._velocity_goal: revolutions_per_minute = 0.0
        self._velocity_tolerance: revolutions_per_minute = 0.0

        # SysID Support - create characterization routine
        self._sysid_routine = SysIdRoutine(
            SysIdRoutine.Config(),
            SysIdRoutine.Mechanism(
                lambda voltage: self._set_voltage(voltage), lambda log: self._log_motor(log), self, name
            ),
        )

    def post_init(self, coast: bool, persist_config: bool) -> None:
        """Validate and finalize configuration after subsystem creation.

        Called after __init__ to perform post-initialization setup. Validates
        that required constants are present and substitutes defaults for None values.

        Subclass should typically:
        1. Create motor/encoder/PID controller
        2. Call super().post_init() to validate constants
        3. Configure motor behavior (coast/brake, current limit, etc.)

        Args:
            coast (bool): True for coast mode (coast to stop), False for brake mode.
            persist_config (bool): True to save motor config to non-volatile memory,
                False to use temporary configuration (faster).

        Note:
            This is a template method; subclass provides motor initialization.
        """
        # Validate and apply default values to constants
        self._constants = self._validate_constants()

    def _validate_constants(self) -> Any:
        """Validate required constants are present and apply defaults to None values.

        Ensures all required attributes exist in the config object (even if None).
        Substitutes default values from RpmConfig for any None attributes.
        Returns a deep copy to prevent mutations affecting the original.

        Returns:
            RpmConfig: Validated constants object with defaults applied.

        Raises:
            AssertionError: If a required attribute is missing from constants object.

        Example:
            # If subclass sets proportional_coefficient = None:
            # After validation, it becomes 0.0001 (from RpmConfig default)
        """
        constants = deepcopy(self._constants)

        for attribute in RpmConfig().required_attributes:
            # Check that attribute exists (can be None)
            if not hasattr(constants, attribute):
                raise ValueError(f"{attribute} was not found in {self.get_name()} object config")

            # If None, use default from RpmConfig
            if getattr(constants, attribute, None) is None:
                setattr(constants, attribute, getattr(RpmConfig(), attribute))

        return constants

    def _motor_config(self, coast: bool) -> SparkBaseConfig:
        """Create motor configuration for this subsystem.

        Abstract method implemented by subclass to return a SparkBaseConfig
        with subsystem-specific settings (current limit, feedback sensor, etc.).

        Args:
            coast (bool): True for coast mode, False for brake mode.

        Returns:
            SparkBaseConfig: Motor configuration object ready to apply to motor.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.

        Example:
            def _motor_config(self, coast):
                config = SparkBaseConfig()
                config.smart_current_limit = self._constants.limit_current
                config.idle_mode = SparkBaseConfig.IdleMode.COAST if coast else SparkBaseConfig.IdleMode.BRAKE
                return config
        """
        raise NotImplementedError("_motor_config: Implement in a derived class")

    @property
    def goal(self) -> revolutions_per_minute:
        """Get the current velocity goal in RPM.

        Returns:
            revolutions_per_minute: Target RPM for the PID controller.
        """
        return self._velocity_goal

    @property
    def tolerance(self) -> revolutions_per_minute:
        """Get the velocity tolerance in RPM.

        The mechanism is considered "ready" when velocity is within
        [goal - tolerance, goal + tolerance].

        Returns:
            revolutions_per_minute: Allowable error from goal.
        """
        return self._velocity_tolerance

    @property
    def velocity_in_rpm(self) -> revolutions_per_minute:
        """Get current motor velocity in revolutions per minute.

        Converts velocity_in_rps to RPM via WPILib conversion.

        Returns:
            revolutions_per_minute: Current velocity.
        """
        return radians_per_second_to_rotations_per_minute(self.velocity_in_rps)

    @property
    def velocity_in_rps(self) -> radians_per_second:
        """Get current motor velocity in radians per second.

        Abstract property implemented by subclass. Typically reads from encoder
        velocity via _encoder.get_velocity().

        Returns:
            radians_per_second: Current angular velocity.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("velocity_in_rps: Implement in a derived class")

    @property
    def position(self) -> radians:
        """Get current motor position in radians.

        Abstract property implemented by subclass. Typically reads from encoder
        position via _encoder.get_position().

        Returns:
            radians: Current angular position (accumulated distance).

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("position: Implement in a derived class")

    @property
    def active(self) -> bool:
        """Check if mechanism is active (has non-zero goal or is still spinning).

        Used to determine if the mechanism should be powered vs idle.

        Returns:
            bool: True if goal RPM is non-zero AND mechanism is rotating,
                False if stopped or goal is zero.

        Example:
            if subsystem.active:
                # Mechanism is running
            else:
                # Motor can be de-energized
        """
        return self.goal != 0.0 and self.velocity_in_rps != 0.0

    @property
    def not_ready(self) -> str:
        """Get readiness status string describing deviation from goal.

        Returns empty string if mechanism is at goal within tolerance.
        Otherwise returns a descriptive message about the deviation.

        Returns:
            str: Empty string if ready, or status message like
                "under velocity goal: 3000 < 3500" or
                "above velocity goal: 3700 > 3500"

        Example:
            if not command.is_ready and subsystem.not_ready:
                Logger.record_output("Status", subsystem.not_ready)
        """
        velocity = self.velocity_in_rpm
        if velocity < self.goal - self.tolerance:
            return f"under velocity goal: {velocity} < {self.goal}"

        if velocity > self.goal + self.tolerance:
            return f"above velocity goal: {velocity} > {self.goal}"

        return ""  # Ready (within tolerance)

    def _set_velocity_goal(self, rpm: revolutions_per_minute, rpm_tolerance: revolutions_per_minute | None) -> None:
        """Set the velocity goal and tolerance for the PID controller.

        Abstract method implemented by subclass. Typically updates _velocity_goal,
        _velocity_tolerance, and calls PID setpoint method.

        Args:
            rpm (revolutions_per_minute): Target RPM to set.
            rpm_tolerance (Optional[revolutions_per_minute]): Tolerance in RPM.
                If None, maintain current tolerance.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.
        """
        raise NotImplementedError("_set_velocity_goal: Implement in a derived class")

    def stop(self) -> None:
        """Stop the motor immediately (zero velocity goal).

        Called when mechanism should stop (e.g., on disable or explicit stop command).
        Sets velocity goal to 0 and disables motor power.
        """
        logger.info("%s: Stop command was called", self._name)
        self._set_velocity_goal(0, 0)
        self._motor.disable()

    # TODO: Add periodic support for fault detection and reporting

    def periodic(self) -> None:
        """Update motor inputs and log telemetry each cycle.

        Called each periodic cycle (default 20 mS) once subsystem is initialized.
        Performs:
        1. Reads motor state via update_inputs()
        2. Logs sensor data and goal via pykit Logger
        3. Records performance timing with LogTracer
        4. Records dashboard telemetry at throttled rate

        Uses robot counter to throttle dashboard updates to ~100 mS
        (except when match is enabled, then ~30 mS).
        """
        if self.is_initialized:
            LogTracer.reset_outer(f"{self.get_name()} periodic")
            try:
                # Read motor state from hardware
                self.update_inputs(self._inputs)

                # Log to pykit for AdvantageScope
                Logger.process_inputs(self.get_name(), self._inputs)
                LogTracer.record("UpdateInputs")

                # Record goal, current, and tolerance to Logger
                Logger.record_output(f"{self._long_name}/goal", self.goal)
                Logger.record_output(f"{self._long_name}/current", self.velocity_in_rpm)
                Logger.record_output(f"{self._long_name}/tolerance", self.tolerance)

                # Update dashboard telemetry throttled (slower than periodic)
                counter = self._robot.counter
                if counter % 100 == 0 or (self._robot.counter % 31 == 0 and self._robot.is_enabled()):
                    self.dashboard_periodic()

                LogTracer.record("UpdateDashboard")

            finally:
                LogTracer.record_total()

    def telemetry_init(self) -> None:
        """Initialize dashboard telemetry for this subsystem.

        Called once at startup. Goal, current RPM and tolerance are recorded every
        periodic by ``periodic()``; applied voltage and supply current are added by
        ``dashboard_periodic()``. Override to add custom entries.
        """
        super().telemetry_init()

    def dashboard_periodic(self) -> None:
        """Record motor electrical state for dashboards.

        Called periodically (throttled via counter). Records applied voltage and
        supply current through the pykit Logger. Override to customize for a
        specific mechanism.
        """
        super().dashboard_periodic()
        Logger.record_output(f"{self._long_name}/voltage", self._inputs.mechanism_applied_voltage)
        Logger.record_output(f"{self._long_name}/supply_current", self._inputs.mechanism_supply_current)

    def update_inputs(self, inputs: RpmMechanismIO.RpmMechanismIOInputs) -> None:
        """Read motor state and populate logging struct.

        Abstract method implemented by subclass. Should read current velocity,
        position, applied voltage, supply current, and other relevant state,
        then populate the RpmMechanismIOInputs struct for logging/replay.

        Args:
            inputs (RpmMechanismIOInputs): Struct to populate with current hardware state.

        Raises:
            NotImplementedError: Always; must be implemented in subclass.

        Example:
            def update_inputs(self, inputs):
                inputs.mechanism_velocity = self._encoder.get_velocity()
                inputs.mechanism_position = self._encoder.get_position()
                inputs.mechanism_applied_voltage = self._motor.get_applied_output() * self._motor.get_bus_voltage()
                inputs.mechanism_supply_current = self._motor.get_output_current()
        """
        raise NotImplementedError("update_inputs: Implement in a derived class")

    # ====================================================================
    # Simulation Support
    # ====================================================================

    def update_sim(self, now: float | int, tm_diff: float | int) -> amperes | None:
        """Update simulation state for this motor mechanism.

        Called by PhysicsEngine during simulation (~10 mS intervals) to update
        the simulated motor state based on commanded voltage. Called after
        CommandScheduler simulation_periodic, so PID outputs are available.

        Simulates:
        1. Motor physics (velocity changes based on applied voltage)
        2. Current draw (returned to PhysicsEngine for battery voltage calculation)

        Args:
            now (float): Current simulation time in seconds (unused).
            tm_diff (float): Time since last update_sim call in seconds (~0.010s).

        Returns:
            Optional[amperes]: Motor current draw in amperes for battery simulation,
                or None if not applicable. PhysicsEngine sums these for BatterySim.

        Note:
            Only runs if robot is enabled AND sim_motor is initialized.
            Calls sim_motor.iterate() to update simulated motor state.
        """
        if self._robot.is_enabled() and self._sim_motor is not None:
            # Get battery voltage for motor simulation
            voltage = RoboRioSim.get_vin_voltage()

            # Update simulated motor based on current control command
            self._sim_motor.iterate(self.velocity_in_rpm, voltage, tm_diff)

            # Return simulated current draw for battery drain
            return self._sim_motor.get_motor_current()
        return None

    # ====================================================================
    # SysID Support (System Identification)
    # ====================================================================

    def _log_motor(self, log: SysIdRoutineLog) -> None:
        """Log motor state for SysID characterization.

        Called by SysIdRoutine during quasistatic and dynamic tests to record
        motor responses. Data is saved to a log file for analysis by SysID tooling.

        Logs:
        1. Motor position (encoder rotations)
        2. Motor velocity (encoder speed)
        3. Applied voltage (from motor output)

        Args:
            log (SysIdRoutineLog): Logger object to record motor state.

        Note:
            Called automatically by SysIdRoutine; teams don't call directly.
        """
        (
            log.motor(self.get_name())
            .position(self._encoder.get_position().get())
            .velocity(self._encoder.get_velocity().get())
            .voltage(self._motor.get_applied_output().get() * self._motor.get_bus_voltage().get())
        )

    def _set_voltage(self, voltage: volts) -> None:
        """Set motor voltage for SysID testing.

        Called by SysIdRoutine to apply test voltages during characterization.
        Logs the voltage change for visibility.

        Args:
            voltage (volts): Voltage to apply to motor (-12 to +12V typical).
        """
        if voltage != self._motor.get_applied_output().get():
            logger.info(f"{self.get_name()}: Setting voltage to {voltage}")
            self._motor.set_voltage(voltage)

    def sys_id_quasistatic(self, direction: SysIdRoutine.Direction) -> Command:
        """Create a quasistatic SysID characterization command.

        Runs a slow voltage ramp (quasistatic) in the specified direction to
        characterize motor response at steady-state (minimal acceleration effects).
        Generates a .json file with motor parameters for tuning.

        Args:
            direction (SysIdRoutine.Direction): FORWARD or REVERSE test direction.

        Returns:
            Command: Quasistatic test command to schedule.

        Example:
            # Set up button to run quasistatic test
            def configure_button_bindings(self):
                self.operator_controller.a().on_true(
                    self.shooter.sys_id_quasistatic(SysIdRoutine.Direction.FORWARD)
                )

        See Also:
            sys_id_dynamic: Fast ramp test to characterize acceleration
        """
        return self._sysid_routine.quasistatic(direction)

    def sys_id_dynamic(self, direction: SysIdRoutine.Direction) -> Command:
        """Create a dynamic SysID characterization command.

        Runs a fast voltage step (dynamic) in the specified direction to
        characterize motor response during acceleration. Captures transient behavior.
        Generates a .json file with motor parameters for tuning.

        Args:
            direction (SysIdRoutine.Direction): FORWARD or REVERSE test direction.

        Returns:
            Command: Dynamic test command to schedule.

        Example:
            # Set up button to run dynamic test
            def configure_button_bindings(self):
                self.operator_controller.b().on_true(
                    self.shooter.sys_id_dynamic(SysIdRoutine.Direction.FORWARD)
                )

        See Also:
            sys_id_quasistatic: Slow ramp test for steady-state characterization
        """
        return self._sysid_routine.dynamic(direction)
