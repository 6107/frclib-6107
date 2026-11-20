"""Tests for the Elastic-editable Tunable used by ApproachTag."""

import pytest
from tunables import TunableRegistry

from lib_6107.commands.vision.approach_tag import Tunable


def test_settings_override_skips_tunable():
    t = Tunable({"GainTran": 2.0}, "ap", "GainTran", 0.5, (0.1, 8.0))
    assert t.chooser is None
    assert t() == 2.0


def test_default_value_is_published(tunables_backend):
    t = Tunable(None, "apt", "GainRot", 0.8, (0.1, 8.0))
    assert t() == pytest.approx(0.8)
    assert tunables_backend.get_value("/aptGainRot") == pytest.approx(0.8)


def test_int_default_is_accepted(tunables_backend):
    t = Tunable(None, "apt", "Headng", 30, (5, 45))
    assert t() == 30.0


def test_fetch_picks_up_elastic_edit(tunables_backend):
    t = Tunable(None, "apt", "Edit", 1.0, (0.0, 10.0))
    tunables_backend.set_double("/aptEdit", 4.0)
    TunableRegistry.update()
    assert t() == pytest.approx(4.0)


def test_out_of_range_edit_is_rejected(tunables_backend):
    t = Tunable(None, "apt", "Range", 1.0, (0.0, 2.0))
    tunables_backend.set_double("/aptRange", 9.0)
    TunableRegistry.update()
    assert t() == pytest.approx(1.0)
