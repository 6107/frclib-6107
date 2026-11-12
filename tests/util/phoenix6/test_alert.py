"""Unit tests for the CTRE alert helper."""

from unittest.mock import MagicMock

import pytest
from phoenix6 import StatusCode

from lib_6107.util.phoenix6.alert import Alert


@pytest.fixture(autouse=True)
def clean_registry():
    saved = list(Alert.registry)
    Alert.registry.clear()
    yield
    Alert.registry[:] = saved


def test_new_alert_is_registered_and_inactive():
    alert = Alert("Motor 1 hot")
    assert alert in Alert.registry
    assert alert.active is False


def test_set_toggles_active_and_refreshes_once_per_change():
    alert = Alert("Motor 1 hot", is_error=True)
    alert.set(True)
    assert alert.active is True
    alert.set(True)
    assert alert.active is True
    alert.set(False)
    assert alert.active is False


def test_clear_sticky_clears_alert_when_device_succeeds():
    alert = Alert("fault", ctre_device=MagicMock(), clear_func=MagicMock(return_value=StatusCode.OK))
    alert.set(True)
    assert alert.clear_sticky() == StatusCode.OK
    assert alert.active is False


def test_clear_sticky_keeps_alert_when_device_fails():
    alert = Alert("fault", ctre_device=MagicMock(), clear_func=MagicMock(return_value=StatusCode.CONFIG_FAILED))
    alert.set(True)
    alert.clear_sticky()
    assert alert.active is True


def test_clear_all_device_sticky_faults_clears_each_device_once():
    device = MagicMock()
    Alert("a", ctre_device=device)
    Alert("b", ctre_device=device)
    Alert("c")
    Alert.clear_all_device_sticky_faults()
    device.clear_sticky_faults.assert_called_once_with()
