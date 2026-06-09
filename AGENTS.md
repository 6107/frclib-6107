# AGENTS.md – Guide for AI Coding Agents

This document provides essential information for AI agents working on **frclib-6107**, Team
6107's FRC Python helper library.

## Project Overview

**frclib-6107** is a high-performance FRC robot library targeting 2026+ seasons. It extracts
common components from Team 6107's actual competition robot into a reusable, modular framework.
Key impact: reducing main robot code bloat while maintaining <20 mS periodic loop time.

### Core Architecture

The library is structured around three critical concerns:

1. **pykit Logging** – Centralized telemetry pipeline handling three execution modes (REAL robot, SIMULATION, REPLAY
   logs). All robot data flows via `Logger` singleton, not `SmartDashboard`.
2. **Robot Lifecycle & Mode Management** – Base `Robot` class extends `LoggedRobot`, orchestrating state transitions (
   Disabled → Autonomous/Teleop → Test) with subsystem hooks (`stop()`, `fault_detection()`, `sim_init()`,
   `update_sim()`).
3. **Constants-Driven Configuration** – Three dataclass patterns (`RobotConstants`, `SimulationConstants`,
   `NetworkConstants`) allow teams to override values for their specific hardware without touching core library code.

### Entry Points

- **`src/lib_6107/robot.py:Robot`** – Main controller; initializes logging pipeline, manages mode transitions, profiles
  performance via `LogTracer`.
- **`src/lib_6107/robotcontainer.py:RobotContainer`** – Teams subclass this to define subsystems, operator interface (
  Xbox controllers), button bindings, and autonomous commands.
- **`src/lib_6107/subsystems/subsystem.py:SubsystemBase`** – Base class for all subsystems; provides lifecycle hooks (
  fault detection, sim support).
- **`src/lib_6107/pykit/logger.py:Logger`** – Singleton managing telemetry capture, replay, and output backends (
  NT4Publisher, WPILOGWriter/Reader).

## Key Patterns & Conventions

### 1. Mode Detection

The library auto-detects execution context at startup via `ROBOT_MODE` global in `constants.py`:

- **REAL** – Physical roboRIO. Logs to USB `/U/logs` (fallback: `/home/lvuser/pyLogs`). Runs vendor logging (Phoenix6
  SignalLogger, REV StatusLogger) disabled; pykit only.
- **SIMULATION** – pyfrc desktop sim. Logs to local file + NT4 for rapid iteration.
- **REPLAY** – Log playback driven by `LOG_PATH` environment variable. Disables WPILib timing to run analysis at maximum
  speed.

**Usage in code:** Check `ROBOT_MODE` enum value or use `RobotBase.isReal()` / `RobotBase.isSimulation()`.

### 2. Logging: Logger Singleton Over SmartDashboard

All telemetry goes through `Logger.recordOutput(key, value)`, not `SmartDashboard.putXXX()`. This integrates
AdvantageScope replay/analysis, handles all three modes transparently, and improves performance.

**Examples from codebase:**

- Robot metadata: `Logger.recordMetadata("Robot", "MyRobot2026")` (called in `Robot.__init__`)
- Periodic data: `Logger.recordOutput("Commands/IntakeCommand", True)` (called by command scheduler callbacks)
- Sensor inputs: Subsystems call `Logger.recordOutput("RobotState/Gyro/Angle", gyro.getAngle())`

**During REPLAY mode:** `Logger.setReplaySource(WPILOGReader(log_path))` feeds historical data; user code reads it as if
live.

### 3. Constants Pattern: Override Without Modification

Three dataclass patterns define all robot configuration:

**RobotConstants** (`src/lib_6107/constants.py`)

- Physical dimensions (robot mass, bumper thickness, wheel radius, chassis width)
- Periodic rates (ROBOT_PERIOD = 20 mS, ODOMETRY_PERIOD = 10 mS)
- Drivetrain limits (MAX_SPEED, MAX_ANGULAR_VELOCITY) – typically overridden from Tuner-X characterization
- Controller ports and deadbands

Teams create a subclass (e.g., `MyCyberJagzzConstants(RobotConstants)`) and pass to
`Robot.__init__(robot_constants=MyCyberJagzzConstants())`.

**SimulationConstants** – Starting poses for blue/red alliance at three drive positions (left, center, right).

**NetworkConstants** – Team number, roboRIO static IP, mDNS hostname (updates automatically via `team` property).

### 4. Subsystem Lifecycle Hooks

All subsystems extend `SubsystemBase` and may implement:

- **`stop()`** – Called on `disabledInit()` and `teleopExit()`; zero out mechanism power.
- **`fault_detection(state, clear, notify)`** – Called at mode transitions to detect/clear faults and send alerts.
  `state` parameter indicates context ("Disabled-Init", "Autonomous-Exit", etc.).
- **`sim_init(physics_controller)`** – Simulation-only setup.
- **`update_sim(now, tm_diff)`** – Simulation-only physics update; called after CommandScheduler's simulationPeriodic().
- **`record_metadata()`** – Initialization hook to log subsystem metadata (firmware versions, mechanism types) to
  Logger.

**Important:** Set `self._initialized = False` at start of `__init__`, then `self._initialized = True` at end.
This prevents race conditions where `periodic()` runs before initialization completes.

### 5. Command Pattern: Commands-v2 with Logger Integration

Commands use standard WPILib Commands-v2 (`commands2.Command`). Robot.robotInit() registers callbacks on
CommandScheduler to track active commands:

```python
def logCommandFunction(command: Command, active: bool) -> None:
    name = command.getName()
    Logger.recordOutput(f"Commands/{name}", active)

scheduler.onCommandInitialize(lambda c: logCommandFunction(c, True))
scheduler.onCommandFinish(lambda c: logCommandFunction(c, False))
scheduler.onCommandInterrupt(lambda c: logCommandFunction(c, False))
```

Command templates in `src/lib_6107/commands/` show structure.

### 6. Performance Profiling: LogTracer

`LogTracer` class (src/lib_6107/pykit/logtracer.py) profiles subsystem code execution. Used in `Robot.robotPeriodic()`:

```python
LogTracer.resetOuter("RobotPeriodic")
self.container.robotPeriodic()
LogTracer.record("ContainerPeriodic")
self._command_scheduler.run()
LogTracer.record("CommandsPeriodic")
LogTracer.recordTotal()
```

Results logged to AdvantageScope; stats aggregated in `RobotStatistics` and pushed to SmartDashboard
every ~1.5 seconds as CPU usage %.

### 7. Vision & Odometry Integration

Vision support (PhotonVision, Limelight) integrates via `VisionSubsystem` in `src/lib_6107/subsystems/vision/`.
Odometry (gyro, wheel encoders) typically updated in RobotContainer's `robotPeriodic()`, feeding
`Robot.field` (Field2d for visualization).

## Developer Workflows

### Running Tests

```bash
make test  # Runs pytest via tox-uv
```

Tests located in `tests/` and `tests/{commands,pykit,subsystems,util}`. All test paths configured in
`pyproject.toml` [tool.pytest.ini_options].

### Linting & Security

```bash
make lint       # pylint on src/lib_6107
make bandit-test  # Security scan
```

Pylint config in `.pylintrc` (disables: similarities, broad-except, missing-class-docstring). Bandit checks
for security vulnerabilities.

### Build & Release

```bash
make release-check   # clean + test + bandit + lint
make release-build   # Create dist/ with sdist/wheel
make publish         # Push to PyPI (requires UV_PUBLISH_TOKEN env var)
```

Release workflow uses `uv build` and `uv publish`. GitHub Actions planned for CI/CD (not yet implemented).

### Virtual Environment

```bash
make venv  # Creates .venv via uv
```

Project uses `uv` for dependency management. See `pyproject.toml` for core and dev dependencies. Python 3.14+ required.

## Critical Files & References

| File                                   | Purpose                                                                  |
|----------------------------------------|--------------------------------------------------------------------------|
| `src/lib_6107/robot.py`                | Base robot class; mode detection, logging setup, periodic coordination   |
| `src/lib_6107/constants.py`            | RobotConstants, SimulationConstants, NetworkConstants; ROBOT_MODE global |
| `src/lib_6107/robotcontainer.py`       | Container for subsystems, operator interface, button bindings            |
| `src/lib_6107/subsystems/subsystem.py` | SubsystemBase with lifecycle hooks                                       |
| `src/lib_6107/pykit/logger.py`         | Logger singleton; telemetry pipeline management                          |
| `src/lib_6107/pykit/logtracer.py`      | Performance profiling spans and timing                                   |
| `Example/robotcontainer.py`            | Reference implementation for teams                                       |
| `Makefile`                             | Build, test, lint, release targets                                       |
| `pyproject.toml`                       | Project metadata, dependencies, tool config                              |

## Common Tasks for AI Agents

### Adding a New Subsystem

1. Create class extending `SubsystemBase` in `src/lib_6107/subsystems/{name}/`.
2. Implement `__init__`, set `_initialized = False` at start, `True` at end.
3. Override lifecycle hooks (`stop()`, `fault_detection()`, `sim_init()`, `update_sim()`) as needed.
4. Log telemetry via `Logger.recordOutput("SubsystemName/Key", value)`.
5. Add to team's RobotContainer subclass in `subsystem_init()`.

### Adding a New Command

1. Copy `src/lib_6107/commands/_command_template.py` or `_commandgroup_template.py`.
2. Implement `initialize()`, `execute()`, `end(interrupted)`, `isFinished()`.
3. Log command state in `robotInit()` callback (automatic if scheduled by container).
4. Bind to Xbox controller in RobotContainer's `_configure_*_button_bindings_xbox()`.

### Adding Telemetry

Use `Logger.recordOutput(path, value)` in any periodic method. Path uses `/` separators
(e.g., `"Subsystems/Drivetrain/Velocity"`). Automatically appears in AdvantageScope upon playback.

### Modifying Constants

Override in team's constants subclass; pass instance to `Robot.__init__()`. Never modify
library defaults in `src/lib_6107/constants.py`.

## Performance Targets & Known Issues

- **Loop time target:** <20 mS for 2026 (README: "23 mS needs to drop to 20 mS"). Phoenix6 SignalLogger disabled to
  conserve cycles; WPILOGWriter used instead.
- **LogTracer overhead:** Minimal; designed for profiling without breaking timing.
- **Replay mode:** Disables WPILib timing (`robot.UseTiming = False`) to maximize log analysis speed.

## Integration Notes

- **PathPlanner:** LocalADStar pathfinder initialized globally in `Robot.robotInit()`.
- **CTRE Phoenix6 & REV:** Both supported; library depends on `phoenix6` and `robotpy-rev`. Vendor logging auto-disabled
  in favor of pykit.
- **WPILib Field2d:** Created in `Robot.robotInit()`; typically updated by odometry subsystem.
- **Elastic Dashboard:** Connects via NT4. Notification system (`send_notification()`) used for alerts. Teams select
  initial tab via `select_tab("PREFLIGHT")`.

## Troubleshooting for AI Agents

1. **"Module not found" errors:** Ensure `src/` is in `PYTHONPATH` (pytest config handles this; see `pyproject.toml`).
2. **Periodic loop slow:** Use `LogTracer` to identify bottleneck, check `RobotStatistics` SmartDashboard output.
3. **Logger not recording data:** Verify `Logger.start()` called (happens in `Robot.__init__` after pipeline setup).
4. **Simulation mode issues:** Check `SimulationConstants` poses match field dimensions; verify
   `robot_drive.set_motor_brake()` called properly.
5. **Replay playback:** Set `LOG_PATH` environment variable to absolute path of `.wpilog` file before running
   simulation.

