# AGENTS.md – Guide for AI Coding Agents

This document provides essential information for AI agents working on **frclib-6107**, Team
6107's FRC Python helper library (`lib_6107`).

## Project Overview

**frclib-6107** is a high-performance FRC robot library for the **2027 season (Systemcore)**. It extracts
common components from Team 6107's competition robot into a reusable, modular framework. Key impact: reducing
main robot code bloat while keeping the periodic loop under 20 mS.

| Item            | Value                                                                                             |
|-----------------|---------------------------------------------------------------------------------------------------|
| Package / src   | `lib_6107` / `src/lib_6107/`                                                                      |
| Version         | `2027.0.0.1` (first number is the FRC season; `pyproject.toml` is authoritative)                  |
| Python          | 3.14+ (`.python-version`)                                                                         |
| Framework       | RobotPy **2027.0.0a8** (alpha; `[tool.uv] prerelease = "allow"`), commands-v2 (`commands2`)       |
| Vendors         | CTRE `phoenix6>=26.70.0a2`, `robotpy-rev`, `robotpy-navx`, `photonlibpy`, `limelightlib-python`   |
| Port status     | Branch `2027-systemcore-port`; see [`docs/2027_port_status.md`](docs/2027_port_status.md)         |

> The 2027 port is a **clean-break rename to snake_case** with no camelCase aliases. All code, snippets and new
> tests must use the 2027 names (`record_output`, `robot_periodic`, `disabled_init`, ...). `pyfrc` is gone.

### Core Architecture

1. **pykit Logging** – Centralized telemetry pipeline for three execution modes (REAL, SIMULATION, REPLAY). All robot
   data flows through the `Logger` singleton.
2. **Robot Lifecycle & Mode Management** – Base `Robot` class extends `pykit`'s `LoggedRobot`, orchestrating state
   transitions (Disabled → Autonomous/Teleop → Utility) with subsystem hooks (`stop()`, `fault_detection()`,
   `sim_init()`, `update_sim()`).
3. **Constants-Driven Configuration** – Three dataclasses (`RobotConstants`, `SimulationConstants`,
   `NetworkConstants`) let teams override values for their hardware without touching library code.

### Directory Structure

```
frclib-6107/
├── src/lib_6107/            # Library package (import as `lib_6107`)
│   ├── robot.py             # Base Robot class (extends pykit LoggedRobot)
│   ├── robotcontainer.py    # Base RobotContainer (subsystems, OI, bindings, autonomous selection)
│   ├── constants.py         # RobotConstants/SimulationConstants/NetworkConstants, ROBOT_MODE
│   ├── physics.py           # PhysicsEngine – driven by Robot.simulation_periodic()
│   ├── commands/            # Command-based v2 commands
│   │   ├── command.py       # BaseCommand – extend this, never commands2.Command directly
│   │   ├── constants.py     # Command-related constants
│   │   ├── pathplanner.py   # PathPlanner helpers (no 2027 pathplannerlib release yet)
│   │   ├── _command_template.py / _commandgroup_template.py  # Copy these for new commands
│   │   ├── drivetrain/      # aimtodirection, arcade_drive, gotopoint, reset_xy, swervetopoint, trajectory
│   │   └── vision/          # approach_tag, find_object, follow_object, set_camera_pipeline, track_tag_command, turn_to_object
│   ├── subsystems/          # Hardware-facing subsystems
│   │   ├── subsystem.py     # SubsystemBase – extend this, never commands2.Subsystem directly
│   │   ├── constants.py     # Subsystem-related constants
│   │   ├── operator_interface.py  # Driver/operator controller helpers (deadband/square/invert, rumble)
│   │   ├── drivetrain/      # DriveSubsystem + CTRE swerve implementations
│   │   ├── gyro/            # Gyro base + NavX (navx_imu) and Pigeon2
│   │   ├── rpm/             # Flywheel/RPM subsystems (generic, CTRE, REV)
│   │   ├── vision/          # PhotonVision/Limelight subsystems, photonvision_sim, odometry/
│   │   └── pykit/           # AdvantageKit-style IO interfaces + robot_state.py (RobotState pose/odometry)
│   ├── pykit/               # Telemetry & logging framework (independent of subsystems)
│   │   ├── logger.py        # Logger singleton – telemetry pipeline entry point
│   │   ├── logtracer.py     # LogTracer performance profiling spans
│   │   ├── loggedrobot.py, logtable.py, logvalue.py, logreplaysource.py, logdatareceiver.py, timeutil.py
│   │   ├── alertlogger.py, autolog.py, LoggedMechanism*.py, LoggedNetworkButton.py
│   │   ├── inputs/          # Loggable wrappers (DriverStation, PowerDistribution, SystemStats)
│   │   ├── networktables/   # NT4Publisher and LoggedNetwork*/LoggedDashboardChooser input wrappers
│   │   └── wpilog/          # WPILOG reader/writer + constants
│   ├── field/               # GameField (field + AprilTags), FieldLayout, FieldSource, FlipUtil, coordinates; see README
│   └── util/                # alerts, asyncio_wrapper, elastic_utils, numerical_chooser,
│                            # preflight, statistics, phoenix6/ (try_until_ok, handle_faults, signals), rev/
├── tests/                   # pytest suite mirroring src/ layout: {commands,pykit,subsystems,util}/ + top-level
│                            # test_robot.py, test_robotcontainer.py, test_physics.py
├── example/                 # Reference team robot (robot.py, robotcontainer.py, constants.py, generated/) with
│                            # its own pyproject.toml/uv.lock; ruff excludes it
├── docs/                    # Project documentation (see "Documentation Map" below)
├── scripts/                 # 2027 port helpers (check_2027_imports.py, skip_tests.py, unskip_tests.py)
├── .github/
│   ├── workflows/           # ci.yml (manual only), code-quality.yml, bandit.yml
│   ├── instructions/        # Path-scoped Copilot rules (commands, constants, python, robotics, subsystems, tests)
│   ├── prompts/             # add-telemetry, generate-unit-tests, new-command, new-subsystem
│   ├── agents/              # ctre-phoenix-api (reads docs/ctre/PHOENIX6_APIs.md), test-agent
│   └── skills/              # build-and-release, frc-rules
├── pyproject.toml           # Metadata, dependencies, pytest/ruff/commitizen config
├── tox.ini, Makefile        # test / lint / bandit / release targets
└── .pre-commit-config.yaml  # ruff-check, ruff-format + hygiene hooks
```

### Entry Points

- **`src/lib_6107/robot.py:Robot`** – Main controller. `Robot(build_year, robot_constants, simulation_constants,
  network_constants)`; `robot_init(container_init)` takes a factory `Callable[[Robot], RobotContainer]`.
- **`src/lib_6107/robotcontainer.py:RobotContainer`** – Teams subclass this and implement `subsystem_init()`, button
  bindings (`_configure_*_button_bindings_xbox`), and `get_autonomous_command()`.
- **`src/lib_6107/subsystems/subsystem.py:SubsystemBase`** – Base class for all subsystems.
- **`src/lib_6107/pykit/logger.py:Logger`** – Singleton managing telemetry capture, replay, and output backends.

## Key Patterns & Conventions

### 1. Mode Detection

`ROBOT_MODE` (in `constants.py`, type `RobotModes`) is set once at import time:

- **REAL** – Physical robot (Systemcore). Logs to USB `/U/logs` (fallback: `<cwd>/pyLogs`, `/home/lvuser` if cwd is
  `/`) plus NT4. Vendor logging (Phoenix6 `SignalLogger`, REV `StatusLogger`) is disabled; pykit only. Python logging
  is set to ERROR.
- **SIMULATION** – WPILib desktop sim (**pyfrc is removed**; sim/testing is part of WPILib in 2027). Logs to a local
  `.wpilog` file + NT4. `Robot.simulation_init()` creates `PhysicsEngine`; `Robot.simulation_periodic()` calls its
  `update_sim()`.
- **REPLAY** – Set `LOG_PATH` to a `.wpilog` file; output is written to `<name>_sim.wpilog`. WPILib timing is disabled
  (`self.UseTiming = False`) for max-speed analysis.

Use `match ROBOT_MODE:` for mode-specific logic, or `RobotBase.is_real()` / `RobotBase.is_simulation()`.

### 2. Logging & Dashboards: Logger + tunables, not SmartDashboard

All telemetry goes through `Logger.record_output(key, value)`. Never use `SmartDashboard.putXXX()`; the 2027
`SmartDashboard`/`Sendable` family is deprecated and being removed (`docs/phase-3-modifications.md`).

- Robot metadata: `Logger.record_metadata("Robot", "MyRobot2027")` (set in `Robot.__init__`)
- Command state: `Logger.record_output(f"Commands/{name}", active)` (registered in `Robot.robot_init`)
- Subsystem data: `Logger.record_output("Subsystems/Drivetrain/Velocity", v)` – paths use `/` separators
- Replay: `Logger.set_replay_source(WPILOGReader(log_path))` feeds historical data back to user code

Operator-editable values and field visualization use WPILib 2027's `tunables` package (e.g.
`tunables.publish("Field", self.field2d)`); output-only data may use `telemetry`. Both are alpha-8 APIs – see
[`docs/2027-telemetry-and-tunables-tutorial.md`](docs/2027-telemetry-and-tunables-tutorial.md), especially the
thread-safety section (`tunables` is main-thread only). The pykit `Logged*` input wrappers (`LoggedDashboardChooser`,
`LoggedNetwork*`, `LoggedNetworkButton`) are tunables-backed and operator-facing values appear in Elastic; do not
reintroduce `SmartDashboard`/`SendableChooser`.

### 3. Constants Pattern: Override Without Modification

**RobotConstants** (`src/lib_6107/constants.py`) – physical dimensions, periodic rates (`ROBOT_PERIOD` 20 mS,
`ODOMETRY_PERIOD` 10 mS), drivetrain limits (`MAX_SPEED`, `MAX_ANGULAR_VELOCITY`, typically from Tuner X), controller
ports and deadbands. Teams subclass it (e.g. `MyCyberJagzzConstants(RobotConstants)`) and pass an instance to
`Robot.__init__(robot_constants=...)`.

**SimulationConstants** – Starting poses for blue/red alliance at three drive positions (left, center, right).

**NetworkConstants** – Team number and addresses (updates via the `team` property). Attribute names still use the
legacy `ROBORIO_*` prefix (including the existing `ROBORIO_MDMS` spelling) even though 2027 targets Systemcore; do not
rename without a deliberate API change.

Constants dataclasses use `@dataclass(slots=True)`. Never modify library defaults.

### 4. Subsystem Lifecycle Hooks

All subsystems extend `SubsystemBase(container, name, long_name)` and may implement:

- **`stop()`** – Called on `disabled_init()` and `teleop_exit()`; zero out mechanism power.
- **`fault_detection(state, clear=True, notify=True)`** – Called at mode transitions (`"Disabled-Init"`,
  `"Autonomous-Exit"`, `"Teleop-Exit"`, `"End-Competition"`, ...).
- **`record_metadata()`** – Log firmware versions, mechanism type, startup faults.
- **`dashboard_initialize()` / `dashboard_periodic()`** – Static / periodic dashboard telemetry via `Logger`.
- **`is_connected`** / **`_check_is_connected()`** – Device connectivity (must be implemented in derived classes).
- **`sim_init(physics_controller)`** / **`update_sim(now, tm_diff)`** – Simulation-only.

**Important:** `SubsystemBase.__init__` sets `self._initialized = False`; set `self._initialized = True` at the very
end of your own `__init__`. This prevents `periodic()` running before vendor firmware init completes.

### 5. Command Pattern: Commands-v2 with Logger Integration

Commands extend `BaseCommand`. `Robot.robot_init()` registers `CommandScheduler` callbacks that log
`Commands/<name>` as active/inactive (reference-counted, so duplicate names work):

```python
scheduler = CommandScheduler.get_instance()
scheduler.on_command_initialize(lambda c: log_command_function(c, True))
scheduler.on_command_finish(lambda c: log_command_function(c, False))
scheduler.on_command_interrupt(lambda c: log_command_function(c, False))
```

### 6. Performance Profiling: LogTracer

`LogTracer` (`pykit/logtracer.py`) profiles code spans; used in `Robot.robot_periodic()`:

```python
LogTracer.reset_outer("RobotPeriodic")
self.container.robot_periodic()
LogTracer.record("ContainerPeriodic")
self._command_scheduler.run()
LogTracer.record("CommandsPeriodic")
LogTracer.record_total()
```

Results appear under `LogTracer/RobotPeriodic/...` in AdvantageScope; loop statistics (`RobotStatistics`) are
published as `Periodic/Robot/*-periodic-%` (% of the robot period).

### 7. Vision & Odometry

Vision (PhotonVision, Limelight) integrates via `VisionSubsystem` in `subsystems/vision/`. Pose state lives in
`subsystems/pykit/robot_state.py:RobotState` (class-level singleton; call `RobotState.configure(kinematics)` once, then
`RobotState.periodic(...)` from the team's `RobotContainer.robot_periodic()` override – the base container does not
call it). It feeds `Robot.field2d` (`Field2d`).

Field and AprilTag data live in `lib_6107/field/` (see its `README.md`). Terminology: `field2d` is the WPILib
`Field2d` dashboard widget; `GameField` (`container.game_field`) is the year-specific field object that owns the
current `FieldLayout` (size + AprilTags) and notifies vision code via `register_callback()`. Teams subclass
`GameField` per season. Use `tag_id` for AprilTag ids in new code.

### 8. Utility mode replaces Test mode

2027 removes Test mode. Use `utility_init()` / `utility_periodic()` / `utility_exit()`; `Robot.utility_init()`
cancels all scheduled commands.

## Developer Workflows

### Environment

```bash
make venv          # Create .venv via uv
uv sync --locked   # What CI runs; keep uv.lock in sync with pyproject.toml
```

The project uses `uv`. RobotPy 2027 is alpha: after changing dependencies run `uv lock` and commit `uv.lock`. A
locally patched `robotpy-native-wpihal` wheel is needed on Ubuntu 24.04 (glibc); that breaks `uv sync --locked`
locally, so see `docs/2027_port_status.md` before debugging import errors.

### Running Tests

```bash
make test                       # tox-uv (envlist clean,py314); pytest config in pyproject.toml / tox.ini
uv run python -m pytest         # What CI runs
uv run python -m pytest tests/pykit/test_logger.py -q   # Targeted run
```

`src/` is on `pythonpath` automatically. Tests mirror `src/` under `tests/`. Some tests are skipped with
`@pytest.mark.skip(reason="Feature is currently under development")` (managed by `scripts/skip_tests.py` /
`scripts/unskip_tests.py`); `tests/commands/test_pathplanner.py` is skipped because pathplannerlib has no 2027 build.
Do not hard-code pass counts in docs; they change (see `docs/2027_port_status.md` for the last recorded numbers).

### Linting & Security

```bash
make lint            # ruff check on src/lib_6107 (config: [tool.ruff] in pyproject.toml, line length 120)
make ruff-fix        # ruff --fix + ruff format
make bandit          # Security scan (config: .bandit)
uv run pre-commit install          # one-time: install git hook
uv run pre-commit run --all-files  # ruff-check, ruff-format, whitespace/yaml/merge hygiene hooks
```

`.pylintrc` and `PYLINT_*` Makefile variables are legacy; `make lint` is ruff. `tests/` and `example/` are excluded
from ruff.

### Build & Release

```bash
make release-check   # distclean + venv + test + bandit + lint + ruff
make release-build   # uv build --no-sources → dist/
make publish         # uv publish (requires UV_PUBLISH_TOKEN, via the gitignored .make/pypi-token.mk)
```

The `build-and-release` skill (`.github/skills/build-and-release/`) automates these (Windows scripts implemented; Linux
placeholder). Never commit tokens. Commit messages follow Conventional Commits (`commitizen`; version bumps update
`pyproject.toml` and `src/lib_6107/__init__.py`; note `__version__` there currently lags at `2026.0.0.6`).

### Continuous Integration

- **CI** (`.github/workflows/ci.yml`) – `uv sync --locked` then `uv run python -m pytest` on `ubuntu-latest` and
  `windows-latest`. **Currently manual (`workflow_dispatch`) only**; push/PR triggers are commented out.
- **Code Quality** (`.github/workflows/code-quality.yml`) – all `pre-commit` hooks on push to `main`, PRs, and manual.
- **Bandit** (`.github/workflows/bandit.yml`) – security scan on push to `main` and PRs to `main`.
- **Release** (`.github/workflows/release.yml`) – on `v*` tags: verify, test, build, TestPyPI, PyPI via trusted
  publishing (see `docs/RELEASING.md`).

CI calls `uv`/`pytest`/`pre-commit` directly instead of `make`, since the Makefile `include`s the gitignored
`.make/pypi-token.mk`.

## Critical Files & References

| File                                   | Purpose                                                                  |
|----------------------------------------|--------------------------------------------------------------------------|
| `src/lib_6107/robot.py`                | Base robot class; mode detection, logging setup, periodic coordination   |
| `src/lib_6107/constants.py`            | RobotConstants, SimulationConstants, NetworkConstants; ROBOT_MODE global |
| `src/lib_6107/robotcontainer.py`       | Container for subsystems, operator interface, button bindings            |
| `src/lib_6107/subsystems/subsystem.py` | SubsystemBase with lifecycle hooks                                       |
| `src/lib_6107/physics.py`              | PhysicsEngine for simulation                                             |
| `src/lib_6107/pykit/logger.py`         | Logger singleton; telemetry pipeline management                          |
| `src/lib_6107/pykit/logtracer.py`      | Performance profiling spans and timing                                   |
| `example/robotcontainer.py`            | Reference implementation for teams                                       |
| `Makefile`, `pyproject.toml`           | Build/test/lint/release targets; metadata, dependencies, tool config     |

## Documentation Map

| Doc                                              | Contents                                                              |
|--------------------------------------------------|-----------------------------------------------------------------------|
| `docs/2027_port_status.md`                       | Current 2027 / Systemcore port status, remaining work, blockers       |
| `docs/2027-telemetry-and-tunables-tutorial.md`   | `telemetry`/`tunables` APIs, threading rules, how lib_6107 uses them  |
| `docs/phase-1-…`, `phase-2-…`, `phase-3-…`       | Port phase write-ups (pyfrc removal, SmartDashboard replacement)      |
| `docs/pykit-akit/`                               | AdvantageKit vs pykit comparisons and telemetry source notes          |
| `docs/Telemetry.md`, `docs/WPILOG-Background-Writer.md` | Telemetry and background WPILOG writer design                  |
| `docs/ctre/PHOENIX6_APIs.md`                     | Phoenix6 `configs` API lookup (used by the ctre-phoenix-api agent)    |
| `docs/CI-SETUP.md`                               | CI setup notes                                                        |
| `CHANGELOG.md`, `README.md`                      | Release history and roadmap                                           |

## Common Tasks for AI Agents

### Adding a New Subsystem

1. Create a class extending `SubsystemBase` in `src/lib_6107/subsystems/{name}/` (see `.github/prompts/new-subsystem.prompt.md`).
2. Call `super().__init__(container, name, long_name)`; set `self._initialized = True` at the end of `__init__`.
3. Override lifecycle hooks (`stop()`, `fault_detection()`, `sim_init()`, `update_sim()`) as needed.
4. Log telemetry via `Logger.record_output("SubsystemName/Key", value)`.
5. Return it from the team's `RobotContainer.subsystem_init()`.
6. Add tests under `tests/subsystems/`.

### Adding a New Command

1. Copy `src/lib_6107/commands/_command_template.py` or `_commandgroup_template.py` (see `new-command.prompt.md`).
2. Implement `initialize()`, `execute()`, `end(interrupted)`, `is_finished()`.
3. Command state logging is automatic once scheduled via the `CommandScheduler`.
4. Bind to a controller in `RobotContainer._configure_*_button_bindings_xbox()`.

### Adding Telemetry

Use `Logger.record_output(path, value)` in any periodic method (see `add-telemetry.prompt.md`). Paths use `/`
separators and appear automatically in AdvantageScope on replay.

### Modifying Constants

Override in the team's constants subclass; pass the instance to `Robot.__init__()`. Never modify library defaults in
`src/lib_6107/constants.py`.

### Working with CTRE Phoenix 6

Constructors take a `CANBus`; check `docs/ctre/PHOENIX6_APIs.md` for config classes and verify names against the
installed `phoenix6` package. Use `try_until_ok()` / `handle_faults()` from `lib_6107.util.phoenix6.utils`.

## Performance Targets & Known Issues

- **Loop time target:** < 20 mS (the 2026 baseline was ~23 mS). Vendor signal logging is disabled in favor of the
  background `WPILOGWriter` (`docs/WPILOG-Background-Writer.md`).
- **LogTracer overhead:** Minimal; designed for profiling without breaking timing.
- **Known 2027 blockers** (details in `docs/2027_port_status.md`):
  - `robotpy-pathplannerlib` has no 2027 release → pathfinding init in `Robot.robot_init()` is skipped
    (`LocalADStar` disabled); `commands/pathplanner.py` and its tests are not usable.
  - `photonlibpy` fails to import against the alpha-8 wheels (`photonvision*.py` cannot be imported).
  - `robotpy-navx` only has a 2027 alpha (`navx.Navx`; no calibration state, no sim device).
  - Limelight-style helpers (`getA`, `getHB`) and `drivetrain.getTurnRate` used by older vision commands are unported.
  - CTRE drivetrain/RPM code imports cleanly but is untested on hardware.

## Integration Notes

- **PathPlanner:** Disabled for 2027 until a compatible `pathplannerlib` is released (see blockers above).
- **CTRE Phoenix6 & REV:** Both supported; REV uses native rotations/RPM converted to radians. Vendor auto-logging is
  disabled in `Robot.robot_init()` in favor of pykit.
- **WPILib Field2d:** Created in `Robot.robot_init()` as `Robot.field2d` and published with
  `tunables.publish("Field", ...)`; updated by the team's odometry code.
- **Elastic Dashboard:** Connects via NT4. `send_notification()` raises alerts; `select_tab("PREFLIGHT")` is called at
  startup (`util/elastic_utils.py`).

## Troubleshooting for AI Agents

1. **`ImportError: cannot import name ... from wpimath/wpilib`** – The environment likely has older wheels than
   `pyproject.toml` requires (e.g. a 2027.0.0a6 `.venv` lacks `wpimath.units.inches_to_meters`; a8+ is required). Run
   `uv sync` and re-check. Use `scripts/check_2027_imports.py` to find
   missing 2027 names.
2. **`AttributeError` on a camelCase call** (`recordOutput`, `robotPeriodic`, `getName`, ...) – the API is snake_case
   in 2027; rename, do not add aliases.
3. **Periodic loop slow** – Use `LogTracer`; check `LogTracer/RobotPeriodic/TotalMS` and `Periodic/Robot/*-periodic-%`.
4. **Logger not recording data** – Verify `Logger.start()` ran (happens at the end of `Robot.__init__` after the
   pipeline is configured).
5. **Simulation issues** – Check `SimulationConstants` poses match field dimensions and that subsystems are returned
   from `subsystem_init()` so `update_sim()` is called.
6. **Replay playback** – Set `LOG_PATH` to the absolute path of a `.wpilog` file before launching the sim; output goes
   to `<log>_sim.wpilog`.
7. **Phoenix6 constructor errors** – Pass a `CANBus`, not a bare device id/string only (see
   `docs/ctre/PHOENIX6_APIs.md`).
