# 2027 Telemetry Review: Phoenix 6 vs. pykit vs. current drivetrain logging

Scope: `2027-tuner-x` (Phoenix 6 `26.70.0a2`, RobotPy `2027.0.0a8`, `robotpy-telemetry 2027.0.0a8`)
and the shared `lib_6107` library (pykit, `DriveSubsystem`, `CtreDriveSubsystem`, `CtreSwerveModule`).

Section 7 covers REV Robotics (`robotpy-rev 2027.0.0a9`) and what AdvantageKit 2027 does for REV.

Everything below was read from the installed packages and the local source.
I could not diff against the 2026 Phoenix release, so "new" means "present in the installed 2027
package and tied to the new `telemetry` module", not a confirmed changelog entry.
Items marked **(verify)** are inferences that should be confirmed on hardware or in sim.

---

## 1. Corrections to earlier work in this session

* `self.robot_drive.register_telemetry(...)` in `_configure_calibration_button_bindings_xbox` is wrong.
  `robot_drive` is `CtreDriveSubsystem`; `register_telemetry` lives on the inner
  `CommandSwerveDrivetrain` (`robot_drive._tuner_x_subsystem`). No `register_telemetry` exists anywhere in
  `lib_6107` (grep). This call would raise `AttributeError`.
  Per the recommendations below it should be removed, not forwarded.

---

## 2. What Phoenix 6 provides for telemetry (installed 26.70.0a2)

| API | Location | What it does |
|---|---|---|
| `SwerveDrivetrain.register_telemetry(fn)` | `swerve/swerve_drivetrain.py:1037` | Registers a Python callback that the **native odometry thread** invokes on every odometry update (250 Hz CAN FD / 100 Hz CAN 2.0). The wrapper takes `__state_lock`, refreshes the cached `SwerveDriveState`, then calls `fn` **while holding the lock**. Docstring: the function "must be cheap" or odometry is hurt. |
| `SwerveDrivetrain.get_state()` / `get_state_copy()` | `:988`, `:1012` | Pull the latest state from native code (builds 3 ctypes arrays + a struct, takes `__state_lock`). `get_state()` returns the shared cached object; `get_state_copy()` deep-copies it. |
| `SwerveDriveState` (struct-capable) | `:131-345` | Fields: `pose`, `velocity` (`ChassisVelocities`), `module_positions`, `module_velocities`, `module_targets`, `raw_heading`, `timestamp`, `odometry_period`, `successful_daqs`, `failed_daqs`. Has `.struct` / `get_struct(num_modules)` (a `wpistruct` descriptor) so it can be logged as one record. |
| `OdometryThread.set_thread_priority(0-99)`, `get_odometry_frequency()` | `:348-392`, `:913` | Tune the native odometry thread's real-time priority. |
| `HootTelemetryBackend(prefix, path)` | `hoot_telemetry_backend.py` | A `telemetry.TelemetryBackend` that writes entries to a `.hoot` file through `SignalLogger`. Ref-counted start/stop of `SignalLogger`. Plug it in with `TelemetryRegistry.register_backend(prefix, backend)`. |
| `HootAutoReplay` | `hoot_auto_replay.py` | Per-subsystem helper. `with_struct/with_double/...` register custom *inputs*; `update()` each loop logs them (normal run) or feeds them back through setters (Hoot Replay). Also `with_timestamp_replay`, `with_driver_station_replay`, `with_joystick_replay`, `with_match_info_replay`. |
| `HootReplay`, `utils.is_replay()`, `HootSchemaType` | `hoot_replay.py`, `utils.py` | CTRE's replay engine and detection. |
| `SignalLogger` | `signal_logger.py` | `start/stop/set_path`, `enable_auto_logging`, `write_*` (incl. `write_struct`, `write_struct_array`), `add_schema/has_schema/write_schema_value`. Writing is done by a native thread. |
| `AlertableCollection`, `PhoenixAlert`, `PhoenixMultiAlert`, `PhoenixAlertable`, `AlertInfo` | `alertable.py`, `alerts.py` | Device fault -> WPILib `Alert` reporting. Already used in `CommandSwerveDrivetrain` (`_device_alerts`). |
| `StatusSignalCollection` | `status_signal_collection.py` | Batch refresh/wait for a set of signals. |

### The WPILib/RobotPy `telemetry` module (what CTRE's backend plugs into)

`TelemetryTable.log(name, value)` (accepts structs, `Field2d`, `Mechanism2d`, ...),
`log_unit`, `TelemetryRegistry.register_backend(prefix, backend)` (longest-prefix routing),
`TelemetryBackend/Entry`, `MultiTelemetryBackend`, `MockTelemetryBackend`, `DiscardTelemetryBackend`.
This is a **second logging pipeline**, independent of pykit.

---

## 3. What we have today

### pykit (`lib_6107/pykit`)
* `Logger` is main-thread only ("Not thread-safe", `logger.py:195`). Each cycle:
  `periodic_before_user` (DS, tunables) -> user code -> `periodic_after_user` (system stats, autolog outputs, alerts).
* Sinks: `NT4Publisher` (delta-compressed) and `WPILOGWriter`. The WPILOG writer already hands records to a
  **native background writer thread** (`wpilogwriter.py:166`).
* Patterns: `Logger.process_inputs(key, inputs)` (replayable inputs), `Logger.record_output`,
  `@autolog_output`, `LogTracer` timing, `LoggedMechanism2d`.
* `robot.py:312` disables CTRE auto-logging (`SignalLogger.enable_auto_logging(False)`) and the signal refresh is commented out
  (`robot.py:447`, `# _status = Phoenix6Signals.refresh()`).

### Swerve I/O today

| Source | What is logged | Cost/notes |
|---|---|---|
| `CtreSwerveModule.periodic` (`ctre_swervedrive.py:158`) | per module: connected flags, drive/steer position, velocity, applied V, currents, absolute angle via `process_inputs("Drive/Module-<name>")` | 4 modules x ~10 signal reads per cycle. `drive_position` is **not** in `Phoenix6Signals.register_signals`, and the refresh call is disabled, so values may be stale **(verify)**. |
| `CtreSwerveModule.set_*_target` | `Drive/<name>/AngleTarget`, `DriveTarget` | Only used by the lib's own kinematics path. In Tuner-X mode requests go through `CommandSwerveDrivetrain.set_control`, so these probably never fire **(verify)**; the real targets are `state.module_targets`. |
| `DriveSubsystem` autolog (`drivesubsystem.py:685-695, 870-883`) | `Robot/Pose` (calls `get_state()`), `drive/fieldSpeeds`, `drive/swerve/real`, `drive/swerve/expected` | `get_pose()` -> `get_state()` -> native call + ctypes allocs **per call**; also called from `get_angle()` and elsewhere. |
| `DriveSubsystem.periodic` | gyro inputs, module periodic, Field2d pose, slow `dashboard_periodic` | OK structure; `LogTracer` already measures it. |
| `swerve_telemetry.SwerveTelemetry` (`swerve_telemetry.py:64`) | **On the odometry thread, every update:** `SignalLogger.write_struct("DriveState")`, `telemetry.log("DriveState")`, `Field2d` pose, 4x `Mechanism2d` | 7 Python log calls x 100-250 Hz, under the GIL **and** `__state_lock`. Duplicates pose (`Robot/Pose`, `field2d`) and module states (`drive/swerve/real`). Goes to the WPILib `telemetry` backends and an unstarted `SignalLogger`, **not pykit**. |
| `CommandSwerveDrivetrain` SysId (`command_swerve_drivetrain.py:155-214`) | `SignalLogger.write_*` | `SignalLogger.start()` is never called, so SysId state goes nowhere. (Also the rotation routine logs as `"SysIdSteer_State"`, a copy/paste bug.) |

### Duplicate work to be aware of
* The Tuner-X `CommandSwerveDrivetrain` is auto-registered with the scheduler (`commands2/subsystem.py:37`), so its
  `periodic()` runs **in addition to** `DriveSubsystem.periodic()`; both set the operator forward direction.
* In simulation both `CommandSwerveDrivetrain._start_sim_thread` and `DriveSubsystem._start_sim_thread`
  (`drivesubsystem.py:324`, which forwards to `update_sim_state`) start a 4 ms `Notifier` for the same drivetrain **(verify)**.

---

## 4. Overlap matrix

| Data | Phoenix path | pykit path today | Keep |
|---|---|---|---|
| Pose | `state.pose` -> telemetry/hoot | `Robot/Pose` autolog + `field2d` | pykit (once per cycle) |
| Chassis velocity | `state.velocity` | `drive/fieldSpeeds` (`_field_speeds`) | pykit, fed from `state.velocity` |
| Module velocities | `state.module_velocities` + Mechanism2d | `drive/swerve/real` | pykit |
| Module targets | `state.module_targets` | `drive/swerve/expected` (own calc) | pykit, fed from `state.module_targets` |
| Raw gyro heading | `state.raw_heading` | `Gyro` inputs | keep gyro inputs; add raw heading only if useful |
| **Odometry health** | `odometry_period`, `successful_daqs`, `failed_daqs` | not logged | **add to pykit** (new information, no duplicate) |
| Per-device signals | auto-logged to hoot (disabled) | `process_inputs` per module | pykit |
| Device faults | `AlertableCollection` | `alertlogger.py` | already flows to pykit alerts (verify the WPILib `Alert`s are picked up) |
| Replay | `HootAutoReplay` / `HootReplay` | pykit WPILOG replay | pykit (single replay story) |

---

## 5. Recommendations

Design rules: **pykit is the only sink**, **one native read per cycle**, **no Python on the odometry thread**, **no new threads**.

### R1. Remove the Python telemetry callback (highest value)
* Delete `SwerveTelemetry` and the `register_telemetry` call (including the one I added).
* Why: the callback runs on CTRE's thread but needs the GIL and holds `__state_lock`, so every
  `get_state()` on the main loop can block behind it. `Logger` is also not thread-safe, so the callback cannot feed pykit directly anyway.
* At 50 Hz pykit cannot use 250 Hz samples; CTRE already uses them internally for pose estimation and
  `add_vision_measurement(timestamp)` latency compensation.

### R2. Read the drivetrain state exactly once per cycle and feed pykit from it
In `CtreDriveSubsystem.periodic()` (lib_6107):
```python
state = self._tuner_x_subsystem.get_state()  # one native call; shared object is fine for immediate use
self._state = state  # cache for the rest of the cycle
```
* Make `get_state()`, `get_pose()`, `get_angle()`, `chassis_speeds`, etc. return the cached `self._state`
  instead of calling native code each time.
* Use a small `@autolog` inputs class, same pattern as `SwerveModuleIO.SwerveModuleIOInputs`, and publish it
  with `Logger.process_inputs("Drive/State", inputs)`:
  `pose`, `velocity`, `module_positions`, `module_velocities`, `module_targets`, `raw_heading`,
  `timestamp`, `odometry_period`, `successful_daqs`, `failed_daqs`.
* Treat the CTRE pose as an **input**, not an `autolog_output`. It is produced in native code and cannot be recomputed in a
  pykit replay, so logging it as an input is what makes replay work.
* Then retire the duplicate autolog outputs (`Robot/Pose`, `drive/swerve/real`, `drive/swerve/expected`), or point them at the cached state.
  Keep the key names AdvantageScope/Elastic layouts already use if that is a concern.

### R3. Do not adopt `HootTelemetryBackend` / `TelemetryRegistry` for normal operation
It creates a second pipeline (`telemetry` -> hoot) next to pykit, which is the duplication you want to avoid.
Likewise skip `HootAutoReplay`; pykit replay should be the single replay mechanism.

### R4. Optional, off by default: native hoot logging for tuning
* Hoot/`SignalLogger` writes on a native thread and records signals at their true update rate (above 50 Hz),
  which pykit cannot do. Useful for SysId and Tuner X plotting.
* Gate it behind a calibration/test-mode flag: `SignalLogger.start()` and `enable_auto_logging(True)` only in test mode.
  This also makes the SysId `record_state` calls in `CommandSwerveDrivetrain` actually produce data.
* Fix the `"SysIdSteer_State"` key for the rotation routine.

### R5. Stop paying for stale/unbatched signal reads
* Re-enable `Phoenix6Signals.refresh()` in `robot_periodic` (`robot.py:447`) after measuring with the existing
  `LogTracer("PhoenixUpdate")`. `StatusSignal.refresh_all` is non-blocking.
* Register `drive_position` with `Phoenix6Signals` (currently omitted) **(verify first that module signals are otherwise refreshed)**.
* Set update frequencies for the signals pykit actually logs and call `optimize_bus_utilization()` for the rest, to cut CAN load.

### R6. Main-loop budget (20 ms) measures
* Everything already off the main thread stays there: CTRE odometry (native), hoot writer (native),
  `WPILOGWriter` background writer (native), NT. The remaining main-thread cost is **serialization into `LogTable`**, so:
  * log arrays/structs once per cycle, not per module getter call;
  * rely on `NT4Publisher` delta detection; throttle low-value outputs with the existing `counter % N` pattern in `dashboard_periodic`;
  * wrap the new block with `LogTracer.record("DriveState")` and watch `LoggedRobot/UserCodeMS`.
* Keep `Field2d` (single owner: `DriveSubsystem.field2d`), drop the 4 per-module `Mechanism2d`; AdvantageScope's swerve
  view uses the module-state arrays. If a widget is still wanted use `LoggedMechanism2d` from the slow `dashboard_periodic`.
* Optional high-rate path (only if sub-cycle samples are ever needed): the callback appends `(timestamp, x, y, theta)` to a
  preallocated `collections.deque` and nothing else; the main loop drains it once per cycle and logs one array. Never call
  `Logger` from the callback.

### R7. Cleanups found along the way
* Remove duplicate `periodic` responsibilities between `CommandSwerveDrivetrain` and `DriveSubsystem` (operator forward direction).
* Only one sim `Notifier` should call `update_sim_state` **(verify)**.
* `_configure_calibration_button_bindings_xbox`: drop the telemetry registration; the method should only bind buttons.

---

## 6. Suggested order of work
1. R1 (remove `SwerveTelemetry` + callback) and the calibration-method fix.
2. R2 (cached per-cycle state + `Drive/State` inputs incl. `odometry_period`/`failed_daqs`).
3. R5 (signal refresh) with `LogTracer` before/after numbers.
4. R4 (test-mode hoot logging) and R7 cleanups.
5. REV items R8-R14 (section 7). R8 and R9 are breakage fixes and should go before step 1 if REV motors are used.

---

## 7. REV Robotics (REVLib 2027, `robotpy-rev 2027.0.0a9`)

Sources: installed `rev/_rev.pyi` and runtime checks in `src\.venv`; REV's alpha changelog
(`wpilibsuite/SystemCoreTesting/REV.md`, REVLib alpha-1..alpha-9); the local AdvantageKit checkout
(`Logger.java`, `spark_swerve` template, docs). Nothing here was run against a real SPARK.

### 7.1 What REVLib 2027 provides

| API | What it does | Telemetry relevance |
|---|---|---|
| `Signal_double`, `Signal_bool`, `Signal_int`, `Signal_SparkFaults`, ... | Every getter (`get_velocity()`, `get_applied_output()`, `get_faults()`, `has_active_fault()` ...) now returns a **signal wrapper** with `get()`, `get(default)`, `is_valid()`, `get_error()`, `get_timestamp()` (alpha-2, breaking change). | A value can now be known to be stale or never received. Both are exactly what a replay-safe input log needs. |
| `SparkBase.configure(...)` / `configure_async(...)` | The async form returns `OK` immediately and reports errors to the Driver Station. | Avoids blocking `robot_init` on CAN round trips. Errors then no longer come back as return codes. |
| `SignalsConfig` (via `SparkBaseConfig.signals`) | Per-signal `*_period_ms(...)` and `*_always_on(...)` (applied output, bus voltage, output current, motor temperature, faults, warnings, primary encoder position/velocity, absolute encoder, setpoint, is-at-setpoint ...). Default period is 20 ms. If several signals share a status frame, the minimum period wins. | The REV equivalent of CTRE's `set_update_frequency` / `optimize_bus_utilization`. |
| `*_always_on` flags | Status frames are normally enabled **only after a getter first asks for the signal**, and data is unavailable until the SPARK acknowledges the enable command. `always_on` turns the frame on from configuration time. | Without it, the first loop(s) after boot return invalid data. |
| `SparkLowLevel.set_periodic_frame_timeout(ms)` | Timeout before a periodic status frame yields a timeout error. Default 500 ms. | Determines how long an unplugged motor looks "valid". |
| `StatusLogger` | Native logger that writes every REV CAN status frame (including devices your code never creates) to a `.revlog`, with Driver Station state and match info. Starts **automatically** on the first REV device on a real robot. Does nothing in sim. Alpha-9 writes REVLOG format v2 and needs `revlog-converter` 2.0+ or a new AdvantageScope. API: `disable_auto_logging()`, `start()`, `stop()`, `set_log_directory()`, `get_log_directory()`. | The REV counterpart of CTRE hoot logging. It runs natively, so it costs the Python loop nothing. |
| `get_last_error()`, `REVLibError` | Errors tracked per thread. | Still the way to detect failed calls. |
| `get_periodic_status0..9()` | Raw periodic status frames as signals. | Low-level diagnostics only. |
| New devices: `A301` (motor controller on the Motioncore), `ServoHub`, `DetachedEncoder` (MAXSpline) | Same `Signal_*` getters; `A301` adds `get_faults`, `get_warnings`, `get_gearbox_rpm`, `get_motor_current`. Constructors take a `wpilib.CANPort`. | Same logging pattern applies. |
| Units | Conversion factors were removed. Positions are in rotations, velocities in RPM (alpha-7, SPARK firmware v27.0.0). `ClosedLoopConfig` position-wrapping bounds were re-added in alpha-9 and are in rotations. | Logged values must be converted explicitly. |
| Firmware | SPARK MAX / Flex need **v27.0.0**. All other REV devices stay on the 2026 firmware (v26.1.3). | Needed before any of this works on hardware. |

There is no REV counterpart to Phoenix's `register_telemetry`, `SwerveDriveState`, or `HootAutoReplay`, and no
vendor-supplied swerve odometry thread. REVLib exposes polled signals only.
I found no Python-specific REV telemetry package besides `robotpy-rev` itself.

### 7.2 What AdvantageKit 2027 does for REV

* **Uses URCL, not REV's `StatusLogger`.** The 2026-style templates call `Logger.registerURCL(URCL.startExternal())`
  and **`StatusLogger.disableAutoLogging()`** (comment: "Disable REVLib's built-in logging"), so there is one log, not two.
* **How URCL data reaches the log** (`Logger.java`, `periodicAfterUser`): URCL's native code captures CAN frames on its own
  thread and exposes three byte buffers. Each loop, on the main thread, AdvantageKit copies them and records
  `URCL/Raw/Persistent`, `URCL/Raw/Periodic`, `URCL/Raw/Aliases` as raw byte arrays. AdvantageScope decodes them.
  It is only done when `RobotBase.isReal()` and not during replay, so replay is unaffected.
* The cost on the main thread is one `memcpy` per buffer. All frame decoding is done in the viewer, not on the robot.
* The AdvantageKit docs note this data can be exported for SysId through AdvantageScope.
* AdvantageKit's `spark_swerve` template uses **`SparkOdometryThread`** (a `Notifier` polling Spark and gyro signals into bounded
  queues under a lock) plus **`SparkUtil.ifOk`/`tryUntilOk`**: values are used only when `getLastError() == OK`, otherwise a
  sticky fault flag is set. In 2027 this validity check is replaced by `Signal.is_valid()`.
* AdvantageKit's 2027 alphas (alpha-1..7) contain no REV-specific changes. The 2027 additions are Systemcore system stats
  (CAN utilization, CAN FPS, faults), alerts, console capture, and the `LoggedOpModeRobot`. The "Template projects not yet
  available for 2027" note still stands, so the REV 2027 patterns above come from the 2026 templates plus REV's changelog.
* There is **no pykit/Python equivalent of URCL** in what I found: `lib_6107` pykit has no `register_urcl`, `StatusLogger` or revlog handling
  (grep of `lib_6107/pykit` for `urcl|revlog|StatusLogger`: no matches).

### 7.3 What lib_6107 does today for REV

| Area | Where | State |
|---|---|---|
| Motor classes | `subsystems/rpm/rev_rpm_subsystem.py`, `rpm_subsystem.py` | `SparkFlex`/`SparkMax` + `SparkRelativeEncoder`; `.get()` already used on signals. |
| Inputs logged | `RevRpmMechanismIO.update_inputs` | Connected flag, position, velocity, applied voltage (`applied_output * bus_voltage`), output current. Five signal reads per motor per cycle. Passed through pykit `process_inputs`. |
| Faults | `util/rev/utils.py::handle_faults`, called at mode transitions | Logs and Elastic notifications only; not recorded in pykit. |
| Auto logging | `robot.py:313` | `StatusLogger.disable_auto_logging()` with a TODO asking whether pykit can capture REV data the way AdvantageKit does. |
| Not logged | | Motor temperature, faults/warnings as inputs, `is_valid()`/`get_error()` of any signal, firmware, `get_last_error()`. |

**Defects found while checking against the installed 2027 package (all verified at runtime in `src\.venv`):**

1. **Motor construction fails.** `SparkFlex(self._device_id, SparkFlex.MotorType.BRUSHLESS)` (`rev_rpm_subsystem.py:302,308`)
   raises `TypeError`: the 2027 constructor is `SparkFlex(can_port: wpilib.CANPort, device_id, type)` (alpha-1/alpha-7).
2. **`handle_faults` never works.** It calls `device.get_warnings().raw_bits`, but `get_warnings()`/`get_faults()` return a
   `Signal_*` that has no `raw_bits`; the value is `signal.get()`. The `AttributeError` is swallowed by the broad
   `except` and logged by `logger.exception`, so faults are silently missed (this is the "sticky"/"active" fault path called on every mode transition).
3. (Not a defect) `REV_FAULTS`/`REV_WARNINGS` already match the 2027 field names
   (faults: `can, esc_eeprom, firmware, gate_driver, motor_type, other, sensor, temperature`;
   warnings: `brownout, esc_eeprom, ext_eeprom, has_reset, other, overcurrent, sensor, stall`), but are hard-coded and would drift.
4. `.get()` is used without checking `is_valid()`, so a dead or not-yet-enabled signal is logged as a plausible number.
   I did not confirm what `get()` returns for an invalid signal **(verify)**; use `get(default)` or check validity.
5. Docstrings describe SparkMax as "PWM-based"; SPARK MAX is a CAN device in REVLib 2027. Documentation only.

### 7.4 Overlap with pykit and where duplication could appear

| Concern | REV `StatusLogger` | URCL (AdvantageKit way) | pykit `process_inputs` |
|---|---|---|---|
| Records at CAN rate | Yes (native thread) | Yes (native thread) | No; 50 Hz samples only |
| Needed for replay | No | No | **Yes** (it is the replay source) |
| Main-thread cost | None | One buffer copy/loop (cheap) | Serialization per logged value |
| Output file | Separate `.revlog` | Inside the pykit/AKit log as raw bytes | The pykit log |
| Duplicates pykit values | Yes (partly) | Yes (partly) | n/a |

So the same decision as for CTRE applies: **pykit inputs are the replayable record; the native high-rate log is only for diagnosis.**

### 7.5 Recommendations (REV)

Same rules as section 5: pykit is the only sink, one read per signal per cycle, no new threads, nothing heavy on the 20 ms loop.

**R8. Fix motor construction (blocking).** Pass a `wpilib.CANPort` (default `CANPort.CAN_S0`) as the first argument in
`rev_rpm_subsystem.py` and any other REV device creation, and expose the bus as a constructor constant/parameter instead of hard-coding it.
The `Sim` wrappers should be checked at the same time (`SparkFlexSim(motor, DCMotor)`).

**R9. Fix `handle_faults` (blocking).** Read `device.get_warnings().get()`, `get_sticky_warnings().get()`, `get_faults().get()`,
`get_sticky_faults().get()` and skip the update when `not signal.is_valid()`. Derive active names from the value's `raw_bits`
rather than hard-coded tuples. Add a unit test with `rev.Signal_SparkFaults(rev.SparkBase.Faults(...), rev.REVLibError.OK, 0)`, which can be
built without hardware.

**R10. Configure signals explicitly; do not read what is not logged.**
Build a `SignalsConfig` per motor in `_motor_config` that:
* sets `primary_encoder_velocity_period_ms`, `primary_encoder_position_period_ms`, `applied_output_period_ms`,
  `output_current_period_ms` to 20 ms (one per loop; shorter wastes CAN bandwidth for a 50 Hz consumer);
* sets `*_always_on(True)` for those four and `faults_always_on(True)`, so no boot-time invalid reads;
* leaves everything unused (analog, absolute encoder, setpoint, selected slot ...) at defaults so the SPARK does not send those frames, and increases
  `motor_temperature_period_ms` to a slow period (e.g. 250 ms) if temperature is logged.
This is the REV counterpart of CTRE's `optimize_bus_utilization`, with the same goal: less CAN traffic and fewer stale reads.

**R11. Log validity and faults as pykit inputs, not as separate logging.**
Extend `RpmMechanismIOInputs` (and any future REV I/O) with `connected` (derived from `is_valid()` of the velocity signal
plus firmware check), `temperature_c`, `faults_raw`, `warnings_raw`, and `last_error`. Read each `Signal` once per cycle, call
`.get()`, and store the numbers; the `Signal` objects themselves must not be logged. Record the **fault bitmask as an integer**
(cheap) and decode names only in `handle_faults` on transitions. This gives replay, keeps one pipeline, and adds roughly three integer fields
per motor.

**R12. Decide on native REV logging deliberately (answers the TODO in `robot.py`).**
Recommended: **keep `StatusLogger.disable_auto_logging()` in normal operation, and start it only in test/calibration mode**
(`StatusLogger.start()`), mirroring R4 for hoot. That way:
* no second always-on log or file writer competes for storage on Systemcore;
* the `.revlog` exists when you need CAN-rate data for tuning or SysId in AdvantageScope.
Pick one policy for both vendors, so test mode starts the hoot log and the revlog together.
If you instead want REV data embedded in the pykit log (AdvantageKit's URCL approach), that needs a Python/native bridge that does
not exist in `robotpy-rev` today; it would only be worth building if you also need the `.revlog` in the same file, and even then it should only move bytes.
Do not build a Python odometry-style thread for REV: REVLib has no queued/timestamped signal API, so a `Notifier` polling loop (AdvantageKit's `SparkOdometryThread`)
would run Python on a second thread under the GIL, which conflicts with the 20 ms constraint. Only consider it if a REV-driven swerve
needs sub-20 ms samples, and then prefer a native consumer.

**R13. Use the unit changes deliberately.** REVLib returns **rotations / RPM**. `rev_rpm_subsystem.py` already notes this and converts on read; keep conversion at the
I/O boundary and log SI units (rad, rad/s) consistently so that CTRE and REV inputs look the same to downstream code. Add unit tests for the converters.

**R14. Operational notes.**
* Flash SPARK firmware **v27.0.0** and use RHC2 1.4.x; older firmware lacks features such as the wrapping bounds.
* `configure_async` is fine for non-critical config at boot, but keep `try_until_ok`/`configure` (blocking) for anything that must be confirmed before enabling;
  with 2027's `configure_async` errors go to the Driver Station, so route them to pykit alerts if you use it.
* Add `Signal.is_valid()`/`get_error()` to the existing `LogTracer`/dashboard checks so a bad CAN cable shows up as an alert, not as 0.0 RPM.

### 7.6 Open items to verify

* What `Signal.get()` returns when `is_valid()` is false.
* Whether `StatusLogger.start()` can be called after `disable_auto_logging()` in robotpy-rev as documented, and how much storage a match log uses on Systemcore.
* Whether a Python-accessible URCL build exists for RobotPy; I did not find one.
* Real per-cycle cost of the five-to-eight REV signal reads per motor, measured with `LogTracer`.


## Implementation status

The recommendations above were implemented for CTRE drivetrain state, REV IO signals, vendor-logger gating, vision guards and periodic budget monitoring. See [telemetry-users-guide.md](telemetry-users-guide.md) for what changed, usage and best practices.
