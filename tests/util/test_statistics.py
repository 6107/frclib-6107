"""Unit tests for MovingAverage and RobotStatistics."""

from unittest.mock import MagicMock

import pytest

from lib_6107.util.statistics import MovingAverage, RobotStatistics


def test_average_of_empty_window_is_zero():
    assert MovingAverage("x").average == 0.0


def test_average_scale_and_precision():
    avg = MovingAverage("x", scale=1000, precision=1)
    avg.add(0.0012)
    avg.add(0.0014)
    assert avg.average == pytest.approx(1.3)


def test_window_drops_oldest_samples():
    avg = MovingAverage("x", max_samples=2)
    for value in (10, 20, 30):
        avg.add(value)
    assert avg.average == 25


def test_add_without_count_accumulates_into_last_sample():
    avg = MovingAverage("x")
    avg.add(1.0)
    avg.add(2.0, count=False)
    assert avg.average == 3.0


def test_add_without_count_on_empty_window_appends():
    avg = MovingAverage("x")
    avg.add(2.0, count=False)
    assert avg.average == 2.0


def test_clear_resets_samples():
    avg = MovingAverage("x")
    avg.add(5)
    avg.clear()
    assert avg.average == 0.0


def _robot(disabled=False, teleop=False, auto=False):
    robot = MagicMock()
    robot.is_disabled.return_value = disabled
    robot.is_teleop.return_value = teleop
    robot.is_autonomous.return_value = auto
    return robot


def test_get_unknown_statistic_is_none():
    assert RobotStatistics(_robot()).get("nope") is None


def test_add_unknown_statistic_is_ignored():
    RobotStatistics(_robot()).add("nope", 1.0)


def test_periodic_duration_charged_to_teleop():
    stats = RobotStatistics(_robot(teleop=True))
    stats.add("teleop-duration", 1.0)
    stats.add("periodic-duration", 0.5)
    assert stats.get("teleop-duration").average == 1.5
    assert stats.get("periodic-duration").average == 0.5


def test_periodic_duration_charged_to_auto():
    stats = RobotStatistics(_robot(auto=True))
    stats.add("auto-duration", 2.0)
    stats.add("periodic-duration", 1.0)
    assert stats.get("auto-duration").average == 3.0


def test_periodic_duration_not_charged_when_disabled():
    stats = RobotStatistics(_robot(disabled=True, teleop=True))
    stats.add("teleop-duration", 1.0)
    stats.add("periodic-duration", 0.5)
    assert stats.get("teleop-duration").average == 1.0


def test_clear_one_and_all():
    stats = RobotStatistics(_robot())
    stats.add("periodic-duration", 1.0)
    stats.add("teleop-duration", 1.0)
    stats.clear("periodic-duration")
    assert stats.get("periodic-duration").average == 0.0
    assert stats.get("teleop-duration").average == 1.0
    stats.clear("all")
    assert stats.get("teleop-duration").average == 0.0
    stats.clear("unknown")
