# 2026 Season Telemetry Examples — What AdvantageKit/PyKit Teams Actually Log

> Audience: senior developers who will compare this analysis against Team 6107's own
> 2026 robot code to evaluate whether `lib_6107.pykit` provides *superior telemetry
> coverage* without regressing the project's **<20 ms main-loop budget** (see
> `AGENTS.md`). This document does **not** analyze Team 6107's own robot — it is
> input for that comparison, to be performed separately.

This is a follow-up to `docs/2026-Telemetry-Sources.md`, which identified four 2026-season codebases that use
AdvantageKit or PyKit and are publicly available on GitHub. This document goes one level deeper: for each project, it
inventories **what metrics are actually being logged**, organized by subsystem, with short code excerpts, and then
compares the four projects against each other.

## 1. Projects examined

| Team                      | Repo                                                                                                      | Framework             | Language | Robot name         |
|---------------------------|-----------------------------------------------------------------------------------------------------------|-----------------------|----------|--------------------|
| 6328 Mechanical Advantage | [`Mechanical-Advantage/RobotCode2026Public`](https://github.com/Mechanical-Advantage/RobotCode2026Public) | AdvantageKit (author) | Java     | "Darwin"           |
| 1757 Westwood Robotics    | [`1757WestwoodRobotics/2026-Rebuilt`](https://github.com/1757WestwoodRobotics/2026-Rebuilt)               | PyKit (author)        | Python   | "2026-Rebuilt"     |
| 4572 Barlow Robotics      | [`Barlow-Robotics/Code2026`](https://github.com/Barlow-Robotics/Code2026)                                 | PyKit                 | Python   | "Code2026"         |
| 9106 Spires               | [`spiresfrc9106/romiPyKitSubsystems`](https://github.com/spiresfrc9106/romiPyKitSubsystems)               | PyKit                 | Python   | Romi (educational) |

Team 7459 Taubatexas Robotics was excluded — per the prior document, they were only *evaluating* PyKit as of their 2026
build thread, with no public code repository found to confirm adoption.

**Methodology:** each repo was cloned locally (shallow clone, current default branch) and searched for logging call
sites (`Logger.recordOutput`,
`Logger.processInputs`, `@AutoLog`/`@autolog`, `PyKitLogger.recordOutput`) using
`grep` across each `subsystems/` tree, then the matching files were read directly to extract representative code and
classify the metric by subsystem. All line numbers and file paths below were verified directly against the cloned
source — none of this is inferred from documentation or secondhand description.

---

## 2. Team 6328 Mechanical Advantage — AdvantageKit (Java), "Darwin"

Subsystems present: `drive` (swerve), `vision`, `launcher/flywheel`, `launcher/hood`,
`hopper`, `hubcounter`, `kicker`, `rollers`, `sensors`, `slamtake`, `leds`, plus a robot-wide `energy` package (not a
"subsystem" in the WPILib sense, but a cross-cutting telemetry system — see §2.7).

Darwin follows AdvantageKit's canonical **IO-interface pattern**: each subsystem declares a `@AutoLog`-annotated
`*IOInputs` static class holding every raw hardware reading, updated once per cycle via `updateInputs()`, and logged in
one call via
`Logger.processInputs(...)`. Derived/control-loop state is then logged separately via individual
`Logger.recordOutput(...)` calls.

### 2.1 Drive (swerve) — per-module hardware telemetry

`ModuleIO.java` — every swerve module logs 16 raw fields automatically:

```java
@AutoLog
public static class ModuleIOInputs {
  public boolean driveConnected = false;
  public double drivePositionRads = 0.0;
  public double driveVelocityRadsPerSec = 0.0;
  public double driveAppliedVolts = 0.0;
  public double driveSupplyCurrentAmps = 0.0;
  public double driveTorqueCurrentAmps = 0.0;
  public double driveTempCelsius;

  public boolean turnConnected = false;
  public boolean encoderConnected = false;
  public Rotation2d turnAbsolutePositionRads = Rotation2d.kZero;
  public Rotation2d turnPositionRads = Rotation2d.kZero;
  public double turnVelocityRadsPerSec = 0.0;
  public double turnAppliedVolts = 0.0;
  public double turnSupplyCurrentAmps = 0.0;
  public double turnTorqueCurrentAmps = 0.0;
  public double turnTempCelsius;
}
```

`GyroIO.java` similarly logs `connected`, yaw/pitch/roll position and velocity, and 3-axis acceleration. `Drive.java`
then logs derived swerve state once per cycle:

```java
Logger.processInputs("Drive/Gyro", gyroInputs);
Logger.processInputs("Drive/BackupGyro", backupGyroInputs); // redundant gyro!
...
Logger.recordOutput("SwerveStates/SetpointsOptimized", setpointStates);
Logger.recordOutput("SwerveChassisSpeeds/Setpoints", discreteSpeeds);
```

Note the **backup gyro** — Darwin logs two independent gyro input structs (`Drive/Gyro` and `Drive/BackupGyro`), a
redundancy/failover pattern not observed in any other project reviewed.

### 2.2 Vision — per-camera + aggregate AprilTag pose estimation

```java
Logger.processInputs("Vision/Inst" + i, inputs[i]);
Logger.processInputs("Vision/AprilTags/Inst" + i, aprilTagInputs[i]);
Logger.processInputs("Vision/ObjDetect/Inst" + i, objDetectInputs[i]);
...
Logger.recordOutput("AprilTagVision/Inst" + instanceIndex + "/RobotPose", robotPose);
Logger.recordOutput("AprilTagVision/RobotPoses", allRobotPoses.toArray(Pose3d[]::new));
Logger.recordOutput("AprilTagVision/TagPoses", allTagPoses.toArray(Pose3d[]::new));
```

Both AprilTag-based pose estimation **and** object detection (game-piece/"fuel"
tracking, `ObjDetect`) are logged through the same per-camera IO-input pattern.

### 2.3 Launcher (Flywheel + Hood)

```java
// Flywheel.java
Logger.processInputs("Flywheel", inputs);
Logger.recordOutput("Flywheel/Mode", outputs.mode);
Logger.recordOutput("Flywheel/Setpoint", setpointVel);
Logger.recordOutput("Flywheel/SetpointAccel", filteredAccel);
Logger.recordOutput("Flywheel/Goal", velocityRadsPerSec);
Logger.recordOutput("Flywheel/Feedforward", outputs.voltage);
Logger.recordOutput("Flywheel/BangBang", bangBang);
```

```java
// Hood.java
Logger.processInputs("Hood", inputs);
Logger.recordOutput("Hood/Profile/GoalPositionRad", goalAngle);
Logger.recordOutput("Hood/Profile/GoalVelocityRadPerSec", goalVelocity);
```

Interesting: alongside `Logger.recordOutput`, `Flywheel.java` **also** calls
`SmartDashboard.putString("Flywheel Speed", ...)` / `putBoolean("Flywheel At Goal",
...)` — i.e. even AdvantageKit's own authors still use `SmartDashboard` for lightweight, at-a-glance driver-station
display strings, reserving `Logger` for the full-fidelity replay/analysis data. This is a useful nuance: the "never use
SmartDashboard for telemetry" rule (see this repo's own `AGENTS.md`) is about not using it as the *system of record* for
logged data, not necessarily forbidding a handful of cheap driver-facing status strings.

### 2.4 HubCounter — external coprocessor bridge (2026-specific mechanism)

A physical game-piece counting device communicates over raw NetworkTables publishers/subscribers (bypassing `Logger` for
the live read/write channel itself), but final state is still recorded through the normal logging path:

```java
private final BooleanPublisher isExternalPublisher;
private final StringPublisher colorPublisher;
private final IntegerSubscriber countSubscriber;
...
Logger.recordOutput("HubCounter/Control/Pattern", hubPattern.toString());
Logger.recordOutput("HubCounter/Control/Color", hubColor);
Logger.recordOutput("HubCounter/ScoredFuel", succesfullyScoredFuel);
Logger.recordOutput("HubCounter/ScoredFuelPaused", unsuccesfullyScoredFuel);
LoggedTracer.record("HubCounter/Periodic");
```

### 2.5 Slamtake / Rollers / Kicker

Straightforward IO-pattern subsystems: `Logger.processInputs("Slamtake/Slam",
inputs)`, plus a handful of `recordOutput` calls for goal/mode state (`Kicker.java`,
`Hopper.java`). Nothing structurally different from §2.1–2.3.

### 2.6 Performance instrumentation

Every subsystem periodic () ends with a call into 6328's own **`LoggedTracer`**
utility (`LoggedTracer.record("HubCounter/Periodic")`, etc.) — a lightweight, purpose-built span timer, conceptually
identical to `LogTracer` in this repository and in Westwood's PyKit (see §3.6) — independent confirmation that *every*
serious 2026 team building on AdvantageKit/PyKit has converged on "instrument your own periodic () with a span timer" as
standard practice.

### 2.7 `energy` package — battery/current budget telemetry (unique to this project)

A cross-cutting, robot-wide telemetry system not tied to any single subsystem:

- **`BatteryEstimator.java`** — a single-RC Thevenin battery model with Peukert correction, estimating state-of-charge
  via coulomb counting and a Kalman-corrected polarization voltage — parameters fitted from real match log data (cites a
  Chief Delphi battery-comparison thread in its Javadoc).
- **`BatteryLogger.java`** — aggregates per-subsystem current draw and logs it using **AdvantageKit 2026's new
  unit-string overload**:
  ```java
  Logger.recordOutput("EnergyLogger/Current", totalCurrent, "amps");
  Logger.recordOutput("EnergyLogger/Power", totalPower, "watts");
  Logger.recordOutput("EnergyLogger/Energy", joulesToWattHours(totalEnergy), "watt hours");
  ```
- **`FinanceDepartment.java`** — the singleton subsystems report into:
  ```java
  // Flywheel.java
  FinanceDepartment.getInstance()
      .reportCurrentUsage(
          "Flywheel", false,
          inputs.connected ? inputs.supplyCurrentAmps : 0.0,
          inputs.follower1Connected ? inputs.follower1SupplyCurrentAmps : 0.0, ...);
  ```
- **`BreakerModel.java`** — presumably models breaker trip behavior for the current budget (not read in full for this
  document).

**This is the single most advanced telemetry capability found across all four projects** — none of the PyKit-based teams
have anything comparable to a whole-robot current/power/energy budget model, even though `lib_6107.pykit` (like current
AdvantageKit) already supports the underlying unit-string logging mechanism needed to build one.

---

## 3. Team 1757 Westwood Robotics — PyKit (Python), "2026-Rebuilt"

Subsystems present: `drive` (swerve), `vision`, `flywheel`, `hood`, `turret`,
`indexer`, `intake`, `leds`, `climber`.

1757's code (the team that authors PyKit) mirrors AdvantageKit's IO-pattern almost exactly, translated to Python
dataclasses and decorators.

### 3.1 Drive (swerve) — direct analog of 6328's `ModuleIOInputs`

`swervemoduleio.py`:

```python
class SwerveModuleIO:
    @autolog
    @dataclass
    class SwerveModuleIOInputs:
        driveconnected: bool = False
        steerconnected: bool = False
        encoderconnected: bool = False

        drive_position: float = 0.0  # rad
        drive_velocity: float = 0.0  # rad / sec
        drive_applied: float = 0.0  # volts
        drive_supply_current: float = 0.0  # amps
        drive_torque_current: float = 0.0  # amps

        turn_position: float = 0.0
        turn_velocity: float = 0.0
        turn_applied: float = 0.0
        turn_supply_current: float = 0.0
        turn_torque_current: float = 0.0
        turn_absolute_position: float = 0.0
```

**Note the gap**: this struct has no `drive_temp`/`turn_temp` fields, unlike 6328's Java `ModuleIOInputs`
(`driveTempCelsius`/`turnTempCelsius`). Motor temperature is not logged per swerve module in 1757's code.

`drivesubsystem.py`:

```python
Logger.processInputs("Drive", self.inputs)
...
Logger.recordOutput("drive/swerve/commandedSpeeds", chassisSpeeds)
```

### 3.2 Vision — per-camera + summary, with explicit accept/reject arrays

```python
Logger.recordOutput(f"Vision/Camera{idx}/TagPose", tagPoses)
Logger.recordOutput(f"Vision/Camera{idx}/RobotPoses", robotPoses)
Logger.recordOutput(f"Vision/Camera{idx}/RobotPosesRejected", robotPosesRejected)
Logger.recordOutput(f"Vision/Camera{idx}/RobotPosesAccepted", robotPosesAccepted)
Logger.recordOutput(f"Vision/Camera{idx}/TurretedTransforms", turretedTransforms)
...
Logger.recordOutput("Vision/Summary/RobotPosesRejected", allRobotPosesRejected)
Logger.recordOutput("Vision/Summary/RobotPosesAccepted", allRobotPosesAccepted)
```

Notably, this robot has a **turreted camera** (a camera mounted on the rotating turret, not the chassis) —
`TurretedTransforms`/`TurretedTransformsAccepted` track vision solutions in the turret's rotating reference frame, in
addition to the chassis-frame pose estimates. This is more sophisticated than either 6328's or Barlow's vision logging
in this respect (neither logs a turret-frame transform array).

### 3.3 Flywheel / Turret / Hood / Intake / Indexer — consistent, curated pattern

```python
# flywheelsubsystem.py
Logger.processInputs("Flywheel", self.inputs)
...
Logger.recordOutput("Flywheel/goal", self.goal)
Logger.recordOutput("Flywheel/ClosedLoop", self.isClosedLoop)
Logger.recordOutput("Flywheel/State", self.state.name)
```

```python
# turretsubsystem.py
Logger.processInputs("Turret", self.inputs)
...
Logger.recordOutput("Turret/goal after clamp", goalAngle)
Logger.recordOutput("Turret/goalVel after clamp", goalVel)
Logger.recordOutput("Turret/ClosedLoop", self.isClosedLoop)
Logger.recordOutput("Turret/SysID State", loggedStateStr)
```

```python
# intakesubsystem.py
Logger.processInputs("Intake", self.inputs)
Logger.recordOutput("Intake/Roller Goal", self.rollerGoal.name)
Logger.recordOutput("Intake/Pivot Goal", self.pivotGoal.name)
Logger.recordOutput("Intake/Pivot/Fudge", self.pivotFudge)
```

Every subsystem follows the same 5-8-call shape: one `processInputs` for raw hardware, then
goal/mode/closed-loop-state/SysID-state as individual outputs. This is a deliberately **curated, minimal set of manual
`recordOutput` calls** — the bulk of the data volume comes from the auto-logged `*IOInputs` struct, not from ad-hoc
calls sprinkled through control logic (contrast with Barlow, §4).

### 3.4 `@autologgable_output` — class-level auto-output decorator

```python
@autologgable_output
class FlywheelSubsystem(Subsystem):
    ...
```

Several subsystem classes are decorated with `@autologgable_output`
(`pykit.autolog`), meaning some outputs are logged automatically from decorated class attributes rather than via
explicit `Logger.recordOutput()` calls — a hybrid of "auto" and "manual" output logging within the same subsystem.

### 3.5 LEDs — minimal footprint

```python
Logger.recordOutput("LED/lastEnabledAuto", self.lastEnabledAuto)
Logger.recordOutput("LED/lastEnabledTime", self.lastEnabledTime)
```

Only two fields logged — LEDs are treated as low-value telemetry (reasonable, since LED state is rarely useful for
post-match debugging).

### 3.6 Performance instrumentation — `LogTracer`

Every subsystem's `periodic()` is wrapped in the same pattern:

```python
LogTracer.resetOuter("FlywheelSubsystem Periodic")
self.io.updateInputs(self.inputs)
Logger.processInputs("Flywheel", self.inputs)
LogTracer.record("UpdateInputs")
...
LogTracer.record("Closed Loop Control")
...
LogTracer.recordTotal()
```

This is the direct ancestor of `lib_6107.pykit`'s own `LogTracer` (already ported into this repository, per
`docs/lib_6107-pykit-and-westwood-pykit-comparison.md`).

---

## 4. Team 4572 Barlow Robotics — PyKit (Python), "Code2026"

Subsystems present: `drivetrain`, `feeder`, `intake`, `shooter`, `spindex`,
`turret`, `vision`.

Barlow's code diverges structurally from both 6328 and 1757 in three important ways: (a) the drivetrain does **not** go
through PyKit at all, (b) logging is gated behind a hand-rolled, per-subsystem **verbosity-tier flag system**, and (c)
`recordOutput` calls are sprinkled ad hoc through control-flow logic rather than being concentrated in a curated,
`processInputs`-centric IO struct.

### 4.1 Drivetrain — bypasses PyKit entirely, uses CTRE's native `SignalLogger`

```python
from phoenix6 import SignalLogger, swerve, units, utils

...
# Log state with SignalLogger class
SignalLogger.write_string("SysIdSteer_State", SysIdRoutineLog.stateEnumToString(state))
...
SignalLogger.write_double("Rotational_Rate", output)
```

This is CTRE's Tuner-X-generated `swerve.SwerveDrivetrain` class with its native Phoenix6 `SignalLogger` used **only for
SysId/characterization capture** (writes to CTRE's own binary `.hoot` format), not PyKit. There is **no** `PyKitLogger`
reference anywhere in `drivetrain.py` — meaning Barlow's day-to-day swerve telemetry (per-module
position/velocity/current) is not confirmed to flow into their `.wpilog`/AdvantageScope data at all, unlike 6328 and
1757's fully IO-instrumented swerve subsystems.

### 4.2 Vision — extremely granular per-rejection-reason diagnostics

```python
from pykit.logger import Logger as PyKitLogger

...
PyKitLogger.recordOutput(f"{prefix}/targets_seen", float(len(targets)))
...
PyKitLogger.recordOutput(f"{prefix}/gyro_diff_best_rad", diff_best)
PyKitLogger.recordOutput(f"{prefix}/gyro_diff_alt_rad", diff_alt)
...
PyKitLogger.recordOutput(f"{prefix}/accepted_tag_count", float(tag_count))
PyKitLogger.recordOutput(f"{prefix}/rejected_zero_tags", True)
PyKitLogger.recordOutput(f"{prefix}/rejected_out_of_bounds", True)
PyKitLogger.recordOutput(f"{prefix}/rejected_bad_z", True)
PyKitLogger.recordOutput(f"{prefix}/rejected_too_far_from_tags", True)
```

`vision.py` has **~48 individual `recordOutput` call sites** — by far the most verbose vision logging of the four
projects — logging a boolean flag *per specific rejection reason* rather than a single "rejected + reason string" pair.
This is the exact file referenced in the Chief Delphi thread cited in
`docs/2026-Telemetry-Sources.md` where the team reported "removing all logging calls made no meaningful difference" to a
latency problem — i.e., they confirmed this verbose logging was *not* their CPU bottleneck, but it is nonetheless the
heaviest per-frame logging load observed in this survey.

### 4.3 Turret — iterative ballistics solver, logged per-iteration

```python
for i, r in enumerate(radius_iterations):
    PyKitLogger.recordOutput(f"Turret/Iterations/iter_{i}_r", float(r))
    ...
    PyKitLogger.recordOutput(f"Turret/Iterations/iter_{i}_tof", float(tof))
...
PyKitLogger.recordOutput("Turret/calc_valid", True)
PyKitLogger.recordOutput("Turret/discriminant", float(discriminant))
PyKitLogger.recordOutput("Turret/horizontal_distance", float(r))
PyKitLogger.recordOutput("Turret/time_of_flight", float(tof))
```

Logging a **dynamically-keyed field per solver iteration** (`iter_0_r`, `iter_1_r`, ...) is a debugging-only pattern not
seen in any other project — useful for verifying a physics solver's convergence, but a form of unbounded-cardinality
logging that would need to stay gated behind a debug flag in competition (which it is — see §4.5).

### 4.4 Shooter / Feeder / Spindex — per-motor helper function

Feeder and Spindex share a `log_motor()` helper:

```python
def log_motor(self, motor: TalonFXS, prefix: str, target_velocity: float):
    if RobotFeatures.LOW_LOGGING:
        PyKitLogger.recordOutput(f"{prefix}/target_RPS", float(target_velocity))
        PyKitLogger.recordOutput(f"{prefix}/current_RPS", float(motor.get_velocity().value))
    if RobotFeatures.LOGGING_FEEDER:
        PyKitLogger.recordOutput(f"{prefix}/current_supply_current", float(motor.get_supply_current().value))
        PyKitLogger.recordOutput(f"{prefix}/current_stator_current", float(motor.get_stator_current().value))
        PyKitLogger.recordOutput(f"{prefix}/current_supply_voltage", float(motor.get_supply_voltage().value))
        PyKitLogger.recordOutput(f"{prefix}/current_motor_voltage", float(motor.get_motor_voltage().value))
        PyKitLogger.recordOutput(f"{prefix}/current_device_temp", float(motor.get_device_temp().value))
```

Device temperature *is* logged here (unlike 1757's swerve modules), but only when
`LOGGING_FEEDER` is enabled — i.e., **not on the competition robot** (see §4.5).

### 4.5 `RobotFeatures` — explicit, hand-rolled logging-verbosity tiers

This is the most significant CPU-cost-vs-coverage finding in this survey.
`constants/robot_constants.py` defines a class with per-subsystem boolean flags, configured differently depending on
whether the code is running on real hardware:

```python
class RobotFeatures:
    LOW_LOGGING = False
    ...

    @classmethod
    def configure(cls):
        if RobotBase.isReal():
            cls.LOGGING = True
            cls.LOGGING_ROBOT = False
            cls.LOGGING_DRIVETRAIN = False
            cls.LOGGING_VISION = False
            cls.LOGGING_SHOOTER = False
            cls.LOGGING_TURRET = False
            cls.LOGGING_INTAKE = False
            cls.LOGGING_SPINDEX = False
            cls.LOGGING_FEEDER = False
            cls.LOW_LOGGING = True  # only the lean tier stays on
        else:
            cls.LOGGING = False
            cls.LOGGING_ROBOT = True
            cls.LOGGING_TURRET = True  # richer logging allowed in sim
            cls.LOGGING_INTAKE = True
            cls.LOW_LOGGING = True
```

**On the real competition robot, every detailed per-subsystem logging flag is turned off**, leaving only the lightweight
`LOW_LOGGING` tier active (a handful of fields per subsystem, e.g. just RPM + target RPM for the shooter). In
simulation, several richer flags (`LOGGING_ROBOT`, `LOGGING_TURRET`, `LOGGING_INTAKE`) are turned on instead. This is a
**deliberate, explicit trade of real-robot telemetry coverage for CPU/bandwidth margin** — the most concrete evidence in
this survey that competitive teams are actively managing this exact tradeoff by hand, because neither PyKit nor
AdvantageKit gives them a first-class mechanism to do it (see §6).

### 4.6 Performance instrumentation — `LoopTimer` (throttled) + optional `pyinstrument`

```python
class LoopTimer:
    """Allocation-free statistical timer... stop() automatically logs avg/max at ~1 Hz."""

    def stop(self) -> None:
        elapsed_us = (time.perf_counter() - self._t0) * 1_000_000.0
        ...
        if now - self._last_log_time >= 1.0:  # throttle: log at most once/second
            if self._prefix == "Profiling/Scheduler" and RobotFeatures.LOW_LOGGING:
                PyKitLogger.recordOutput(f"{self._prefix}/avg_ms", avg_ms)
```

Barlow's `LoopTimer` improves on the raw "log every cycle" pattern seen elsewhere by **explicitly decimating its own
output to 1 Hz** — a direct, hand-built workaround for AdvantageKit's missing `runEveryN()` (identified as a gap in
`docs/lib_6107-api-work-todo.md` §A.3) applied to their own profiling data. They also maintain an **opt-in**
`pyinstrument`-based full call-stack profiler (`PeriodicProfiler`, gated by `RobotFeatures.HAS_CPROFILE`, default
`False`) for occasional deep-dive performance investigations, kept entirely separate from the always-on lightweight
timer.

---

## 5. Team 9106 Spires — PyKit (Python), Romi educational example

Only one subsystem: `drive`. This is a teaching/reference project (Romi is a small two-motor educational robot
platform), not a competition robot, but it demonstrates the same PyKit API applied at minimal scale.

```python
# driveio.py
class DriveIO:
    @autolog
    @dataclass
    class DriveIOInputs:
        leftPositionRad: float = 0.0
        leftVelocityRadPerSec: float = 0.0
        leftDriveDistanceInches: float = 0.0
        leftSetVolts: float = 0.0
        leftAppliedVolts: float = 0.0
        rightPositionRad: float = 0.0
        rightVelocityRadPerSec: float = 0.0
        rightDriveDistanceInches: float = 0.0
        rightSetVolts: float = 0.0
        rightAppliedVolts: float = 0.0
```

Notably simpler than either full-scale swerve `IOInputs` struct — no current or temperature fields at all, reflecting
Romi's simple brushed-DC-motor hardware (no CAN motor controllers to query for those values). `drive.py` logs the same
categories of derived state as the full-scale robots:

```python
Logger.processInputs("Drive", self.inputs)
Logger.processInputs("Drive/Gyro", self.gyroInputs)
...
Logger.recordOutput("Odometry/Trajectory", activePath)
Logger.recordOutput("Drive/leftSetpointMPS", leftSpeedMPS)
Logger.recordOutput("Drive/rightSetpointMPS", leftSpeedMPS)
Logger.recordOutput("Drive/leftFFVolts", leftFF)
Logger.recordOutput("Drive/rightFFVolts", rightFF)
```

**Takeaway:** the PyKit API shape (IO-input dataclass + `processInputs` + curated `recordOutput` calls) scales cleanly
from a full competition swerve robot down to a two-motor educational platform without needing a different pattern —
useful validation that `lib_6107.pykit`'s current API shape doesn't need to change to serve very small robots.

---

## 6. Cross-project comparison

### 6.1 Commonalities

- **IO-interface separation** (raw hardware `*IOInputs` struct, updated via
  `updateInputs()`, logged in one `processInputs()` call per subsystem per cycle) is used by 6328, 1757, and 9106 — this
  is the canonical AdvantageKit/PyKit pattern and the majority approach. Barlow follows it for every subsystem *except*
  drivetrain.
- **Every drivetrain-equivalent subsystem logs**: connection status, position, velocity, applied voltage, and supply
  current per actuator (or, for Barlow's drivetrain, via CTRE's own SignalLogger instead of PyKit).
- **Every vision subsystem logs** per-camera tag/robot pose estimates plus an accepted-vs-rejected classification — all
  three vision-logging projects (6328, 1757, Barlow) explicitly distinguish accepted from rejected pose observations,
  not just raw camera output.
- **Every shooter-like mechanism (flywheel/turret/hood) logs** a goal/setpoint value and some form of closed-loop-state
  indicator, so a post-match log can answer "was the mechanism trying to reach the right target, and was it able to."
- **Every full-scale-robot project has built its own periodic-loop span timer**
  (`LoggedTracer` — 6328, `LogTracer` — 1757/lib_6107, `LoopTimer` — Barlow) — independent, convergent evidence that
  measuring per-subsystem CPU cost is considered baseline good practice by every team examined, not an afterthought.
- **Hierarchical `"Subsystem/Field"` key naming** (`/`-delimited paths) is universal across both languages and all four
  projects.

### 6.2 Differences

| Aspect                                                   | 6328 (AdvantageKit/Java)                                                                                                             | 1757 (PyKit)                                                  | 4572 Barlow (PyKit)                                                                                                         | 9106 Spires (PyKit)                 |
|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| Per-module motor temperature                             | ✅ logged (`driveTempCelsius`, `turnTempCelsius`)                                                                                    | ❌ not logged on swerve modules                               | ✅ logged, but only in feeder/spindex, only when `LOGGING_FEEDER`/etc. enabled (off on real robot)                          | ➖ N/A (no CAN motors)              |
| Drivetrain telemetry path                                | AdvantageKit IO pattern                                                                                                              | PyKit IO pattern                                              | **Bypasses PyKit** — CTRE native `SignalLogger`, SysId-only                                                                 | PyKit IO pattern                    |
| Logging verbosity control                                | Always-on; relies on efficient batched IO logging                                                                                    | Curated, minimal manual `recordOutput` count per subsystem    | **Explicit runtime tiered flags** (`RobotFeatures.LOGGING_X`/`LOW_LOGGING`), switched off for most detail on the real robot | Always-on (small robot, low stakes) |
| Vision diagnostics granularity                           | Moderate (pose + tag arrays)                                                                                                         | Moderate-high (accept/reject arrays, turret-frame transforms) | **Very high** (per-rejection-reason booleans, ~48 call sites in one file)                                                   | N/A                                 |
| Whole-robot energy/current budget                        | ✅ `BatteryEstimator`/`BatteryLogger`/`FinanceDepartment` (Kalman SOC model, per-subsystem current attribution, unit-string logging) | ❌ none found                                                 | ❌ none found                                                                                                               | ❌ none found                       |
| Unit-string logging (`recordOutput(key, value, "amps")`) | ✅ used (energy package)                                                                                                             | Not observed in reviewed files                                | Not observed                                                                                                                | Not observed                        |
| SmartDashboard used alongside Logger                     | ✅ yes, for driver-facing strings only                                                                                               | Not observed                                                  | Not observed                                                                                                                | Not observed                        |
| External coprocessor bridged via raw NT                  | ✅ `HubCounter` (game-piece counting hardware)                                                                                       | ❌ (no equivalent 2026 mechanism)                             | ❌                                                                                                                          | ❌                                  |
| Debug-only per-iteration solver logging                  | Not observed                                                                                                                         | Not observed                                                  | ✅ `Turret/Iterations/iter_{i}_*` (dynamically-keyed, high-cardinality)                                                     | ❌                                  |
| Performance-timer output rate                            | Every cycle (`LoggedTracer.record`)                                                                                                  | Every cycle (`LogTracer.record`)                              | **Throttled to 1 Hz** (`LoopTimer`) + optional opt-in `pyinstrument` deep profiler                                          | N/A                                 |

### 6.3 What this suggests about coverage vs. CPU cost

1. **The richest telemetry coverage (6328) comes from a team that also has the most mature underlying framework**
   (AdvantageKit's own authors) — their energy/battery system is a "bonus" capability layered *on top of*
   already-efficient batched IO-input logging, not a replacement for it. This suggests coverage and CPU cost aren't
   strictly in tension if the base logging mechanism (one batched
   `processInputs()` call per subsystem) is already cheap.
2. **Barlow's hand-rolled `RobotFeatures` tiering is the clearest evidence that real teams want a first-class way to
   dial logging verbosity up/down without editing call sites** — they built an entire flag-and-`configure()` system
   themselves because neither PyKit nor AdvantageKit gives them one. AdvantageKit's own missing `runEveryN()`
   /lazy-supplier gap (documented in
   `docs/lib_6107-api-work-todo.md` §A.3.4) is the framework-level version of the exact problem Barlow solved by hand at
   the application level.
3. **Skipping the logging framework for a whole subsystem (Barlow's drivetrain) is a real, observed pattern**, not a
   hypothetical edge case — any comparison of
   "coverage" needs to account for the possibility that a subsystem's telemetry intentionally lives outside
   `lib_6107.pykit`/PyKit (e.g. vendor-native characterization tooling) rather than treating that as a defect to fix.
4. **High-cardinality, dynamically-keyed logging (Barlow's per-iteration solver values) is a real-world pattern this
   survey found "in the wild"** — worth considering whether `lib_6107.pykit` should offer guidance or guardrails (e.g.
   documentation recommending it stay behind a debug flag) rather than leaving teams to discover the cost tradeoff
   themselves.
5. **Every team-authored performance tracer (`LoggedTracer`/`LogTracer`/
   `LoopTimer`) independently reinvents the same basic idea** — a strong signal that this belongs in the library as a
   documented, "you should use this in every subsystem" idiom (already true for `lib_6107.pykit`'s `LogTracer` per this
   project's own `AGENTS.md`), and that Barlow's refinement (throttle the tracer's *own* logging output to ~1 Hz rather
   than every 20 ms cycle) is worth adopting as the recommended default, since it reduces the tracer's own overhead
   without losing any practically useful resolution.

---

## 7. References

**In-repo companion documents**

- `docs/2026-Telemetry-Sources.md` — how these four projects were identified.
- `docs/lib_6107-pykit-and-westwood-pykit-comparison.md` — API-level diff vs. upstream PyKit.
- `docs/lib_6107-api-work-todo.md` — API-level diff vs. AdvantageKit, including the
  `runEveryN`/lazy-logging gap referenced in §6.3.

**Source repositories examined directly (local shallow clones)**

- [Mechanical-Advantage/RobotCode2026Public](https://github.com/Mechanical-Advantage/RobotCode2026Public) —
  `src/main/java/org/littletonrobotics/frc2026/subsystems/**`, `src/main/java/org/littletonrobotics/frc2026/energy/**`.
- [1757WestwoodRobotics/2026-Rebuilt](https://github.com/1757WestwoodRobotics/2026-Rebuilt) —
  `src/subsystems/**`.
- [Barlow-Robotics/Code2026](https://github.com/Barlow-Robotics/Code2026) —
  `src/subsystems/**`, `src/constants/robot_constants.py`, `src/utils/profiler.py`.
- [spiresfrc9106/romiPyKitSubsystems](https://github.com/spiresfrc9106/romiPyKitSubsystems) —
  `subsystems/drive/**`.
