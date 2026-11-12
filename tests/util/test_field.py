"""Unit tests for the Field base class (AprilTag layouts are not available in 2027 alpha-8 yet)."""

from unittest.mock import patch

import pytest

from lib_6107.util.field import Field


@pytest.fixture
def field():
    with patch("lib_6107.util.field.RobotBase.is_simulation", return_value=False):
        yield Field()


def test_defaults_without_layout(field):
    assert field.field_length == 0
    assert field.field_width == 0
    assert field.origin is None
    assert field.get_tag_pos(1) is None


def test_zone_checks_must_be_overridden(field):
    with pytest.raises(NotImplementedError):
        field.in_blue_alliance_zone(1.0)
    with pytest.raises(NotImplementedError):
        field.in_red_alliance_zone(1.0)


def test_subclass_supplies_zones():
    class MyField(Field):
        def in_blue_alliance_zone(self, x: float) -> bool:
            return x < 4.0

        def in_red_alliance_zone(self, x: float) -> bool:
            return x > 12.0

    with patch("lib_6107.util.field.RobotBase.is_simulation", return_value=False):
        f = MyField()
    assert f.in_blue_alliance_zone(1.0) and not f.in_red_alliance_zone(1.0)


def test_simulation_creates_field_chooser():
    with patch("lib_6107.util.field.RobotBase.is_simulation", return_value=True):
        f = Field()
    assert f._april_tag_chooser is not None
