"""Unit tests for Robot (src/lib_6107/robot.py)."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest

from lib_6107.constants import RobotModes
from lib_6107.robot import Robot


def _patch_infra():
    """Build an ExitStack patching all collaborators touched by Robot.__init__/robotInit.

    Keeps real WPILib simulation objects (Field2d, CommandScheduler, DriverStation,
    NetworkTableInstance) since those are safe to use directly under the sim HAL, but
    mocks out Logger (which swaps sys.stdout/sys.stderr and is unsafe to leave active
    across test/interpreter teardown), the vendor logging singletons, and the
    notification/pathfinding helpers that have side effects outside the test process.
    """
    stack = ExitStack()
    stack.enter_context(patch("lib_6107.robot.NT4Publisher"))
    stack.enter_context(patch("lib_6107.robot.WPILOGWriter"))
    stack.enter_context(patch("lib_6107.robot.WPILOGReader"))
    stack.enter_context(patch("lib_6107.robot.SignalLogger"))
    stack.enter_context(patch("lib_6107.robot.StatusLogger"))
    stack.enter_context(patch("lib_6107.robot.LiveWindow"))
    stack.enter_context(patch("lib_6107.robot.select_tab"))
    stack.enter_context(patch("lib_6107.robot.send_notification"))
    stack.enter_context(patch("lib_6107.robot.Pathfinding"))
    stack.enter_context(patch("lib_6107.robot.LocalADStar"))
    stack.enter_context(patch("lib_6107.robot.LogTracer"))
    mock_logger = stack.enter_context(patch("lib_6107.robot.Logger"))
    return stack, mock_logger


@pytest.fixture
def infra():
    """Patch all Robot collaborators for the duration of a test."""
    stack, mock_logger = _patch_infra()
    with stack:
        yield mock_logger


@pytest.fixture
def robot(infra):
    """Create a Robot (SIMULATION mode, default ROBOT_MODE in the test environment)."""
    return Robot("2026")


def make_fake_subsystem(**hooks):
    """Create a MagicMock subsystem restricted to the given hook names.

    Using ``spec`` restricts which attributes exist, so ``hasattr(subsystem, name)``
    behaves like a real subsystem that only implements a subset of the optional hooks.
    """
    mock = MagicMock(spec=list(hooks.keys()))
    for name, value in hooks.items():
        setattr(mock, name, value)
    return mock


class TestRobotInitBuildYear:
    """Tests for build_year validation in Robot.__init__."""

    def test_build_year_2025_raises_value_error(self, infra):
        with pytest.raises(ValueError, match=r"Not within supported rage"):
            Robot("2025")

    def test_build_year_2051_raises_value_error(self, infra):
        with pytest.raises(ValueError, match=r"Not within supported rage"):
            Robot("2051")

    def test_build_year_2026_lower_boundary_is_valid(self, infra):
        r = Robot("2026")
        assert r is not None

    def test_build_year_2050_upper_boundary_is_valid(self, infra):
        r = Robot("2050")
        assert r is not None


class TestRobotInitModeBranches:
    """Tests for the ROBOT_MODE match statement inside Robot.__init__."""

    def test_simulation_mode_adds_wpilogwriter_and_nt4publisher(self, infra):
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.SIMULATION):
            Robot("2026")
        assert infra.addDataReciever.call_count == 2

    def test_replay_mode_sets_replay_source_and_writer(self, infra, monkeypatch, tmp_path):
        log_file = tmp_path / "match.wpilog"
        log_file.write_bytes(b"")
        monkeypatch.setenv("LOG_PATH", str(log_file))

        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REPLAY):
            r = Robot("2026")

        infra.setReplaySource.assert_called_once()
        infra.addDataReciever.assert_called_once()
        assert r.UseTiming is False

    def test_real_mode_with_usb_mounted_adds_nt4_and_wpilogwriter(self, infra):
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REAL), \
                patch("lib_6107.robot.wpilib.deployinfo.getDeployData", return_value=None), \
                patch("lib_6107.robot.os.path.ismount", return_value=True), \
                patch("lib_6107.robot.os.path.exists", return_value=True), \
                patch("lib_6107.robot.os.makedirs") as mock_makedirs:
            Robot("2026")

        mock_makedirs.assert_called_once()
        assert infra.addDataReciever.call_count == 2

    def test_real_mode_without_usb_falls_back_to_pylogs(self, infra):
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REAL), \
                patch("lib_6107.robot.wpilib.deployinfo.getDeployData", return_value=None), \
                patch("lib_6107.robot.os.path.ismount", return_value=False), \
                patch("lib_6107.robot.os.path.exists", return_value=False), \
                patch("lib_6107.robot.os.makedirs") as mock_makedirs:
            Robot("2026")

        mock_makedirs.assert_called_once()
        assert infra.addDataReciever.call_count == 2

    def test_real_mode_records_deploy_metadata_when_present(self, infra):
        deploy_data = {
            "deploy-host": "host", "deploy-user": "user", "deploy-date": "date",
            "code-path"  : "path", "git-hash": "hash", "git-branch": "branch",
            "git-desc"   : "desc",
        }
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REAL), \
                patch("lib_6107.robot.wpilib.deployinfo.getDeployData", return_value=deploy_data), \
                patch("lib_6107.robot.os.path.ismount", return_value=True), \
                patch("lib_6107.robot.os.path.exists", return_value=True), \
                patch("lib_6107.robot.os.makedirs"):
            Robot("2026")

        infra.recordMetadata.assert_any_call("Deploy Host", "host")
        infra.recordMetadata.assert_any_call("Git Hash", "hash")

    def test_logger_start_called_in_every_mode(self, infra):
        Robot("2026")
        infra.start.assert_called_once()

    def test_records_robot_team_and_year_metadata(self, infra):
        Robot("2026")
        infra.recordMetadata.assert_any_call("Team", "61.07")
        infra.recordMetadata.assert_any_call("Year", "2026")


class TestRobotProperties:
    """Tests for simple Robot properties."""

    def test_container_property_returns_none_before_robot_init(self, robot):
        assert robot.container is None

    def test_period_property_matches_robot_constants(self, robot):
        assert robot.period == robot.robot_constants.ROBOT_PERIOD

    def test_counter_starts_at_zero(self, robot):
        assert robot.counter == 0

    def test_counter_increments_each_robot_periodic(self, robot):
        robot._container = MagicMock()
        robot.robotPeriodic()
        robot.robotPeriodic()
        assert robot.counter == 2


class TestRobotLoggingInit:
    """Tests for Robot._logging_init() mode-specific log level configuration."""

    def test_real_mode_sets_error_level(self, robot):
        import logging
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REAL):
            robot._logging_init()
        assert logging.getLogger("lib_6107.robot").level == logging.ERROR

    def test_simulation_mode_sets_info_level(self, robot):
        import logging
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.SIMULATION):
            robot._logging_init()
        assert logging.getLogger("lib_6107.robot").level == logging.INFO

    def test_replay_mode_sets_error_level(self, robot):
        import logging
        with patch("lib_6107.robot.ROBOT_MODE", RobotModes.REPLAY):
            robot._logging_init()
        assert logging.getLogger("lib_6107.robot").level == logging.ERROR


class TestRobotInit:
    """Tests for Robot.robotInit()."""

    def test_robot_init_calls_container_init_with_self(self, robot):
        container_init = MagicMock(return_value=MagicMock())
        robot.robotInit(container_init)
        container_init.assert_called_once_with(robot)

    def test_robot_init_sets_container_from_callback_result(self, robot):
        fake_container = MagicMock()
        robot.robotInit(lambda r: fake_container)
        assert robot.container is fake_container

    def test_robot_init_disables_vendor_auto_logging(self, robot):
        with patch("lib_6107.robot.SignalLogger") as mock_signal, \
                patch("lib_6107.robot.StatusLogger") as mock_status, \
                patch("lib_6107.robot.LiveWindow") as mock_live:
            robot.robotInit(lambda r: MagicMock())

        mock_signal.enable_auto_logging.assert_called_once_with(False)
        mock_status.disableAutoLogging.assert_called_once()
        mock_live.disableAllTelemetry.assert_called_once()

    def test_robot_init_configures_pathfinding(self, robot):
        with patch("lib_6107.robot.Pathfinding") as mock_pathfinding, \
                patch("lib_6107.robot.LocalADStar") as mock_adstar:
            robot.robotInit(lambda r: MagicMock())

        mock_pathfinding.setPathfinder.assert_called_once_with(mock_adstar.return_value)

    def test_robot_init_selects_preflight_tab(self, robot):
        with patch("lib_6107.robot.select_tab") as mock_select_tab:
            robot.robotInit(lambda r: MagicMock())

        mock_select_tab.assert_called_once_with("PREFLIGHT")


class TestRobotPeriodic:
    """Tests for Robot.robotPeriodic()."""

    def test_robot_periodic_calls_container_robot_periodic(self, robot):
        robot._container = MagicMock()
        robot.robotPeriodic()
        robot._container.robotPeriodic.assert_called_once()

    def test_robot_periodic_runs_command_scheduler(self, robot):
        robot._container = MagicMock()
        with patch.object(robot, "_command_scheduler") as mock_scheduler:
            robot.robotPeriodic()
            mock_scheduler.run.assert_called_once()

    def test_robot_periodic_lazily_initializes_command_scheduler(self, robot):
        robot._container = MagicMock()
        assert robot._command_scheduler is None
        robot.robotPeriodic()
        assert robot._command_scheduler is not None

    def test_robot_periodic_records_duration_stat(self, robot):
        robot._container = MagicMock()
        with patch.object(robot._stats, "add") as mock_add:
            robot.robotPeriodic()
        assert mock_add.call_args[0][0] == "periodic-duration"

    def test_robot_periodic_uses_log_tracer(self, robot):
        robot._container = MagicMock()
        with patch("lib_6107.robot.LogTracer") as mock_tracer:
            robot.robotPeriodic()
        mock_tracer.resetOuter.assert_called_once_with("RobotPeriodic")
        mock_tracer.recordTotal.assert_called_once()


class TestRobotDisabledMode:
    """Tests for disabledInit/disabledPeriodic/disabledExit."""

    def test_disabled_init_stops_subsystems_with_stop_hook(self, robot):
        stoppable = make_fake_subsystem(stop=MagicMock())
        not_stoppable = make_fake_subsystem(fault_detection=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (stoppable, not_stoppable)

        robot.disabledInit()

        stoppable.stop.assert_called_once()

    def test_disabled_init_calls_disable_pid_subsystems(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.disabledInit()
        robot._container.disable_pid_subsystems.assert_called_once()

    def test_disabled_init_starts_disabled_timer(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.disabledInit()
        assert robot.disabledTimer.isRunning()

    def test_disabled_init_runs_fault_detection_disabled_init(self, robot):
        sub = make_fake_subsystem(fault_detection=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (sub,)
        robot.disabledInit()
        sub.fault_detection.assert_called_once_with("Disabled-Init", clear=True, notify=True)

    def test_disabled_periodic_calls_container_disable_periodic(self, robot):
        robot._container = MagicMock()
        robot.match_started = True
        robot.disabledTimer = MagicMock()
        robot.disabledTimer.hasElapsed.return_value = False
        robot.disabledPeriodic()
        robot._container.disable_periodic.assert_called_once()

    def test_disabled_periodic_releases_brakes_after_wheel_lock_time(self, robot):
        robot._container = MagicMock()
        robot.match_started = True
        robot.disabledTimer = MagicMock()
        robot.disabledTimer.hasElapsed.return_value = True
        robot.disabledPeriodic()
        robot._container.robot_drive.set_motor_brake.assert_called_once_with(False)
        robot.disabledTimer.stop.assert_called_once()
        robot.disabledTimer.reset.assert_called_once()

    def test_disabled_periodic_does_not_release_brakes_before_wheel_lock_time(self, robot):
        robot._container = MagicMock()
        robot.match_started = True
        robot.disabledTimer = MagicMock()
        robot.disabledTimer.hasElapsed.return_value = False
        robot.disabledPeriodic()
        robot._container.robot_drive.set_motor_brake.assert_not_called()

    def test_disabled_periodic_checks_alliance_when_match_not_started(self, robot):
        robot._container = MagicMock()
        robot.match_started = False
        robot.disabledTimer = MagicMock()
        robot.disabledTimer.hasElapsed.return_value = False
        robot.disabledPeriodic()
        robot._container.check_alliance.assert_called_once()

    def test_disabled_periodic_skips_alliance_check_when_match_started(self, robot):
        robot._container = MagicMock()
        robot.match_started = True
        robot.disabledTimer = MagicMock()
        robot.disabledTimer.hasElapsed.return_value = False
        robot.disabledPeriodic()
        robot._container.check_alliance.assert_not_called()

    def test_disabled_exit_stops_and_resets_timer(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.disabledTimer = MagicMock()
        robot.disabledExit()
        robot.disabledTimer.stop.assert_called_once()
        robot.disabledTimer.reset.assert_called_once()

    def test_disabled_exit_runs_fault_detection_disabled_exit(self, robot):
        sub = make_fake_subsystem(fault_detection=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (sub,)
        robot.disabledTimer = MagicMock()
        robot.disabledExit()
        sub.fault_detection.assert_called_once_with("Disabled-Exit", clear=True, notify=True)


class TestRobotAutonomousMode:
    """Tests for autonomousInit/autonomousExit."""

    def test_autonomous_init_sets_start_time(self, robot):
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = None
        robot.autonomousInit()
        robot._container.set_start_time.assert_called_once()

    def test_autonomous_init_locks_motor_brake(self, robot):
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = None
        robot.autonomousInit()
        robot._container.robot_drive.set_motor_brake.assert_called_once_with(True)

    def test_autonomous_init_schedules_autonomous_command_when_present(self, robot):
        auto_command = MagicMock()
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = auto_command
        robot.autonomousInit()
        auto_command.schedule.assert_called_once()

    def test_autonomous_init_does_not_schedule_when_command_is_none(self, robot):
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = None
        robot.autonomousInit()
        assert robot._autonomous_command is None

    def test_autonomous_init_marks_match_started_when_not_already(self, robot):
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = None
        robot.match_started = False
        robot.autonomousInit()
        assert robot.match_started is True
        robot._container.check_alliance.assert_called_once()

    def test_autonomous_init_does_not_recheck_alliance_once_match_started(self, robot):
        robot._container = MagicMock()
        robot._container.get_autonomous_command.return_value = None
        robot.match_started = True
        robot.autonomousInit()
        robot._container.check_alliance.assert_not_called()

    def test_autonomous_exit_cancels_autonomous_command(self, robot):
        auto_command = MagicMock()
        robot._autonomous_command = auto_command
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.autonomousExit()
        auto_command.cancel.assert_called_once()

    def test_autonomous_exit_skips_cancel_when_no_command(self, robot):
        robot._autonomous_command = None
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.autonomousExit()  # should not raise

    def test_autonomous_exit_runs_fault_detection(self, robot):
        sub = make_fake_subsystem(fault_detection=MagicMock())
        robot._autonomous_command = None
        robot._container = MagicMock()
        robot._container.subsystems = (sub,)
        robot.autonomousExit()
        sub.fault_detection.assert_called_once_with("Autonomous-Exit", clear=True, notify=True)


class TestRobotTeleopMode:
    """Tests for teleopInit/teleopPeriodic/teleopExit."""

    def test_teleop_init_sets_start_time(self, robot):
        robot._container = MagicMock()
        robot._autonomous_command = None
        robot.teleopInit()
        robot._container.set_start_time.assert_called_once()

    def test_teleop_init_cancels_autonomous_command_when_present(self, robot):
        auto_command = MagicMock()
        robot._container = MagicMock()
        robot._autonomous_command = auto_command
        robot.teleopInit()
        auto_command.cancel.assert_called_once()

    def test_teleop_init_cancels_all_commands_when_no_autonomous_command(self, robot):
        robot._container = MagicMock()
        robot._autonomous_command = None
        with patch("lib_6107.robot.CommandScheduler") as mock_scheduler_cls:
            robot.teleopInit()
        mock_scheduler_cls.getInstance.return_value.cancelAll.assert_called_once()

    def test_teleop_init_marks_match_started_when_not_already(self, robot):
        robot._container = MagicMock()
        robot._autonomous_command = None
        robot.match_started = False
        robot.teleopInit()
        assert robot.match_started is True
        robot._container.check_alliance.assert_called_once()

    def test_teleop_init_does_not_recheck_alliance_once_match_started(self, robot):
        robot._container = MagicMock()
        robot._autonomous_command = None
        robot.match_started = True
        robot.teleopInit()
        robot._container.check_alliance.assert_not_called()

    def test_teleop_exit_stops_subsystems(self, robot):
        stoppable = make_fake_subsystem(stop=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (stoppable,)
        robot.teleopExit()
        stoppable.stop.assert_called_once()

    def test_teleop_exit_sets_drivetrain_straight(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        robot.teleopExit()
        robot._container.robot_drive.set_straight.assert_called_once()

    def test_teleop_exit_runs_fault_detection(self, robot):
        sub = make_fake_subsystem(fault_detection=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (sub,)
        robot.teleopExit()
        sub.fault_detection.assert_called_once_with("Teleop-Exit", clear=True, notify=True)


class TestRobotTestMode:
    """Tests for testInit()."""

    def test_test_init_cancels_all_commands(self, robot):
        with patch("lib_6107.robot.CommandScheduler") as mock_scheduler_cls:
            robot.testInit()
        mock_scheduler_cls.getInstance.return_value.cancelAll.assert_called_once()


class TestRobotEndCompetition:
    """Tests for endCompetition()."""

    def test_end_competition_runs_fault_detection(self, robot):
        sub = make_fake_subsystem(fault_detection=MagicMock())
        robot._container = MagicMock()
        robot._container.subsystems = (sub,)
        with patch("lib_6107.robot.send_notification"):
            robot.endCompetition()
        sub.fault_detection.assert_called_once_with("End-Competition", clear=True, notify=True)

    def test_end_competition_sends_notification(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        with patch("lib_6107.robot.send_notification") as mock_notify:
            robot.endCompetition()
        mock_notify.assert_called_once()

    def test_end_competition_calls_super(self, robot):
        robot._container = MagicMock()
        robot._container.subsystems = ()
        with patch("lib_6107.robot.send_notification"), \
                patch("lib_6107.pykit.loggedrobot.LoggedRobot.endCompetition") as mock_super:
            robot.endCompetition()
        mock_super.assert_called_once()
