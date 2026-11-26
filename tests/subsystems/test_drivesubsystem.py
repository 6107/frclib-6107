"""Unit tests for the vendor-neutral DriveSubsystem base class (no hardware)."""

from unittest.mock import MagicMock, patch

import pytest
from commands2.sysid import SysIdRoutine
from wpilib import Alliance
from wpimath import ChassisVelocities, Pose2d, Rotation2d, Rotation3d, SwerveModulePosition, SwerveModuleVelocity

import lib_6107.subsystems.drivetrain.drivesubsystem as ds_mod
from lib_6107.subsystems.drivetrain.drivesubsystem import DriveSubsystem

NAMES = ["front-left", "front-right", "back-left", "back-right"]


class FakeDrive(DriveSubsystem):
    """Concrete drive with the vendor hooks stubbed."""

    def __init__(self, *args, **kwargs):
        self._fake_pose = Pose2d(1.0, 2.0, Rotation2d(0.3))
        self.reset_calls = []
        self.std_devs = None
        self.controls = []
        self.perspective = []
        super().__init__(*args, **kwargs)
        self._initialized = True

    def get_state(self):
        return MagicMock(pose=self._fake_pose)

    def reset_pose(self, pose):
        self.reset_calls.append(pose)
        self._fake_pose = pose

    def set_vision_measurement_std_devs(self, std_devs):
        self.std_devs = std_devs

    def set_control(self, request):
        self.controls.append(request)

    def set_operator_forward_direction(self, direction):
        self.perspective.append(direction)

    def update_sim_state(self, dt, voltage):
        self.sim_state = (dt, voltage)


def _module():
    m = MagicMock()
    m.get_position.return_value = SwerveModulePosition()
    m.get_state.return_value = SwerveModuleVelocity()
    m.update_sim.return_value = 2.0
    return m


def _container():
    c = MagicMock()
    c.robot.period = 0.02
    c.robot.counter = 1
    c.robot.robot_constants.MAX_WHEEL_LINEAR_VELOCITY = 4.0
    c.robot_x_width = 0.8
    c.robot_y_width = 0.8
    c.game_field.field_length = 16.0
    c.game_field.field_width = 8.0
    c.max_speed = 4.0
    c.is_red_alliance = False
    c.alliance_location = 0
    c._limit_chooser.get_selected.return_value = 1.0
    return c


def _consts():
    k = MagicMock()
    k.DriveSlewRate = k.RotationSlewRate = 3.0
    k.TranslationStepVoltage = 4.0
    k.SteerStepVoltage = 7.0
    k.RotationStepVoltage = 7.0
    k.RotationRampRate = 1.0
    return k


@pytest.fixture(autouse=True)
def quiet_logger():
    with patch.object(ds_mod, "Logger"), patch.object(ds_mod, "LogTracer"):
        yield


def make(sim = False, container = None):
    container = container or _container()
    modules = {n: _module() for n in NAMES}
    with (
        patch.object(ds_mod.RobotBase, "is_simulation", return_value=sim),
        patch.object(DriveSubsystem, "_start_sim_thread") as start,
    ):
        d = FakeDrive(_consts(), modules, container)
    d._start_mock = start
    return d, modules, container


def test_init_sets_defaults():
    d, modules, c = make()
    assert d.is_initialized
    assert d.robot is c.robot
    assert d.container is c
    assert d.gyro is d._gyro
    assert d.vision_odometry is False
    assert d.field_relative is False
    d._start_mock.assert_not_called()
    c.register_alliance_change_callback.assert_called_once_with(d._alliance_change)
    assert d._sys_id_routine_to_apply is d._sys_id_routine_translation
    assert d.counter == c.robot.counter
    assert d.field2d is c.robot.field2d


def test_init_in_simulation_starts_sim_thread():
    d, _, _ = make(sim=True)
    d._start_mock.assert_called_once()


def test_sysid_commands_delegate_to_selected_routine():
    d, _, _ = make()
    d._sys_id_routine_to_apply = MagicMock()
    d.sys_id_quasistatic("fwd")
    d.sys_id_dynamic("rev")
    d._sys_id_routine_to_apply.quasistatic.assert_called_once_with("fwd")
    d._sys_id_routine_to_apply.dynamic.assert_called_once_with("rev")


def test_sysid_config_and_mechanism_callbacks():
    configs, mechs = [], []
    with patch.object(ds_mod, "SysIdRoutine") as routine_cls, patch.object(ds_mod, "SignalLogger") as sl, patch.object(
            ds_mod, "SysIdRoutineLog"):
        routine_cls.Config.side_effect = lambda **kw: configs.append(kw) or kw
        routine_cls.Mechanism.side_effect = lambda *a: mechs.append(a) or a
        d, _, _ = make()
        for cfg in configs:
            cfg["record_state"](MagicMock())
        for drive_fn, log_fn, _ in mechs:
            drive_fn(1.5)
            log_fn(MagicMock())
    assert len(configs) == len(mechs) == 3
    assert len(d.controls) == 3
    assert sl.write_string.call_count == 3
    sl.write_double.assert_called_once_with("Rotational_Rate", 1.5)


def test_abstract_methods_raise():
    d, _, _ = make()
    with pytest.raises(NotImplementedError):
        DriveSubsystem.add_vision_measurement(d, Pose2d(), 0.0)
    with pytest.raises(NotImplementedError):
        d.sample_pose_at(0.0)
    with pytest.raises(NotImplementedError):
        d.set_module_states([])
    with pytest.raises(NotImplementedError):
        d.set_motor_brake(True)
    with pytest.raises(NotImplementedError):
        d.set_straight()


def test_start_sim_thread_runs_callback():
    container = _container()
    with patch.object(ds_mod.RobotBase, "is_simulation", return_value=False):
        d = FakeDrive(_consts(), {n: _module() for n in NAMES}, container)
    with (
        patch.object(ds_mod, "Notifier") as notifier,
        patch.object(ds_mod.utils, "get_current_time_seconds", side_effect=[1.0, 1.5]),
        patch.object(ds_mod.RobotController, "get_battery_voltage", return_value=12.0),
    ):
        d._start_sim_thread()
        callback = notifier.call_args.args[0]
        callback()
    notifier.return_value.start_periodic.assert_called_once_with(d._SIM_LOOP_PERIOD)
    assert d.sim_state == (0.5, 12.0)


@pytest.mark.parametrize("sim,loc,red", [(False, 1, False), (True, 0, False), (True, 2, True), (True, 3, False)])
def test_alliance_change(sim, loc, red):
    d, _, c = make(sim=sim)
    d._is_simulation = sim
    d._gyro.yaw = 45.0
    c.robot.simulation_constants.RED_TEST_POSE = {1: Pose2d(9, 9, 0), 2: Pose2d(8, 8, 0), 3: Pose2d(7, 7, 0)}
    c.robot.simulation_constants.BLUE_TEST_POSE = {1: Pose2d(1, 1, 0), 2: Pose2d(2, 2, 0), 3: Pose2d(3, 3, 0)}
    pose = d._alliance_change(red, loc)
    if not sim:
        assert pose == Pose2d(0, 0, 0)
    elif loc == 0:
        assert pose.rotation().degrees() == pytest.approx(45.0)
    else:
        table = c.robot.simulation_constants.RED_TEST_POSE if red else c.robot.simulation_constants.BLUE_TEST_POSE
        assert pose == table[loc]


def test_telemetry_and_dashboard():
    d, _, _ = make()
    d._gyro = MagicMock()
    d.telemetry_init()
    d._gyro.telemetry_init.assert_called_once()
    d.dashboard_periodic()
    d._gyro.dashboard_periodic.assert_called_once()
    d._is_simulation = True
    d._last_pose = Pose2d(1, 2, Rotation2d(0))
    d.dashboard_periodic()
    assert ds_mod.Logger.record_output.call_count == 3


@pytest.mark.parametrize(
    "initialized, applied, disabled, alliance",
    [
        (False, False, True, Alliance.RED),
        (True, False, True, Alliance.RED),
        (True, False, True, Alliance.BLUE),
        (True, False, True, None),
        (True, True, False, Alliance.RED),
        (True, True, True, Alliance.BLUE),
    ],
)
def test_periodic(initialized, applied, disabled, alliance):
    d, modules, c = make()
    d._initialized = initialized
    d._has_applied_operator_perspective = applied
    d._gyro = MagicMock()
    c.robot.counter = 100
    c.robot.is_enabled.return_value = True
    with (
        patch.object(ds_mod.DriverStationBackend, "is_disabled", return_value=disabled),
        patch.object(ds_mod.DriverStationBackend, "get_alliance", return_value=alliance),
    ):
        d.periodic()
    if not initialized:
        d._gyro.periodic.assert_not_called()
        return
    d._gyro.periodic.assert_called_once()
    for m in modules.values():
        m.periodic.assert_called_once()
    expect_set = (not applied or disabled) and alliance is not None
    assert bool(d.perspective) == expect_set
    if expect_set:
        expected = d._RED_ALLIANCE_PERSPECTIVE_ROTATION if alliance == Alliance.RED else d._BLUE_ALLIANCE_PERSPECTIVE_ROTATION
        assert d.perspective[0] == expected


def test_periodic_dashboard_cadence_when_enabled():
    d, _, c = make()
    d._gyro = MagicMock()
    c.robot.counter = 23
    c.robot.is_enabled.return_value = True
    with (
        patch.object(ds_mod.DriverStationBackend, "is_disabled", return_value=False),
        patch.object(ds_mod.DriverStationBackend, "get_alliance", return_value=None),
    ):
        d.periodic()
    d._gyro.dashboard_periodic.assert_called_once()


def test_sim_init_and_update_sim():
    d, modules, _ = make()
    d._gyro = MagicMock()
    del modules["back-right"].sim_init
    del modules["back-right"].update_sim
    del modules["back-left"].simulation_periodic
    physics = MagicMock()
    d.sim_init(physics)
    assert d._physics_controller is physics
    modules["front-left"].sim_init.assert_called_once_with(physics)
    d._gyro.sim_init.assert_called_once_with(physics)
    assert d.update_sim(1.0, 0.02) == pytest.approx(6.0)
    for m in modules.values():
        if hasattr(m, "update_sim"):
            m.update_sim.return_value = None
    assert d.update_sim(1.0, 0.02) is None
    d._gyro = None
    d.sim_init(physics)


def test_simulation_periodic_clamps_pose_to_field():
    d, modules, _ = make()
    del modules["back-left"].simulation_periodic
    d._fake_pose = Pose2d(-5.0, 20.0, Rotation2d(0.1))
    d.simulation_periodic()
    assert d.reset_calls[-1].x == pytest.approx(0.4)
    assert d.reset_calls[-1].y == pytest.approx(7.6)
    n = len(d.reset_calls)
    d._fake_pose = Pose2d(20.0, 4.0, Rotation2d(0.1))
    d.simulation_periodic()
    assert d.reset_calls[-1].x == pytest.approx(15.6)
    d._fake_pose = Pose2d(5.0, 4.0, Rotation2d(0.1))
    k = len(d.reset_calls)
    d.simulation_periodic()
    assert len(d.reset_calls) == k
    assert n >= 1
    d._initialized = False
    d.simulation_periodic()
    assert len(d.reset_calls) == k


def test_pose_accessors():
    d, _, _ = make()
    d._fake_pose = Pose2d(3, 4, Rotation2d.from_degrees(90))
    assert d.pose == d._fake_pose
    assert d.heading.degrees() == pytest.approx(90)
    assert d.get_angle() == pytest.approx(90)
    d.pose = Pose2d(5, 6, Rotation2d(0))
    assert d.reset_calls[-1] == Pose2d(5, 6, Rotation2d(0))
    assert d.chassis_speeds() is d._field_speeds
    assert d.get_swerve_expected_state() is d._expected_swerve_states
    pose3d = d.get_robot_3d(Pose2d(1, 2, Rotation2d(0)), Rotation3d())
    assert (pose3d.x, pose3d.y, pose3d.z) == (1.0, 2.0, 0.0)


def test_get_angular_velocity():
    d, _, _ = make()
    d._gyro = MagicMock()
    d._gyro.inputs.yaw_rate = 1.25
    assert d.get_angular_velocity() == 1.25


def test_drive_robot_relative_and_scaling():
    d, _, c = make()
    d.drive(1.0, 0.5, 0.2)
    assert d._field_speeds.vx == pytest.approx(1.0, abs=0.05)
    c._limit_chooser.get_selected.return_value = 0.5
    d.drive(2.0, 0.0, 0.0)
    assert d._field_speeds.vx == pytest.approx(1.0, abs=0.05)
    # clipped to max speed
    c.max_speed = 0.1
    d.drive(2.0, 0.0, 0.0)
    assert d._field_speeds.vx == pytest.approx(0.1)


def test_drive_field_relative_uses_gyro_heading():
    d, _, _ = make()
    d._gyro = MagicMock()
    d._gyro.heading = Rotation2d.from_degrees(90)
    d.drive(1.0, 0.0, 0.0, field_relative=True)
    assert abs(d._field_speeds.vx) < 0.05
    assert abs(d._field_speeds.vy) == pytest.approx(1.0, abs=0.05)


def test_drive_square_not_supported():
    d, _, _ = make()
    with pytest.raises(NotImplementedError):
        d.drive(1, 0, 0, square=True)
    with pytest.raises(NotImplementedError):
        d.arcade_drive(1, 0, assume_manual_input=True)


def test_arcade_rotate_and_stop():
    d, _, _ = make()
    d._gyro = MagicMock()
    d._gyro.heading = Rotation2d()
    d.rotate(0.5)
    assert d._field_speeds.omega == pytest.approx(0.5, abs=0.02)
    d.stop()
    assert d._field_speeds.omega == pytest.approx(0.0)


@pytest.mark.parametrize("selected, expected", [(0.5, 0.5), (3.0, 1.0), (-1.0, 0.0), ("x", 0.1), (None, 0.1)])
def test_drive_scale_factor(selected, expected):
    d, _, c = make()
    c._limit_chooser.get_selected.return_value = selected
    assert d.drive_scale_factor == expected


def test_drive_scale_factor_exception_defaults_to_one():
    d, _, c = make()
    c._limit_chooser.get_selected.side_effect = RuntimeError("boom")
    assert d.drive_scale_factor == 1.0


def test_apply_states_desaturates_and_forwards():
    d, modules, _ = make()
    states = tuple(SwerveModuleVelocity(10.0, Rotation2d(0.1)) for _ in range(4))
    d.apply_states(states)
    for m in modules.values():
        m.apply_states.assert_called_once()
    assert all(abs(s.velocity) <= 4.0 + 1e-9 for s in d._expected_swerve_states)


def test_module_positions_and_states():
    d, modules, _ = make()
    assert len(d.get_module_positions()) == 4
    assert len(d.get_module_states()) == 4
    modules["front-left"].get_state.assert_called()


def test_drive_with_pathplanner_path_sets_control():
    d, _, _ = make()
    ff = MagicMock()
    ff.robotRelativeForcesXNewtons = [0.0] * 4
    ff.robotRelativeForcesYNewtons = [0.0] * 4
    d.apply_robot_speeds = MagicMock()
    d.drive_with_pathplanner_path(ChassisVelocities(1, 0, 0), ff)
    assert len(d.controls) == 1
