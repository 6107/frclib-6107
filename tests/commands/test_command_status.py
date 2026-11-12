"""Tests for dashboard telemetry that replaced the 2026 SmartDashboard calls."""

from unittest.mock import MagicMock, patch

from lib_6107.commands.command import BaseCommand
from lib_6107.subsystems.gyro.gyro import Gyro

LOGGER = "lib_6107.commands.command.Logger.record_output"


def test_record_status_logs_under_commands_path():
    container = MagicMock()
    cmd = BaseCommand(container)
    with patch(LOGGER) as record:
        cmd.record_status("overshot")
    record.assert_called_once_with("Commands/BaseCommand/Status", "overshot")


def test_gyro_dashboard_records_via_logger():
    gyro = MagicMock(spec=Gyro)
    gyro.gyro_type = "pigeon2"
    gyro.yaw, gyro.angle, gyro.pitch, gyro.roll = 1.0, 2.0, 3.0, 4.0
    with patch("lib_6107.subsystems.gyro.gyro.Logger.record_output") as record:
        Gyro.dashboard_initialize(gyro)
        Gyro.dashboard_periodic(gyro)
    logged = {c.args[0]: c.args[1] for c in record.call_args_list}
    assert logged == {
        "Gyro/Type": "pigeon2",
        "Gyro/Yaw": 1.0,
        "Gyro/Angle": 2.0,
        "Gyro/Pitch": 3.0,
        "Gyro/Roll": 4.0,
    }
