"""Unit tests for Phoenix 6 helper routines."""

from unittest.mock import MagicMock

import pytest
from phoenix6 import StatusCode

from lib_6107.util.phoenix6.utils import handle_faults, try_until_ok


def test_try_until_ok_returns_on_first_success():
    command = MagicMock(return_value=StatusCode.OK)
    assert try_until_ok("cfg", 3, command) == StatusCode.OK
    assert command.call_count == 1


def test_try_until_ok_retries_until_success():
    command = MagicMock(side_effect=[StatusCode.CONFIG_FAILED, StatusCode.OK])
    assert try_until_ok("cfg", 5, command) == StatusCode.OK
    assert command.call_count == 2


def test_try_until_ok_returns_last_failure_after_all_attempts():
    command = MagicMock(return_value=StatusCode.CONFIG_FAILED)
    assert try_until_ok("cfg", 3, command) == StatusCode.CONFIG_FAILED
    assert command.call_count == 3


def test_try_until_ok_rejects_negative_attempts():
    with pytest.raises(ValueError):
        try_until_ok("cfg", -1, MagicMock())


def test_handle_faults_is_currently_a_noop():
    assert handle_faults("dev", "Disabled-Init", MagicMock()) is None
