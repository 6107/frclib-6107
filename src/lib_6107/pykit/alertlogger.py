"""
Alert Logger Module

This module provides the AlertLogger class for managing and monitoring alerts from NetworkTables.
It subscribes to SmartDashboard alert topics and periodically retrieves and logs alerts by category
(errors, warnings, info).
"""

from ntcore import NetworkTableInstance, StringArraySubscriber

from lib_6107.pykit.logtable import LogTable


class AlertLogger:
    """
    Singleton class for managing and logging alerts from NetworkTables.
    
    This class monitors alert groups and retrieves alerts from SmartDashboard topics
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

    @classmethod
    def periodic(cls, output_table: LogTable) -> None:
        """
        Periodically checks for new alerts and logs them to the output table.
        
        This method should be called regularly (typically in the robot's periodic method)
        to retrieve the latest alerts from each registered group. For each group, it:
        1. Creates subscribers for each alert level if they don't exist
        2. Retrieves the latest alert arrays from NetworkTables
        3. Writes the alerts to the output LogTable
        
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
            
            # Create error subscriber if not already present
            if group not in cls.error_subscribers:
                cls.error_subscribers[group] = (
                    NetworkTableInstance.getDefault()
                    .getStringArrayTopic(f"/SmartDashboard/{group}/errors")
                    .subscribe([])
                )
            
            # Create warning subscriber if not already present
            if group not in cls.warning_subscribers:
                cls.warning_subscribers[group] = (
                    NetworkTableInstance.getDefault()
                    .getStringArrayTopic(f"/SmartDashboard/{group}/warnings")
                    .subscribe([])
                )
            
            # Create info subscriber if not already present
            if group not in cls.info_subscribers:
                cls.info_subscribers[group] = (
                    NetworkTableInstance.getDefault()
                    .getStringArrayTopic(f"/SmartDashboard/{group}/info")
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
        log alerts from SmartDashboard topics for that group. If the group is already
        registered, this call is a no-op.
        
        Args:
            group (str): The name of the alert group to register. This group name
                will be used to form NetworkTables topic paths:
                - /SmartDashboard/{group}/errors
                - /SmartDashboard/{group}/warnings
                - /SmartDashboard/{group}/info
                
        Example:
            AlertLogger.registerGroup("Drivetrain")
            AlertLogger.registerGroup("Shooter")
        """
        if group not in cls.groups:
            cls.groups.append(group)