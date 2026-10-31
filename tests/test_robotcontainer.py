"""Unit tests for RobotContainer (src/lib_6107/robotcontainer.py)."""

from unittest.mock import MagicMock, patch

import pytest
from commands2 import InstantCommand, PrintCommand

from lib_6107.constants import RobotConstants
from lib_6107.robotcontainer import RobotContainer


class ConcreteRobotContainer(RobotContainer):
    """Minimal concrete RobotContainer used to exercise the base class behavior."""

    def subsystem_init(self):
        self.robot_drive = MagicMock()
        self.robot_drive.drive_scale_factor = 1.0
        return (self.robot_drive,)

    def _configure_driver_button_bindings_xbox(self, controller):
        self.driver_bindings_configured = True

    def _configure_operator_button_bindings_xbox(self, controller):
        self.operator_bindings_configured = True

    def _configure_calibration_button_bindings_xbox(self, controller):
        self.calibration_bindings_configured = True


def make_fake_robot(robot_constants: RobotConstants | None = None):
    """Create a lightweight fake Robot for RobotContainer construction."""
    robot = MagicMock()
    robot.robot_constants = robot_constants or RobotConstants()
    robot.field = MagicMock()
    return robot


@pytest.fixture
def container_infra():
    """Patch collaborators instantiated/invoked directly by RobotContainer.__init__."""
    with patch("lib_6107.robotcontainer.PathPlanner") as mock_planner_cls, \
            patch("lib_6107.robotcontainer.RobotAlerts") as mock_alerts_cls, \
            patch("lib_6107.robotcontainer.LoggedDashboardChooser") as mock_chooser_cls:
        mock_planner = mock_planner_cls.return_value
        mock_planner.configure_auto_builder.return_value = mock_chooser_cls.return_value
        yield {
            "planner_cls": mock_planner_cls,
            "planner"    : mock_planner,
            "alerts_cls" : mock_alerts_cls,
            "chooser_cls": mock_chooser_cls,
        }


@pytest.fixture
def container(container_infra):
    """Build a ConcreteRobotContainer with a fake Robot."""
    return ConcreteRobotContainer(make_fake_robot())


class TestRobotContainerConstruction:
    """Tests for RobotContainer.__init__."""

    def test_construction_succeeds_with_concrete_subclass(self, container):
        assert container is not None

    def test_construction_calls_subsystem_init(self, container):
        assert container.subsystems == (container.robot_drive,)

    def test_construction_raises_not_implemented_on_base_class(self, container_infra):
        with pytest.raises(NotImplementedError):
            RobotContainer(make_fake_robot())

    def test_construction_sets_default_autonomous_option(self, container, container_infra):
        call_args = [c[0] for c in container.auto_chooser.setDefaultOption.call_args_list]
        assert call_args[0][0] == "Do nothing"

    def test_construction_configures_speed_limiter_chooser(self, container):
        assert container._limit_chooser is not None
        container._limit_chooser.setDefaultOption.assert_any_call("60%", 0.6)

    def test_construction_stores_robot_x_and_y_width_from_constants(self, container):
        constants = RobotConstants()
        assert container.robot_x_width == constants.ROBOT_X_WIDTH
        assert container.robot_y_width == constants.ROBOT_Y_WIDTH


class TestRobotContainerSpeedProperties:
    """Tests for max_speed/max_angular_rate properties."""

    def test_max_speed_applies_drive_scale_factor(self, container):
        container.robot_drive.drive_scale_factor = 0.5
        expected = container._max_speed * 0.5
        assert container.max_speed == expected

    def test_max_angular_rate_applies_drive_scale_factor(self, container):
        container.robot_drive.drive_scale_factor = 0.25
        expected = container._max_angular_rate * 0.25
        assert container.max_angular_rate == expected


class TestRobotContainerCamera:
    """Tests for camera() lookups."""

    def test_camera_returns_none_when_label_absent(self, container):
        assert container.camera("front") is None

    def test_camera_returns_registered_subsystem(self, container):
        fake_camera = MagicMock()
        container._cameras["front"] = fake_camera
        assert container.camera("front") is fake_camera


class TestRobotContainerAlliance:
    """Tests for check_alliance()/register_alliance_change_callback()."""

    def test_register_alliance_change_callback_appends_callback(self, container):
        callback = MagicMock()
        container.register_alliance_change_callback(callback)
        assert callback in container._alliance_change_callbacks

    def test_check_alliance_updates_state_and_fires_callback_on_change(self, container):
        container.robot.match_started = False
        container._is_red_alliance = False
        container._alliance_location = 1
        callback = MagicMock()
        container.register_alliance_change_callback(callback)

        with patch("lib_6107.robotcontainer.DriverStation") as mock_ds:
            mock_ds.getAlliance.return_value = mock_ds.Alliance.kRed
            mock_ds.getLocation.return_value = 2
            container.check_alliance()

        assert container.is_red_alliance is True
        assert container.alliance_location == 2
        callback.assert_called_once_with(True, 2)

    def test_check_alliance_does_not_fire_callback_when_unchanged(self, container):
        container.robot.match_started = False
        container._is_red_alliance = False
        container._alliance_location = 1
        callback = MagicMock()
        container.register_alliance_change_callback(callback)

        with patch("lib_6107.robotcontainer.DriverStation") as mock_ds:
            mock_ds.getAlliance.return_value = mock_ds.Alliance.kBlue
            mock_ds.getLocation.return_value = 1
            container.check_alliance()

        callback.assert_not_called()

    def test_check_alliance_ignores_invalid_location(self, container):
        container.robot.match_started = False
        container._is_red_alliance = False
        container._alliance_location = 1
        callback = MagicMock()
        container.register_alliance_change_callback(callback)

        with patch("lib_6107.robotcontainer.DriverStation") as mock_ds:
            mock_ds.getAlliance.return_value = mock_ds.Alliance.kBlue
            mock_ds.getLocation.return_value = 99
            container.check_alliance()

        assert container.alliance_location == 1

    def test_check_alliance_noop_when_match_started(self, container):
        container.robot.match_started = True
        callback = MagicMock()
        container.register_alliance_change_callback(callback)

        with patch("lib_6107.robotcontainer.DriverStation") as mock_ds:
            mock_ds.getAlliance.return_value = mock_ds.Alliance.kRed
            mock_ds.getLocation.return_value = 3
            container.check_alliance()

        callback.assert_not_called()


class TestRobotContainerElapsedTime:
    """Tests for set_start_time/get_elapsed_time/elapsed_time."""

    def test_get_elapsed_time_reflects_time_since_start(self, container):
        with patch("lib_6107.robotcontainer.time.time", side_effect=[100.0, 105.5]):
            container.set_start_time()
            assert container.get_elapsed_time() == pytest.approx(5.5)

    def test_elapsed_time_is_alias_for_get_elapsed_time(self, container):
        with patch("lib_6107.robotcontainer.time.time", side_effect=[200.0, 203.0]):
            container.set_start_time()
            assert container.elapsed_time() == pytest.approx(3.0)


class TestRobotContainerAbstractHooks:
    """Tests for NotImplementedError raised by base-class abstract methods."""

    def test_subsystem_init_raises_not_implemented(self, container):
        with pytest.raises(NotImplementedError):
            RobotContainer.subsystem_init(container)

    def test_configure_driver_button_bindings_raises_not_implemented(self, container):
        with pytest.raises(NotImplementedError):
            RobotContainer._configure_driver_button_bindings_xbox(container, MagicMock())

    def test_configure_operator_button_bindings_raises_not_implemented(self, container):
        with pytest.raises(NotImplementedError):
            RobotContainer._configure_operator_button_bindings_xbox(container, MagicMock())

    def test_configure_calibration_button_bindings_raises_not_implemented(self, container):
        with pytest.raises(NotImplementedError):
            RobotContainer._configure_calibration_button_bindings_xbox(container, MagicMock())


class TestRobotContainerButtonBindingRouting:
    """Tests for configure_button_bindings_xbox() port routing."""

    def test_routes_to_driver_bindings_for_driver_port(self, container):
        controller = MagicMock()
        container.configure_button_bindings_xbox(controller, container.robot.robot_constants.DRIVER_CONTROLLER_PORT)
        assert container.driver_bindings_configured is True

    def test_routes_to_operator_bindings_for_operator_port(self, container):
        controller = MagicMock()
        container.configure_button_bindings_xbox(controller, container.robot.robot_constants.OPERATOR_CONTROLLER_PORT)
        assert container.operator_bindings_configured is True

    def test_routes_to_calibration_bindings_for_calibration_port(self, container):
        controller = MagicMock()
        container.configure_button_bindings_xbox(
            controller, container.robot.robot_constants.CALIBRATION_CONTROLLER_PORT
        )
        assert container.calibration_bindings_configured is True


class TestRobotContainerPidAndAutonomous:
    """Tests for disable_pid_subsystems/get_autonomous_command/get_autonomous_end_game_command."""

    def test_disable_pid_subsystems_sets_motor_brake(self, container):
        container.disable_pid_subsystems()
        container.robot_drive.set_motor_brake.assert_called_once_with(True)

    def test_get_autonomous_command_delegates_to_chooser(self, container):
        expected = MagicMock()
        container.auto_chooser.get_selected.return_value = expected
        assert container.get_autonomous_command() is expected

    def test_get_autonomous_end_game_command_delegates_to_chooser(self, container):
        expected = MagicMock()
        container._auto_end_chooser.get_selected.return_value = expected
        assert container.get_autonomous_end_game_command() is expected


class TestRobotContainerSpeedLimiter:
    """Tests for configure_speed_limiter()."""

    def test_configure_speed_limiter_adds_all_expected_options(self, container):
        add_option_calls = container._limit_chooser.addOption.call_args_list
        labels = [c[0][0] for c in add_option_calls]
        assert labels == ["10%", "20%", "40%", "80%", "100%"]

    def test_configure_speed_limiter_sets_60_percent_default(self, container):
        container._limit_chooser.setDefaultOption.assert_any_call("60%", 0.6)


class TestRobotContainerDoNothing:
    """Tests for get_do_nothing()."""

    def test_get_do_nothing_stop_true_returns_instant_command(self, container):
        command = container.get_do_nothing(stop=True)
        assert isinstance(command, InstantCommand)

    def test_get_do_nothing_stop_false_returns_print_command(self, container):
        command = container.get_do_nothing(stop=False)
        assert isinstance(command, PrintCommand)

    def test_get_do_nothing_default_stops_drivetrain(self, container):
        command = container.get_do_nothing()
        command.initialize()
        container.robot_drive.stop.assert_called_once()


class TestRobotContainerPeriodic:
    """Tests for disable_periodic()/robotPeriodic()."""

    def test_disable_periodic_calls_alerts_preflight_update(self, container):
        container.disable_periodic()
        container._alerts.preflight_update.assert_called_once()

    def test_robot_periodic_calls_alerts_update(self, container):
        container.robotPeriodic()
        container._alerts.update.assert_called_once()
