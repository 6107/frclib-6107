"""Unit tests for PathPlanner module."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.commands.pathplanner import PathPlanner
from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser


class TestPathPlannerInitialization:
    """Tests for PathPlanner initialization."""

    def test_initialization_stores_drivetrain_reference(self):
        """Verify PathPlanner stores drivetrain reference."""
        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        assert planner._drivetrain is mock_drivetrain

    def test_initialization_stores_container_reference(self):
        """Verify PathPlanner stores container reference."""
        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        assert planner._container is mock_container


class TestPathPlannerConfigureAutoBuilder:
    """Tests for configure_auto_builder method."""

    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_registers_commands_before_checking_file(self, mock_access, mock_isfile,
                                                                            mock_deploy_dir):
        """Verify register_commands_and_triggers is called before checking PathPlanner settings."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = False
        mock_access.return_value = False

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with patch.object(planner, 'register_commands_and_triggers') as mock_register:
            planner.configure_auto_builder()
            mock_register.assert_called_once()

    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_returns_chooser_when_settings_file_not_found(self, mock_access, mock_isfile,
                                                                                 mock_deploy_dir):
        """Verify configure_auto_builder returns a LoggedDashboardChooser when settings file not found."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = False
        mock_access.return_value = False

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.configure_auto_builder()

        assert isinstance(result, LoggedDashboardChooser)

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.RobotConfig')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_configure_auto_builder_calls_auto_builder_configure_when_file_exists(self, mock_listdir, mock_access,
                                                                                  mock_isfile, mock_deploy_dir,
                                                                                  mock_robot_config, mock_auto_builder):
        """Verify AutoBuilder.configure is called when settings file exists."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = []
        mock_robot_config.fromGUISettings.return_value = MagicMock()
        mock_auto_builder.isConfigured.return_value = True

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.configure_auto_builder()

        mock_auto_builder.configure.assert_called_once()

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.RobotConfig')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_configure_auto_builder_configures_logging_callbacks(self, mock_listdir, mock_access, mock_isfile,
                                                                 mock_deploy_dir, mock_robot_config, mock_auto_builder):
        """Verify PathPlanner logging callbacks are configured."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = []
        mock_robot_config.fromGUISettings.return_value = MagicMock()
        mock_auto_builder.isConfigured.return_value = True

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with patch('lib_6107.commands.pathplanner.PathPlannerLogging') as mock_logging:
            planner.configure_auto_builder()

            mock_logging.setLogCurrentPoseCallback.assert_called_once()
            mock_logging.setLogTargetPoseCallback.assert_called_once()
            mock_logging.setLogActivePathCallback.assert_called_once()

    @patch('lib_6107.commands.pathplanner.CommandScheduler')
    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.RobotConfig')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_configure_auto_builder_sets_command_scheduler_callbacks(self, mock_listdir, mock_access, mock_isfile,
                                                                     mock_deploy_dir, mock_robot_config,
                                                                     mock_auto_builder, mock_scheduler):
        """Verify command scheduler logging callbacks are registered."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = []
        mock_robot_config.fromGUISettings.return_value = MagicMock()
        mock_auto_builder.isConfigured.return_value = True
        mock_scheduler_instance = MagicMock()
        mock_scheduler.getInstance.return_value = mock_scheduler_instance

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.configure_auto_builder()

        mock_scheduler_instance.onCommandInitialize.assert_called_once()
        mock_scheduler_instance.onCommandFinish.assert_called_once()
        mock_scheduler_instance.onCommandInterrupt.assert_called_once()

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.RobotConfig')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_returns_auto_chooser_when_file_exists(self, mock_access, mock_isfile,
                                                                          mock_deploy_dir, mock_robot_config,
                                                                          mock_auto_builder):
        """Verify configure_auto_builder returns auto chooser when settings file exists."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = True
        mock_robot_config.fromGUISettings.return_value = MagicMock()

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with patch.object(planner, 'build_auto_chooser', return_value=MagicMock()) as mock_build:
            result = planner.configure_auto_builder()

            mock_build.assert_called_once()
            assert result is not None

    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_passes_default_command_to_build_auto_chooser(self, mock_access, mock_isfile,
                                                                                 mock_deploy_dir):
        """Verify default_command parameter is passed to build_auto_chooser."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = True

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with patch('lib_6107.commands.pathplanner.RobotConfig'):
            with patch('lib_6107.commands.pathplanner.AutoBuilder'):
                with patch.object(planner, 'build_auto_chooser') as mock_build:
                    planner.configure_auto_builder(default_command="test_auto")

                    mock_build.assert_called_once_with("test_auto")


class TestPathPlannerBuildAutoChooser:
    """Tests for build_auto_chooser method."""

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    def test_build_auto_chooser_raises_error_when_auto_builder_not_configured(self, mock_auto_builder):
        """Verify RuntimeError raised when AutoBuilder not configured."""
        mock_auto_builder.isConfigured.return_value = False

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with pytest.raises(RuntimeError, match="AutoBuilder was not configured"):
            planner.build_auto_chooser()

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_creates_chooser_with_autos(self, mock_listdir, mock_deploy_dir, mock_auto_builder):
        """Verify build_auto_chooser creates chooser with available autos."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = ['auto1.auto', 'auto2.auto']
        mock_auto_builder.buildAuto.return_value = MagicMock()

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.build_auto_chooser()

        assert isinstance(result, LoggedDashboardChooser)
        assert mock_auto_builder.buildAuto.call_count >= 1

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_sets_default_option_when_matching_default_name(self, mock_listdir, mock_deploy_dir,
                                                                               mock_auto_builder):
        """Verify default option is set when matching default_auto_name."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = ['default_auto.auto', 'other_auto.auto']
        mock_command = MagicMock()
        mock_auto_builder.buildAuto.return_value = mock_command

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.build_auto_chooser(default_auto_name='default_auto')

        assert isinstance(result, LoggedDashboardChooser)

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_handles_general_exception(self, mock_listdir, mock_deploy_dir, mock_auto_builder):
        """Verify build_auto_chooser handles general exceptions gracefully."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = ['bad_auto.auto']
        mock_auto_builder.buildAuto.side_effect = Exception("Build failed")

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)

        with patch('lib_6107.commands.pathplanner.logger') as mock_logger:
            result = planner.build_auto_chooser()

            assert isinstance(result, LoggedDashboardChooser)
            mock_logger.error.assert_called()

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_removes_auto_extension(self, mock_listdir, mock_deploy_dir, mock_auto_builder):
        """Verify build_auto_chooser removes .auto extension from filenames."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = ['test_auto.auto']
        mock_command = MagicMock()
        mock_auto_builder.buildAuto.return_value = mock_command

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.build_auto_chooser()

        mock_auto_builder.buildAuto.assert_called_with('test_auto')

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_with_empty_auto_list(self, mock_listdir, mock_deploy_dir, mock_auto_builder):
        """Verify build_auto_chooser handles empty auto list."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = []

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.build_auto_chooser()

        assert isinstance(result, LoggedDashboardChooser)


class TestPathPlannerRegisterCommandsAndTriggers:
    """Tests for register_commands_and_triggers method."""

    @patch('lib_6107.commands.pathplanner.ArcadeDrive')
    @patch('lib_6107.commands.pathplanner.AimToDirection')
    @patch('lib_6107.commands.pathplanner.GoToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveMove')
    def test_register_commands_and_triggers_registers_drivetrain_commands(self, mock_swerve_move, mock_swerve_to_point,
                                                                          mock_go_to_point, mock_aim_to_direction,
                                                                          mock_arcade_drive):
        """Verify drivetrain commands are registered."""
        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.register_commands_and_triggers()

        mock_arcade_drive.pathplanner_register.assert_called_once_with(mock_drivetrain)
        mock_aim_to_direction.pathplanner_register.assert_called_once_with(mock_drivetrain)
        mock_go_to_point.pathplanner_register.assert_called_once_with(mock_drivetrain)
        mock_swerve_to_point.pathplanner_register.assert_called_once_with(mock_drivetrain)
        mock_swerve_move.pathplanner_register.assert_called_once_with(mock_drivetrain)

    @patch('lib_6107.commands.pathplanner.ApproachTag')
    @patch('lib_6107.commands.pathplanner.ArcadeDrive')
    @patch('lib_6107.commands.pathplanner.AimToDirection')
    @patch('lib_6107.commands.pathplanner.GoToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveMove')
    def test_register_commands_and_triggers_registers_approach_tag_when_camera_available(self, mock_swerve_move,
                                                                                         mock_swerve_to_point,
                                                                                         mock_go_to_point,
                                                                                         mock_aim_to_direction,
                                                                                         mock_arcade_drive,
                                                                                         mock_approach_tag):
        """Verify ApproachTag is registered when front camera available."""
        mock_drivetrain = MagicMock()
        mock_container = MagicMock()
        mock_camera = MagicMock()
        mock_drivetrain.container.camera.return_value = mock_camera

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.register_commands_and_triggers()

        mock_approach_tag.pathplanner_register.assert_called_once_with(mock_drivetrain)

    @patch('lib_6107.commands.pathplanner.ApproachTag')
    @patch('lib_6107.commands.pathplanner.ArcadeDrive')
    @patch('lib_6107.commands.pathplanner.AimToDirection')
    @patch('lib_6107.commands.pathplanner.GoToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveToPoint')
    @patch('lib_6107.commands.pathplanner.SwerveMove')
    def test_register_commands_and_triggers_skips_approach_tag_when_no_camera(self, mock_swerve_move,
                                                                              mock_swerve_to_point, mock_go_to_point,
                                                                              mock_aim_to_direction, mock_arcade_drive,
                                                                              mock_approach_tag):
        """Verify ApproachTag is not registered when front camera unavailable."""
        mock_drivetrain = MagicMock()
        mock_container = MagicMock()
        mock_drivetrain.container.camera.return_value = None

        planner = PathPlanner(mock_drivetrain, mock_container)
        planner.register_commands_and_triggers()

        mock_approach_tag.pathplanner_register.assert_not_called()


class TestPathPlannerEdgeCases:
    """Tests for edge cases and error handling."""

    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_with_no_default_command(self, mock_access, mock_isfile, mock_deploy_dir):
        """Verify configure_auto_builder works with empty default_command."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = False
        mock_access.return_value = False

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.configure_auto_builder(default_command="")

        assert isinstance(result, LoggedDashboardChooser)

    @patch('lib_6107.commands.pathplanner.AutoBuilder')
    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.listdir')
    def test_build_auto_chooser_with_multiple_autos(self, mock_listdir, mock_deploy_dir, mock_auto_builder):
        """Verify build_auto_chooser processes multiple autos correctly."""
        mock_auto_builder.isConfigured.return_value = True
        mock_deploy_dir.return_value = '/deploy'
        mock_listdir.return_value = ['auto1.auto', 'auto2.auto', 'auto3.auto']
        mock_auto_builder.buildAuto.return_value = MagicMock()

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.build_auto_chooser()

        assert isinstance(result, LoggedDashboardChooser)
        assert mock_auto_builder.buildAuto.call_count == 3

    @patch('lib_6107.commands.pathplanner.getDeployDirectory')
    @patch('lib_6107.commands.pathplanner.os.path.isfile')
    @patch('lib_6107.commands.pathplanner.os.access')
    def test_configure_auto_builder_checks_file_readability(self, mock_access, mock_isfile, mock_deploy_dir):
        """Verify configure_auto_builder checks both file existence and readability."""
        mock_deploy_dir.return_value = '/deploy'
        mock_isfile.return_value = True
        mock_access.return_value = False

        mock_drivetrain = MagicMock()
        mock_container = MagicMock()

        planner = PathPlanner(mock_drivetrain, mock_container)
        result = planner.configure_auto_builder()

        mock_access.assert_called_once()
        assert isinstance(result, LoggedDashboardChooser)
