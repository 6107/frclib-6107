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
#
# Constants for source in this subdirectory will go here

from dataclasses import dataclass
from enum import IntEnum, unique

from wpimath.geometry import Rotation3d, Transform3d, Translation2d, Translation3d
from wpimath.kinematics import SwerveDrive4Kinematics

from wpimath.units import degreesToRadians, inchesToMeters, kilograms, lbsToKilograms, meters, \
    meters_per_second, radians_per_second, rotationsToRadians, seconds

from lib_6107.constants import RobotConstants, NetworkConstants
from lib_6107.subsystems.constants import VisionSubsystemType

# For this example robot, we had a CTRE swerve-drive and used the Tuner-X utility to
# create our swerve drivetrain
from generated.tuner_constants import TunerConstants  # Use Tuner X constants if available


@dataclass(slots=True)
class MyRobotConstants(RobotConstants):
    """
    Update for fields unique to the 2026-Rebuilt robot
    """
    ROBOT_MASS: kilograms = lbsToKilograms(60)

    ROBOT_CHASSIS_X_WIDTH: meters = inchesToMeters(27)
    ROBOT_CHASSIS_Y_WIDTH: meters = inchesToMeters(27)

    ###########################
    # Robot periodic rate
    ROBOT_PERIOD: seconds = 0.0333

    ###########################
    # Drivetrain  (often overridden in real-robot based on Tuner-X constants)
    MAX_SPEED: meters_per_second = TunerConstants.speed_at_12_volts
    MAX_ANGULAR_VELOCITY: radians_per_second = rotationsToRadians(0.75)  # TODO: Measure this

    ###########################
    # Additional 2026 game constants
    AUTONOMOUS_END_TRIGGER_TIME = 10  # Autonomous End Game Timing

GYRO_REVERSED = False  # (affects field-relative driving)

DriveKinematics = SwerveDrive4Kinematics(
    Translation2d(TunerConstants._front_left_x_pos, TunerConstants._front_left_y_pos),
    Translation2d(TunerConstants._front_right_x_pos, TunerConstants._front_right_y_pos),
    Translation2d(TunerConstants._back_left_x_pos, TunerConstants._back_left_y_pos),
    Translation2d(TunerConstants._back_right_x_pos, TunerConstants._back_right_y_pos)
)

#################################################################
# Other subsystem and device constants for this year's project

@unique
class DeviceID(IntEnum):
    REV_POWER_DISTRIBUTION_HUB = 1

    # Drivetrain and IMU is provided already via Tuner X
    DRIVETRAIN_LEFT_FRONT_TURNING_ID = TunerConstants._front_left_steer_motor_id
    DRIVETRAIN_LEFT_FRONT_DRIVING_ID = TunerConstants._front_left_drive_motor_id
    DRIVETRAIN_LEFT_FRONT_ENCODER_ID = TunerConstants._front_left_encoder_id

    DRIVETRAIN_RIGHT_FRONT_TURNING_ID = TunerConstants._front_right_steer_motor_id
    DRIVETRAIN_RIGHT_FRONT_DRIVING_ID = TunerConstants._front_right_drive_motor_id
    DRIVETRAIN_RIGHT_FRONT_ENCODER_ID = TunerConstants._front_right_encoder_id

    DRIVETRAIN_LEFT_REAR_TURNING_ID = TunerConstants._back_left_steer_motor_id
    DRIVETRAIN_LEFT_REAR_DRIVING_ID = TunerConstants._back_left_drive_motor_id
    DRIVETRAIN_LEFT_REAR_ENCODER_ID = TunerConstants._back_left_encoder_id

    DRIVETRAIN_RIGHT_REAR_TURNING_ID = TunerConstants._back_right_steer_motor_id
    DRIVETRAIN_RIGHT_REAR_DRIVING_ID = TunerConstants._back_right_drive_motor_id
    DRIVETRAIN_RIGHT_REAR_ENCODER_ID = TunerConstants._back_right_encoder_id

    GYRO_DEVICE_ID = TunerConstants._pigeon_id

    # Climber Subsystem
    CLIMBER_DEVICE_ID = 35

#################################################################################
# Camera configurations     TODO: Move this to subsystems

FRONT_CAMERA_INFO = {
    "Type"     : VisionSubsystemType.NONE,   # CAMERA_TYPE_PHOTONVISION,
    "Label"    : "front",
    "Name"     : "PhotonVision",
    "Transform": Transform3d(Translation3d(x=inchesToMeters(-11.0),
                                           y=inchesToMeters(4.25),
                                           z=inchesToMeters(13.625)),
                             Rotation3d(degreesToRadians(0.0),  # Roll  -  front/back x-axis rotation
                                        degreesToRadians(-3.0),  # Pitch -  side/side y-axis rotation
                                        degreesToRadians(0.0))),# Yaw   - left(+) / right(-) z-axis
    "Localizer": False,
    "Trust"    : 1.0  # [0.0..1.0] More trusted cameras are closer to 1.0
}
