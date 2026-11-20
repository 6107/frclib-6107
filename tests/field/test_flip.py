"""Unit tests for alliance-based geometry flipping."""

from math import pi

import pytest
from wpilib import Alliance
from wpimath import Pose2d, Rotation2d, Translation2d

from lib_6107.field.coordinates import DEFAULT_COORDINATES
from lib_6107.field.flip import FlipUtil


class StubField:
    coordinates = DEFAULT_COORDINATES
    field_length = 16.0
    field_width = 8.0

    def __init__(self, alliance):
        self.alliance = alliance


def test_should_flip_only_for_red():
    assert FlipUtil(StubField(Alliance.RED)).should_flip() is True
    assert FlipUtil(StubField(Alliance.BLUE)).should_flip() is False
    assert FlipUtil(StubField(None)).should_flip() is False


def test_translation_unchanged_for_blue():
    result = FlipUtil(StubField(Alliance.BLUE)).field_translation(Translation2d(2.0, 3.0))
    assert (result.x, result.y) == (2.0, 3.0)


def test_translation_mirrored_for_red():
    result = FlipUtil(StubField(Alliance.RED)).field_translation(Translation2d(2.0, 3.0))
    assert result.x == pytest.approx(14.0)
    assert result.y == pytest.approx(5.0)


def test_rotation_flipped_by_pi_for_red():
    assert FlipUtil(StubField(Alliance.RED)).field_rotation(Rotation2d(0.0)).radians() == pytest.approx(-pi)
    assert FlipUtil(StubField(Alliance.BLUE)).field_rotation(Rotation2d(0.5)).radians() == pytest.approx(0.5)


def test_pose_flips_translation_and_rotation_for_red():
    pose = FlipUtil(StubField(Alliance.RED)).field_pose(Pose2d(1.0, 1.0, Rotation2d(0.0)))
    assert pose.x == pytest.approx(15.0)
    assert pose.y == pytest.approx(7.0)
    assert abs(pose.rotation().radians()) == pytest.approx(pi)
