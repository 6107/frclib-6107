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
"""
Alert Logger Module

This module provides the AlertLogger class for managing and monitoring alerts from NetworkTables.
It subscribes to the robot's ``/Alerts/<group>/{errors,warnings,info}`` topics (published by
``lib_6107.util.alerts``, which Elastic's alerts widget can also display) and
periodically retrieves and logs alerts by category (errors, warnings, info).

NOTE (2027): wpiutil.Alert does not publish NetworkTables topics by itself, so a group only has
content once an ``AlertPublisher`` is feeding it.
"""

from ntcore import NetworkTableInstance, StringArraySubscriber

from lib_6107.pykit.logtable import LogTable

ALERT_TOPIC_ROOT = "/Alerts"
"""NetworkTables root under which each alert group publishes its errors/warnings/info arrays."""


class AlertLogger:
    """
    Singleton class for managing and logging alerts from NetworkTables.

    This class monitors alert groups and retrieves alerts from the ``/Alerts/<group>`` topics
    organized by severity level (errors, warnings, info). It uses NetworkTables
    subscribers to stay updated with new alerts in real-time.

    Attributes:
        groups (list[str]): List of registered alert group names to monitor.
        error_subscribers (dict[str, StringArraySubscriber]): Mapping of group names
            to subscribers for error-level alerts.
        warning_subscribers (dict[str, StringArraySubscriber]): Mapping of group names
            to subscribers for warning-level alerts.
        info_subscribers (dict[str, StringArraySubscriber]): Mapping of group names
            to subscribers for info-level alerts.
    """

    groups: list[str] = []
    """List of registered alert groups being monitored."""

    error_subscribers: dict[str, StringArraySubscriber] = {}
    """NetworkTables subscribers for error alerts, indexed by group name."""

    warning_subscribers: dict[str, StringArraySubscriber] = {}
    """NetworkTables subscribers for warning alerts, indexed by group name."""

    info_subscribers: dict[str, StringArraySubscriber] = {}
    """NetworkTables subscribers for info alerts, indexed by group name."""

    local_alerts: dict[str, tuple[list[str], list[str], list[str]]] = {}
    """In-process (errors, warnings, info) text per group, set by ``set_alerts``.

    Groups present here are logged straight from memory, with no NetworkTables round trip.
    Groups registered without local data fall back to the ``/Alerts/<group>`` subscribers.
    """

    @classmethod
    def set_alerts(cls, group: str, errors: list[str], warnings: list[str], info: list[str]) -> None:
        """
        Record the currently active alert text for a group (called by ``AlertPublisher.update``).

        Also registers the group. The lists are copied, so callers may keep mutating them.

        Args:
            group (str): Alert group name.
            errors (list[str]): Active HIGH-level alert text.
            warnings (list[str]): Active MEDIUM-level alert text.
            info (list[str]): Active LOW-level alert text.
        """
        cls.register_group(group)
        cls.local_alerts[group] = (list(errors), list(warnings), list(info))

    @classmethod
    def periodic(cls, output_table: LogTable) -> None:
        """
        Periodically checks for new alerts and logs them to the output table.

        This method should be called regularly (typically in the robot's periodic method)
        to retrieve the latest alerts from each registered group. For each group it uses the
        in-process data from ``set_alerts`` if present; otherwise it:
        1. Creates subscribers for each alert level if they don't exist
        2. Retrieves the latest alert arrays from NetworkTables
        Then it writes the alerts to the output LogTable.

        Args:
            output_table (LogTable): The LogTable instance to write alert data to.
                Alert data will be written as:
                - {group}/.type = "Alerts"
                - {group}/errors = list of error messages
                - {group}/warnings = list of warning messages
                - {group}/info = list of info messages
        """
        for group in cls.groups:
            output_table.put(f"{group}/.type", "Alerts")

            local = cls.local_alerts.get(group)
            if local is not None:
                output_table.put(f"{group}/errors", local[0])
                output_table.put(f"{group}/warnings", local[1])
                output_table.put(f"{group}/info", local[2])
                continue

            # Create error subscriber if not already present
            if group not in cls.error_subscribers:
                cls.error_subscribers[group] = (
                    NetworkTableInstance.get_default()
                    .get_string_array_topic(f"{ALERT_TOPIC_ROOT}/{group}/errors")
                    .subscribe([])
                )

            # Create warning subscriber if not already present
            if group not in cls.warning_subscribers:
                cls.warning_subscribers[group] = (
                    NetworkTableInstance.get_default()
                    .get_string_array_topic(f"{ALERT_TOPIC_ROOT}/{group}/warnings")
                    .subscribe([])
                )

            # Create info subscriber if not already present
            if group not in cls.info_subscribers:
                cls.info_subscribers[group] = (
                    NetworkTableInstance.get_default()
                    .get_string_array_topic(f"{ALERT_TOPIC_ROOT}/{group}/info")
                    .subscribe([])
                )

            # Retrieve and log current alerts from subscribers
            output_table.put(f"{group}/errors", cls.error_subscribers[group].get())
            output_table.put(f"{group}/warnings", cls.warning_subscribers[group].get())
            output_table.put(f"{group}/info", cls.info_subscribers[group].get())

    @classmethod
    def register_group(cls, group: str) -> None:
        """
        Registers a new alert group to monitor.

        Registers a group name with the AlertLogger, enabling it to subscribe to and
        log alerts from the ``/Alerts/<group>`` topics for that group. If the group is already
        registered, this call is a no-op.

        Args:
            group (str): The name of the alert group to register. This group name
                will be used to form NetworkTables topic paths:
                - /Alerts/{group}/errors
                - /Alerts/{group}/warnings
                - /Alerts/{group}/info

        Example:
            AlertLogger.registerGroup("Drivetrain")
            AlertLogger.registerGroup("Shooter")
        """
        if group not in cls.groups:
            cls.groups.append(group)
