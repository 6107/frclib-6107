"""Unit tests for wpilogwriter module."""

from unittest.mock import patch
from lib_6107.pykit.wpilog.wpilogwriter import WPILOGWriter


@patch('lib_6107.pykit.wpilog.wpilogwriter.RobotBase')
@patch('lib_6107.pykit.wpilog.wpilogwriter.DataLogWriter')
def test_wpilogwriter_init_simulation_mode(mock_writer_class, mock_robot_base):
    """Verify WPILOGWriter accepts filename and path parameters."""
    mock_robot_base.isSimulation.return_value = True

    writer = WPILOGWriter("test.wpilog", None)
    assert writer._is_simulation is True


@patch('lib_6107.pykit.wpilog.wpilogwriter.RobotBase')
@patch('lib_6107.pykit.wpilog.wpilogwriter.DataLogWriter')
def test_wpilogwriter_init_real_mode(mock_writer_class, mock_robot_base):
    """Verify WPILOGWriter initializes in real mode."""
    mock_robot_base.isSimulation.return_value = False

    writer = WPILOGWriter("test.wpilog", None)
    assert writer._is_simulation is False

