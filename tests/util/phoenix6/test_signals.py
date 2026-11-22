"""Unit tests for the batched Phoenix 6 status-signal refresh helper."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.util.phoenix6.signals import Phoenix6Signals


@pytest.fixture(autouse=True)
def clean_registry():
    saved = set(Phoenix6Signals._signals)
    Phoenix6Signals._signals.clear()
    yield
    Phoenix6Signals._signals.clear()
    Phoenix6Signals._signals.update(saved)


def test_register_signal_adds_once():
    signal = MagicMock()
    Phoenix6Signals.register_signal(signal)
    Phoenix6Signals.register_signal(signal)
    assert Phoenix6Signals._signals == {signal}


def test_register_signals_adds_all():
    a, b = MagicMock(), MagicMock()
    Phoenix6Signals.register_signals(a, b)
    assert Phoenix6Signals._signals == {a, b}


def test_refresh_requests_all_registered_signals():
    a, b = MagicMock(), MagicMock()
    Phoenix6Signals.register_signals(a, b)
    with patch("lib_6107.util.phoenix6.signals.StatusSignal.refresh_all", return_value="ok") as refresh:
        assert Phoenix6Signals.refresh() == "ok"
    assert set(refresh.call_args.args) == {a, b}


def test_refresh_with_no_signals_skips_native_call():
    with patch('lib_6107.util.phoenix6.signals.StatusSignal.refresh_all') as refresh:
        Phoenix6Signals.refresh()
    refresh.assert_not_called()


def test_unregister_and_clear():
    a, b = MagicMock(), MagicMock()
    Phoenix6Signals.register_signals(a, b)
    Phoenix6Signals.unregister_signal(a)
    assert Phoenix6Signals._signals == {b}
    Phoenix6Signals.unregister_signal(a)
    Phoenix6Signals.clear()
    assert Phoenix6Signals._signals == set()
