---
applyTo: "tests/**/*.py"
---

## Test Rules – frclib-6107

### Environment

- `src/` is on `PYTHONPATH` automatically via `pyproject.toml [tool.pytest.ini_options]`. No manual path manipulation
  needed.
- Run with `make test` (uses tox-uv). Direct pytest: `uv run pytest`.
- Tests are in `tests/` mirroring `src/lib_6107/` structure: `tests/pykit/`, `tests/commands/`, `tests/subsystems/`,
  `tests/util/`.

### WPILib Hardware Mocking

WPILib hardware classes (`RobotController`, `DriverStation`, `SmartDashboard`, etc.) are not available outside a real
robot or simulation. Mock them with `unittest.mock.patch`:

```python
from unittest.mock import patch, MagicMock

def test_something():
    with patch('lib_6107.pykit.logtracer.RobotController.getFPGATime', return_value=1000000):
        # test code here
```

See `tests/pykit/test_logtracer.py` for the established mocking pattern for `RobotController` and `Logger.recordOutput`.

### Logger Mocking Pattern

When testing code that calls `Logger.recordOutput()`:

```python
with patch('lib_6107.pykit.<module>.Logger.recordOutput') as mock_logger:
    # trigger code under test
    mock_logger.assert_called_once_with("Expected/Key", expected_value)
```

### Test Function Naming

- Test functions use `snake_case` descriptive names (e.g., `logtracer_record_logs_phase_time_in_milliseconds`).
- No `Test` class wrapper required for simple unit tests — top-level functions are fine.
- For parametrized or grouped tests, use `class Test<ComponentName>`.

### What to Test

- Focus test coverage on `src/lib_6107/pykit/` (Logger, LogTracer, LogTable, etc.) — these are the highest-value targets
  per the README roadmap.
- Avoid testing WPILib internals; test the library's behavior around them.
- Performance-sensitive paths: verify timing calculations in milliseconds (microseconds → ms conversion uses `/1000.0`).

