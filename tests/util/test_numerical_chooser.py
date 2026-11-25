"""Unit tests for the tunables-backed numeric edit boxes."""

import pytest

from lib_6107.dashboard.numerical_chooser import FloatEditBox, IntegerEditBox


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


def test_edit_boxes_publish_matching_tunable_types(tunables_backend):
    IntegerEditBox("Test/PubInt", 3)
    FloatEditBox("Test/PubFloat", 1.5)
    assert tunables_backend.get_value("/Test/PubInt") == 3
    assert tunables_backend.get_value("/Test/PubFloat") == 1.5


def test_edit_boxes_without_initial_value_publish_type_default(tunables_backend):
    IntegerEditBox("Test/DefInt")
    FloatEditBox("Test/DefFloat")
    assert tunables_backend.get_value("/Test/DefInt") == 0
    assert tunables_backend.get_value("/Test/DefFloat") == 0.0


def test_integer_edit_box_does_not_bind_publisher_as_method():
    # _ADD is a plain function stored on the class; it must not receive ``self``
    box = IntegerEditBox("Test/Bound", 1)
    assert box._tunable is not None


def test_float_edit_box_rejects_int_and_bool():
    box = FloatEditBox("Test/StrictFloat", 0.5)
    box.set_value(1)
    box.set_value(True)
    assert box.value == pytest.approx(0.5)
