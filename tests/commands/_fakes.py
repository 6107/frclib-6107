"""Local fakes for drivetrain command tests."""

from unittest.mock import MagicMock

from wpimath import Pose2d, Rotation2d


class FakeDrive:
    def __init__(self, x=0.0, y=0.0, degrees=0.0, turn_rate=0.0):
        self.pose = Pose2d(x, y, Rotation2d.from_degrees(degrees))
        self.container = MagicMock()
        self.container.get_elapsed_time.return_value = 1.0
        self.gyro = MagicMock()
        self.gyro.turn_rate_degrees_per_second = turn_rate
        self.arcade_drive = MagicMock()
        self.drive = MagicMock()
        self.stop = MagicMock()

    @property
    def heading(self):
        return self.pose.rotation()

    def place(self, x, y, degrees=0.0):
        self.pose = Pose2d(x, y, Rotation2d.from_degrees(degrees))
