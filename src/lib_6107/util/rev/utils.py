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

import logging
from collections.abc import Callable

from rev import REVLibError, SparkFlex, SparkFlexSim, SparkMax, SparkMaxSim

from lib_6107.util.elastic_utils import Notification, NotificationLevel, send_notification

logger = logging.getLogger(__name__)

SparkDevices = SparkFlex | SparkMax | SparkFlexSim | SparkMaxSim

# Devices whose exception has already been reported, so a broken device does not flood the log every mode change
_reported_failures: set[str] = set()


def active_flags(bits: object) -> list[str]:
    """
    Return the names of the boolean flags that are set on a REV Faults/Warnings value

    The names come from the object itself, so they follow whatever the installed REVLib defines.
    """
    return sorted(
        name
        for name in dir(bits)
        if not name.startswith("_") and name != "raw_bits" and getattr(bits, name, False) is True
    )


def signal_value(signal: object) -> object | None:
    """
    Unwrap a REVLib 2027 Signal, returning None when the signal has no valid (recent) data
    """
    return signal.get() if signal.is_valid() else None


def try_until_ok(what: str, attempts: int, command: Callable[[], REVLibError]) -> REVLibError:
    """
    Repeat a command for certain number of attempts or until it succeeds
    """
    if attempts <= 0:
        raise ValueError(f"{what} -> {str(command)}: Attempts must be greater than 0")
    prev_code: REVLibError | None = None

    for attempt in range(attempts):
        code: REVLibError = command()

        if code == REVLibError.OK:
            if attempt > 0:
                logger.warning(
                    f"{what}: {str(command)} succeeded on {attempt} attempt last failed status: {prev_code.value} - {prev_code.name}"
                )
            return code
        prev_code = code

    logger.error(f"{what}: {str(command)} failed after {attempts} attempts. Final Status: {code.value} - {code.name}")
    return code


def handle_faults(
    name: str, state: str, device: SparkDevices, clear: bool | None = True, notify: bool | None = True
) -> None:
    """
    This routine is responsible for reading any existing faults and based
    input parameters, report them for display, and possibly clear them

    All faults detected always results in a warning log message, so please be
    aware of this if you do not clear them

    TODO: Good thing for a base class, don't you think
    """

    def elastic_notification(title: str, message: str, level: NotificationLevel) -> None:
        send_notification(Notification(level=level, title=title, description=message))

    def report(title: str, bits: object | None, sticky: bool) -> None:
        # None means the signal had no valid data; raw_bits == 0 means nothing is set
        if bits is None or bits.raw_bits == 0:
            return
        msg = f"Device {name} during {state}: ({', '.join(active_flags(bits))})"
        if notify:
            elastic_notification(title, msg, NotificationLevel.WARNING)
        logger.warning("%s: %s", title, msg)
        nonlocal sticky_issues_found
        sticky_issues_found = sticky_issues_found or sticky

    sticky_issues_found = False
    try:
        # REVLib 2027 returns Signal wrappers; the bitmask value is signal.get() and may be stale
        report("Active Warning", signal_value(device.get_warnings()), False)
        report("'Sticky' Warning", signal_value(device.get_sticky_warnings()), True)
        report("Active Fault", signal_value(device.get_faults()), False)
        report("'Sticky' Fault", signal_value(device.get_sticky_faults()), True)

        if clear and sticky_issues_found:
            device.clear_faults()

    except Exception as e:
        if name not in _reported_failures:
            _reported_failures.add(name)
            logger.exception("REV:handle_faults: Exception while processing faults for %s: %s", name, e)
