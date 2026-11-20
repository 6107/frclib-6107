"""Unit tests for PhysicsEngine (src/lib_6107/physics.py)."""

from unittest.mock import MagicMock, patch

import pytest
from wpimath import Pose2d

from lib_6107.constants import SimulationConstants
from lib_6107.physics import PhysicsEngine


def make_fake_subsystem(name = "Subsystem", **hooks):
    """Create a MagicMock subsystem restricted to the given hook names plus getName()."""
    mock = MagicMock(spec=[*hooks.keys(), "get_name"])
    mock.get_name.return_value = name
    for hook_name, value in hooks.items():
        setattr(mock, hook_name, value)
    return mock


def make_fake_robot(subsystems = (), is_red_alliance = False, alliance_location = 1):
    """Create a lightweight fake Robot/container pair for PhysicsEngine construction."""
    robot = MagicMock()
    robot.field2d = MagicMock()
    robot.simulation_constants = SimulationConstants()
    robot.container.subsystems = subsystems
    robot.container.is_red_alliance = is_red_alliance
    robot.container.alliance_location = alliance_location
    robot.container.register_alliance_change_callback = MagicMock()
    return robot


class TestPhysicsEngineInit:
    """Tests for PhysicsEngine.__init__."""

    def test_calls_sim_init_on_subsystems_that_implement_it(self):
        sim_init = MagicMock()
        sub = make_fake_subsystem(sim_init=sim_init)
        robot = make_fake_robot(subsystems=(sub,))

        engine = PhysicsEngine(robot)

        sim_init.assert_called_once_with(engine)

    def test_skips_subsystems_without_sim_init(self):
        sub = make_fake_subsystem()
        robot = make_fake_robot(subsystems=(sub,))

        # Should not raise even though subsystem has no sim_init hook.
        PhysicsEngine(robot)

        assert not hasattr(sub, "sim_init")

    def test_sets_field_from_robot(self):
        robot = make_fake_robot(subsystems=())
        engine = PhysicsEngine(robot)
        assert engine.field2d is robot.field2d

    def test_registers_alliance_change_callback(self):
        robot = make_fake_robot(subsystems=())
        engine = PhysicsEngine(robot)
        robot.container.register_alliance_change_callback.assert_called_once_with(engine._alliance_change)

    def test_fires_initial_pose_update_for_blue_alliance(self):
        robot = make_fake_robot(subsystems=(), is_red_alliance=False, alliance_location=2)
        PhysicsEngine(robot)
        expected_pose = robot.simulation_constants.BLUE_TEST_POSE[2]
        robot.field2d.set_robot_pose.assert_called_once_with(expected_pose)

    def test_fires_initial_pose_update_for_red_alliance(self):
        robot = make_fake_robot(subsystems=(), is_red_alliance=True, alliance_location=3)
        PhysicsEngine(robot)
        expected_pose = robot.simulation_constants.RED_TEST_POSE[3]
        robot.field2d.set_robot_pose.assert_called_once_with(expected_pose)


class TestPhysicsEngineUpdateSim:
    """Tests for PhysicsEngine.update_sim()."""

    def test_calls_update_sim_hook_on_each_subsystem(self):
        update_sim = MagicMock(return_value=None)
        sub = make_fake_subsystem(update_sim=update_sim)
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer"):
            engine.update_sim(1.0, 0.02)

        update_sim.assert_called_once_with(1.0, 0.02)

    def test_skips_subsystems_without_update_sim_hook(self):
        sub = make_fake_subsystem()
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer"):
            engine.update_sim(1.0, 0.02)  # should not raise

        assert not hasattr(sub, "update_sim")

    def test_aggregates_current_and_updates_battery_when_present(self):
        sub = make_fake_subsystem(update_sim=MagicMock(return_value=5.0))
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer"), \
                patch("lib_6107.physics.BatterySim") as mock_battery, \
                patch("lib_6107.physics.RoboRioSim") as mock_rio:
            mock_battery.calculate.return_value = 11.5
            engine.update_sim(1.0, 0.02)

        mock_battery.calculate.assert_called_once_with([5.0])
        mock_rio.set_vin_voltage.assert_called_once_with(11.5)

    def test_skips_battery_update_when_no_current_collected(self):
        sub = make_fake_subsystem(update_sim=MagicMock(return_value=None))
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer"), \
                patch("lib_6107.physics.BatterySim") as mock_battery, \
                patch("lib_6107.physics.RoboRioSim") as mock_rio:
            engine.update_sim(1.0, 0.02)

        mock_battery.calculate.assert_not_called()
        mock_rio.set_vin_voltage.assert_not_called()

    def test_propagates_exception_raised_by_subsystem_update_sim(self):
        sub = make_fake_subsystem(update_sim=MagicMock(side_effect=RuntimeError("boom")))
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer"), \
                pytest.raises(RuntimeError, match="boom"):
            engine.update_sim(1.0, 0.02)

    def test_uses_log_tracer_reset_and_total(self):
        sub = make_fake_subsystem(update_sim=MagicMock(return_value=None))
        robot = make_fake_robot(subsystems=(sub,))
        engine = PhysicsEngine(robot)

        with patch("lib_6107.physics.LogTracer") as mock_tracer:
            engine.update_sim(1.0, 0.02)

        mock_tracer.reset_outer.assert_called_once_with("UpdateSim")
        mock_tracer.record.assert_called_once_with("Subsystem-UpdateSim")
        mock_tracer.record_total.assert_called_once()


class TestPhysicsEngineAllianceChange:
    """Tests for PhysicsEngine._alliance_change()."""

    def test_selects_red_pose_by_location_when_red(self):
        robot = make_fake_robot(subsystems=())
        engine = PhysicsEngine(robot)
        robot.field2d.set_robot_pose.reset_mock()

        engine._alliance_change(True, 2)

        expected_pose = robot.simulation_constants.RED_TEST_POSE[2]
        robot.field2d.set_robot_pose.assert_called_once_with(expected_pose)
        assert isinstance(expected_pose, Pose2d)

    def test_selects_blue_pose_by_location_when_blue(self):
        robot = make_fake_robot(subsystems=())
        engine = PhysicsEngine(robot)
        robot.field2d.set_robot_pose.reset_mock()

        engine._alliance_change(False, 3)

        expected_pose = robot.simulation_constants.BLUE_TEST_POSE[3]
        robot.field2d.set_robot_pose.assert_called_once_with(expected_pose)


class TestRobotSimulationPeriodic:
    """Tests for Robot.simulation_periodic driving the PhysicsEngine (replaces pyfrc's physics loop)."""

    def test_forwards_time_and_delta_to_engine(self):
        from lib_6107.robot import Robot

        fake = MagicMock()
        fake._sim = MagicMock()
        fake._last_sim_time = None
        fake.get_period.return_value = 0.02

        with patch("lib_6107.robot.Timer.get_timestamp", side_effect=[1.0, 1.02]):
            Robot.simulation_periodic(fake)
            Robot.simulation_periodic(fake)

        first, second = fake._sim.update_sim.call_args_list
        assert first.args == (1.0, 0.02)
        assert second.args[0] == 1.02
        assert second.args[1] == pytest.approx(0.02)

    def test_noop_without_engine(self):
        from lib_6107.robot import Robot

        fake = MagicMock()
        fake._sim = None
        Robot.simulation_periodic(fake)
