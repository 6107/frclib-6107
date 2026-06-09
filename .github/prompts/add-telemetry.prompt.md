# Add Telemetry – frclib-6107

Add `Logger.recordOutput()` telemetry to `${input:file}`.

## Rules

- Use `Logger.recordOutput("Path/Key", value)` — **never** `SmartDashboard.putXXX()`.
- Call from `periodic()` or mode-specific periodic methods, not from `__init__`.
- Path convention: `"<SubsystemOrComponent>/<Category>/<Key>"` using `/` separators.
- Paths appear as-is in AdvantageScope for visualization and replay analysis.

## Import

```python
from lib_6107.pykit.logger import Logger
```

## Common Patterns

### Sensor value

```python
Logger.recordOutput("Gyro/Angle", self._gyro.getAngle())
Logger.recordOutput("Gyro/AngularVelocity", self._gyro.getRate())
```

### Motor state

```python
Logger.recordOutput("Intake/MotorVoltage", self._motor.getAppliedOutput())
Logger.recordOutput("Intake/CurrentAmps", self._motor.getOutputCurrent())
```

### Boolean flag

```python
Logger.recordOutput("Intake/HasGamePiece", self._sensor.get())
```

### Pose / geometry

```python
Logger.recordOutput("Odometry/RobotPose", self._odometry.getPoseMeters())
```

### Metadata (called once in record_metadata(), not periodic)

```python
Logger.recordMetadata("Subsystem/FirmwareVersion", self._motor.getFirmwareVersionString())
```

## Performance Profiling

To measure how long a subsystem update takes, wrap it in `RobotContainer.robotPeriodic()`:

```python
# In RobotContainer.robotPeriodic():
self._my_subsystem.update()
LogTracer.record("MySubsystemUpdate")  # Logs to LogTracer/RobotPeriodic/MySubsystemUpdateMS
```

`LogTracer.record()` must come **after** `LogTracer.resetOuter("RobotPeriodic")` — see `robot.py:robotPeriodic()`.

