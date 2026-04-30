# Imported from https://github.com/Gold872/elastic_dashboard/blob/main/elasticlib/elasticlib.py
# pylint: disable=global-statement,broad-exception-caught

import json
from enum import Enum

from ntcore import NetworkTableInstance, PubSubOptions


class NotificationLevel(Enum):
    """
    Enumeration representing the severity levels for dashboard notifications.

    This enum defines the different priority/severity levels that can be assigned
    to notifications displayed on the Elastic dashboard. Each level corresponds to
    a visual severity indicator in the dashboard UI.

    Attributes:
        INFO: Informational notification level - used for general updates and
              non-critical information.
        WARNING: Warning notification level - used for alerts that require attention
                 but are not critical errors.
        ERROR: Error notification level - used for critical errors that require
               immediate attention and action.

    Example:
        >>> notification = Notification(
        ...     level=NotificationLevel.WARNING,
        ...     title="Battery Low",
        ...     description="Robot battery is running low"
        ... )
        >>> send_notification(notification)
    """
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Notification:
    """
    Represents a notification to be displayed on the Elastic dashboard.

    This class encapsulates all the information needed to display a notification
    in the Elastic dashboard, including severity level, title, description, and
    display properties. Notifications are used to alert operators of important
    events during robot operation (e.g., preflight checks, faults, status updates).

    Notifications are typically created and sent using send_notification() function
    which publishes them to the dashboard via NetworkTables.

    Attributes:
        level (NotificationLevel): The severity level of the notification (INFO, WARNING, or ERROR).
                                    Determines the visual styling and priority on the dashboard.
        title (str): The title/heading of the notification, displayed prominently.
        description (str): The detailed message body of the notification.
        display_time (int): Duration in milliseconds that the notification persists on screen.
                           Defaults to 3000ms (3 seconds).
        width (float): Width of the notification display area in pixels. Defaults to 350px.
        height (float): Height of the notification display area in pixels.
                       Defaults to -1 (automatic height based on content).

    Example:
        >>> # Create and send an informational notification
        >>> status_notif = Notification(
        ...     level=NotificationLevel.INFO,
        ...     title="Pre-match Check",
        ...     description="All systems operational"
        ... )
        >>> send_notification(status_notif)

        >>> # Create an error notification with custom display time
        >>> error_notif = Notification(
        ...     level=NotificationLevel.ERROR,
        ...     title="Motor Fault",
        ...     description="Left drive motor temperature critical",
        ...     display_time=5000
        ... )
        >>> send_notification(error_notif)
    """

    def __init__(
            self,
            level = NotificationLevel.INFO,
            title: str = "",
            description: str = "",
            display_time: int = 3000,
            width: float = 350,
            height: float = -1,
    ):
        """
        Initializes a Notification object.

        Args:
            level (NotificationLevel): The severity level of the notification.
                                       Defaults to NotificationLevel.INFO.
            title (str): The title/heading of the notification.
                        Defaults to an empty string.
            description (str): The detailed message or body text of the notification.
                              Defaults to an empty string.
            display_time (int): Time in milliseconds for which the notification should remain
                               visible on the dashboard. Defaults to 3000 ms (3 seconds).
            width (float): Width of the notification display area in pixels.
                          Defaults to 350 pixels.
            height (float): Height of the notification display area in pixels.
                           Defaults to -1 (automatic height based on content).
        """
        self.level = level
        self.title = title
        self.description = description
        self.display_time = display_time
        self.width = width
        self.height = height


__selected_tab_topic = None
__selected_tab_publisher = None

__notification_topic = None
__notification_publisher = None


def send_notification(notification: Notification):
    """
    Publishes a notification to the Elastic dashboard via NetworkTables.

    This function sends a notification to the Elastic dashboard by serializing the
    Notification object to JSON and publishing it to the "/Elastic/RobotNotifications"
    NetworkTables topic. The notification appears on the dashboard with styling and
    behavior determined by its severity level (INFO, WARNING, or ERROR).

    The function uses lazy initialization of NetworkTables topics and publishers,
    which are cached as module-level globals to avoid repeated initialization overhead.
    This approach is optimized for competitive matches where notifications may be sent
    frequently.

    Thread Safety:
        This function uses global state (module-level publisher variables) and is
        not thread-safe. Ensure this function is called from the main robot thread
        or properly synchronize access in multi-threaded environments.

    Args:
        notification (Notification): The notification object to publish. Must be a
                                    Notification instance with properly configured
                                    level, title, description, and display properties.

    Raises:
        Exception: If there is an error during JSON serialization or NetworkTables
                  publishing. The exception is caught and printed to stderr but not
                  re-raised, allowing robot code to continue operation. Check console
                  logs if notifications fail to appear on the dashboard.

    Example:
        >>> # Send an informational status notification
        >>> from lib_6107.util.elastic_utils import Notification, NotificationLevel, send_notification
        >>> notif = Notification(
        ...     level=NotificationLevel.INFO,
        ...     title="System Status",
        ...     description="Robot initialized successfully"
        ... )
        >>> send_notification(notif)

        >>> # Send a warning that persists longer than default
        >>> warning = Notification(
        ...     level=NotificationLevel.WARNING,
        ...     title="Low Battery",
        ...     description="Battery voltage below 10.5V",
        ...     display_time=5000
        ... )
        >>> send_notification(warning)

        >>> # Send an error with custom dimensions
        >>> error = Notification(
        ...     level=NotificationLevel.ERROR,
        ...     title="Motor Disconnected",
        ...     description="Right front drive motor timeout",
        ...     display_time=7000,
        ...     width=450
        ... )
        >>> send_notification(error)

    Note:
        - Notifications are automatically converted to a JSON object with camelCase keys
          for compatibility with the Elastic dashboard frontend.
        - The display_time parameter specifies how long the notification persists;
          set it to 0 for permanent notifications (manual dismissal required).
        - This function should typically be called from robotPeriodic() or command
          execution, not from initialization routines.
    """
    global __notification_topic
    global __notification_publisher

    if not __notification_topic:
        __notification_topic = NetworkTableInstance.getDefault().getStringTopic(
            "/Elastic/RobotNotifications"
        )
    if not __notification_publisher:
        __notification_publisher = __notification_topic.publish(
            PubSubOptions(sendAll=True, keepDuplicates=True)
        )

    try:
        __notification_publisher.set(
            json.dumps(
                {
                    "level"      : notification.level.value,
                    "title"      : notification.title,
                    "description": notification.description,
                    "displayTime": notification.display_time,
                    "width"      : notification.width,
                    "height"     : notification.height,
                }
            )
        )
    except Exception as e:
        print(f"Error serializing notification: {e}")


def select_tab(tab_name: str):
    """
    Selects (switches to) a specific tab in the Elastic dashboard by name or index.

    This function publishes a tab selection command to the Elastic dashboard via
    NetworkTables, causing the specified tab to become the active/visible tab.
    The dashboard will display the tab's widgets and content immediately.

    Tab Selection Modes:
        - **By Name**: Pass the exact name of the tab as displayed in the dashboard.
          If no tab with that name exists, nothing happens and the current tab remains active.
        - **By Index**: Pass a numeric string (e.g., "0", "1", "2") to select the tab
          at that position (0-indexed). Invalid indices are silently ignored.

    The function uses lazy initialization with module-level globals for the NetworkTables
    topic and publisher, optimizing repeated calls during competition operation.

    Thread Safety:
        This function uses global state (module-level publisher variables) and is
        not thread-safe. Ensure this function is called from the main robot thread
        or properly synchronize access in multi-threaded environments.

    Args:
        tab_name (str): The name or numeric index of the tab to select.
                       For named selection, pass the exact tab name (e.g., "Shooter").
                       For index selection, pass a numeric string (e.g., "0", "1", "2").

    Returns:
        None

    Example:
        >>> from lib_6107.util.elastic_utils import select_tab, select_tab_index

        >>> # Select a tab by name
        >>> select_tab("Drivetrain")

        >>> # Select a tab by numeric index (second tab)
        >>> select_tab("1")

        >>> # Equivalent to above, using the dedicated index function
        >>> select_tab_index(1)

        >>> # Select first tab
        >>> select_tab_index(0)

    Note:
        - This function is typically called from subsystems during mode transitions
          (e.g., switching to autonomous vs. teleop view) or from commands that need
          to display specific dashboard tabs.
        - The dashboard does not provide feedback if the tab selection fails; ensure
          your dashboard configuration matches the tab names used in this function.
        - Use select_tab_index() for numeric selection to avoid string conversion confusion.
        - There is no return value or exception raised if the tab is not found;
          the operation silently succeeds or fails on the dashboard side.
    """
    global __selected_tab_topic
    global __selected_tab_publisher

    if not __selected_tab_topic:
        __selected_tab_topic = NetworkTableInstance.getDefault().getStringTopic(
            "/Elastic/SelectedTab"
        )
    if not __selected_tab_publisher:
        __selected_tab_publisher = __selected_tab_topic.publish(
            PubSubOptions(keepDuplicates=True)
        )

    __selected_tab_publisher.set(tab_name)


def select_tab_index(tab_index: int):
    """
    Selects a tab in the Elastic dashboard by its numeric index (0-based).

    This is a convenience wrapper around select_tab() that converts an integer tab
    index to a string and delegates the actual selection. This function is the
    recommended approach when you have a numeric tab identifier rather than a tab name.

    Tabs are indexed starting from 0 (the first tab is at index 0, second at index 1,
    etc.). If the provided index is out of bounds (greater than or equal to the number
    of tabs), the operation silently fails and the dashboard retains the current tab.

    Thread Safety:
        This function uses global state (module-level publisher variables shared with
        select_tab()) and is not thread-safe. Ensure this function is called from the
        main robot thread or properly synchronize access in multi-threaded environments.

    Args:
        tab_index (int): The 0-based numeric index of the tab to select.
                        Valid indices range from 0 to (number_of_tabs - 1).
                        Out-of-bounds indices are silently ignored by the dashboard.

    Returns:
        None

    Example:
        >>> from lib_6107.util.elastic_utils import select_tab_index

        >>> # Select the first tab (index 0)
        >>> select_tab_index(0)

        >>> # Select the second tab (index 1)
        >>> select_tab_index(1)

        >>> # Select the third tab (index 2)
        >>> select_tab_index(2)

        >>> # Invalid index (silently ignored by dashboard)
        >>> select_tab_index(99)  # No effect if only 3 tabs exist

    Note:
        - This function internally calls select_tab(str(tab_index)) to perform the
          actual NetworkTables publication. Both functions share the same NetworkTables
          topic and publisher globals.
        - Use this function when you have a numeric tab identifier; use select_tab()
          directly when selecting tabs by name.
        - Typical use cases include programmatic tab switching during autonomous
          transitions, command execution, or based on sensor/game data.
        - The dashboard provides no feedback if the index is invalid; ensure your
          dashboard has enough tabs for the indices you're using.
        - Calling this function with negative indices (e.g., -1 for last tab) will
          convert to a string and be passed to the dashboard as-is; behavior depends
          on the dashboard's index parsing implementation.
    """
    select_tab(str(tab_index))
