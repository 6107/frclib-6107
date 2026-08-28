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
# From Gene Panov's (Team 714) CommandRevSwerve project (and FRC Python videos)
#
# Copyright (c) FIRST and other WPILib contributors.
# Open Source Software; you can modify and/or share it under the terms of
# the WPILib BSD license file in the root directory of this project.

from wpimath.geometry import Rotation2d, Translation2d
from wpimath.trajectory import TrapezoidProfileRadians
from wpimath.units import radians_per_second, rotationsToRadians

# TODO: All the following needs to be added to our constants
# from robot_2026.subsystems.swervedrive.constants import AutoConstants, DriveConstants
# from robot_2026.subsystems.swervedrive.drivesubsystem import DriveSubsystem
# from constants import MAX_SPEED, THETA_CONTROLLER_CONSTRAINTS




MAX_SPEED = 5
MAX_ANGULAR_SPEED: radians_per_second = rotationsToRadians(0.75)  # TODO: Measure this
MAX_ANGULAR_ACCELERATION: radians_per_second = rotationsToRadians(0.75)  # Actually is radians/second^2

# Constraint for the motion profiled robot angle controller
THETA_CONTROLLER_CONSTRAINTS = TrapezoidProfileRadians.Constraints(MAX_ANGULAR_SPEED,
                                                                   MAX_ANGULAR_ACCELERATION)


FIELD_WIDTH = 8.052
FIELD_LENGTH = 17.55
U_TURN = Rotation2d.fromDegrees(180)


def mirror(waypoints, width=FIELD_WIDTH):
    """
    Converts right-side trajectory into left-side trajectory
    :param waypoints: original trajectory, list of tuples of (x, y, heading) or (x, y)
    :param width: width of the field
    :return: a mirror image of trajectory waypoints
    """
    # a tuple is treated as a single waypoint
    if isinstance(waypoints, tuple):
        return mirror([waypoints])[0]

    def reflect(heading):
        if heading is not None:
            return heading * -1.0
        return 0.0

    result = []
    for point in waypoints:
        if len(point) == 2 and isinstance(point[0], Translation2d):
            location, heading = point
            result.append((Translation2d(location.x, width - location.y), reflect(heading)))
        elif len(point) == 2:
            x, y = point
            result.append((x, width - y))
        elif len(point) == 3:
            x, y, heading = point
            result.append((x, width - y, reflect(heading)))
        else:
            AssertionError(f"unknown waypoint format: {point}")

    return result


def _flipWaypoint(waypoint, width = FIELD_WIDTH, length = FIELD_LENGTH) -> tuple[Translation2d, Rotation2d]:
    translation, rotation = waypoint
    translation = Translation2d(length - translation.x, width - translation.y)
    if rotation is not None:
        rotation = rotation + U_TURN
    return translation, rotation


def _sameDirection(direction1: Translation2d, direction2: Translation2d, minCos=0.5) -> bool:
    """
    :param minCos: minimum cosine of angles between two directions (to be considered "same direction")
    """
    length1, length2 = direction1.norm(), direction2.norm()
    product = direction1.x * direction2.x + direction1.y * direction2.y
    return product > length1 * length2 * minCos
