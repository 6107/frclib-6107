"""Unit tests for REV helper utilities (2027 REVLib naming)."""

from unittest.mock import MagicMock

import pytest
from rev import REVLibError

from lib_6107.util.rev.utils import handle_faults, try_until_ok


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


def test_handle_faults_clears_sticky_faults():
    device = MagicMock()
    device.get_warnings.return_value = MagicMock(raw_bits=0)
    device.get_sticky_warnings.return_value = MagicMock(raw_bits=0)
    device.get_faults.return_value = MagicMock(raw_bits=0)
    device.get_sticky_faults.return_value = MagicMock(raw_bits=1, can=True)
    handle_faults("motor", "Disabled-Init", device, clear=True, notify=False)
    device.clear_faults.assert_called_once()
