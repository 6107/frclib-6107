"""Unit tests for alliance-based geometry flipping."""

from math import pi
from unittest.mock import MagicMock, patch

import pytest
from wpilib import Alliance
from wpimath import Pose2d, Rotation2d, Translation2d

from lib_6107.util.fliputil import FlipUtil


@pytest.fixture
def field():
    f = MagicMock()
    f.field_length = 16.0
    f.field_width = 8.0
    return f


def _alliance(alliance):
    return patch("lib_6107.util.fliputil.DriverStationBackend.get_alliance", return_value=alliance)


def test_should_flip_only_for_red():
    with _alliance(Alliance.RED):
        assert FlipUtil.should_flip() is True
    with _alliance(Alliance.BLUE):
        assert FlipUtil.should_flip() is False


def test_translation_unchanged_for_blue(field):
    with _alliance(Alliance.BLUE):
        result = FlipUtil(field).field_translation(Translation2d(2.0, 3.0))
    assert (result.x, result.y) == (2.0, 3.0)


def test_translation_mirrored_for_red(field):
    with _alliance(Alliance.RED):
        result = FlipUtil(field).field_translation(Translation2d(2.0, 3.0))
    assert result.x == pytest.approx(14.0)
    assert result.y == pytest.approx(5.0)


def test_rotation_flipped_by_pi_for_red():
    with _alliance(Alliance.RED):
        assert FlipUtil.field_rotation(Rotation2d(0.0)).radians() == pytest.approx(-pi)
    with _alliance(Alliance.BLUE):
        assert FlipUtil.field_rotation(Rotation2d(0.5)).radians() == pytest.approx(0.5)


def test_pose_flips_translation_and_rotation_for_red(field):
    with _alliance(Alliance.RED):
        pose = FlipUtil(field).field_pose(Pose2d(1.0, 1.0, Rotation2d(0.0)))
    assert pose.x == pytest.approx(15.0)
    assert pose.y == pytest.approx(7.0)
    assert abs(pose.rotation().radians()) == pytest.approx(pi)
