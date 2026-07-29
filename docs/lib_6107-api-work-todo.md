# `lib_6107.pykit` API — AdvantageKit Alignment & Work To-Do

> Audience: senior developers maintaining (or building) a comparable Python-based FRC
> logging/telemetry/replay framework. This document compares `src/lib_6107/pykit`'s
> public API against **AdvantageKit** (the Java framework both PyKit and
> `lib_6107.pykit` are conceptually ported from), in two separate baselines:
>
> - **Section A** — AdvantageKit **`v26.0.2`** (the last tagged 2026-season release,
>   released 2026-03-19) — the most relevant baseline, since `lib_6107.pykit`/PyKit
>   targets the same 2026-season WPILib/roboRIO stack.
> - **Section B** — AdvantageKit **current `main`** (commit `1fad15f`, ~4 months past
>   `v26.0.2`, already past `v27.0.0-alpha-4`) — mostly a WPILib-2027/"SystemCore"
>   migration, not yet relevant to a roboRIO-targeted RobotPy project, but tracked
>   here so the gap doesn't have to be re-discovered later.
>
> Each section ends with concrete upgrade recommendations; §4 consolidates both into
> a single prioritized backlog.

## 1. How this comparison was produced

Findings below were verified directly against a local clone of
[Mechanical-Advantage/AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit)
(tags `v26.0.2` and current `main` @ `1fad15f`), the current `src/lib_6107/pykit`
source tree, and the prior research captured in `docs/akit-changes-to-date.md`. Java ↔ Python capability mapping is
necessarily conceptual (interfaces, generics, and annotation processors don't have 1:1 Python equivalents) — differences
are flagged as **gaps** only when there is no reasonable Python-idiomatic equivalent already present, not merely because
the mechanism differs.

---

## Section A — `lib_6107.pykit` vs. AdvantageKit `v26.0.2` (Java)

### A.1 Architectural mapping

| Concept                     | AdvantageKit `v26.0.2` (Java)                                                                                        | `lib_6107.pykit` (Python)                                                                                                                         | Parity                                                                                                                                             |
|-----------------------------|----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Central orchestrator        | `Logger` (static class)                                                                                              | `Logger` (classmethods only)                                                                                                                      | Equivalent                                                                                                                                         |
| Per-cycle record            | `LogTable`                                                                                                           | `LogTable`                                                                                                                                        | Equivalent                                                                                                                                         |
| Robot base                  | `LoggedRobot`                                                                                                        | `LoggedRobot`                                                                                                                                     | Equivalent                                                                                                                                         |
| Loggable input contract     | `LoggableInputs` interface (`toLog`/`fromLog`)                                                                       | Duck-typed `to_log(table, prefix)` / `from_log(table, prefix)` (no formal interface/Protocol declared)                                            | Equivalent, less strict                                                                                                                            |
| Input codegen               | `@AutoLog` annotation → generates `<X>AutoLogged` class (separate Gradle annotation-processor module `akit/autolog`) | `@autolog` class decorator on a `dataclass`, generates `to_log`/`from_log` + `__post_init__` at **runtime** via `dataclasses.fields()` reflection | Equivalent goal, very different mechanism (compile-time codegen vs. runtime reflection)                                                            |
| Auto output publishing      | `@AutoLogOutput` field/method annotation, managed by internal `AutoLogOutputManager`                                 | `@autolog_output` + `@autologgable_output` decorators, `AutoLogOutputManager`                                                                     | Equivalent                                                                                                                                         |
| WPILOG file I/O             | `wpilog.WPILOGWriter` / `wpilog.WPILOGReader`                                                                        | `wpilog.wpilogwriter.WPILOGWriter` / `wpilog.wpilogreader.WPILOGReader`                                                                           | Equivalent; file format cross-compatible (see `docs/lib_6107-pykit-and-westwood-pykit-comparison.md` §8)                                           |
| Live NT streaming           | `networktables.NT4Publisher`                                                                                         | `networktables.nt4Publisher.NT4Publisher`                                                                                                         | Equivalent                                                                                                                                         |
| Live streaming w/o a file   | `rlog.RLOGServer` (+ `RLOGEncoder`) — confirmed present in `v26.0.2`                                                 | **Not present**                                                                                                                                   | **Gap** — see A.3                                                                                                                                  |
| Dashboard inputs            | `LoggedNetworkBoolean/Number/String`, `LoggedDashboardChooser`                                                       | Same set, plus `NetworkTableButton` (Trigger wrapper, `lib_6107`-only addition)                                                                   | Equivalent-or-better                                                                                                                               |
| Mechanism visualization     | `mechanism.LoggedMechanism2d/Root2d/Ligament2d/Object2d` (confirmed present already in `v26.0.2`)                    | `LoggedMechanism2d`/`LoggedMechanismRoot2d`/`LoggedMechanismLigament2d`/`LoggedMechanismObject2d` (ported)                                        | Equivalent — this port closes what was previously a gap                                                                                            |
| Power distribution          | `LoggedPowerDistribution` — public singleton, `getInstance()` / `getInstance(moduleID, moduleType)`                  | `LoggedPowerDistribution.get_instance()` (zero-arg only; custom module/type set via direct construction before first `get_instance()` call)       | Equivalent, different ergonomics                                                                                                                   |
| System stats                | `LoggedSystemStats`, `LoggedDriverStation` — package-private, internal only                                          | `LoggedSystemStats`, `LoggedDriverStation` — public classes, called directly by `Logger`                                                          | Equivalent capability, `lib_6107` exposes them as public API (arguably clearer for a smaller Python ecosystem without package-private enforcement) |
| Alerts                      | `AlertLogger` — package-private                                                                                      | `AlertLogger` — public                                                                                                                            | Equivalent                                                                                                                                         |
| Robot radio connectivity    | `RadioLogger` — package-private, logs radio/robot-radio connectivity (confirmed present in `v26.0.2`)                | **Not present**                                                                                                                                   | **Gap** — see A.3                                                                                                                                  |
| Replay file discovery       | `LogFileUtil.addPathSuffix()` / `LogFileUtil.findReplayLog()` (confirmed present in `v26.0.2`)                       | **Not present** — `WPILOGReader(filename)` requires an exact, caller-supplied path                                                                | **Gap** — see A.3                                                                                                                                  |
| Advanced/non-standard hooks | `Logger.AdvancedHooks` (disable robot-base check, manually invoke periodic hooks, custom console source)             | **Not present**                                                                                                                                   | **Gap**, low priority                                                                                                                              |
| Distribution                | WPILib **vendor dependency** (JSON manifest + Maven artifact), installed via VS Code                                 | In-tree fork inside `lib_6107` package, installed as part of the `lib_6107` pip package                                                           | Different by necessity (Python packaging vs. Java/Gradle vendor deps) — not a gap, just a different ecosystem                                      |

### A.2 `Logger` method-level comparison

| AdvantageKit `v26.0.2` `Logger` method                                                                                                                                                                                           | `lib_6107.pykit` `Logger` equivalent                                                                                                               | Notes                                                                                                                                                                                                                                    |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `start()` / `end()`                                                                                                                                                                                                              | `start()` / `end()`                                                                                                                                | Equivalent                                                                                                                                                                                                                               |
| `hasReplaySource()`                                                                                                                                                                                                              | `isReplay()`                                                                                                                                       | Equivalent, inverted-sounding name but same truth value                                                                                                                                                                                  |
| `setReplaySource(LogReplaySource)`                                                                                                                                                                                               | `setReplaySource(replaySource)`                                                                                                                    | Equivalent                                                                                                                                                                                                                               |
| `addDataReceiver(LogDataReceiver)`                                                                                                                                                                                               | `addDataReciever(reciever)`                                                                                                                        | Equivalent, but note the retained typo (see `docs/lib_6107-pykit-and-westwood-pykit-comparison.md` §5)                                                                                                                                   |
| `registerDashboardInput(...)`                                                                                                                                                                                                    | `registerDashboardInput(dashboardInput)`                                                                                                           | Equivalent                                                                                                                                                                                                                               |
| `registerURCL(Supplier<ByteBuffer[]>)`                                                                                                                                                                                           | **Not present**                                                                                                                                    | **Gap** (URCL = "Unofficial REV-Compatible Logger", CAN-bus-level REV telemetry capture) — low priority unless the team uses REV hardware URCL logging                                                                                   |
| `recordMetadata(String, String)`                                                                                                                                                                                                 | `recordMetadata(key, value)`                                                                                                                       | Equivalent                                                                                                                                                                                                                               |
| `disableConsoleCapture()`                                                                                                                                                                                                        | No method; `Logger.checkConsole = False` **before** `start()` achieves the same effect                                                             | Equivalent capability, exposed as a class attribute instead of a method                                                                                                                                                                  |
| `getTimestamp()`                                                                                                                                                                                                                 | `getTimestamp()`                                                                                                                                   | Equivalent                                                                                                                                                                                                                               |
| `runEveryN(int, Runnable)`                                                                                                                                                                                                       | **Not present**                                                                                                                                    | **Gap** — convenience for sub-sampling expensive periodic work (`lib_6107`'s `LoggedSystemStats` hand-rolls the same idea internally via `save_pass % N`, but there is no reusable public helper for user subsystem code to do the same) |
| `processInputs(String, LoggableInputs)`                                                                                                                                                                                          | `processInputs(prefix, inputs)`                                                                                                                    | Equivalent                                                                                                                                                                                                                               |
| **44** `recordOutput(...)` overloads covering primitives, 1D/2D arrays, enums, `Struct<T>`/`StructSerializable`, `Protobuf`/`ProtoMessage`, generic `Record` types, `LoggedMechanism2d`, `Color`, and lazy `*Supplier` overloads | **1** generic `recordOutput(key, value, unit=None)` that infers type from the Python value at runtime (`LogValue.__init__`'s `match value:` block) | See A.3 for the specific capability gaps this collapses/loses                                                                                                                                                                            |
| `Logger.AdvancedHooks.*`                                                                                                                                                                                                         | **Not present**                                                                                                                                    | **Gap**, low priority                                                                                                                                                                                                                    |

### A.3 Concrete capability gaps (things AdvantageKit `v26.0.2` can do that `lib_6107.pykit` cannot)

1. **No 2D array logging.** `LogValue`'s type inference (`bool`/`int`/`float`/`str`/
   `bytes`/`list`-of-primitives) has no case for nested lists / 2D arrays. AdvantageKit supports `boolean[][]`,
   `int[][]`, `long[][]`, `float[][]`, `double[][]`,
   `String[][]`, `T[][]` for structs/records/enums. A team logging, e.g., a 2D vision correspondence table or a swerve
   module state grid has no direct equivalent in
   `lib_6107.pykit` today — it must flatten to a 1D array manually.
2. **No native `Enum` logging.** `Logger.recordOutput(key, someEnum)` works directly in Java. In `lib_6107.pykit`,
   passing a Python `Enum` to `LogTable.put()`/`recordOutput()`
   raises `TypeError` (an `Enum` instance matches none of the `LogValue.__init__` cases)
   unless the caller manually logs `.name` or `.value` instead.
3. **No `Protobuf`/`ProtoMessage` support.** Neither `lib_6107.pykit` nor the Westwood PyKit it was forked from
   implement anything analogous to AdvantageKit's Protobuf record logging.
4. **No lazy/deferred-evaluation logging.** AdvantageKit's `*Supplier` overloads (`BooleanSupplier`, `IntSupplier`,
   `LongSupplier`, `DoubleSupplier`) let a caller pass `() -> expensiveComputation()` so the value is only computed if
   the logger is actually running/recording that key. `Logger.recordOutput(cls, key, value, ...)`
   in Python always requires the caller to have already computed `value` before the call (Python evaluates arguments
   eagerly) — there's no way to skip an expensive computation when logging is disabled. **This is directly relevant to
   this project's own stated <20 ms loop-time target** (see `AGENTS.md`): any team tempted to log an expensive derived
   value unconditionally pays its cost every cycle, whether or not the value is actually recorded.
5. **No `RLOGServer`.** AdvantageKit can stream live telemetry to AdvantageScope over its own RLOG socket protocol
   without writing a file at all. `lib_6107.pykit` only offers `NT4Publisher` (NetworkTables) or `WPILOGWriter` (file)
   as live/durable options — both fine for most use cases, but there is no equivalent to RLOG's lower-overhead,
   file-free live connection.
6. **No `LogFileUtil` replay-file discovery.** AdvantageKit's `findReplayLog()` +
   `addPathSuffix()` help locate the most likely `.wpilog` to replay (e.g. from a USB drive or a known folder), reducing
   manual path bookkeeping when setting up replay.
   `lib_6107.pykit`'s `WPILOGReader(filename)` requires an exact, hand-supplied path.
7. **No `RadioLogger`.** AdvantageKit tracks and logs robot-radio (OpenMesh/Vivid-Hosting)
   connectivity/diagnostics automatically. `lib_6107.pykit` has no equivalent — teams relying on radio health telemetry
   today would need to add this themselves (e.g. via the radio's own web API) rather than getting it "for free."
8. **No `Logger.AdvancedHooks`.** No equivalent for disabling the robot-base sanity check or manually invoking the
   before/after-user hooks outside the normal
   `LoggedRobot` loop. Low priority — mostly useful for non-standard robot base integrations, which `lib_6107.pykit`
   doesn't otherwise support either.
9. **No `registerURCL`.** No hook point for a REV Unofficial-REV-Compatible-Logger CAN-frame supplier. Low priority
   unless the team adopts URCL.

### A.4 Things done differently but *not* a gap

- **Struct serialization parity, different trigger.** Java uses generic
  `Struct<T>`/`StructSerializable` interface bounds; `lib_6107.pykit`'s
  `LogTable.put()` duck-types via `hasattr(value, "WPIStruct")`
  (`wpiutil.wpistruct`) and handles both scalar structs and arrays-of-structs. This is a faithful, idiomatic-Python
  equivalent — not a real gap.
- **`@AutoLog` vs. `@autolog`.** Java's version is a compile-time annotation processor generating a separate
  `<X>AutoLogged` class; Python's is a runtime class decorator mutating the class in place. Functionally equivalent for
  the common case; the Python version has zero build-step cost but a small amount of per-import runtime reflection
  overhead (`typing.get_type_hints`, `dataclasses.fields`) that Java's codegen avoids entirely.
- **`Logger.recordOutput(key, LoggedMechanism2d)` vs. `mechanism.log_output(table)`.**
  Java lets `Logger` dispatch on the mechanism type directly; Python instead exposes
  `log_output(table)` as a method on the mechanism object itself, called directly by user code. Same net effect,
  different call site — acceptable idiomatic difference.
- **`LoggedPowerDistribution.getInstance()` ergonomics.** Java's `v26.0.2` overload takes `(moduleID, moduleType)`
  directly; Python's `get_instance()` is always zero-arg, with custom hardware selected by constructing a
  `LoggedPowerDistribution(module_id=..., module_type=...)` instance *before* the first `get_instance()` call.
  Equivalent capability, less discoverable API (a developer must know to construct-before-get; passing arguments to
  `get_instance()`
  itself is not supported).

### A.5 Recommendations for `v26.0.2` parity

1. **Add 2D-array and `Enum` support to `LogValue`/`LogTable.put()`.** These are the two gaps most likely to be hit by
   ordinary robot code (vision correspondence tables, drivetrain state enums), not just advanced/rare use cases.
2. **Add a lazy-logging path.** Even a simple `Logger.record_output_lazy(key,
   supplier: Callable[[], Any])` that checks `cls.running` *before* calling
   `supplier()` would close gap A.3.4 and directly support the project's own loop-time goals.
3. **Add `LogFileUtil`-style replay discovery** (`find_replay_log()` scanning a known folder / USB mount for the newest
   `.wpilog`) — a small, high-value quality-of-life addition for anyone running replay sessions regularly.
4. **Treat `RLOGServer` and `RadioLogger` as optional, lower-priority ports** — valuable if the team wants file-free
   live AdvantageScope streaming or radio telemetry, but not blocking for core functionality.

---

## Section B — `lib_6107.pykit` vs. AdvantageKit current `main` (commit `1fad15f`)

This section is scoped narrowly: it only lists what **changed in AdvantageKit itself**
between `v26.0.2` and current `main` (per `docs/akit-changes-to-date.md`, independently spot-verified against the local
`AdvantageKit` clone for this document), and whether each change is *actionable* for `lib_6107.pykit` today.

### B.1 What changed upstream, and its relevance to `lib_6107.pykit`

| AdvantageKit change (`v26.0.2` → current `main`)                                                                                                                                           | Verified?                                                                                           | Relevant to `lib_6107.pykit` today?                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| WPILib 2027 / `edu.wpi.first.*` → `org.wpilib.*` package migration                                                                                                                         | Yes (release notes + `docs/akit-changes-to-date.md`)                                                | **No** — RobotPy/WPILib-Python has not migrated to the 2027 package layout; nothing to change yet                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| RoboRIO → "SystemCore" target hardware                                                                                                                                                     | Yes                                                                                                 | **No** — RobotPy targets roboRIO/HAL; SystemCore is not a RobotPy target as of this writing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `Logger.recordOutput(String, Measure<U>)` → renamed `recordOutputMeasure` (collision with the new `Record`-based generic overload); same rename for `LogTable.put`/`get` Measure overloads | **Directly verified** in local clone (`recordOutputMeasure` present in `HEAD`, absent in `v26.0.2`) | **Indirectly relevant.** `lib_6107.pykit` never had a `Measure`-typed overload to collide with in the first place — its `unit: Optional[str]` parameter on every `put`/`recordOutput` call already avoids this whole class of ambiguity by keeping "value" and "unit" as two always-separate parameters rather than one polymorphic `Measure` object. **This is a design choice worth explicitly keeping** if the team ever considers adding a `Quantity`/`Measure`-like Python type — don't let it collide with generic dataclass/record output logging the way Java's did. |
| `SystemStats`/`DriverStation` log-key schema overhaul (FPGA/rail-voltage model → SystemCore fault/network/IMU model)                                                                       | Yes (per `docs/akit-changes-to-date.md`)                                                            | **Not actionable now** — `lib_6107.pykit`'s `LoggedSystemStats` still logs the pre-2027, FPGA-oriented field set (`FPGAVersion`, `FPGARevision`, `SerialNumber`, `BrownedOut`, `RSLState`, etc.), which matches roboRIO/`v26.0.2`-era AdvantageKit, not current `main`. Track this only if/when RobotPy adds SystemCore support.                                                                                                                                                                                                                                             |
| `LoggedPowerDistribution.getInstance()` (no-arg) no longer lazily creates a default instance; `getInstance(moduleID, moduleType)` → `getInstance(busID, moduleID, moduleType)`             | **Directly verified** in local clone (compared `v26.0.2` vs. `HEAD` bodies)                         | **Worth noting, not urgent.** `lib_6107.pykit`'s `get_instance()` already has no-arg-lazily-creates-default semantics matching *old* (`v26.0.2`) AdvantageKit, not the new stricter one. If multi-CAN-bus hardware (SystemCore-class) is ever targeted, a `bus_id` parameter would need to be threaded through the same way.                                                                                                                                                                                                                                                 |
| `ConsoleSource.RoboRIO` → renamed/re-scoped to package-private `Systemcore`, now shells to `journalctl`/`robot.service` instead of tailing a log file                                      | Yes                                                                                                 | **Not applicable.** `lib_6107.pykit`'s `_ConsoleRecorder` wraps `sys.stdout`/`sys.stderr` directly in-process — it never depended on roboRIO-specific file-tailing or systemd log sources in the first place, so this migration doesn't affect it either way. Arguably a more portable design already.                                                                                                                                                                                                                                                                       |
| First-time protobuf/`Record` logging `DriverStation` warning removed                                                                                                                       | Yes                                                                                                 | **Not applicable** — no Protobuf/Record-equivalent warning exists in `lib_6107.pykit` today (see A.3.3)                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| PDP/PDH direct-CAN-frame native reads removed (~4,000 lines), PD data now only via the standard `PowerDistribution` HAL path                                                               | Yes                                                                                                 | **Already aligned** — `lib_6107.pykit`'s `LoggedPowerDistribution` already only reads via `wpilib.PowerDistribution` (the standard HAL path), never direct CAN frames, so this AdvantageKit-side removal doesn't create any new divergence.                                                                                                                                                                                                                                                                                                                                  |
| Misc (Clang warnings, CI bumps, dependency version bumps, `MatchType` enum casing)                                                                                                         | Yes                                                                                                 | Not applicable — internal/Java-toolchain-only                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

### B.2 Recommendations for tracking "current" AdvantageKit

1. **Nothing here is actionable today.** The overwhelming majority of the `v26.0.2`→ current delta is a
   WPILib-2027/SystemCore platform migration that RobotPy has not undergone. Re-visit this section (or regenerate
   `docs/akit-changes-to-date.md`)
   once RobotPy ships 2027/SystemCore support, rather than trying to track it continuously now.
2. **Preserve the `unit`-as-separate-parameter design** if/when adding richer typed quantities — it already sidesteps
   the exact ambiguity that forced AdvantageKit's
   `recordOutputMeasure` rename.
3. **Treat `SystemStats`/`DriverStation` log keys as a schema contract**, same guidance AdvantageKit's own maintainers
   give downstream tooling authors (see
   `docs/akit-changes-to-date.md` §4): if `lib_6107.pykit`'s schema for these ever changes, bump a schema-version marker
   so old logs remain distinguishable from new ones, rather than silently changing field names in place.
4. **Don't couple the API to one hardware generation.** AdvantageKit's own
   `LoggedPowerDistribution`/`ConsoleSource` rework shows the cost of assuming a single hardware target (roboRIO) — the
   busID/SystemCore rename was a breaking change forced by that assumption. `lib_6107.pykit`'s `LoggedPowerDistribution`
   already takes `module_id`/`module_type` as constructor parameters (good), but has no
   `bus_id` concept; if multi-bus hardware is ever on the roadmap, plan the parameter now rather than retrofitting it as
   a breaking change later.

---

## 4. Consolidated work backlog

| #  | Item                                                                                                                                                                                                     | Baseline                                          | Priority                                       | Effort (rough)                                          |
|----|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|------------------------------------------------|---------------------------------------------------------|
| 1  | Fix `Logger.addDataReciever` typo (rename to `add_data_receiver`, matching the already-corrected `LogDataReceiver` class)                                                                                | Westwood/internal consistency (see companion doc) | High (correctness/consistency)                 | Small                                                   |
| 2  | Add 2D-array (`list[list[...]]`) support to `LogValue`/`LogTable`                                                                                                                                        | AdvantageKit `v26.0.2`                            | Medium-High                                    | Medium                                                  |
| 3  | Add native `Enum` logging support to `LogValue` (log `.name`/`.value` automatically)                                                                                                                     | AdvantageKit `v26.0.2`                            | Medium-High                                    | Small-Medium                                            |
| 4  | Add a lazy/deferred `recordOutput` path (supplier callable, only invoked if running)                                                                                                                     | AdvantageKit `v26.0.2`                            | High (perf-aligned with project's <20 ms goal) | Small-Medium                                            |
| 5  | Add `LogFileUtil`-equivalent replay-file discovery helper                                                                                                                                                | AdvantageKit `v26.0.2`                            | Medium (QoL)                                   | Small                                                   |
| 6  | Complete or formally abandon the PEP 8 rename migration on `Logger`/`LogTable`/`LogValue` (see companion doc §4)                                                                                         | Internal consistency                              | Medium                                         | Medium-Large (repo-wide, needs careful call-site audit) |
| 7  | Consider `RLOGServer` port (file-free live AdvantageScope streaming)                                                                                                                                     | AdvantageKit `v26.0.2`                            | Low-Medium                                     | Large                                                   |
| 8  | Consider `RadioLogger` port (robot radio connectivity telemetry)                                                                                                                                         | AdvantageKit `v26.0.2`                            | Low                                            | Medium                                                  |
| 9  | Consider `registerURCL`-equivalent hook (REV CAN-frame logging)                                                                                                                                          | AdvantageKit `v26.0.2`                            | Low (only if URCL/REV hardware adopted)        | Medium                                                  |
| 10 | Add a schema-version marker to `LoggedSystemStats`/`LoggedDriverStation` output, in anticipation of any future field-set changes                                                                         | AdvantageKit current (`main`) — precautionary     | Low (no urgency today)                         | Small                                                   |
| 11 | If/when a `Quantity`/`Measure`-like typed-unit value is added, keep it structurally distinct from generic dataclass/record output logging (avoid AdvantageKit's `recordOutputMeasure` collision problem) | AdvantageKit current (`main`) — precautionary     | Low (design guidance only)                     | N/A                                                     |
| 12 | If multi-CAN-bus hardware is ever targeted, add a `bus_id` parameter to `LoggedPowerDistribution` proactively                                                                                            | AdvantageKit current (`main`) — precautionary     | Low (no urgency today)                         | Small                                                   |

---

## 5. References

- `docs/akit-changes-to-date.md` (in-repo) — prior detailed analysis of AdvantageKit's public API as of `main` and the
  full `v26.0.2` → current delta; the primary source for Section B, independently spot-verified for this document (see
  below).
- `docs/lib_6107-pykit-and-westwood-pykit-comparison.md` (in-repo, companion document)
  — covers the PyKit-fork-specific naming/behavior differences referenced in item #1 and §A.1/A.4 above.
- Source read/verified directly for this document:
    - `src/lib_6107/pykit/**/*.py` (this repository, current working tree)
    - `D:\Source\repos\github\AdvantageKit` — local clone of
      [Mechanical-Advantage/AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit). Verified directly: tag
      `v26.0.2` contents (`Logger.java`, `LoggedPowerDistribution.java`,
      `LogFileUtil.java`, `mechanism/LoggedMechanism2d.java`, presence of `rlog/RLOGServer.java`
      and `RadioLogger.java`, `runEveryN`/`registerURCL`/`disableConsoleCapture`/
      `hasReplaySource` on `Logger`); current `main` @ `1fad15f` / tag proximity
      `v27.0.0-alpha-4` (`git describe --tags` → `v27.0.0-alpha-4-1-g1fad15f`); diffed
      `Logger.java`/`LogTable.java`/`LoggedPowerDistribution.java` between the two tags to confirm the
      `recordOutputMeasure` rename and the `getInstance` signature change.
- [AdvantageKit (Mechanical Advantage / FRC 6328)](https://github.com/Mechanical-Advantage/AdvantageKit/)
  — upstream Java framework.
- [AdvantageKit documentation site](https://docs.advantagekit.org) — referenced for conceptual framing of `Logger`/
  `LoggableInputs`/replay architecture.
- [RLOG-SPEC.md](https://github.com/Mechanical-Advantage/AdvantageKit/blob/main/RLOG-SPEC.md)
  — AdvantageKit's own binary log/streaming protocol specification, relevant to backlog item #7.
- [WPILib Data Logging docs](https://docs.wpilib.org/en/stable/docs/software/telemetry/datalog.html)
  — `.wpilog` file format shared by both frameworks.
