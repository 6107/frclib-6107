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
"""
Swerve Drive Subsystem Module

This module implements the drive subsystem for a 4-wheel swerve drive robot base-class. Specific
vendor implementations (CTRE, REV) are derived from this class. It provides comprehensive control
over swerve module states, robot pose estimation with vision
support, and system identification capabilities.

The DriveSubsystem manages:
- Four swerve modules (front-left, front-right, back-left, back-right)
- Pose estimation and odometry using gyro and module encoders
- Vision-based pose corrections via Kalman filter
- Field-relative and robot-relative drive modes
- Slew rate limiting for smooth acceleration control
- SysId characterization for drive, steer, and rotation control loops
- Simulation support with field boundary constraints

Key Constants:
    SwerveModuleStates: Type alias for sequence of SwerveModuleState objects
"""

import logging
from collections import OrderedDict
from typing import Optional, Sequence, Tuple, TYPE_CHECKING

from commands2 import Command, Subsystem
from commands2.sysid import SysIdRoutine
from phoenix6 import SignalLogger, swerve, units, utils
from wpilib import DriverStation, Field2d, Notifier, RobotBase, RobotController, SmartDashboard
from wpilib.sysid import SysIdRoutineLog
from wpimath.filter import SlewRateLimiter
from wpimath.geometry import Pose2d, Rotation2d, Rotation3d
from wpimath.geometry import Pose3d
from wpimath.kinematics import ChassisSpeeds, SwerveDrive4Kinematics, SwerveModulePosition, SwerveModuleState
from wpimath.units import degrees, meters_per_second, radians_per_second, seconds

from lib_6107.pykit.autolog import autolog_output
from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer
from lib_6107.subsystems.constants import DriveConstants
from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.pykit.swervedrive_io import SwerveModuleIO
from lib_6107.util.field import Field

if TYPE_CHECKING:
    from lib_6107.robotcontainer import RobotContainer

# TODO: This value needs to be tested. Perform the following on a real robot
#
# Measuring Overshoot
# Implement a Control Loop:
#   You cannot simply apply constant power until the target angle is reached, as the robot needs time to decelerate
#   and will inevitably overshoot. A simple Proportional (P) loop is the standard starting point for FRC teams.
#   The motor power is made proportional to the difference between the target angle and the current angle.
#
#      Formula (simplified P-loop): motorPower = (targetAngle - currentAngle) * kP
#      kP is a constant you tune to get the desired performance.
#
# Log Data:
#   Use your FRC development environment (e.g., WPILib) to log the robot's current gyro angle and the target
#   angle to a file or SmartDashboard/Shuffleboard.
#
# Perform a Test Turn:
#   Command your robot to turn to a specific, significant angle (e.g., 90 degrees) using the P-loop,
#   and log the data during the process.
#
# Analyze the Data:
#   After the test, view the logged data in a graph or spreadsheet.
# Target Angle:
#   The desired final angle (e.g., 90 degrees).
#
# Peak Angle:
#   The maximum angle the robot reaches during the turn before it starts correcting back towards the target.
#
# Calculate Overshoot:
#   The difference between the peak angle and the target angle is the overshoot.
#
# Overshoot = Peak Angle - Target Angle
#
# Correcting Overshoot
#
# The primary method for reducing overshoot is tuning your control loop.
#
# Adjust kP:
#   If your robot consistently overshoots significantly, your kP value is likely too high. Lowering it
#   will make the turn slower but more accurate.
#
# Add Derivative (D) control:
#   Implementing a full PID loop can help. The derivative term (kD) dampens the system by applying a
#   counter-force based on how fast the error is changing (i.e., the robot's turn rate), which helps
#   slow the robot down as it approaches the target.
#
# Slow Down Turns:
#   As a simple fix, reducing the maximum motor power or speed used for turns will also reduce overshoot,
#   though it makes the robot slower overall.
#
# Ensure Proper Calibration:
#   Make sure the gyro is stationary during its initial calibration phase (when the robot code starts)
#   to minimize drift and baseline errors.
#

SwerveModuleStates = Sequence[SwerveModuleState]

logger = logging.getLogger(__name__)


# @autologgable_output
class DriveSubsystem(Subsystem):
    """
    Swerve Drive Subsystem for 4-wheel drive FRC robot.

    This subsystem manages a 4-wheel independent swerve drive system with integrated gyro,
    odometry, vision support, and SysId characterization capabilities. It supports both
    field-relative and robot-relative driving modes with joystick input filtering.

    Attributes:
        vision_odometry (bool): Flag to enable/disable vision-based odometry corrections
        field_relative (bool): Current drive mode (True for field-relative, False for robot-relative)
        last_heading (Rotation2d): Last recorded heading from gyro
        last_heading_timestamp (seconds): Timestamp of the last heading measurement
        x_drive_limiter (SlewRateLimiter): Slew rate limiter for X-axis acceleration
        y_drive_limiter (SlewRateLimiter): Slew rate limiter for Y-axis acceleration
        turn_limiter (SlewRateLimiter): Slew rate limiter for rotational acceleration
        apply_robot_speeds (swerve.requests.ApplyRobotSpeeds): Phoenix6 request for applying robot-relative speeds

    Class Attributes:
        _SIM_LOOP_PERIOD (units.second): Simulation update period (4 ms for faster convergence)
        _BLUE_ALLIANCE_PERSPECTIVE_ROTATION (Rotation2d): Forward direction for blue alliance (0°)
        _RED_ALLIANCE_PERSPECTIVE_ROTATION (Rotation2d): Forward direction for red alliance (180°)
    """
    _SIM_LOOP_PERIOD: units.second = 0.004  # 4 ms

    _BLUE_ALLIANCE_PERSPECTIVE_ROTATION = Rotation2d.fromDegrees(0)
    """Blue alliance sees forward as 0 degrees (toward red alliance wall)"""
    _RED_ALLIANCE_PERSPECTIVE_ROTATION = Rotation2d.fromDegrees(180)
    """Red alliance sees forward as 180 degrees (toward blue alliance wall)"""

    def __init__(self, consts: DriveConstants,
                 modules: OrderedDict[str, SwerveModuleIO],
                 container: RobotContainer):
        """
        Initialize the Drive Subsystem.

        Sets up all swerve modules, gyro sensor, slew rate limiters, and SysId routines.
        Configures Phoenix6 swerve drive requests with deadband settings. In simulation mode,
        starts the simulation thread for physics updates.

        :param consts: Swerve drivetrain constants from tuner
        :param modules: List of swerve module objects (4 modules in order: FL, FR, BL, BR)
        :param container: RobotContainer reference for robot state and constants
        :type container: RobotContainer
        """
        Subsystem.__init__(self)

        self._container = container
        self._robot = container.robot
        self._period: seconds = container.robot.period
        self._field: Field = container.field
        self._physics_controller = None
        self._is_simulation = RobotBase.isSimulation()

        # IMU
        self._gyro: Gyro = consts.gyro

        # Camera/localizer defaults
        self.vision_odometry = False
        self.field_relative = False  # Assume robot-relative to start with

        self._last_pose: Optional[Pose2d] = None
        self._field_speeds = ChassisSpeeds()

        self.last_heading: Rotation2d = Rotation2d()
        self.last_heading_timestamp: seconds = 0.0

        self._swerve_modules: OrderedDict[str, SwerveModuleIO] = modules
        self._expected_swerve_states = (SwerveModuleState(), SwerveModuleState(),
                                        SwerveModuleState(), SwerveModuleState())

        # Positions/pose for access via pykit
        self._last_module_positions = self.get_module_positions()  # TODO: Do we use this? From westwood

        self._is_field_centric = True

        # Slew rate filter variables and limiters for controlling lateral acceleration. This is only used
        # in teleop mode. Each input requires its own limiter.
        self.x_drive_limiter = SlewRateLimiter(consts.DriveSlewRate)
        self.y_drive_limiter = SlewRateLimiter(consts.DriveSlewRate)
        self.turn_limiter = SlewRateLimiter(consts.RotationSlewRate)

        # The next attributes are set depending on if vision is unsupported for tracking the robot pose
        self._network_table_inst = None

        # Check for any alliance change and return our initial pose
        self.pose = self._alliance_change(container.is_red_alliance,
                                          container.alliance_location)

        #  The call to 'addVisionMeasurement' can optionally have a standard deviation value, and
        #  it remains in effect until another measurement std deviation is provided. We will start
        #  with a high confidence since autonomous mode is heavily reliant on vision, and we
        #  expect to traverse the 'bump' at least twice.
        self.set_vision_measurement_std_devs(consts.VisionStdDevs)

        # Register for any changes in alliance before the match starts
        container.register_alliance_change_callback(self._alliance_change)

        self._sim_notifier: Notifier = None
        self._last_sim_time: units.second = 0.0

        self._has_applied_operator_perspective = False
        """Keep track if we've ever applied the operator perspective before or not"""

        # Swerve request to apply during path following
        self.apply_robot_speeds = swerve.requests.ApplyRobotSpeeds()

        # Swerve requests to apply during SysId characterization
        self._translation_characterization = swerve.requests.SysIdSwerveTranslation()
        self._steer_characterization = swerve.requests.SysIdSwerveSteerGains()
        self._rotation_characterization = swerve.requests.SysIdSwerveRotation()

        #######################################################
        # SysID Routines and functionality    TODO: Need to dig into this and get it working
        self._sys_id_routine_translation = SysIdRoutine(
            SysIdRoutine.Config(
                # Use default ramp rate (1 V/s) and timeout (10 s)
                # Reduce dynamic voltage to 4 V to prevent brownout
                stepVoltage=consts.TranslationStepVoltage,
                # Log state with SignalLogger class
                recordState=lambda state: SignalLogger.write_string(
                    "SysIdTranslation_State", SysIdRoutineLog.stateEnumToString(state)
                )
                                          and None,
            ),
            SysIdRoutine.Mechanism(
                lambda output: self.set_control(self._translation_characterization.with_volts(output)),
                lambda log: None,
                self,
            ),
        )
        """
        SysId routine for characterizing translation. This is used to find PID gains for 
        the drive motors.
        """
        self._sys_id_routine_steer = SysIdRoutine(
            SysIdRoutine.Config(
                # Use default ramp rate (1 V/s) and timeout (10 s)
                # Use dynamic voltage of 7 V
                stepVoltage=consts.SteerStepVoltage,
                # Log state with SignalLogger class
                recordState=lambda state: SignalLogger.write_string(
                    "SysIdSteer_State", SysIdRoutineLog.stateEnumToString(state)
                )
                                          and None,
            ),
            SysIdRoutine.Mechanism(
                lambda output: self.set_control(self._steer_characterization.with_volts(output)),
                lambda log: None,
                self,
            ),
        )
        """
        SysId routine for characterizing steer. This is used to find PID gains for 
        the steer motors.
        """
        self._sys_id_routine_rotation = SysIdRoutine(
            SysIdRoutine.Config(
                # This is in radians per second², but SysId only supports "volts per second"
                rampRate=consts.RotationRampRate,
                # Use dynamic voltage of 7 V
                stepVoltage=consts.RotationStepVoltage,
                # Use default timeout (10 s)
                # Log state with SignalLogger class
                recordState=lambda state: SignalLogger.write_string(
                    "SysIdSteer_State", SysIdRoutineLog.stateEnumToString(state)
                )
                                          and None,
            ),
            SysIdRoutine.Mechanism(
                lambda output: (
                                   # output is actually radians per second, but SysId only supports "volts"
                                   self.set_control(self._rotation_characterization.with_rotational_rate(output)),
                                   # also log the requested output for SysId
                                   SignalLogger.write_double("Rotational_Rate", output),
                               )
                               and None,
                lambda log: None,
                self,
            ),
        )
        """
        SysId routine for characterizing rotation.
        
        This is used to find PID gains for the FieldCentricFacingAngle HeadingController.
        See the documentation of swerve.requests.SysIdSwerveRotation for info on importing the 
        log to SysId.
        
        The SysId routine to test
        """
        self._sys_id_routine_to_apply = self._sys_id_routine_translation

        if self._is_simulation:
            self._start_sim_thread()

    @property
    def robot(self) -> 'MyRobot':
        """
        Get reference to the main robot object.

        :returns: Robot instance
        :rtype: MyRobot
        """
        return self._robot

    @property
    def container(self) -> 'RobotContainer':
        """
        Get reference to the RobotContainer.

        :returns: RobotContainer instance
        :rtype: RobotContainer
        """
        return self._container

    @property
    def is_initialized(self) -> bool:
        """
        Check if the drive subsystem has completed initialization.

        :returns: True if subsystem is fully initialized
        :rtype: bool
        """
        return self._initialized

    def sys_id_quasistatic(self, direction: SysIdRoutine.Direction) -> Command:
        """
        Runs the SysId Quasistatic test in the given direction for the routine
        specified by self.sys_id_routine_to_apply.

        :param direction: Direction of the SysId Quasistatic test
        :type direction: SysIdRoutine.Direction
        :returns: Command to run
        :rtype: Command
        """
        return self._sys_id_routine_to_apply.quasistatic(direction)

    def sys_id_dynamic(self, direction: SysIdRoutine.Direction) -> Command:
        """
        Runs the SysId Dynamic test in the given direction for the routine
        specified by self.sys_id_routine_to_apply.

        :param direction: Direction of the SysId Dynamic test
        :type direction: SysIdRoutine.Direction
        :returns: Command to run
        :rtype: Command
        """
        return self._sys_id_routine_to_apply.dynamic(direction)

    def _start_sim_thread(self):
        """
        Start the simulation thread for physics updates.

        Initializes and runs a periodic notifier that updates the simulation state at
        _SIM_LOOP_PERIOD intervals (4 ms). This ensures that physics simulations run faster
        than the default CommandScheduler period, allowing PID gains to behave more realistically.
        """

        def _sim_periodic():
            current_time = utils.get_current_time_seconds()
            delta_time = current_time - self._last_sim_time
            self._last_sim_time = current_time

            # use the measured time delta, get battery voltage from WPILib
            self.update_sim_state(delta_time, RobotController.getBatteryVoltage())

        # Run simulation at a faster rate so PID gains behave more reasonably
        self._last_sim_time = utils.get_current_time_seconds()
        self._sim_notifier = Notifier(_sim_periodic)
        self._sim_notifier.startPeriodic(self._SIM_LOOP_PERIOD)

    def add_vision_measurement(self, vision_robot_pose: Pose2d | Pose3d, timestamp: units.second,
                               vision_measurement_std_devs: tuple[float, float, float] | None = None):
        """
        Adds a vision measurement to the Kalman Filter. This will correct the
        odometry pose estimate while still accounting for measurement noise.

        Note that the vision measurement standard deviations passed into this method
        will continue to apply to future measurements until a subsequent call to
        set_vision_measurement_std_devs or this method.

        :param vision_robot_pose:           The pose of the robot as measured by the vision camera.
        :type vision_robot_pose:            Pose2d
        :param timestamp:                   The timestamp of the vision measurement in seconds.
        :type timestamp:                    second
        :param vision_measurement_std_devs: Standard deviations of the vision pose measurement
                                            in the form [x, y, theta]ᵀ, with units in meters
                                            and radians.
        :type vision_measurement_std_devs:  tuple[float, float, float] | None
        """
        raise NotImplementedError("Implement in your derived class")

    def sample_pose_at(self, timestamp: units.second) -> Pose2d | None:
        """
        Return the pose at a given timestamp, if the buffer is not empty.

        :param timestamp: The timestamp of the pose in seconds.
        :type timestamp: second
        :returns: The pose at the given timestamp (or None if the buffer is empty).
        :rtype: Pose2d | None
        """
        raise NotImplementedError("Implement in your derived class")

    @property
    def counter(self) -> int:
        return self._robot.counter

    @property
    def field2d(self) -> Field2d:
        return self._robot.field

    @property
    def gyro(self) -> Gyro:
        return self._gyro

    # ###########################################
    # # PathPlanner Support (TODO: NOT FULLY SUPPORTED YET ENABLED - COMMENTED OUT IN INIT)
    # def runClosedLoop(self, speeds: ChassisSpeeds,
    #                   _feedForwards: Optional[DriveFeedforwards] = None):
    #     wheelSpeeds = self.kinematics.toWheelSpeeds(speeds)
    #     self.runClosedLoopParameters(wheelSpeeds.left, wheelSpeeds.right)
    #
    if False:
        # TODO: Need these (look up pykit sysID in the pathplanner.py file?
        def runClosedLoopParameters(self, left_speed: float, right_speed: float):
            from numpy import sign

            left_rad_per_s = left_speed / WHEEL_RADIUS
            right_rad_per_s = right_speed / WHEEL_RADIUS

            Logger.recordOutput("Drive/LeftSetpoint", left_rad_per_s)
            Logger.recordOutput("Drive/RightSetpoint", right_rad_per_s)

            left_ff = self.kS * sign(left_rad_per_s) + self.kV * left_rad_per_s
            right_ff = self.kS * sign(right_rad_per_s) + self.kV * right_rad_per_s

            self._inputs.setVelocity(left_rad_per_s, right_rad_per_s, left_ff, right_ff)

        def runOpenLoop(self, left_v: float, right_v: float) -> None:
            self._inputs.setVoltage(left_v, right_v)

        def sysIdQuasistatic(self, direction: SysIdRoutine.Direction):
            return self.sysid.quasistatic(direction)

        def sysIdDynamic(self, direction: SysIdRoutine.Direction):
            return self.sysid.dynamic(direction)

    def _alliance_change(self, is_red: bool, location: int) -> Pose2d:
        """
        Change in alliance occurred before match started. If simulation is
        supported, then 'physics.py' handles this.
        """
        if not self._is_simulation:
            return Pose2d(0, 0, 0)

        initial_pose = Pose2d(0, 0, Rotation2d.fromDegrees(self.gyro.yaw))
        if location in (1, 2, 3):
            # Use test subsystem settings if simulation
            initial_pose = self._robot.simulation_constants.RED_TEST_POSE[location] if is_red \
                else self._robot.simulation_constants.BLUE_TEST_POSE[location]

        self.pose = initial_pose
        return initial_pose

    def dashboard_initialize(self) -> None:
        """
        Configure the SmartDashboard for this subsystem
        """
        self.gyro.dashboard_initialize()

    def dashboard_periodic(self) -> None:
        """
        Called from periodic function to update dashboard elements for this subsystem
        """
        if self._is_simulation and self._last_pose is not None:
            SmartDashboard.putNumber("Drivetrain/x", self._last_pose.x)
            SmartDashboard.putNumber("Drivetrain/y", self._last_pose.y)
            SmartDashboard.putNumber("Drivetrain/heading", self._last_pose.rotation().degrees())

        self.gyro.dashboard_periodic()

    def periodic(self) -> None:
        # Note: The gyro is its own subsystem and its pykit I/O is handle by the gyro
        #       periodic function
        if not self.is_initialized:
            return

        LogTracer.resetOuter("DriveSubsystemPeriodic")
        self._last_module_positions = self.get_module_positions()

        LogTracer.record("StateUpdate")

        # Periodically try to apply the operator perspective.
        # If we haven't applied the operator perspective before, then we should apply it regardless of DS state.
        # This allows us to correct the perspective in case the robot code restarts mid-match.
        # Otherwise, only check and apply the operator perspective if the DS is disabled.
        # This ensures driving behavior doesn't change until an explicit disable event occurs during testing.
        if not self._has_applied_operator_perspective or DriverStation.isDisabled():
            alliance_color = DriverStation.getAlliance()
            if alliance_color is not None:
                self.set_operator_perspective_forward(
                    self._RED_ALLIANCE_PERSPECTIVE_ROTATION
                    if alliance_color == DriverStation.Alliance.kRed
                    else self._BLUE_ALLIANCE_PERSPECTIVE_ROTATION
                )
                self._has_applied_operator_perspective = True

        # Update gyro first. We use to have this as a subsystem, but now it is not and we
        # call it here so it is up to date
        self.gyro.periodic()  # This call will log the gyro inputs for us...

        self.last_heading = Rotation2d(self.gyro.inputs.yaw)
        self.last_heading_timestamp = self.gyro.inputs.yaw_timestamp

        for _label, module in self._swerve_modules.items():
            module.periodic()

        LogTracer.record("ModulesPeriodic")
        LogTracer.recordTotal()

        # Update the odometry in the periodic block
        # TODO: For phoenix6 library, just need to pass in vision measurements
        self._last_pose = self.pose

        if self._last_pose is not None:
            self.field2d.setRobotPose(self._last_pose)

        # Update SmartDashboard for this subsystem at a rate slower than the period
        counter = self._robot.counter
        if counter % 100 == 0 or (self._robot.counter % 23 == 0 and
                                  self._robot.isEnabled()):
            self.dashboard_periodic()

        LogTracer.record("DashboardUpdate")
        LogTracer.recordTotal()

    def sim_init(self, physics_controller: 'PhysicsInterface') -> None:
        """
        Initialize any simulation only needed parameters.

        This is called from the physic's __init__ function
        """
        self._physics_controller = physics_controller

        for position, module in self._swerve_modules.items():
            if hasattr(module, 'sim_init'):
                module.sim_init(physics_controller)
            else:
                logger.warning(f"Module {module} does not have a sim_init method")

        self.gyro.sim_init(physics_controller)

    def update_sim(self, now: float, tm_diff: float) -> None:
        """Update robot physics simulation for the current time step."""

        for _position, module in self._swerve_modules.items():
            if hasattr(module, 'update_sim'):
                module.update_sim(now, tm_diff)
            else:
                logger.warning(f"Module {module} does not have an update_sim method")

    def simulationPeriodic(self) -> None:
        """
        This method is called periodically by the CommandScheduler (after the periodic
        function). It is useful for updating subsystem-specific state that needs to be
        maintained for simulations, such as for updating simulation classes and setting
        simulated sensor readings.

        Unlike the physics 'update_sim', it is not called with the current time (now)
        or the amount of time since 'update_sim' was called (tm_diff).  It is called
        just after the 'periodic' call and before the 'update_sim' is called. One other
        'important' difference is 'update_sim' is called at a period >= 10 ms instead
        of the default 20 mS for the CommandScheduler's simulationPeriodic (this function).
        """
        if not self.is_initialized:
            return

        LogTracer.resetOuter(f"{self.getName()}-simulationPeriodic")

        # now, tm_diff = kwargs["now"], kwargs["tm_diff"]
        amperes_used = 0.0  # TODO: Support in future

        for _position, module in self._swerve_modules.items():
            if hasattr(module, 'simulationPeriodic'):
                module.simulationPeriodic()
            else:
                logger.warning(f"Module {module} does not have a simulationPeriodic method")

        # Since simulation, limit it to the field of play.
        pose = self.pose
        # self.gyro.sim_yaw = pose.rotation().degrees()     # Not saving this yet.

        # Limit it to the field size (manually)
        robot_x_offset = self.container.robot_x_width / 2
        robot_y_offset = self.container.robot_y_width / 2

        x, y = pose.x, pose.y

        if x < robot_x_offset or x > self._field.field_length - robot_x_offset or \
                y < robot_y_offset or y > self._field.field_width - robot_y_offset:
            x = min(self._field.field_length - robot_x_offset, max(robot_x_offset, x))
            y = min(self._field.field_width - robot_y_offset, max(robot_y_offset, y))

            if x != pose.x or y != pose.y:
                self.pose = Pose2d(x, y, pose.rotation())
        LogTracer.recordTotal()

    # def update_sim(self, now: float, tm_diff: float) -> None:
    #     """
    #     Called when the simulation parameters for the program need to be updated.
    #     This function is called from the '_simulationPeriodic' function of the
    #     robotpy core routine and is called at a period >= 10 mS. Note that the
    #     CommandScheduler also has a 'simulationPeriodic' function that it calls
    #     into all Command2 based subsystems at its update period which has a
    #     default rate of 20 mS.
    #
    #     This is called 'after' the CommandScheduler's 'simulationPeriodic', so if
    #     that function uses pykit's logging method, you should use those values in
    #     your simulation.
    #
    #     :param now:     The current time as a float
    #     :param tm_diff: The amount of time that has passed since the last
    #                     time that this function was called
    #     """
    #         if not self.is_initialized:
    #             return

    @property
    def heading(self) -> Rotation2d:
        return self.pose.rotation()

    @property
    def pose(self) -> Pose2d:
        """
        Returns the currently-estimated pose of the robot.
        """
        return self.get_pose()

    @pose.setter
    def pose(self, pose: Pose2d) -> None:
        # Update the drivetrain
        self.reset_pose(pose)

    @autolog_output(key="Robot/Pose")
    def get_pose(self) -> Pose2d:
        return self.get_state().pose

    @autolog_output(key="drive/fieldSpeeds")
    def chassis_speeds(self) -> ChassisSpeeds:
        return self._field_speeds

    @autolog_output(key="drive/swerve/expected")
    def get_swerve_expected_state(self) -> Tuple[
        SwerveModuleState, SwerveModuleState, SwerveModuleState, SwerveModuleState]:
        return self._expected_swerve_states

    # if USE_PYKIT:
    #     # TODO: FOLLOWING needed to support swerve drive.
    #     @autolog_output(key="Drive/LeftPosition")
    #     def getLeftPosition(self) -> float:
    #         return self._inputs.leftPositionRad * driveconstants.kWheelRadius
    #
    #     @autolog_output(key="Drive/RightPosition")
    #     def getRightPosition(self) -> float:
    #         return self._inputs.rightPositionRad * driveconstants.kWheelRadius
    #
    #     @autolog_output(key="Drive/LeftVelocity")
    #     def getLeftVelocity(self) -> float:
    #         return self._inputs.leftVelocityRadPerSec * driveconstants.kWheelRadius
    #
    #     @autolog_output(key="Drive/RightVelocity")
    #     def getRightVelocity(self) -> float:
    #         return self._inputs.rightVelocityRadPerSec * driveconstants.kWheelRadius

    def stop(self):
        if False:
            pass  # TODO: self.runOpenLoop(0, 0)    # TODO: Look at pykit sysid work

        self.arcade_drive(0, 0, field_relative=True)

    def arcade_drive(self, speed: meters_per_second, rot: radians_per_second, field_relative: Optional[bool] = False,
                     assume_manual_input: bool = False) -> None:
        self.drive(speed, 0, rot, square=assume_manual_input, field_relative=field_relative)

    def rotate(self, rotation: radians_per_second) -> None:
        """
        Rotate the robot in place, without moving laterally (for example, for aiming)

        :param rotation: rotational speed
        """
        self.arcade_drive(0, rotation, field_relative=True)

    def drive(self, x_speed: meters_per_second, y_speed: meters_per_second,
              rotation: radians_per_second, field_relative: Optional[bool] = False,
              square: Optional[bool] = False) -> None:
        """
        Method to drive the robot using joystick info.

        :param x_speed:        Speed of the robot in the x direction (forward).
        :param y_speed:        Speed of the robot in the y direction (sideways).
        :param rotation:       Angular rate of the robot.
        :param field_relative: Whether the provided x and y speeds are relative to the field.
        :param square:         Whether to square the inputs (useful for manual control)
        """
        if square:
            raise NotImplementedError("drive: Look at 2025 code if you need this")

        # Scale is used during development      # TODO: Condition to skip/ignore in competition
        scale_factor = self.drive_scale_factor
        max_speed = self._container.max_speed  # This is already adjusted by the scaling factor

        if field_relative:
            robot_speeds = ChassisSpeeds.fromFieldRelativeSpeeds(x_speed, y_speed,
                                                                 rotation, self.gyro.heading)
            x_speed = robot_speeds.vx
            y_speed = robot_speeds.vy
            rotation = robot_speeds.omega

        speeds = ChassisSpeeds.discretize(ChassisSpeeds(x_speed, y_speed, rotation),
                                          self._period)  # TODO: Pass in period here

        def adjust(rate: meters_per_second) -> meters_per_second:
            return min(max_speed, rate * scale_factor)

        speeds.vx = adjust(speeds.vx)
        speeds.vy = adjust(speeds.vy)
        speeds.omega = adjust(speeds.omega)

        # TODO: see if we can use the same as westwood here
        # request = (RobotCentric().with_velocity_x(adjust(speeds.vx)).
        #                           with_velocity_y(adjust(speeds.vy)).
        #                           with_rotational_rate(speeds.omega * scale_factor))
        #
        # self.set_control(request)

        # Update saved states
        self._field_speeds = speeds
        Logger.recordOutput("drive/swerve/commandedSpeeds", speeds)

    def apply_states(self, module_states: Tuple[
        SwerveModuleState, SwerveModuleState, SwerveModuleState, SwerveModuleState]) -> None:
        # desaturate the states
        front_left_state, front_right_state, back_left_state, back_right_state = \
            SwerveDrive4Kinematics.desaturateWheelSpeeds(module_states,
                                                         self.robot.robot_constants.MAX_WHEEL_LINEAR_VELOCITY)

        self._expected_swerve_states = (front_left_state, front_right_state,
                                        back_left_state, back_right_state)

        # TODO: Is this method ever called?  What is its purpose?

        self._swerve_modules["front-left"].apply_states(front_left_state)
        self._swerve_modules["front-right"].apply_states(front_right_state)
        self._swerve_modules["back-left"].apply_states(back_left_state)
        self._swerve_modules["back-right"].apply_states(back_right_state)

    def drive_with_pathplanner_path(self, chassis_speeds: ChassisSpeeds, feed_forward: list[float]) -> None:
        # TODO: Wire into pathplanner config and debug

        Logger.recordOutput("drive/swerve/commandedSpeeds", chassis_speeds)

        self.set_control(
            self.apply_robot_speeds
            .with_speeds(ChassisSpeeds.discretize(chassis_speeds, self._period))
            .with_wheel_force_feedforwards_x(feed_forward.robotRelativeForcesXNewtons)
            .with_wheel_force_feedforwards_y(feed_forward.robotRelativeForcesYNewtons)
        ),

    def set_module_states(self, module_states: SwerveModuleStates) -> None:
        """
        Set the module state. The modules in the sequence are always provided (and used) in the
        order when the SwerveDriveKinematics object was created. Convention is typically:

           (Front Left, Front Right, Rear Left, Rear Right)
        """
        raise NotImplementedError("Implement in your derived class")

    @property
    def drive_scale_factor(self) -> float:
        # We scale our speed down during development
        scaler = 1.0

        try:
            scaler = self._container._limit_chooser.getSelected()
            if not isinstance(scaler, (int, float)):
                logger.error(f"Invalid Drive Rate Limiter: '{scaler}")
                scaler = 0.1
            else:
                scaler = max(min(scaler, 1.0), 0.0)

        except Exception as _e:
            pass

        return scaler

    def set_motor_brake(self, brake: bool) -> None:
        raise NotImplementedError("Implement in your derived class")

    def set_straight(self) -> None:
        """
        Sets the wheels straight so we can push the robot.
        """
        raise NotImplementedError("Implement in your derived class")

    def get_module_positions(self) -> Tuple[
        SwerveModulePosition, SwerveModulePosition, SwerveModulePosition, SwerveModulePosition]:
        pos = [m.getPosition() for m in self._swerve_modules.values()]
        return pos[0], pos[1], pos[2], pos[3]

    def get_angle(self) -> degrees:
        return self.get_pose.rotation().degrees()

    @autolog_output(key="Robot/velocity")
    def get_angular_velocity(self) -> radians_per_second:
        return self.gyro.inputs.yaw_rate

    @autolog_output(key="drive/swerve/real")
    def get_module_states(self) -> Tuple[SwerveModuleState, SwerveModuleState, SwerveModuleState, SwerveModuleState]:
        return (self._swerve_modules["front-left"].getState(),
                self._swerve_modules["front-right"].getState(),
                self._swerve_modules["back-left"].getState(),
                self._swerve_modules["back-right"].getState())

    # @autolog_output(key="drive/viz/Pose3d")
    def get_robot_3d(self, pose: Pose2d, rotation: Rotation3d) -> Pose3d:
        # TODO: Can we get the 'z' component?
        #       If you are using AprilTags to determine your 3D pose on the field, this is
        #       the most direct method to get the robot's Z position.
        #
        #       Limelight: Use botpose in NetworkTables, which returns an array of [x, y, z, roll,
        #              pitch, yaw]. The 3rd element (index 2) is the Z position in meters, generally
        #              representing the height of the camera above the floor.
        #
        #       PhotonVision: Use PhotonPoseEstimator and get the bestCameraToTarget transform to
        #              calculate the robot's 3D position.

        return Pose3d(pose.X(), pose.Y(), 0.0, rotation)

    ##########################################################
    # TODO: All the following are related to team 2429 and pathplanner. These have not been tested and
    #       we may need to refactor the 'drive()' method above

    #  -------------  THINGS PATHPLANNER NEEDS  - added for pathplanner 20230218 CJH

    # def follow_pathplanner_trajectory_command(self, trajectory:PathPlannerTrajectory, is_first_path:bool):
    #     #from pathplannerlib.path import PathPlannerPath
    #     #from pathplannerlib.commands import FollowPathWithEvents, FollowPathHolonomic
    #     #from pathplannerlib.config import HolonomicPathFollowerConfig, ReplanningConfig, PIDConstants

    #     # copy of pathplannerlib's method for returning a swervecommand, with an optional odometry reset
    #     # using the first pose of the trajectory
    #     if is_first_path:
    #         reset_cmd = commands2.InstantCommand(lambda: self.pose = trajectory.getInitialTargetHolonomicPose()))
    #     else:
    #         reset_cmd = commands2.InstantCommand()

    #     # useful stuff controller.PPHolonomicDriveController, controller.PIDController, auto.FollowPathHolonomic
    #     swerve_controller_cmd = None

    #     cmd = commands2.SequentialCommandGroup(reset_cmd, swerve_controller_cmd)

    #     return cmd

    #  END PATHPLANNER STUFF
