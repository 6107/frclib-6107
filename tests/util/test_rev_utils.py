"""Unit tests for REV helper utilities (2027 REVLib naming)."""

from unittest.mock import MagicMock, patch

import pytest
from rev import REVLibError, Signal_SparkFaults, Signal_SparkWarnings, SparkBase

from lib_6107.util.rev.utils import active_flags, handle_faults, signal_value, try_until_ok


def test_try_until_ok_returns_on_first_success():
    command = MagicMock(return_value=REVLibError.OK)
    assert try_until_ok("cfg", 3, command) == REVLibError.OK
    assert command.call_count == 1


def test_try_until_ok_retries_then_fails():
    command = MagicMock(return_value=REVLibError.TIMEOUT)
    assert try_until_ok("cfg", 2, command) == REVLibError.TIMEOUT
    assert command.call_count == 2


def test_try_until_ok_rejects_zero_attempts():
    with pytest.raises(ValueError):
        try_until_ok("cfg", 0, MagicMock())


def _faults(bits=0, error=REVLibError.OK):
    return Signal_SparkFaults(SparkBase.Faults(bits), error, 0)


def _warnings(bits=0, error=REVLibError.OK):
    return Signal_SparkWarnings(SparkBase.Warnings(bits), error, 0)


def _device(faults=0, sticky_faults=0, warnings=0, sticky_warnings=0, error=REVLibError.OK):
    device = MagicMock()
    device.get_faults.return_value = _faults(faults, error)
    device.get_sticky_faults.return_value = _faults(sticky_faults, error)
    device.get_warnings.return_value = _warnings(warnings, error)
    device.get_sticky_warnings.return_value = _warnings(sticky_warnings, error)
    return device


def test_active_flags_names_from_value():
    assert active_flags(SparkBase.Faults(4)) == ["sensor"]
    assert active_flags(SparkBase.Warnings(0)) == []


def test_signal_value_none_when_invalid():
    assert signal_value(_faults(1, REVLibError.TIMEOUT)) is None
    assert signal_value(_faults(1)).raw_bits == 1


def test_handle_faults_clears_sticky_faults():
    device = _device(sticky_faults=1)
    handle_faults("motor", "Disabled-Init", device, clear=True, notify=False)
    device.clear_faults.assert_called_once()


def test_handle_faults_clear_false_keeps_faults():
    device = _device(sticky_faults=1)
    handle_faults("motor", "Disabled-Init", device, clear=False, notify=False)
    device.clear_faults.assert_not_called()


def test_handle_faults_active_only_does_not_clear():
    device = _device(faults=4, warnings=1)
    handle_faults("motor", "Teleop", device, clear=True, notify=False)
    device.clear_faults.assert_not_called()


def test_handle_faults_invalid_signal_ignored():
    device = _device(faults=4, sticky_faults=4, error=REVLibError.TIMEOUT)
    with patch("lib_6107.util.rev.utils.send_notification") as notify:
        handle_faults("motor", "Teleop", device, clear=True, notify=True)
    notify.assert_not_called()
    device.clear_faults.assert_not_called()


def test_handle_faults_notifies_with_flag_names(caplog):
    device = _device(sticky_faults=4)
    with patch("lib_6107.util.rev.utils.send_notification") as notify:
        handle_faults("motor", "Teleop", device, clear=False, notify=True)
    notify.assert_called_once()
    assert "sensor" in notify.call_args.args[0].description


def test_handle_faults_exception_logged_once(caplog):
    device = MagicMock()
    device.get_warnings.side_effect = RuntimeError("boom")
    with caplog.at_level("ERROR"):
        for _ in range(3):
            handle_faults("exploding-motor", "Teleop", device, notify=False)
    assert len([r for r in caplog.records if "exploding-motor" in r.getMessage()]) == 1
