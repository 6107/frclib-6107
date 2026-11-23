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

import ntcore
from wpiutil import Alert

from lib_6107.util.alerts import AlertPublisher, RobotAlerts
import pytest


def _read_topic(path):
    sub = ntcore.NetworkTableInstance.get_default().get_string_array_topic(path).subscribe([])
    return sub.get()


def test_alert_publisher_maps_levels_to_topics():
    high = Alert("t_high", "high text", Alert.Level.HIGH)
    medium = Alert("t_med", "medium text", Alert.Level.MEDIUM)
    low = Alert("t_low", "low text", Alert.Level.LOW)
    inactive = Alert("t_off", "never shown", Alert.Level.HIGH)
    for alert in (high, medium, low):
        alert.set(True)

    publisher = AlertPublisher("PublisherTest", [high, medium, low, inactive])
    publisher.update()
    ntcore.NetworkTableInstance.get_default().flush()

    assert _read_topic("/Alerts/PublisherTest/errors") == ["high text"]
    assert _read_topic("/Alerts/PublisherTest/warnings") == ["medium text"]
    assert _read_topic("/Alerts/PublisherTest/info") == ["low text"]


def test_alert_publisher_clears_topic_when_alert_deactivates():
    alert = Alert("t_clear", "temporary", Alert.Level.MEDIUM)
    publisher = AlertPublisher("PublisherClear", [alert])

    alert.set(True)
    publisher.update()
    assert _read_topic("/Alerts/PublisherClear/warnings") == ["temporary"]

    alert.set(False)
    publisher.update()
    assert _read_topic("/Alerts/PublisherClear/warnings") == []


def test_alert_publisher_feeds_alert_logger_in_process():
    from lib_6107.pykit.alertlogger import AlertLogger

    alert = Alert("t_logger", "logged text", Alert.Level.HIGH)
    alert.set(True)
    publisher = AlertPublisher("PublisherLogger", [alert])

    publisher.update()

    assert "PublisherLogger" in AlertLogger.groups
    assert AlertLogger.local_alerts["PublisherLogger"] == (["logged text"], [], [])
    AlertLogger.groups.remove("PublisherLogger")
    del AlertLogger.local_alerts["PublisherLogger"]


def test_robot_alerts_update_publishes_active_alerts():
    do_nothing = MagicMock(name="do_nothing")
    alerts = RobotAlerts(make_fake_container(auto_selected=do_nothing, do_nothing=do_nothing))

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True):
        alerts.update()

    assert "No auto selected!!!" in _read_topic("/Alerts/Alerts/warnings")


def make_fake_container(auto_selected=None, do_nothing=None):
    """Create a lightweight fake RobotContainer suitable for RobotAlerts."""
    container = MagicMock()
    do_nothing = do_nothing if do_nothing is not None else MagicMock(name="do_nothing")
    container.get_do_nothing = do_nothing
    container.auto_chooser.get_selected.return_value = do_nothing if auto_selected is None else auto_selected
    return container


def test_alerts_init_registers_alert_groups():
    with patch("lib_6107.util.alerts.AlertLogger.register_group") as mock_register:
        RobotAlerts(make_fake_container())
        mock_register.assert_any_call("Alerts")
        mock_register.assert_any_call("preflight")
        assert mock_register.call_count == 2


def test_alerts_init_creates_expected_alerts():
    alerts = RobotAlerts(make_fake_container())
    assert alerts.driver_disconnected.get_text() == "Driver controller disconnected (port 0)"
    assert alerts.operator_disconnected.get_text() == "Operator controller disconnected (port 1)"
    assert alerts.dead_in_the_water_alert.get_text() == "No auto selected!!!"
    assert alerts.usbAlert.get_text() == "No USB Drive in robot!"


def test_alerts_init_does_not_set_usb_alert_in_simulation():
    with patch("lib_6107.util.alerts.RobotBase.is_real", return_value=False):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is False


def test_alerts_init_sets_usb_alert_when_real_and_no_usb_drive():
    with (
        patch("lib_6107.util.alerts.RobotBase.is_real", return_value=True),
        patch("lib_6107.util.alerts.os.path.exists", return_value=False),
    ):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is True


def test_alerts_init_does_not_set_usb_alert_when_real_and_usb_drive_present():
    with (
        patch("lib_6107.util.alerts.RobotBase.is_real", return_value=True),
        patch("lib_6107.util.alerts.os.path.exists", return_value=True),
    ):
        alerts = RobotAlerts(make_fake_container())
        assert alerts.usbAlert.get() is False


def test_alerts_update_sets_driver_disconnected_when_joystick_zero_not_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    def joystick_connected(port):
        return port != 0

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", side_effect=joystick_connected):
        alerts.update()

    assert alerts.driver_disconnected.get() is True
    assert alerts.operator_disconnected.get() is False


def test_alerts_update_sets_operator_disconnected_when_joystick_one_not_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    def joystick_connected(port):
        return port != 1

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", side_effect=joystick_connected):
        alerts.update()

    assert alerts.operator_disconnected.get() is True
    assert alerts.driver_disconnected.get() is False


def test_alerts_update_clears_driver_and_operator_alerts_when_both_connected():
    container = make_fake_container()
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True):
        alerts.update()

    assert alerts.driver_disconnected.get() is False
    assert alerts.operator_disconnected.get() is False


def test_alerts_update_sets_dead_in_the_water_when_do_nothing_selected():
    do_nothing = MagicMock(name="do_nothing")
    container = make_fake_container(auto_selected=do_nothing, do_nothing=do_nothing)
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True):
        alerts.update()

    assert alerts.dead_in_the_water_alert.get() is True


def test_alerts_update_clears_dead_in_the_water_when_real_auto_selected():
    real_auto = MagicMock(name="real_auto_command")
    container = make_fake_container(auto_selected=real_auto)
    alerts = RobotAlerts(container)

    with patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True):
        alerts.update()

    assert alerts.dead_in_the_water_alert.get() is False


def test_alerts_update_sets_preflight_alert_when_checklist_incomplete():
    alerts = RobotAlerts(make_fake_container())

    with (
        patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True),
        patch.object(alerts._preflight, "is_complete", return_value=False),
    ):
        alerts.update()

    assert alerts._preflight_alert.get() is True


def test_alerts_update_clears_preflight_alert_when_checklist_complete():
    alerts = RobotAlerts(make_fake_container())

    with (
        patch("lib_6107.util.alerts.DriverStationBackend.is_joystick_connected", return_value=True),
        patch.object(alerts._preflight, "is_complete", return_value=True),
    ):
        alerts.update()

    assert alerts._preflight_alert.get() is False


def test_alerts_preflight_update_delegates_to_checklist():
    alerts = RobotAlerts(make_fake_container())

    with patch.object(alerts._preflight, "update") as mock_update:
        alerts.preflight_update()

    mock_update.assert_called_once_with()
