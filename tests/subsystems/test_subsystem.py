"""Unit tests for SubsystemBase."""

from unittest.mock import MagicMock

import pytest

from lib_6107.subsystems.subsystem import SubsystemBase


@pytest.fixture
def container():
    c = MagicMock()
    c.robot.period = 0.02
    return c


def test_init_captures_container_robot_and_period(container):
    sub = SubsystemBase(container, "Intake", "intake/indexer")
    assert sub.get_name() == "Intake"
    assert sub._long_name == "intake/indexer"
    assert sub._container is container
    assert sub._robot is container.robot
    assert sub._period == 0.02
    assert sub._physics_controller is None


def test_long_name_defaults_to_name(container):
    assert SubsystemBase(container, "Intake", None)._long_name == "Intake"


def test_not_initialized_until_derived_class_says_so(container):
    sub = SubsystemBase(container, "Intake", None)
    assert sub.is_initialized is False
    sub._initialized = True
    assert sub.is_initialized is True


def test_connection_checks_must_be_implemented(container):
    sub = SubsystemBase(container, "Intake", None)
    with pytest.raises(NotImplementedError):
        sub._check_is_connected(None)
    with pytest.raises(NotImplementedError):
        _ = sub.is_connected


def test_lifecycle_hooks_default_to_noops(container):
    sub = SubsystemBase(container, "Intake", None)
    assert sub.stop() is None
    assert sub.telemetry_init() is None
    assert sub.dashboard_periodic() is None
    assert sub.fault_detection("Disabled-Init") is None
    assert sub.record_metadata() is None
    assert sub.update_sim(0.0, 0.02) is None


def test_sim_init_stores_physics_controller(container):
    sub = SubsystemBase(container, "Intake", None)
    engine = MagicMock()
    sub.sim_init(engine)
    assert sub._physics_controller is engine
