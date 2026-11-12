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
"""Unit tests for OperatorInterface (src/lib_6107/subsystems/operator_interface.py)."""

from unittest.mock import call, patch

from wpilib import GenericHID
from wpilib.simulation import DriverStationSim

from lib_6107.subsystems.operator_interface import (deadband, invert, kXboxJoystickDeadband, OperatorInterface,
                                                    sign_square)
import pytest


def test_deadband_passes_value_through_when_above_limit():
    fn = deadband(lambda: 0.5, 0.1)
    assert fn() == 0.5


def test_deadband_zeroes_value_within_limit():
    fn = deadband(lambda: 0.05, 0.1)
    assert fn() == 0


def test_deadband_zeroes_value_at_exact_limit():
    fn = deadband(lambda: 0.1, 0.1)
    assert fn() == 0


def test_deadband_handles_negative_values_within_limit():
    fn = deadband(lambda: -0.05, 0.1)
    assert fn() == 0


def test_deadband_passes_negative_value_above_limit():
    fn = deadband(lambda: -0.5, 0.1)
    assert fn() == -0.5


def test_invert_negates_positive_value():
    fn = invert(lambda: 0.3)
    assert fn() == -0.3


def test_invert_negates_negative_value():
    fn = invert(lambda: -0.3)
    assert fn() == 0.3


def test_sign_square_preserves_sign_of_positive_input():
    fn = sign_square(lambda: 0.5)
    assert fn() == 0.25


def test_sign_square_preserves_sign_of_negative_input():
    fn = sign_square(lambda: -0.5)
    assert fn() == -0.25


def test_sign_square_handles_zero():
    fn = sign_square(lambda: 0.0)
    assert fn() == 0.0


def test_operator_interface_init_creates_controllers_on_expected_ports():
    oi = OperatorInterface()
    assert oi.driverController.get_controller().get_port() == 0
    assert oi.operatorController.get_controller().get_port() == 1


def test_operator_interface_init_wires_driver_axes():
    oi = OperatorInterface()
    # Axes should be callables derived from the driver controller.
    assert callable(oi.driverX)
    assert callable(oi.driverY)
    assert callable(oi.driverRotationX)
    assert callable(oi.driverRotationY)


def test_operator_interface_driver_x_applies_deadband_invert_and_square():
    oi = OperatorInterface()
    try:
        DriverStationSim.set_joystick_axes_maximum_index(0, 6)
        DriverStationSim.set_joystick_axes_available(0, 0x3F)
        DriverStationSim.set_joystick_axis(0, 0, 0.5)
        DriverStationSim.notify_new_data()

        # get_left_x -> scaled deadband -> invert -> sign_square
        assert oi.driverX() == pytest.approx(-((0.5 - kXboxJoystickDeadband) / (1 - kXboxJoystickDeadband)) ** 2)
    finally:
        DriverStationSim.set_joystick_axis(0, 0, 0.0)
        DriverStationSim.notify_new_data()


def test_operator_interface_driver_x_applies_deadband_for_small_input():
    oi = OperatorInterface()
    try:
        DriverStationSim.set_joystick_axes_maximum_index(0, 6)
        DriverStationSim.set_joystick_axes_available(0, 0x3F)
        DriverStationSim.set_joystick_axis(0, 0, kXboxJoystickDeadband / 2)
        DriverStationSim.notify_new_data()

        assert oi.driverX() == 0
    finally:
        DriverStationSim.set_joystick_axis(0, 0, 0.0)
        DriverStationSim.notify_new_data()


def test_operator_interface_rumble_controllers_sets_rumble_on_both_controllers():
    oi = OperatorInterface()
    with patch.object(oi.driverController.get_hid(), "set_rumble") as mock_driver_rumble, \
            patch.object(oi.operatorController.get_hid(), "set_rumble") as mock_operator_rumble:
        oi.rumble_controllers(0.75)

    mock_driver_rumble.assert_has_calls([call(GenericHID.RumbleType.LEFT_RUMBLE, 0.75), call(GenericHID.RumbleType.RIGHT_RUMBLE, 0.75)])
    mock_operator_rumble.assert_has_calls([call(GenericHID.RumbleType.LEFT_RUMBLE, 0.75), call(GenericHID.RumbleType.RIGHT_RUMBLE, 0.75)])


def test_operator_interface_rumble_controllers_defaults_to_full_power():
    oi = OperatorInterface()
    with patch.object(oi.driverController.get_hid(), "set_rumble") as mock_driver_rumble, \
            patch.object(oi.operatorController.get_hid(), "set_rumble") as mock_operator_rumble:
        oi.rumble_controllers()

    mock_driver_rumble.assert_has_calls([call(GenericHID.RumbleType.LEFT_RUMBLE, 1.0), call(GenericHID.RumbleType.RIGHT_RUMBLE, 1.0)])
    mock_operator_rumble.assert_has_calls([call(GenericHID.RumbleType.LEFT_RUMBLE, 1.0), call(GenericHID.RumbleType.RIGHT_RUMBLE, 1.0)])


def test_operator_interface_rumble_controllers_command_starts_and_ends_rumble():
    oi = OperatorInterface()
    with patch.object(oi, "rumble_controllers") as mock_rumble:
        command = oi.rumble_controllers_command(0.5)
        command.initialize()
        mock_rumble.assert_called_once_with(0.5)

        mock_rumble.reset_mock()
        command.end(False)
        mock_rumble.assert_called_once_with(0.0)
