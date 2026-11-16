"""Tests for the LoggedRobot main loop on the 2027 HAL notifier API."""

import threading
from unittest.mock import patch

import pytest

from lib_6107.pykit.loggedrobot import LoggedRobot


class CountingRobot(LoggedRobot):
    def __init__(self, stop_after: int) -> None:
        super().__init__(period=0.01)
        self.loops = 0
        self.stop_after = stop_after

    def _loop_func(self) -> None:
        self.loops += 1
        if self.loops >= self.stop_after:
            self.end_competition()


def run_with_timeout(robot: LoggedRobot, timeout: float = 5.0) -> None:
    thread = threading.Thread(target=robot.start_competition, daemon=True)
    with patch("lib_6107.pykit.loggedrobot.Logger"):
        thread.start()
        thread.join(timeout)
    assert not thread.is_alive(), "main loop did not exit after end_competition()"


def test_notifier_is_created_with_valid_handle():
    robot = CountingRobot(1)
    try:
        assert robot._notifier
    finally:
        robot.end_competition()
    assert robot._notifier is None


def test_end_competition_is_idempotent():
    robot = CountingRobot(1)
    robot.end_competition()
    robot.end_competition()
    assert robot._notifier is None


def test_main_loop_runs_until_end_competition():
    robot = CountingRobot(3)
    run_with_timeout(robot)
    assert robot.loops >= 3
