"""Unit tests for lib_6107.dashboard.preflight."""

from unittest.mock import MagicMock

import pytest
from lib_6107.dashboard import preflight
from lib_6107.dashboard.preflight import PreflightChecklist

MODULE = "lib_6107.dashboard.preflight"


class FakeBool:
    def __init__(self, key, default):
        self.key = key
        self.value = default


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(f"{MODULE}.LoggedNetworkBoolean", FakeBool)
    monkeypatch.setattr(f"{MODULE}.Alert", MagicMock(side_effect=lambda *a, **k: MagicMock()))


def test_checklist_starts_incomplete_with_all_missing():
    cl = PreflightChecklist()
    assert len(cl.checks) == 6
    assert not cl.is_complete()
    assert cl.missing() == [c.name for c in cl.checks]


def test_checklist_complete_when_all_expected_set():
    cl = PreflightChecklist()
    for c in cl.checks:
        c._value.value = True
    assert cl.is_complete()
    assert cl.missing() == []


def test_checklist_partial_missing():
    cl = PreflightChecklist()
    cl.checks[0]._value.value = True
    assert cl.checks[0].name not in cl.missing()
    assert len(cl.missing()) == 5
    assert not cl.is_complete()


def test_update_sets_alert_for_each_check():
    cl = PreflightChecklist()
    cl.checks[1]._value.value = True
    cl.update()
    cl.checks[0].alert.set.assert_called_with(True)
    cl.checks[1].alert.set.assert_called_with(False)


def test_check_value_with_expected_false():
    check = PreflightChecklist.PreflightCheck("n", "Preflight/x", False)
    assert check._value.value is True
    assert check.value() is False
    check._value.value = False
    assert check.value() is True


def test_check_str_and_repr():
    check = PreflightChecklist.PreflightCheck("Name", "Preflight/x", True)
    assert repr(check) == "PreflightCheck(Name: False)"
    assert str(check) == repr(check)
    assert check.name == "Name"


def test_alert_constructed_with_failure_text():
    PreflightChecklist.PreflightCheck("Name", "Preflight/x", True)
    args = preflight.Alert.call_args.args
    assert args[0] == "preflight"
    assert "Check Failed: Name" in args
