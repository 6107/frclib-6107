"""Unit tests for trajectory helpers."""

import pytest
from wpimath import Rotation2d, Translation2d

from lib_6107.commands.drivetrain import trajectory as t


def test_mirror_tuple_and_formats():
    assert t.mirror((1.0, 2.0)) == (1.0, t.FIELD_WIDTH - 2.0)
    res = t.mirror([(1.0, 2.0), (1.0, 2.0, 30.0), (1.0, 2.0, None)])
    assert res[0] == (1.0, t.FIELD_WIDTH - 2.0)
    assert res[1] == (1.0, t.FIELD_WIDTH - 2.0, -30.0)
    assert res[2][2] == 0.0


def test_mirror_translation_waypoints_and_unknown():
    loc = Translation2d(1.0, 2.0)
    res = t.mirror([(loc, Rotation2d.from_degrees(10).degrees()), (1, 2, 3, 4)], width=10)
    assert res[0][0].y == pytest.approx(8.0)
    assert res[0][1] == -10.0
    assert len(res) == 1  # unknown format is skipped


def test_flip_waypoint():
    pt, rot = t._flipWaypoint((Translation2d(1, 2), Rotation2d.from_degrees(0)))
    assert pt.x == pytest.approx(t.FIELD_LENGTH - 1)
    assert pt.y == pytest.approx(t.FIELD_WIDTH - 2)
    assert abs(rot.degrees()) == pytest.approx(180)
    _, rot = t._flipWaypoint((Translation2d(1, 2), None))
    assert rot is None


def test_same_direction():
    assert t._sameDirection(Translation2d(1, 0), Translation2d(1, 0.1))
    assert not t._sameDirection(Translation2d(1, 0), Translation2d(-1, 0))
