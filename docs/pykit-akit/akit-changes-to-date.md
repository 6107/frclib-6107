# AdvantageKit: Project Layout, Public API, and Changes Since v26.0.2

_Prepared for engineers maintaining a Python port of AdvantageKit's logging/replay capabilities. Covers the state of the
`main` branch as of 2026-07-29, compared against the last tagged release, **v26.0.2** (released 2026-03-19, ~4 months
prior)._

---

## 1. Project Layout

AdvantageKit is a Java library (targeting FRC robot code, built on WPILib) plus a small amount of native (C++/JNI) code,
packaged as a Gradle project. Top-level structure:

```
AdvantageKit/
├── akit/                     # The library itself (published as a WPILib vendor dependency)
│   ├── AdvantageKit.json     # Vendor dep manifest (JSON descriptor consumed by WPILib/VS Code)
│   ├── build.gradle.kts      # Java build, dependency versions (WPILib, quickbuf, jackson, etc.)
│   ├── native.gradle         # Native (C++/JNI) cross-compilation config, target platforms
│   ├── src/main/java/...     # Java source (the actual public API — see §2)
│   ├── src/main/native/      # C++ JNI glue ("conduit") that reads HAL/DriverStation data
│   ├── src/main/fbs/         # FlatBuffers schema for the native<->Java "conduit" data channel
│   ├── src/main/generated/   # Generated FlatBuffers code (C++ header + Java classes)
│   ├── src/main/thirdparty/  # Vendored FlatBuffers runtime
│   └── autolog/              # A separate annotation-processor module (`@AutoLog` codegen)
├── template_projects/         # Example/starter robot projects generated for each release
│   ├── template/              # Bare-bones starter project (what `gradlew` downloads)
│   ├── sources/                # Full example projects: diff_drive, kitbot_2026, skeleton,
│   │                            spark_swerve, talonfx_swerve, vision
│   └── generate_projects.sh   # Produces the distributable template zip files
├── docs/                      # Docusaurus site → https://docs.advantagekit.org
├── RLOG-SPEC.md               # Specification of AdvantageKit's own binary log format ("RLOG")
├── publish_zip.py             # Packages release artifacts
└── generate_sources.sh        # Regenerates FlatBuffers / native headers
```

Key architectural concept for the Python port: AdvantageKit's Java side is organized around a **conduit** (native code
that snapshots HAL/DriverStation/CAN/IMU/network state each cycle into a FlatBuffers-backed structure) and a **Logger**
singleton that drives a periodic "capture inputs → run user code → save outputs" cycle, writing everything to a
`LogTable` and then out to one or more `LogDataReceiver`s (WPILOG file, NT4, RLOG) or reading it back from a
`LogReplaySource` for deterministic replay in simulation.

---

## 2. Public API (as of `main`, commit `1fad15f`)

All public classes live under `org.littletonrobotics.junction` (with a separate
`org.littletonrobotics.conduit` package for the low-level native bridge, which is explicitly excluded from the published
Javadoc and not intended for direct use).

### Core logging

- **`Logger`** — central static/singleton API. Key methods:
    - `start()`, `end()`, `hasReplaySource()`, `setReplaySource(LogReplaySource)`,
      `addDataReceiver(LogDataReceiver)`, `registerDashboardInput(...)`,
      `registerURCL(...)`, `recordMetadata(String, String)`, `disableConsoleCapture()`,
      `getTimestamp()`, `runEveryN(int, Runnable)`.
    - `processInputs(String key, LoggableInputs inputs)` — the standard way subsystems log/replay their hardware inputs.
    - A very large family of `recordOutput(String key, <type> value)` overloads covering primitives, arrays, 2D arrays,
      enums, `Struct<T>`/`StructSerializable`,
      `Protobuf`/`ProtoMessage`, `Record` types, `LoggedMechanism2d`, and `Color`.
    - `Logger.AdvancedHooks` — nested class exposing low-level hooks (`disableRobotBaseCheck`,
      `invokePeriodicBeforeUser`, `invokePeriodicAfterUser`,
      `setConsoleSource`) for advanced/non-standard robot base integration.
- **`LoggedRobot`** — replacement for WPILib's `IterativeRobotBase`/`TimedRobot` that drives the AdvantageKit
  capture/replay cycle each loop.
- **`LogTable`** — the in-memory key/value log record (per-cycle "table" of fields), with typed `put`/`get` accessors
  mirroring `Logger.recordOutput`.
- **`LoggableInputs`** (interface, `org.littletonrobotics.junction.inputs`) —
  `toLog(LogTable)` / `fromLog(LogTable)`; implemented by IO layer classes to make hardware inputs loggable and
  replayable.
- **`@AutoLog`** — annotation (processed by the `akit/autolog` annotation processor) that generates a `<X>AutoLogged`
  class implementing `LoggableInputs` from a plain inputs class.
- **`@AutoLogOutput`** — annotation for fields/methods to be automatically logged as outputs each cycle, with optional
  `key`, `unit`, `forceSerializable` parameters (managed by `AutoLogOutputManager`).
- **`LogDataReceiver`** / **`LogReplaySource`** (interfaces) — pluggable sinks/sources for log data.
- **`LogFileUtil`** — helpers for locating/selecting log files (e.g. for replay).

### Data receivers / sources (implementations)

- **`wpilog.WPILOGWriter`** / **`wpilog.WPILOGReader`** — read/write WPILib's `.wpilog`
  binary format; `WPILOGWriter` supports auto-opening the file in AdvantageScope.
- **`networktables.NT4Publisher`** — publishes live log data over NetworkTables 4 (for real-time viewing in
  AdvantageScope without a file).
- **`rlog.RLOGServer`** — serves AdvantageKit's own RLOG binary protocol (see
  `RLOG-SPEC.md`) over a socket, primarily for the AdvantageScope live connection.
- **`ConsoleSource`** (interface with nested implementations) — captures stdout/stderr for inclusion in the log. Users
  are not expected to interact with this directly.

### Dashboard/network inputs

- **`networktables.LoggedNetworkBoolean/Number/String`**, **`LoggedNetworkInput`**
  (interface), **`LoggedDashboardChooser`** — replay-safe wrappers around NetworkTables values so dashboard/
  `SendableChooser`-style inputs are recorded and replayed deterministically.

### Mechanism visualization

- **`mechanism.LoggedMechanism2d`**, **`LoggedMechanismRoot2d`**, **`LoggedMechanismLigament2d`**, **
  `LoggedMechanismObject2d`** — replay-safe equivalents of WPILib's `Mechanism2d` visualization classes.

### System/robot state (mostly read-only, some public)

- **`LoggedDriverStation`**, **`LoggedSystemStats`** — package-private; not directly called by user code (they're
  invoked internally by `Logger`), but their output keys under the `DriverStation/` and `SystemStats/` log tables form
  part of the effective
  "on-disk schema" that AdvantageScope and any replacement reader must understand.
- **`LoggedPowerDistribution`** — **public**, singleton accessor for logging power distribution module (PDP/PDH) data;
  used directly by robot code.
- **`AlertLogger`**, **`RadioLogger`** — package-private internal helpers (not public API), log `Alert` state and
  radio/robot-radio connectivity status respectively.

### Build/distribution

- Published as a WPILib **vendor dependency** (`AdvantageKit.json` + Maven artifacts), installed via VS Code's "Install
  New Library" / a JSON URL, not via a package manager like pip — a relevant difference to flag for a Python port's
  distribution story.

---

## 3. Summary of Changes: v26.0.2 → `main` (current)

37 commits, ~165 files changed (+5,097 / −7,927 lines, including generated native headers). The overwhelming majority of
the work is a coordinated migration to **WPILib 2027** (currently alpha) and its new target hardware, **"SystemCore"**,
the successor to the roboRIO. There are no new logging concepts or format changes; this is primarily a
platform/dependency migration release with some incidental telemetry additions.

High-level themes:

1. **WPILib 2027 / Java package migration.** WPILib renamed its Java package root from
   `edu.wpi.first.*` to `org.wpilib.*` for the 2027 season, and AdvantageKit's Java sources were updated throughout to
   match (imports only — `edu.wpi.first.wpilibj.*` →
   `org.wpilib.framework.*` / `org.wpilib.system.*` / `org.wpilib.hardware.*`, etc.).
   `wpilibVersion` bumped from `2026.2.1` to `2027.0.0-alpha-6`. Gradle plugin IDs (e.g.
   `edu.wpi.first.NativeUtils` → `org.wpilib.NativeUtils`) were updated to match.
2. **RoboRIO → SystemCore.** The native build now cross-compiles for
   `linuxsystemcore` instead of `linuxathena`, and the legacy `linuxarm32` (original roboRIO 1) target was dropped.
   `nativeUtils.withCrossRoboRIO()` →
   `withCrossSystemCore()`.
3. **System/telemetry data model overhaul.** `LoggedSystemStats` (internal, but affects the logged field schema) was
   substantially rewritten for SystemCore's richer telemetry: FPGA-specific fields (FPGA version/revision, brownout
   counters, rail voltages, RSL state) were replaced with a fault/fault-count model (`Faults/*`, `FaultCounts/*`),
   per-network-interface stats (`Network/Ethernet|WiFi|USBTether|CAN{n}` with RX/TX bandwidth, bytes, drops, errors),
   CPU/memory/storage percentages, and onboard IMU data (accel, gyro rates, gyro Euler angles in flat/landscape/portrait
   orientations, gyro yaw, 3D gyro rotation). Any downstream tooling (e.g. a Python replacement) that parses these log
   keys needs to be updated to the new schema — this is **not** backward compatible with old logs' field names.
4. **Console capture rewritten for SystemCore.** `ConsoleSource.RoboRIO` (a file-tailing implementation reading
   `/home/lvuser/FRC_UserProgram.log`) was replaced with
   `ConsoleSource.Systemcore`, which shells out to `journalctl` to follow the
   `robot.service` systemd unit's log stream. This is an internal implementation detail but reflects the shift to a
   Linux/systemd-managed robot process rather than the roboRIO's `netconsole`-based logging.
5. **Misc reliability/CI fixes:** Clang warning suppressions, CI Ubuntu version bump, Java 21 build requirement,
   Docusaurus/browserslist updates, a typo fix in the privacy policy, and a fix to use an `ArrayList` (rather than a
   fixed-size structure) for status signals in `PhoenixOdometryThread` in the swerve template project.

### 3.1 External/Public API Changes (detail)

These are the changes a consuming team (robot programmers, or the team building an equivalent Python framework) would
need to react to. All are breaking, source-level changes requiring call-site updates — none are silently compatible
signature changes.

| Area                                                                                             | Before (v26.0.2)                                                                                                                                            | After (current)                                                                                                                                                        | Impact                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **`Logger.recordOutput(String, Measure<U>)`**                                                    | Overload named `recordOutput`                                                                                                                               | **Renamed to `Logger.recordOutputMeasure(String, Measure<U>)`**                                                                                                        | Necessitated because WPILib's `Measure` types became Java `Record`s in 2027, which collided with the existing generic `recordOutput(String, R value)` (`R extends Record`) overload. Any code calling `Logger.recordOutput(key, someMeasure)` must be updated to `recordOutputMeasure`. The generic `Record` overload now internally detects `Measure` instances and forwards to `recordOutputMeasure` automatically, so passing a `Measure` as a plain `Record` still "works", but the explicit overload was removed. |
| **`LogTable.put(String, Measure<U>)`**                                                           | `put`                                                                                                                                                       | **Renamed to `LogTable.putMeasure(String, Measure<U>)`**                                                                                                               | Same root cause as above; affects any custom `LoggableInputs`/`LogTable` usage that logs `Measure` values directly.                                                                                                                                                                                                                                                                                                                                                                                                    |
| **`LogTable.get(String key, M defaultValue)` (Measure overload)**                                | `get`                                                                                                                                                       | **Renamed to `LogTable.getMeasure(String, M defaultValue)`**                                                                                                           | Same as above, for reading a `Measure` back out of a table.                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **`LogTable.get(String, MutableMeasure)`**                                                       | Present (mutates in place)                                                                                                                                  | **Removed entirely**                                                                                                                                                   | `MutableMeasure` support for in-place reads was dropped; no replacement — callers must use the immutable `getMeasure` overload and re-assign.                                                                                                                                                                                                                                                                                                                                                                          |
| **`LoggedPowerDistribution.getInstance()`** (no-arg)                                             | Present — defaulted to `PowerDistributionJNI.DEFAULT_MODULE` / `AUTOMATIC_TYPE`                                                                             | **Removed.** `getInstance()` now simply returns the existing singleton (or `null` if never configured) — it no longer lazily creates a default instance.               | Any code relying on the zero-arg call to auto-detect the PDP/PDH module will now get `null` unless `getInstance(busID, moduleID, moduleType)` was called first.                                                                                                                                                                                                                                                                                                                                                        |
| **`LoggedPowerDistribution.getInstance(int moduleID, PowerDistribution.ModuleType moduleType)`** | 2-arg                                                                                                                                                       | **Now `getInstance(int busID, int moduleID, PowerDistribution.ModuleType moduleType)`** — a `busID` parameter was added (for multi-CAN-bus SystemCore hardware).       | Every existing call site needs an additional leading CAN bus ID argument.                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **`ConsoleSource.RoboRIO`** (public nested class)                                                | `public class RoboRIO`                                                                                                                                      | **Renamed/re-scoped to package-visible `class Systemcore`** (no longer `public`)                                                                                       | Only relevant if user code directly instantiated `ConsoleSource.RoboRIO` (documented as discouraged, but was technically public API). No longer possible; console source is chosen automatically by `Logger.start()`.                                                                                                                                                                                                                                                                                                  |
| **`WPILOGWriter` default log path constant**                                                     | `defaultPathRio = "/U/logs"` (internal)                                                                                                                     | Renamed to `defaultPathRobot`                                                                                                                                          | Internal rename only; behavior/path unchanged (`/U/logs` on-robot, `logs` in sim). Mentioned because Javadoc/user-facing text changed "RIO" → "robot" throughout.                                                                                                                                                                                                                                                                                                                                                      |
| **`SystemStats/SystemTimeValid` log key**                                                        | Present                                                                                                                                                     | **Renamed to `SystemStats/EpochTimeValid`** (used by `WPILOGWriter` to gate when the wall-clock filename timestamp is finalized)                                       | Any external tooling gating on log readiness via this key must be updated.                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **First-time protobuf/record logging warnings**                                                  | `Logger`/`LogTable` emitted a `DriverStation` warning the first time a protobuf or `Record` type was logged while the robot was enabled (loop-overrun risk) | **Removed**                                                                                                                                                            | Behavioral change only (no signature change): these warnings no longer fire; equivalent guidance should probably still be documented for a Python port even though AdvantageKit no longer warns at runtime.                                                                                                                                                                                                                                                                                                            |
| **PDP/PDH direct CAN logging (native)**                                                          | The C++ conduit directly read power distribution CAN frames (`pdp_reader.cc`/`pdp_util.cc`/`PDHFrames.h`)                                                   | **Removed** (~4,000 lines of native code deleted); PD data now expected to come through the standard WPILib `PowerDistribution` HAL path via `LoggedPowerDistribution` | Not a Java API signature change, but removes a whole class of native functionality; relevant if the Python equivalent tried to mirror this direct-CAN-read approach.                                                                                                                                                                                                                                                                                                                                                   |

### 3.2 Non-breaking / internal-only changes (for awareness, lower priority)

- Internal calls migrated from `RobotController.getFPGATime()` to
  `RobotController.getMonotonicTime()`, and `DriverStation.reportError/reportWarning` to
  `DriverStationErrors.reportError/reportWarning` — these are WPILib-internal API renames that AdvantageKit had to
  follow; they don't change AdvantageKit's own public surface.
- `RadioLogger.periodic(...)` gained a `teamNumber` parameter, but `RadioLogger` is package-private (not part of the
  public API).
- `LogTable.get(String, Color)` now constructs `Color` via an intermediate `Color8Bit`
  — an internal implementation detail with no signature change.
- WPILib's `DriverStation.MatchType` enum constants changed casing convention (`Practice`→`PRACTICE`, etc.) — only
  affects `WPILOGWriter`'s internal switch statement, not user-facing API.
- Dependency bumps: `com.diffplug.spotless` 6.25.0→8.6.0, `ejml-simple` 0.43.1→0.44.0,
  `quickbuf-runtime` 1.3.3→1.4, OpenCV 4.10.0-3→4.13.0-3 (repackaged under
  `org.wpilib.thirdparty.opencv`), new `io.avaje:avaje-jsonb` dependency added, Java target bumped (Javadoc links now
  point at JDK 25 docs, CI now builds with Java 21).

---

## 4. Recommendations for the Python Port

- **Prioritize the `Measure`/`Record` naming collision fix** (`recordOutputMeasure` /
  `putMeasure` / `getMeasure`) if the Python implementation has an analogous "generic dataclass/NamedTuple" logging
  path — the same ambiguity could arise for a Python
  `Quantity`-like unit type overlapping with generic structured-record logging.
- **Treat `SystemStats/*` and `DriverStation/*` log keys as a schema contract**, even though the Java classes producing
  them are package-private — any Python tooling reading or writing AdvantageKit-compatible logs (`.wpilog`/RLOG) needs
  to track this schema, and it changed substantially in this release (FPGA/rail-voltage model → fault/network/ IMU
  model).
- **Don't couple hardware-generation assumptions into the public API** the way
  `LoggedPowerDistribution`/`ConsoleSource` did — this release shows how a single-target hardware assumption
  (roboRIO-only) forced breaking signature and visibility changes when a second target (SystemCore) was introduced.
  Consider parameterizing bus/hardware IDs from the start.
- The core logging contract (`processInputs`/`recordOutput`/`LoggableInputs`/`LogTable`)
  remains conceptually **stable** across this release — this is a good sign that the core abstraction (periodic
  capture → typed table → pluggable receivers) is a solid target for the Python port and shouldn't need redesigning to
  track this kind of platform-migration churn.
