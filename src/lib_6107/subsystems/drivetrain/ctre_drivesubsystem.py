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

This module implements the drive subsystem based on CTRE Phoenix6 swerve modules.
"""

import logging
from collections import OrderedDict
from typing import Callable, Sequence, TYPE_CHECKING

from commands2 import Command
from phoenix6 import swerve, units, utils
from phoenix6.swerve import SwerveModule
from phoenix6.swerve.requests import FieldCentric, RobotCentric
from wpilib import Notifier
from wpimath.geometry import Pose2d, Rotation2d
from wpimath.geometry import Pose3d
from wpimath.kinematics import SwerveModuleState
from wpimath.units import meters

from lib_6107.subsystems.constants import DriveConstants
from lib_6107.subsystems.drivetrain.ctre_swervedrive import CtreSwerveModule
from lib_6107.subsystems.drivetrain.drivesubsystem import DriveSubsystem
from lib_6107.subsystems.pykit.swervedrive_io import SwerveModuleIO

if TYPE_CHECKING:
    from lib_6107.robotcontainer import RobotContainer

SwerveModuleStates = Sequence[SwerveModuleState]

logger = logging.getLogger(__name__)


# @autologgable_output
class CtreDriveSubsystem(DriveSubsystem):
    """
    Swerve Drive Subsystem for 4-wheel drive FRC robot.
    """

    def __init__(self, tuner_x_subsystem: 'TunerSwerveDrivetrain',
                 consts: DriveConstants,
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
        if consts.VendorConstants.vendor != "CTRE":
            raise TypeError(f"Expected CTRE vendor constants, got {consts.VendorConstants.vendor}")

        self._tuner_x_subsystem = tuner_x_subsystem

        # The modules are created in the following order in our tuner_constants 'create_drivetrain' func
        modules: Sequence[SwerveModule] = tuner_x_subsystem.modules

        swerve_modules: OrderedDict[str, SwerveModuleIO] = OrderedDict(
            [
                ("front-left", CtreSwerveModule(modules[0], "front-left", container)),
                ("front-right", CtreSwerveModule(modules[1], "front-right", container)),
                ("back-left", CtreSwerveModule(modules[2], "back-left", container)),
                ("back-right", CtreSwerveModule(modules[3], "back-right", container))
            ])
        super().__init__(consts, swerve_modules, container)

        # Some useful requests amd constants
        max_speed = container.robot.robot_constants.MAX_SPEED
        max_angular_rate = container.robot.robot_constants.MAX_ANGULAR_VELOCITY  # 3/4 of a rotation per second max angular velocity

        # Setting up bindings for necessary control of the Phoenix6 swerve drive platform.
        # This sets a deadband for both the speed and rotation control
        #  Use open-loop control for drive motors
        self._field_centric_drive: FieldCentric = (
            FieldCentric()
            .with_deadband(max_speed * container.robot.robot_constants.JOYSTICK_DEADBAND)
            .with_rotational_deadband(max_angular_rate * container.robot.robot_constants.JOYSTICK_DEADBAND)
            .with_drive_request_type(swerve.SwerveModule.DriveRequestType.OPEN_LOOP_VOLTAGE))

        self._robot_centric_drive: RobotCentric = (
            RobotCentric()
            .with_deadband(max_speed * container.robot.robot_constants.JOYSTICK_DEADBAND)
            .with_rotational_deadband(max_angular_rate * container.robot.robot_constants.JOYSTICK_DEADBAND)
            .with_drive_request_type(swerve.SwerveModule.DriveRequestType.OPEN_LOOP_VOLTAGE))

        self._is_field_centric = True

        self._brake = swerve.requests.SwerveDriveBrake()

        self._point = swerve.requests.PointWheelsAt()

        self._forward_straight = (swerve.requests.RobotCentric().
                                  with_drive_request_type(swerve.SwerveModule.DriveRequestType.OPEN_LOOP_VOLTAGE))

        # TODO: Look into these
        logger.error("TODO: look into these")
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

    @property
    def drive_request(self) -> FieldCentric | RobotCentric:
        """
        Get the current drive request mode (field-centric or robot-centric).

        :returns: Currently active drive request
        :rtype: FieldCentric | RobotCentric
        """
        return self._field_centric_drive if self._is_field_centric else self._robot_centric_drive

    def set_field_centric_drive(self, field_centric: bool) -> None:
        """
        Set the drive mode between field-centric and robot-centric.

        Field-centric: Movement is relative to the field, with forward always away from the driver.
        Robot-centric: Movement is relative to the robot's orientation.

        :param field_centric: True for field-centric, False for robot-centric
        :type field_centric: bool
        """
        logger.info(f"Setting field centric drive to {field_centric}")
        self._is_field_centric = field_centric

    @property
    def point_at_request(self) -> swerve.requests.PointWheelsAt:
        """
        Get the point wheels request for manual wheel angle control.

        :returns: PointWheelsAt request object
        :rtype: swerve.requests.PointWheelsAt
        """
        return self._point

    @property
    def forward_straight_request(self) -> RobotCentric:
        """
        Get the forward straight request for driving in a straight line.

        :returns: RobotCentric request configured for straight movement
        :rtype: RobotCentric
        """
        return self._forward_straight

    @property
    def brake_request(self) -> swerve.requests.SwerveDriveBrake:
        """
        Get the brake request for locking all swerve modules.

        :returns: SwerveDriveBrake request object
        :rtype: swerve.requests.SwerveDriveBrake
        """
        return self._brake

    def apply_request(self, request: Callable[[], swerve.requests.SwerveRequest]) -> Command:
        """
        Returns a command that applies the specified control request to this swerve drivetrain.

        :param request: Lambda returning the request to apply
        :type request: Callable[[], swerve.requests.SwerveRequest]
        :returns: Command to run
        :rtype: Command
        """
        return self.run(lambda: self.set_control(request()))

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
        if isinstance(vision_robot_pose, Pose3d):
            vision_robot_pose = vision_robot_pose.toPose2d()

        TunerSwerveDrivetrain.add_vision_measurement(
            self,
            vision_robot_pose,
            utils.fpga_to_current_time(timestamp),
            vision_measurement_std_devs
        )

    def sample_pose_at(self, timestamp: units.second) -> Pose2d | None:
        """
        Return the pose at a given timestamp, if the buffer is not empty.

        :param timestamp: The timestamp of the pose in seconds.
        :type timestamp: second
        :returns: The pose at the given timestamp (or None if the buffer is empty).
        :rtype: Pose2d | None
        """
        return TunerSwerveDrivetrain.sample_pose_at(self, utils.fpga_to_current_time(timestamp))

    def set_module_states(self, module_states: SwerveModuleStates) -> None:
        """
        Set the module state. The modules in the sequence are always provided (and used) in the
        order when the SwerveDriveKinematics object was created. Convention is typically:

           (Front Left, Front Right, Rear Left, Rear Right)
        """
        from phoenix6.controls import VelocityTorqueCurrentFOC, PositionVoltage

        angle_setter: PositionVoltage = PositionVoltage(0, 0, enable_foc=False, override_brake_dur_neutral=False)
        velocity_setter: VelocityTorqueCurrentFOC = VelocityTorqueCurrentFOC(0, 0)
        ticks_per_revolution = 4096
        # wheel_radius: meters = WHEEL_RADIUS
        wheel_circumference: meters = self.robot.robot_constants.WHEEL_CIRCUMFERENCE

        for index, module in enumerate(self._swerve_modules):
            drive_motor = module.drive_motor
            steer_motor = module.steer_motor

            state: SwerveModuleState = module_states[index]
            state.optimize(module.get_current_state().angle)

            # Convert linear speed (m/s) to wheel rotations per second (RPS)
            wheel_rps = state.speed / wheel_circumference
            angle_to_set = (state.angle.degrees() / 360.0) * ticks_per_revolution

            steer_motor.set_control(angle_setter.with_position(angle_to_set))
            drive_motor.set_control(velocity_setter.with_velocity(wheel_rps))

    def set_motor_brake(self, brake: bool) -> None:
        if brake:
            self.stop()
            self.apply_request(lambda: self.brake_request)
        else:
            self.set_straight()

    def set_straight(self) -> None:
        """
        Sets the wheels straight so we can push the robot.
        """
        self.apply_request(lambda: self.point_at_request.with_module_direction(Rotation2d(0.0)))

    #########################################################################################
    # Tuner subsystem methods called by our base classes. These need to be overloaded as we need
    # to construct our Tuner subsystem in the main application (not this library) since it is
    # generated by the Tuner-X tool and we need to pass in the constants and modules.

    def reset_pose(self, pose: Pose2d) -> None:
        """
        Resets the pose of the robot. The pose should be from the
        ForwardPerspectiveValue.BLUE_ALLIANCE perspective.

        :param pose: Pose to make the current pose
        :type pose: Pose2d
        """
        self._tuner_x_subsystem.reset_pose(pose)

    def set_vision_measurement_std_devs(self, vision_measurement_std_devs: tuple[float, float, float]) -> None:
        """
        Sets the pose estimator's trust of global measurements. This might be used to
        change trust in vision measurements after the autonomous period, or to change
        trust as distance to a vision target increases.

        :param vision_measurement_std_devs: Standard deviations of the vision
                                            measurements. Increase these numbers to
                                            trust global measurements from vision less.
                                            This matrix is in the form [x, y, theta]ᵀ,
                                            with units in meters and radians.
        :type vision_measurement_std_devs:  tuple[float, float, float]
        """
        self._tuner_x_subsystem.set_vision_measurement_std_devs(vision_measurement_std_devs)

    def seed_field_centric(self, rotation: Rotation2d = Rotation2d()) -> None:
        """
        Resets the rotation of the robot pose to the given value from
        the ForwardPerspectiveValue.OPERATOR_PERSPECTIVE perspective.
        This makes the current orientation of the robot minus
        `rotation` the X forward for field-centric maneuvers.

        This is equivalent to calling reset_rotation with
        `rotation + self.get_operator_perspective()`.
        """
        self._tuner_x_subsystem.seed_field_centric(rotatiom)

    def get_state(self) -> SwerveDriveState:
        """
        Gets the current state of the swerve drivetrain.
        This includes information such as the pose estimate,
        module states, and chassis speeds.

        :returns: Current state of the drivetrain
        :rtype: SwerveDriveState
        """
        return self._tuner_x_subsystem.get_state()
