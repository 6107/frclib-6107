"""Unit tests for the tunables-backed numeric edit boxes."""

import pytest

from lib_6107.util.numerical_chooser import FloatEditBox, IntegerEditBox


def test_integer_edit_box_accepts_initial_value():
    box = IntegerEditBox("Test/Int", 5, 0, 10)
    assert box.value == 5
    assert box.name == "Test/Int"
    assert str(box) == "5"


def test_integer_edit_box_rejects_out_of_range_and_wrong_type():
    box = IntegerEditBox("Test/Int2", 5, 0, 10)
    box.set_value(11)
    box.set_value(-1)
    box.set_value(2.5)
    box.set_value(True)
    assert box.value == 5


def test_integer_edit_box_remote_update_restores_on_invalid():
    box = IntegerEditBox("Test/Int3", 5, 0, 10)
    box._on_tune(8)
    assert box.value == 8
    box._on_tune(99)
    assert box.value == 8
    assert box._tunable.get() == 8


def test_integer_edit_box_without_initial_value_is_none():
    assert IntegerEditBox("Test/Int4").value is None


def test_float_edit_box_validates_range_and_type():
    box = FloatEditBox("Test/Float", 0.5, 0.0, 1.0)
    assert box.value == pytest.approx(0.5)
    box.set_value(2.0)
    box.set_value(3)
    assert box.value == pytest.approx(0.5)
    box.set_value(0.75)
    assert box.value == pytest.approx(0.75)
    assert "FloatEditBox" in repr(box)
