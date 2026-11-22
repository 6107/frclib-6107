from unittest.mock import patch

import pytest

from lib_6107.util import telemetry_mode


@pytest.fixture(autouse=True)
def loggers():
    with (
        patch("lib_6107.util.telemetry_mode.SignalLogger") as sig,
        patch("lib_6107.util.telemetry_mode.StatusLogger") as stat,
    ):
        telemetry_mode._diagnostic_enabled = False
        yield sig, stat
        telemetry_mode._diagnostic_enabled = False


def test_default_disables_vendor_logging(loggers):
    sig, stat = loggers
    telemetry_mode.disable_vendor_auto_logging()
    sig.enable_auto_logging.assert_called_once_with(False)
    stat.disable_auto_logging.assert_called_once()
    sig.start.assert_not_called()
    stat.start.assert_not_called()
    assert not telemetry_mode.is_diagnostic_logging_enabled()


def test_enable_starts_both_loggers_once(loggers):
    sig, stat = loggers
    telemetry_mode.enable_diagnostic_logging()
    telemetry_mode.enable_diagnostic_logging()
    sig.enable_auto_logging.assert_called_once_with(True)
    sig.start.assert_called_once()
    stat.start.assert_called_once()
    assert telemetry_mode.is_diagnostic_logging_enabled()


def test_disable_stops_loggers_only_if_enabled(loggers):
    sig, stat = loggers
    telemetry_mode.disable_diagnostic_logging()
    sig.stop.assert_not_called()

    telemetry_mode.enable_diagnostic_logging()
    telemetry_mode.disable_diagnostic_logging()
    sig.stop.assert_called_once()
    stat.stop.assert_called_once()
    assert not telemetry_mode.is_diagnostic_logging_enabled()
