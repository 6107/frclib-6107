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

from wpimath import (
    ChassisVelocities,
    Pose2d,
    Pose3d,
    Rotation2d,
    SwerveDrive4Kinematics,
    SwerveDrive4Odometry,
    SwerveModulePosition,
)
from wpimath.units import meters, radians_per_second, seconds

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtracer import LogTracer

ModulePositionType = tuple[SwerveModulePosition, SwerveModulePosition, SwerveModulePosition, SwerveModulePosition]


class RobotState:
    auto_distance_tolerance: meters = 0.1
    auto_rotation_tolerance: meters = 0.1

    robot_pose: Pose2d = Pose2d()
    heading_offset: Rotation2d = Rotation2d()
    robot_heading: Rotation2d = Rotation2d()

    module_positions: ModulePositionType = (
        SwerveModulePosition(),
        SwerveModulePosition(),
        SwerveModulePosition(),
        SwerveModulePosition(),
    )

    odometry: SwerveDrive4Odometry | None = None
    robot_field_velocity: ChassisVelocities = ChassisVelocities()

    @classmethod
    def configure(cls, kinematics: SwerveDrive4Kinematics) -> None:
        """Create the odometry for the team's drivetrain kinematics. Must be called before periodic().

        Args:
            kinematics (SwerveDrive4Kinematics): Kinematics of the team's swerve drivetrain.
        """
        cls.odometry = SwerveDrive4Odometry(kinematics, Rotation2d(), cls.module_positions, Pose2d())

    @classmethod
    def periodic(
        cls,
        pose: Pose2d,
        heading: Rotation2d,
        pose3d: Pose3d,
        heading_timestamp: seconds,
        yaw_rate: radians_per_second,
        field_relative_robot_velocity: ChassisVelocities,
        module_positions: tuple[SwerveModulePosition, SwerveModulePosition, SwerveModulePosition, SwerveModulePosition],
    ) -> None:

        LogTracer.reset_outer("RobotState")
        try:
            cls.robot_heading = heading
            cls.module_positions = module_positions
            cls.robot_pose = pose

            estimated_field_pose = cls.odometry.update(heading, module_positions)

            cls.robot_field_velocity = field_relative_robot_velocity

            LogTracer.record("OdometryUpdate")

            Logger.record_output("Robot/Pose/EstimatorPose", estimated_field_pose)
            Logger.record_output("Robot/Pose/OdometryPose", pose)

            Logger.record_output("Robot/Heading", cls.robot_heading)
            Logger.record_output("Robot/HeadingVelocity", yaw_rate)
            Logger.record_output("Robot/Velocity", field_relative_robot_velocity)
            Logger.record_output("Robot/HeadingOffset", cls.heading_offset)

            position_delta = pose - estimated_field_pose

            Logger.record_output("Auto/PositionOffset", position_delta)
            Logger.record_output(
                "Auto/PositionCorrect", position_delta.translation().norm() < cls.auto_distance_tolerance
            )
            Logger.record_output(
                "Auto/RotationCorrect", abs(position_delta.rotation().radians()) < cls.auto_rotation_tolerance
            )

            # Alternatively, a Pose3d can be constructed directly from x, y, z, and a Rotation3
            # Logger.record_output("Robot/Pose3d", pose3d)
            Logger.record_output("Odometry/Robot", pose3d)

            # TODO: Should we log starting location in AutonomousInit?  Would that be metadata
        finally:
            LogTracer.record_total()

    @classmethod
    def get_pose(cls) -> Pose2d:
        return cls.estimator.estimatedPose  # TODO: Is this called?  May need it commands

    @classmethod
    def get_rotation(cls) -> Rotation2d:
        return cls.robot_pose.rotation()

    @classmethod
    def reset_pose(cls, pose: Pose2d | None = None) -> None:  # TODO: Is this called?  May need it commands
        pose = pose or Pose2d()
        cls.heading_offset = cls.robot_heading - pose.rotation()
        cls.odometry.reset_position(cls.robot_heading, cls.module_positions, pose)
