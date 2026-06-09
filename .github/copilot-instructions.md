# GitHub Copilot Instructions – frclib-6107

**frclib-6107** is a Python FRC robot helper library for Team 6107 (CyberJagzz). It targets Python 3.14+ and WPILib
2026+. The package name is `lib_6107`; source lives in `src/lib_6107/`.

## Build & Test Commands

```bash
make test           # Run pytest via tox-uv (primary test target)
make lint           # pylint on src/lib_6107/
make bandit-test    # Security scan with bandit
make release-check  # Full pre-release: clean + test + bandit + lint
make release-build  # Build dist/ with uv build
make publish        # Publish to PyPI (requires UV_PUBLISH_TOKEN)
make venv           # Create .venv via uv
```

Tests are in `tests/` and subdirectories `tests/{commands,pykit,subsystems,util}`. `src/` is on `PYTHONPATH`
automatically via `pyproject.toml`.

## Critical Rules

- **Never** use `SmartDashboard.putXXX()` for telemetry — use `Logger.recordOutput("Path/Key", value)` instead.
- **Never** modify `src/lib_6107/constants.py` defaults — teams subclass `RobotConstants`, `SimulationConstants`, or
  `NetworkConstants` and pass instances to `Robot.__init__()`.
- **Never** use `commands2.Subsystem` directly — extend `lib_6107.subsystems.subsystem.SubsystemBase`.
- **Never** use `commands2.Command` directly — extend `lib_6107.commands.command.BaseCommand`.
- All telemetry paths use `/` separators, e.g. `"Subsystems/Drivetrain/Velocity"`.
- Vendor auto-logging is disabled at robot startup (`SignalLogger`, `StatusLogger`, `LiveWindow`) — do not re-enable.

## Mode Detection

`ROBOT_MODE` (from `lib_6107.constants`) is set automatically at startup:

- `RobotModes.REAL` – roboRIO hardware
- `RobotModes.SIMULATION` – pyfrc desktop sim
- `RobotModes.REPLAY` – set `LOG_PATH` env var to a `.wpilog` file path before running

## Key Files

| File                                   | Role                                                            |
|----------------------------------------|-----------------------------------------------------------------|
| `src/lib_6107/robot.py`                | Base robot class; lifecycle, logging pipeline, mode transitions |
| `src/lib_6107/constants.py`            | Three constants dataclasses + ROBOT_MODE global                 |
| `src/lib_6107/robotcontainer.py`       | Subsystems, OI, button bindings, autonomous selection           |
| `src/lib_6107/subsystems/subsystem.py` | `SubsystemBase` with lifecycle hooks                            |
| `src/lib_6107/pykit/logger.py`         | `Logger` singleton; telemetry pipeline                          |
| `src/lib_6107/pykit/logtracer.py`      | `LogTracer`; performance profiling spans                        |
| `src/lib_6107/commands/command.py`     | `BaseCommand`; base for all commands                            |
| `example/robotcontainer.py`            | Reference implementation                                        |

## Performance Target

Main loop must stay **<20 mS**. Use `LogTracer` to profile; check `LogTracer/RobotPeriodic/TotalMS` in AdvantageScope.

## Python Code Standards and Best Practices

When generating any Python code for this library, adhere to the following guidelines:
1 **PEP 8 Compliance*: Follow PEP 8 style guidelines for formatting, naming, and structure. Use tools like `black` and
`flake8` for automated checks.
2 **Type Hints**: Use Python type hints for all function signatures and class attributes to improve readability and
enable static analysis.
3 **Docstrings**: Provide clear docstrings for all classes, methods, and functions using the Google style format.
Include descriptions of parameters, return values, and any exceptions raised.
4 **Logging**: Use the `Logger` class from `pykit` for all telemetry and debugging output. Avoid using `print()`
statements or `SmartDashboard` for logging
5 **Performance**: Ensure that all code is optimized for performance, especially in periodic methods. Avoid blocking
calls and ensure that any I/O operations are asynchronous or non-blocking.
6 **Testing**: Write unit tests for all new functionality using `pytest`. Ensure that tests are comprehensive and cover
edge cases. Use mocks for hardware interactions where necessary.
7 **Consistent Naming Conventions**: Use consistent naming conventions for classes, methods, and variables. For example,
use `CamelCase` for classes and `snake_case` for functions and variables.
8 **Small Functions**: Keep functions small and focused on a single task. This improves readability and maintainability.
9 **Single Responsibility Principle**: Ensure that each class and function has a single responsibility. This makes the
code easier to test and maintain.
10 **Error Handling**: Implement robust error handling, especially for hardware interactions. Use try-except blocks
where appropriate and log any exceptions using the `Logger`.
11 **Imports**: Organize imports according to PEP 8 guidelines: standard library imports first, followed by third-party
imports, and then local application imports. Use absolute imports where possible.
12 **Avoid Global State**: Minimize the use of global variables. Pass necessary state through function parameters or
class attributes to improve modularity and testability.
13 **Use of Constants**: Define constants in the appropriate dataclasses (`RobotConstants`, `SimulationConstants`,
`NetworkConstants`) and avoid hardcoding values throughout the codebase. This improves maintainability and readability.
14 **Documentation of Constants**: Provide clear documentation for each constant defined in the dataclasses, including
its purpose and any relevant units or constraints.
15 **Code Reviews**: All AI-generated code should be reviewed by a human developer to ensure it meets the above
standards and integrates well with the existing codebase. Address any issues or improvements identified during the
review process.
16 **Avoid Magic Numbers**: Replace magic numbers with named constants defined in the appropriate dataclass. This
improves code readability and maintainability.
17 **Credentials**: Never hardcode credentials, instead use environment variables or secure credential management
systems.
18 **Spelling**: Use consistent spelling throughout the codebase and documentation. Use english/United States spelling.
19 **Use of Enums**: Where appropriate, use `Enum` classes to represent fixed sets of values (e.g., robot modes, command
states) to improve code clarity and reduce errors.
