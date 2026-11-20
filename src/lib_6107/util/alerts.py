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

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ntcore import NetworkTableInstance
from wpilib import DriverStationBackend, RobotBase
from wpiutil import Alert

from lib_6107.pykit.alertlogger import ALERT_TOPIC_ROOT, AlertLogger
from lib_6107.util.preflight import PreflightChecklist

if TYPE_CHECKING:
    from lib_6107.robotcontainer import RobotContainer


class AlertPublisher:
    """Publishes the active alerts of a group to ``/Alerts/<group>/{errors,warnings,info}``.

    ``wpiutil.Alert`` does not publish NetworkTables topics itself, so this class mirrors the
    active alerts into the string-array topics that Elastic's alerts widget and
    ``AlertLogger`` read. HIGH alerts go to ``errors``, MEDIUM to ``warnings`` and LOW to ``info``.
    """

    _LEVEL_TOPICS = {
        Alert.Level.HIGH: "errors",
        Alert.Level.MEDIUM: "warnings",
        Alert.Level.LOW: "info",
    }

    def __init__(self, group: str, alerts: list[Alert]) -> None:
        """
        Args:
            group: Alert group name; used as the ``/Alerts/<group>`` topic folder.
            alerts: The alerts to mirror. Their active state is sampled on each ``update()``.
        """
        self._group = group
        self._alerts = list(alerts)
        inst = NetworkTableInstance.get_default()
        self._publishers = {
            level: inst.get_string_array_topic(f"{ALERT_TOPIC_ROOT}/{group}/{topic}").publish()
            for level, topic in self._LEVEL_TOPICS.items()
        }

    @property
    def group(self) -> str:
        """Alert group name."""
        return self._group

    def update(self) -> None:
        """Publish the text of every currently active alert, grouped by severity."""
        active: dict = {level: [] for level in self._LEVEL_TOPICS}
        for alert in self._alerts:
            if alert.get():
                active[alert.get_level()].append(alert.get_text())
        for level, publisher in self._publishers.items():
            publisher.set(active[level])


class RobotAlerts:
    """
    Manages robot-wide system alerts and preflight checks.

    This class centralizes alert management for critical robot conditions including
    controller connections, autonomous mode selection, and USB drive availability.
    It integrates with the AlertLogger for real-time telemetry and maintains a
    preflight checklist that must be completed before enabling the robot.

    The class handles both environmental checks (USB drive presence on real robots)
    and runtime checks (joystick connectivity, autonomous selection). Alerts are
    organized into groups via AlertLogger for better visibility in Elastic telemetry.

    Attributes:
        driver_disconnected (Alert): Warning alert triggered when driver controller
                                     (port 0) is not connected.
        operator_disconnected (Alert): Warning alert triggered when operator controller
                                       (port 1) is not connected.
        dead_in_the_water_alert (Alert): Warning alert triggered when no autonomous
                                         routine is selected.
        usbAlert (Alert): Error alert triggered on real robots when USB drive is not
                         mounted at /U/logs (used for log capture).
    """

    def __init__(self, container: RobotContainer):
        """
        Initializes the RobotAlerts system with all monitored alerts and checks.

        Creates all alert monitors and registers them with the AlertLogger for
        telemetry tracking. Performs an immediate USB drive check on real robots
        at initialization time. Instantiates the preflight checklist which will be
        updated and validated during robot operation.

        USB Drive Check:
            On real robot hardware (RobotBase.is_real()), immediately checks for the
            presence of /U/logs directory. If not found, the usbAlert is triggered,
            which blocks robot enable until the drive is connected.

        Args:
            container (RobotContainer): The robot container instance providing access
                                       to autonomous and subsystem configurations.
                                       Used to check selected autonomous routine and
                                       preflight status during updates.
        """
        self._container = container

        AlertLogger.register_group("Alerts")

        self.driver_disconnected = Alert(
            "driver_disconnected", "Driver controller disconnected (port 0)", Alert.Level.MEDIUM
        )
        self.operator_disconnected = Alert(
            "operator_disconnected", "Operator controller disconnected (port 1)", Alert.Level.MEDIUM
        )
        self.dead_in_the_water_alert = Alert("no_auto_selected", "No auto selected!!!", Alert.Level.MEDIUM)

        self.usbAlert = Alert("no_usb_drive", "No USB Drive in robot!", Alert.Level.HIGH)

        if RobotBase.is_real() and not os.path.exists("/U/logs"):
            self.usbAlert.set(True)

        self._preflight_alert = Alert("preflight_incomplete", "Preflight checking not complete", Alert.Level.HIGH)
        # preflight checklist
        AlertLogger.register_group("preflight")
        self._preflight = PreflightChecklist()

        self._publishers = [
            AlertPublisher(
                "Alerts",
                [self.driver_disconnected, self.operator_disconnected, self.dead_in_the_water_alert, self.usbAlert],
            ),
            AlertPublisher("preflight", [self._preflight_alert]),
        ]

    def update(self) -> None:
        """
        Updates all runtime alert states based on current robot conditions.

        Periodically polls hardware and configuration state to determine if alerts
        should be active. This method should be called from robot_periodic() or a
        periodic subsystem to keep alert states synchronized with actual conditions.

        Monitored Conditions:
            - Driver Joystick Connection (port 0): Checked against DriverStation
            - Operator Joystick Connection (port 1): Checked against DriverStation
            - Autonomous Routine Selection: Verified against container's auto_chooser
            - Preflight Checklist Completion: Validated against preflight status

        Note:
            Does not update the preflight checklist itself; call preflight_update()
            separately to advance preflight checks. This method only validates whether
            preflight is complete.
        """
        self.driver_disconnected.set(not DriverStationBackend.is_joystick_connected(0))
        self.operator_disconnected.set(not DriverStationBackend.is_joystick_connected(1))

        self.dead_in_the_water_alert.set(self._container.auto_chooser.get_selected() == self._container.get_do_nothing)

        self._preflight_alert.set(not self._preflight.is_complete())

        for publisher in self._publishers:
            publisher.update()

    def preflight_update(self) -> None:
        """
        Advances the preflight checklist through its check sequence.

        Executes one step/check in the preflight verification process. This method
        should be called periodically (e.g., from robot_init() or a periodic routine)
        to allow operators to verify subsystem status and confirm system readiness.

        The preflight process can block robot enable until checks are marked complete
        by the operator (typically via Elastic confirmation). Once complete, the
        preflight_alert is cleared by the update() method.

        Note:
            This method advances the preflight state machine; the preflight_alert
            alert status is updated in the update() method, not here.
        """
        self._preflight.update()
