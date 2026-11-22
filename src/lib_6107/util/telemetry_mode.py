"""
Opt-in vendor diagnostic logging (CTRE SignalLogger and REV StatusLogger).

pykit is the only logging sink during a match. Both vendor loggers run their own native
threads and write their own files, so they are kept off by default and are only enabled
for calibration, SysId or bench diagnostics.
"""

from __future__ import annotations

import logging

from phoenix6 import SignalLogger
from rev import StatusLogger

logger = logging.getLogger(__name__)

_diagnostic_enabled = False


def is_diagnostic_logging_enabled() -> bool:
    return _diagnostic_enabled


def disable_vendor_auto_logging() -> None:
    """Default state: no vendor-owned logging threads."""
    global _diagnostic_enabled
    SignalLogger.enable_auto_logging(False)
    StatusLogger.disable_auto_logging()
    _diagnostic_enabled = False


def enable_diagnostic_logging() -> None:
    """Start the vendor loggers. Intended for test/calibration mode only."""
    global _diagnostic_enabled
    if _diagnostic_enabled:
        return
    SignalLogger.enable_auto_logging(True)
    SignalLogger.start()
    StatusLogger.start()
    _diagnostic_enabled = True
    logger.info("Vendor diagnostic logging enabled")


def disable_diagnostic_logging() -> None:
    """Stop the vendor loggers started by enable_diagnostic_logging."""
    global _diagnostic_enabled
    if not _diagnostic_enabled:
        return
    SignalLogger.stop()
    StatusLogger.stop()
    SignalLogger.enable_auto_logging(False)
    _diagnostic_enabled = False
    logger.info("Vendor diagnostic logging disabled")
