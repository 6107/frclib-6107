"""Time helpers bridging WPILib 2027 nanosecond timestamps and pykit microsecond timestamps.

WPILib 2027 reports integer timestamps in nanoseconds. pykit, the WPILOG format and NetworkTables
wire formats continue to use microseconds, so all pykit internals go through these helpers.
"""

from wpilib import RobotController

NS_PER_US = 1000


def fpga_time_us() -> int:
    """Returns the current robot time in microseconds.

    Returns:
        The value of ``RobotController.get_time()`` (nanoseconds) converted to microseconds.
    """
    return int(RobotController.get_time()) // NS_PER_US


def us_to_ns(timestamp_us: int) -> int:
    """Converts a microsecond timestamp to nanoseconds.

    Args:
        timestamp_us: Timestamp in microseconds.

    Returns:
        The timestamp in nanoseconds.
    """
    return int(timestamp_us) * NS_PER_US
