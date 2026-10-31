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
"""Unit tests for RobotAlerts (src/lib_6107/util/alerts.py)."""

from unittest.mock import MagicMock, patch

from lib_6107.util.alerts import RobotAlerts


def make_fake_container(auto_selected = None, do_nothing = None):
    """Create a lightweight fake RobotContainer suitable for RobotAlerts."""
    container = MagicMock()
    do_nothing = do_nothing if do_nothing is not None else MagicMock(name="do_nothing")
    container.get_do_nothing = do_nothing
    container.auto_chooser.get_selected.return_value = (
        do_nothing if auto_selected is None else auto_selected
    )
    return container


def test_alerts_init_registers_alert_groups():
    with patch("lib_6107.util.alerts.AlertLogger.register_group") as mock_register:
        RobotAlerts(make_fake_container())
        mock_register.assert_any_call("Alerts")
        mock_register.assert_any_call("preflight")
        assert mock_register.call_count == 2


def test_alerts_init_creates_expected_alerts():
    alerts = RobotAlerts(make_fake_container())
    assert alerts.driver_disconnected.getText() == "Driver controller disconnected (port 0)"
    assert alerts.operator_disconnected.getText() == "Operator controller disconnected (port 1)"
    assert alerts.dead_in_the_water_alert.getText() == "No auto selected!!!"
    assert alerts.usbAlert.getText() == "No USB Drive in robot!"


def test_alerts_init_does_not_set_usb_alert_in_simulation():
    with patch("lib_6107.util.alerts.RobotBase.isReal", return_value=False):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is False


def test_alerts_init_sets_usb_alert_when_real_and_no_usb_drive():
    with patch("lib_6107.util.alerts.RobotBase.isReal", return_value=True), \
            patch("lib_6107.util.alerts.os.path.exists", return_value=False):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is True


def test_alerts_init_does_not_set_usb_alert_when_real_and_usb_drive_present():
    with patch("lib_6107.util.alerts.RobotBase.isReal", return_value=True), \
            patch("lib_6107.util.alerts.os.path.exists", return_value=True):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is False


def test_alerts_update_sets_driver_disconnected_when_joystick_zero_not_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    def joystick_connected(port):
        return port != 0

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", side_effect=joystick_connected):
        alerts.update()

    assert alerts.driver_disconnected.get() is True
    assert alerts.operator_disconnected.get() is False


def test_alerts_update_sets_operator_disconnected_when_joystick_one_not_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    def joystick_connected(port):
        return port != 1

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", side_effect=joystick_connected):
        alerts.update()

    assert alerts.operator_disconnected.get() is True
    assert alerts.driver_disconnected.get() is False


def test_alerts_update_clears_driver_and_operator_alerts_when_both_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", return_value=True):
        alerts.update()

    assert alerts.driver_disconnected.get() is False
    assert alerts.operator_disconnected.get() is False


def test_alerts_update_sets_dead_in_the_water_when_do_nothing_selected():
    do_nothing = MagicMock(name="do_nothing")
    container = make_fake_container(auto_selected=do_nothing, do_nothing=do_nothing)
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", return_value=True):
        alerts.update()

    assert alerts.dead_in_the_water_alert.get() is True


def test_alerts_update_clears_dead_in_the_water_when_real_auto_selected():
    real_auto = MagicMock(name="real_auto_command")
    container = make_fake_container(auto_selected=real_auto)
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", return_value=True):
        alerts.update()

    assert alerts.dead_in_the_water_alert.get() is False


def test_alerts_update_sets_preflight_alert_when_checklist_incomplete():
    alerts = RobotAlerts(make_fake_container())

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", return_value=True), \
            patch.object(alerts._preflight, "is_complete", return_value=False):
        alerts.update()

    assert alerts._preflight_alert.get() is True


def test_alerts_update_clears_preflight_alert_when_checklist_complete():
    alerts = RobotAlerts(make_fake_container())

    with patch("lib_6107.util.alerts.DriverStation.isJoystickConnected", return_value=True), \
            patch.object(alerts._preflight, "is_complete", return_value=True):
        alerts.update()

    assert alerts._preflight_alert.get() is False


def test_alerts_preflight_update_delegates_to_checklist():
    alerts = RobotAlerts(make_fake_container())

    with patch.object(alerts._preflight, "update") as mock_update:
        alerts.preflight_update()

    mock_update.assert_called_once_with()
