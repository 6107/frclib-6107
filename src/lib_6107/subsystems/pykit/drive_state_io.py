from dataclasses import dataclass

from wpimath.units import meters, meters_per_second, radians, radians_per_second, seconds

from lib_6107.pykit.autolog import autolog


class DriveStateIO:
    """
    Drivetrain state published as a pykit input (``Drive/State``).

    The CTRE odometry thread produces one ``SwerveDriveState`` snapshot; the drive subsystem copies it into this
    dataclass once per periodic so the whole cycle (logging, commands, vision) sees the same values and replay
    can restore them. Per-module data is logged separately by each module (``Drive/Module-*``).
    """

    @autolog
    @dataclass(slots=True)
    class DriveStateIOInputs:
        pose_x: meters = 0.0
        pose_y: meters = 0.0
        pose_heading: radians = 0.0

        velocity_x: meters_per_second = 0.0
        velocity_y: meters_per_second = 0.0
        velocity_omega: radians_per_second = 0.0

        raw_heading: radians = 0.0
        timestamp: seconds = 0.0

        # Odometry thread health: use these to correlate bad vision fusion with degraded odometry
        odometry_period: seconds = 0.0
        successful_daqs: int = 0
        failed_daqs: int = 0

    @staticmethod
    def update_from_state(inputs: DriveStateIOInputs, state) -> None:
        """Copy a CTRE SwerveDriveState snapshot into the inputs (no native calls)."""
        pose = state.pose
        inputs.pose_x = pose.x
        inputs.pose_y = pose.y
        inputs.pose_heading = pose.rotation().radians()
        inputs.velocity_x = state.velocity.vx
        inputs.velocity_y = state.velocity.vy
        inputs.velocity_omega = state.velocity.omega
        inputs.raw_heading = state.raw_heading.radians()
        inputs.timestamp = state.timestamp
        inputs.odometry_period = state.odometry_period
        inputs.successful_daqs = state.successful_daqs
        inputs.failed_daqs = state.failed_daqs
