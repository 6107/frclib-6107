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

class RobotAlerts:
    """
    Manages robot-wide system alerts and preflight checks.

    This class centralizes alert management for critical robot conditions including
    controller connections, autonomous mode selection, and USB drive availability.
    It integrates with the AlertLogger for real-time telemetry and maintains a
    preflight checklist that must be completed before enabling the robot.

    The class handles both environmental checks (USB drive presence on real robots)
    and runtime checks (joystick connectivity, autonomous selection). Alerts are
    organized into groups via AlertLogger for better visibility in dashboard telemetry.

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

    def __init__(self, container: 'RobotContainer'):
        """
        Initializes the RobotAlerts system with all monitored alerts and checks.

        Creates all alert monitors and registers them with the AlertLogger for
        telemetry tracking. Performs an immediate USB drive check on real robots
        at initialization time. Instantiates the preflight checklist which will be
        updated and validated during robot operation.

        USB Drive Check:
            On real robot hardware (RobotBase.isReal()), immediately checks for the
            presence of /U/logs directory. If not found, the usbAlert is triggered,
            which blocks robot enable until the drive is connected.

        Args:
            container (RobotContainer): The robot container instance providing access
                                       to autonomous and subsystem configurations.
                                       Used to check selected autonomous routine and
                                       preflight status during updates.
        """
        self._container = container

        # TODO: Need to validate all alerts so we can trust them
        AlertLogger.register_group("Alerts")

        self.driver_disconnected = Alert("Driver controller disconnected (port 0)",
                                         Alert.AlertType.kWarning)
        self.operator_disconnected = Alert("Operator controller disconnected (port 1)",
                                           Alert.AlertType.kWarning)
        self.dead_in_the_water_alert = Alert("No auto selected!!!",
                                             Alert.AlertType.kWarning)

        self.usbAlert = Alert("No USB Drive in robot!", Alert.AlertType.kError)

        if RobotBase.isReal() and not os.path.exists("/U/logs"):
            self.usbAlert.set(True)

        self._preflight_alert = Alert("Preflight checking not complete",
                                      Alert.AlertType.kError)
        # preflight checklist
        AlertLogger.register_group("preflight")
        self._preflight = PreflightChecklist()

    def update(self) -> None:
        """
        Updates all runtime alert states based on current robot conditions.

        Periodically polls hardware and configuration state to determine if alerts
        should be active. This method should be called from robotPeriodic() or a
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
        self.driver_disconnected.set(not DriverStation.isJoystickConnected(0))
        self.operator_disconnected.set(not DriverStation.isJoystickConnected(1))

        self.dead_in_the_water_alert.set(self._container.auto_chooser.get_selected() == self._container.get_do_nothing)

        self._preflight_alert.set(not self._preflight.is_complete())

    def preflight_update(self) -> None:
        """
        Advances the preflight checklist through its check sequence.

        Executes one step/check in the preflight verification process. This method
        should be called periodically (e.g., from robotInit() or a periodic routine)
        to allow operators to verify subsystem status and confirm system readiness.

        The preflight process can block robot enable until checks are marked complete
        by the operator (typically via dashboard confirmation). Once complete, the
        preflight_alert is cleared by the update() method.

        Note:
            This method advances the preflight state machine; the preflight_alert
            alert status is updated in the update() method, not here.
        """
        self._preflight.update()
