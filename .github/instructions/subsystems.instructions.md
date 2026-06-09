---
applyTo: "src/**/subsystems/**/*.py"
---

## Subsystem Rules – frclib-6107

### Mandatory Structure

Every subsystem **must**:

1. Extend `SubsystemBase` from `lib_6107.subsystems.subsystem` — never `commands2.Subsystem` directly.
2. Set `self._initialized = False` as the **first line** of `__init__` (before `super().__init__()`).
3. Set `self._initialized = True` as the **last line** of `__init__`.
4. Accept `container: RobotContainer` as first `__init__` argument; pass it to
   `super().__init__(container, name, long_name)`.

This `_initialized` guard prevents race conditions where WPILib/vendor firmware calls `periodic()` before the subsystem
is fully constructed.

### Lifecycle Hooks to Implement

| Method                                  | When called                                   | Purpose                                                             |
|-----------------------------------------|-----------------------------------------------|---------------------------------------------------------------------|
| `stop()`                                | `disabledInit()`, `teleopExit()`              | Zero out all motor/actuator power                                   |
| `fault_detection(state, clear, notify)` | All mode transitions                          | Read and optionally clear device faults; log via `logger.warning()` |
| `sim_init(physics_controller)`          | Simulation startup                            | Set up simulation-only state; store `self._physics_controller`      |
| `update_sim(now, tm_diff)`              | After `CommandScheduler.simulationPeriodic()` | Update physics model; return ampere draw                            |
| `record_metadata()`                     | Initialization                                | Log firmware versions, device info via `Logger.recordMetadata()`    |

All hooks are **optional** (no-op in base class). Only implement what the subsystem needs.

### Telemetry

- All sensor/state output via `Logger.recordOutput("SubsystemName/Key", value)`.
- Log paths follow `"<SubsystemName>/<Category>/<Key>"`, e.g. `"Gyro/Angle"`, `"RPM/CurrentVelocity"`.
- Call `Logger.recordOutput` in `periodic()`, not in `__init__`.
- Use `LogTracer.record("SubsystemNameUpdate")` in `RobotContainer.robotPeriodic()` to profile timing.

### Example `__init__` Skeleton

```python
class MySubsystem(SubsystemBase):
    def __init__(self, container: RobotContainer) -> None:
        self._initialized = False          # MUST be first
        super().__init__(container, "MySubsystem", "my/subsystem")
        # ... hardware init ...
        self._initialized = True           # MUST be last
```

### Hardware Patterns

- REV motor connectivity is checked via `REVLibError` return from config calls; use `_check_is_connected()`.
- CTRE devices have an `isStatusOK()` pattern; override `is_connected` property accordingly.
- See `src/lib_6107/subsystems/gyro/` for a complete real-hardware + sim example.

