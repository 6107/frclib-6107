# AdvantageKit v26.0.2 vs. PyKit v1.0.5 — API Parity Comparison

> Audience: senior developers maintaining `lib_6107.pykit`, comparing the **last
> tagged, released** version of each framework — AdvantageKit **v26.0.2** (Java,
> released 2026-03-19) and Westwood PyKit **v1.0.5** (Python, released
> 2026-03-23) — to determine whether PyKit's public API is a comparable match for
> AdvantageKit's, object-for-object and call-for-call. This intentionally excludes
> both projects' in-progress/unreleased work (see `docs/2027-akit-v-pykit-deltas.md`
> for the WPILib-2027/SystemCore-specific delta, which is a *separate*, later-stage
> comparison).

Both versions were checked out directly from their tags in local clones and read at the source level (not inferred from
documentation) — `git show v26.0.2:<path>` for AdvantageKit and `git show v1.0.5:<path>` for PyKit. All signatures below
are taken verbatim from those trees.

## TL;DR

PyKit reproduces AdvantageKit's **core contract** faithfully — the same capture/replay lifecycle (`processInputs`/
`recordOutput`/`LoggableInputs`/`LogTable`), the same three main integration points (WPILOG, NT4, dashboard-input
mirroring), and the same central `Logger` singleton design. Where it differs is almost entirely in **breadth of the
surrounding feature set**, not depth of the core idea:

- PyKit has **no equivalent at all** for AdvantageKit's `rlog` package (RLOGServer / AdvantageScope's live-socket
  protocol) or its `mechanism` package (2D/3D mechanism visualization, `LoggedMechanism2d` & friends).
- PyKit has **no equivalent** for several `Logger` utility methods present in AdvantageKit v26.0.2: `runEveryN`,
  `registerURCL`, `disableConsoleCapture`,
  `hasReplaySource`/`getReceiverQueueFault`, and the `AdvancedHooks` grouping. (`runEveryN` in particular was already
  flagged as a gap for `lib_6107.pykit` in
  `docs/lib_6107-api-work-todo.md` — this document confirms the gap traces all the way back to upstream PyKit, it isn't
  something `lib_6107` introduced.)
- PyKit's generic `recordOutput(key, value, unit=None)` **does** cover WPILib struct types and arrays-of-structs (via
  `wpiutil.wpistruct`, duck-typed on a `WPIStruct`
  attribute) — a closer match to AdvantageKit's `Struct<T>` overloads than a first read suggests — but has **no
  equivalent** for AdvantageKit's `Protobuf`/enum/
  `Color`/`Measure`/Java-`Record` overloads, because Python's dynamic typing collapses the ~50 Java overloads into one
  method, and that method's type-inference logic was never extended to cover those extra categories.
- PyKit's `WPILOGWriter` has no equivalent of AdvantageKit's `AdvantageScopeOpenBehavior`
  (auto-opening the written log in a running AdvantageScope instance).
- PyKit's autologging story is architecturally different but functionally comparable: AdvantageKit's `@AutoLog`/
  `@AutoLogOutput` require a build-time annotation processor and (for outputs) explicit
  `AutoLogOutputManager.addPackage`/
  `addObject` registration calls; PyKit's `@autolog`/`@autolog_output`/
  `@autologgable_output` do the equivalent work at runtime via decorators and
  `gc.get_referrers`-based reflection, with no explicit registration call required.
- Some AdvantageKit classes that look "missing" in PyKit (`AlertLogger`,
  `LoggedDriverStation`, `LoggedSystemStats`) are not actually missing — PyKit has all three — the apparent asymmetry is
  a **Java visibility artifact**: AdvantageKit deliberately marks these package-private (not part of its public API),
  whereas Python has no equivalent access-control keyword, so PyKit's versions are all technically public, whether or
  not that was a deliberate design choice.

---

## 1. API object/call mapping table

`AK` = `org.littletonrobotics.junction` (AdvantageKit v26.0.2). `PK` = `pykit`
(Westwood PyKit v1.0.5, i.e. `src/pykit/...`).

### 1.1 Core logging (`Logger`)

| AdvantageKit (`Logger`)                                                            | PyKit (`Logger`)                                                                   | Δ                                                                                                                                                                                      |
|------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `start()`                                                                          | `start()`                                                                          | Same.                                                                                                                                                                                  |
| `end()`                                                                            | `end()`                                                                            | Same.                                                                                                                                                                                  |
| `setReplaySource(LogReplaySource)`                                                 | `setReplaySource(replaySource: LogReplaySource)`                                   | Same.                                                                                                                                                                                  |
| `hasReplaySource() -> boolean`                                                     | `isReplay() -> bool`                                                               | **Renamed, not just moved** — semantically equivalent but different name; no PyKit method literally named `hasReplaySource`.                                                           |
| `addDataReceiver(LogDataReceiver)`                                                 | `addDataReciever(reciever: LogDataReciever)`                                       | Same (note PyKit's consistent "reciever" misspelling throughout its own API, not a documentation typo — it is the real public name).                                                   |
| `registerDashboardInput(LoggedNetworkInput)`                                       | `registerDashboardInput(dashboardInput: LoggedNetworkInput)`                       | Same.                                                                                                                                                                                  |
| `registerURCL(Supplier<ByteBuffer[]>)`                                             | —                                                                                  | **Gap.** No PyKit equivalent. URCL ("Unofficial REV-Compatible Logger") integration is REV-motor-controller-specific; not ported.                                                      |
| `recordMetadata(String, String)`                                                   | `recordMetadata(key: str, value: str)`                                             | Same.                                                                                                                                                                                  |
| `disableConsoleCapture()`                                                          | —                                                                                  | **Gap.** PyKit's console capture (`_ConsoleRecorder`) is always on once `Logger.start()` runs; there is no opt-out call.                                                               |
| `getReceiverQueueFault() -> boolean`                                               | —                                                                                  | **Gap.** No equivalent back-pressure/fault flag exposed for the async data-receiver queue.                                                                                             |
| `getTimestamp() -> long`                                                           | `getTimestamp() -> int`                                                            | Same, aside from the expected Java/Python numeric-type difference.                                                                                                                     |
| `runEveryN(int n, Runnable function)`                                              | —                                                                                  | **Gap.** No decimation helper; teams must hand-roll a modulo counter (as Team 4572 Barlow Robotics does — see `docs/2026-telemetry-examples.md` §4.6).                                 |
| `processInputs(String, LoggableInputs)`                                            | `processInputs(prefix: str, inputs)`                                               | Same. `inputs` is untyped in PyKit (duck-typed on `toLog`/`fromLog`), vs. Java's `LoggableInputs` interface constraint.                                                                |
| `recordOutput(String, <~50 typed overloads>)`                                      | `recordOutput(key: str, value: Any, unit: Optional[str] = None)`                   | **Collapsed to one method.** See §2.1 for the detailed type-coverage comparison.                                                                                                       |
| `Logger.AdvancedHooks.disableRobotBaseCheck()`                                     | —                                                                                  | **Gap.** No equivalent "unsafe" opt-out grouping.                                                                                                                                      |
| `Logger.AdvancedHooks.invokePeriodicBeforeUser()` / `invokePeriodicAfterUser(...)` | `periodicBeforeUser()` / `periodicAfterUser(userCodeLength, periodicBeforeLength)` | **Present, but not gated.** PyKit exposes these directly on `Logger` as ordinary public methods rather than behind an "advanced/internal use" marker class.                            |
| `Logger.AdvancedHooks.setConsoleSource(ConsoleSource)`                             | —                                                                                  | **Gap** (follows from PyKit's `ConsoleSource` not being a pluggable interface — see §2.4).                                                                                             |
| `startReciever()`/`end()` split for start-up                                       | *(no direct AK equivalent — folded into `start()`)*                                | PyKit exposes `startReciever()` as a distinct step from `start()`; AdvantageKit's `start()` does both in one call. Minor structural difference, not a capability gap either direction. |

### 1.2 Data model (`LogTable` / `LogValue` / `LoggableInputs`)

| AdvantageKit                                                                                 | PyKit                                                                                                                                                                 | Δ                                                                                                                                                                                                                                                                                                                 |
|----------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LogTable(long timestamp)`                                                                   | `LogTable(timestamp: int, prefix="/")`                                                                                                                                | PyKit's constructor also takes the hierarchical `prefix` directly; AdvantageKit derives subtables via `getSubtable(String)` instead (see below) — different construction API, same resulting model.                                                                                                               |
| `LogTable.clone(LogTable source)` (static)                                                   | `LogTable.clone(source)` (static)                                                                                                                                     | Same.                                                                                                                                                                                                                                                                                                             |
| `getTimestamp()` / `setTimestamp(long)`                                                      | `getTimestamp()` / `setTimestamp(timestamp: int)`                                                                                                                     | Same.                                                                                                                                                                                                                                                                                                             |
| `getSubtable(String tableName) -> LogTable`                                                  | `getSubTable(subtablePrefix: str) -> "LogTable"`                                                                                                                      | Same (casing difference only: `Subtable` vs `SubTable`).                                                                                                                                                                                                                                                          |
| `getAll(boolean subtableOnly) -> Map<String, LogValue>`                                      | `getAll(subtableOnly: bool = False) -> dict[str, LogValue]`                                                                                                           | Same.                                                                                                                                                                                                                                                                                                             |
| `put(String, <~50 typed overloads incl. Struct<T>, Protobuf, Record, Color, Measure, Enum>)` | `put(key: str, value: Any, typeStr: str = "", unit: Optional[str] = None)`                                                                                            | **Collapsed to one method**, but with built-in struct/array-of-struct auto-detection via `wpiutil.wpistruct` (checks `hasattr(value, "WPIStruct")`). No Protobuf, Java-Record-equivalent, `Color`, `Measure`, or `Enum` handling. See §2.1.                                                                       |
| `get(String key, <~50 typed overloads>)`                                                     | `get(key: str, defaultValue: Any) -> Any` + typed convenience methods (`getBoolean`, `getInteger`, `getFloat`, `getDouble`, `getString`, and the 5 `*Array` variants) | PyKit supplies named typed getters (closer in spirit to `LogTable.get(key, boolean default)` overload resolution than the generic `get`), but again no struct/Protobuf/Record/Color/Measure/Enum read-back path.                                                                                                  |
| `LogValue` (nested nested class; typed constructors per primitive)                           | `LogValue` (own module, `logvalue.py`)                                                                                                                                | Structurally analogous — a typed value + `LoggableType` enum — but AdvantageKit's `LogValue` has one constructor per primitive type (compile-time dispatch); PyKit's has one constructor with `isinstance` chains (runtime dispatch: bool → int → float → str → bytes → homogeneous list).                        |
| `LoggableType` enum, `getWPILOGType()`/`getNT4Type()`/`fromWPILOGType()`/`fromNT4Type()`     | `LogValue.LoggableType` enum, same four methods                                                                                                                       | Same shape.                                                                                                                                                                                                                                                                                                       |
| `LoggableInputs` interface (`toLog`/`fromLog`)                                               | No formal interface/ABC — any object with `toLog(table, prefix)`/`fromLog(table, prefix)` methods works (typically generated by `@autolog`)                           | Same contract, enforced structurally (duck typing) instead of nominally (Java interface). Note PyKit's methods take an extra `prefix` argument not present in AdvantageKit's `toLog(LogTable)`/`fromLog(LogTable)` (AdvantageKit uses per-subtable `LogTable` instances instead of a flat table + prefix string). |

### 1.3 Robot base (`LoggedRobot`)

| AdvantageKit                                     | PyKit                                                          | Δ                                                                                                                                                                                                                                                                                 |
|--------------------------------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `class LoggedRobot extends IterativeRobotBase`   | `class LoggedRobot(IterativeRobotBase)`                        | Same base-class relationship.                                                                                                                                                                                                                                                     |
| `defaultPeriodSecs = 0.02` (public static final) | *(not found as a public class attribute in the reviewed file)* | Minor — PyKit's default period constant, if present, was not exposed at this same location; not confirmed as a gap, just an unconfirmed asymmetry worth a quick follow-up look if precise parity matters.                                                                         |
| `startCompetition()` / `endCompetition()`        | `startCompetition()` / `endCompetition()`                      | Same.                                                                                                                                                                                                                                                                             |
| `setUseTiming(boolean)`                          | *(not found)*                                                  | **Possible gap** — no direct `setUseTiming`-style toggle found in `loggedrobot.py`; `lib_6107`'s own `AGENTS.md` mentions replay disabling WPILib timing, which may be handled differently (e.g. a module-level flag) rather than via an instance method on `LoggedRobot` itself. |
| `close()`                                        | *(not found)*                                                  | Not confirmed present; likely a non-issue since Python doesn't require the same explicit-close pattern as Java's `AutoCloseable`.                                                                                                                                                 |

### 1.4 Autologging (`@AutoLog` / `@AutoLogOutput` vs. `@autolog` / `@autolog_output`)

| AdvantageKit                                                                                                                                                                                                                | PyKit                                                                                                                                                                                                     | Δ                                                                                                                                                                                                                                                                                                                                                                        |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `@AutoLog` (annotation, processed by a **separate Gradle annotation-processor module**, `akit/autolog`) — generates a `<X>AutoLogged` subclass implementing `LoggableInputs`                                                | `@autolog` (decorator, `pykit.autolog`) — injects `toLog`/`fromLog`/`registerAutologged` methods directly onto the decorated `@dataclass` at **class-definition time**, no separate build step            | **Architecturally different, functionally equivalent.** AdvantageKit requires a compile-time codegen step (a second Gradle module dependency); PyKit needs nothing beyond importing the decorator — a simpler build/tooling story, at the cost of runtime (rather than compile-time) verification of field types.                                                        |
| `@AutoLogOutput(key, unit, forceSerializable)` (field/method annotation)                                                                                                                                                    | `@autolog_output(key, log_type, custom_type, unit)` (member decorator) + `@autologgable_output` (class decorator)                                                                                         | Same intent (mark a field/method for automatic per-cycle output logging), but PyKit **splits** the work across two decorators (member-level + class-level) where AdvantageKit needs only the one annotation.                                                                                                                                                             |
| `AutoLogOutputManager.addPackage(String packageName)` / `addObject(Object root)` — **user must explicitly call one of these** (typically in `robotInit()`) to register where to scan for `@AutoLogOutput`-annotated members | `AutoLogOutputManager.register_member(...)` / `publish_all(table, root_instance=None)` — driven automatically; no user-facing "please register your package/object" call exists in the public API surface | **Meaningful difference.** AdvantageKit requires an explicit, one-time registration call wiring up *which* packages/objects to scan; PyKit's manager discovers live instances itself (per the design notes in `docs/westwood-pykit-changes-to-date.md`, via `gc.get_referrers`), which is more automatic but also more "magic"/harder to reason about deterministically. |

### 1.5 Data receivers & replay sources

| AdvantageKit                                                                                                                                                       | PyKit                                                                                                                                                                                                                            | Δ                                                                                                                                                                                                                                                                                                                                                                    |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LogDataReceiver` (interface: `start()`, `end()`, `putTable(LogTable) throws InterruptedException`)                                                                | `LogDataReciever` (class: `start()`, `end()`, `putTable(table: LogTable)`)                                                                                                                                                       | Same contract (note the "Reciever" spelling again). Java declares a checked `InterruptedException`; Python has no checked-exception concept, so this is a language artifact, not a capability gap.                                                                                                                                                                   |
| `LogReplaySource` (interface: `start()`, `end()`, `updateTable(LogTable) -> boolean`)                                                                              | `LogReplaySource` (class: `start()`, `end()`, `updateTable(_table: LogTable) -> bool`)                                                                                                                                           | Same.                                                                                                                                                                                                                                                                                                                                                                |
| `wpilog.WPILOGWriter(String path, AdvantageScopeOpenBehavior openBehavior)` / `(String path)` / `(AdvantageScopeOpenBehavior)` / `()`                              | `wpilog.WPILOGWriter(filename: str                                                                                                                                                                                               | None = None, path: str                                                                                                                                                                                                                                                                                                                                               | None = None)` | **Different constructor semantics, one real feature gap.** (1) AdvantageKit's first constructor argument is a directory *path*; PyKit's first argument is a *filename*, with `path` as a second, independent parameter (see `docs/westwood-pykit-changes-to-date.md` §4 for the v1.0.4→v1.0.5 change that added it). (2) **`AdvantageScopeOpenBehavior` has no PyKit equivalent at all** — AdvantageKit can auto-open the just-written log in a running local AdvantageScope instance; PyKit cannot. |
| `wpilog.WPILOGReader(String filename)`                                                                                                                             | `wpilog.WPILOGReader(filename: str)`                                                                                                                                                                                             | Same.                                                                                                                                                                                                                                                                                                                                                                |
| `wpilog.WPILOGConstants.extraHeader = "AdvantageKit"`                                                                                                              | `wpilog.wpilogconstants` module — PyKit writes its own extra-header string (per `docs/westwood-pykit-changes-to-date.md`, logs from other tools including AdvantageKit are rejected on read via a mismatched extra-header check) | **Deliberately incompatible by design** — the two frameworks' `.wpilog` files are not cross-readable with each other's reader, even though both target the same underlying WPILib `.wpilog` container format.                                                                                                                                                        |
| `networktables.NT4Publisher()` (no-arg only)                                                                                                                       | `networktables.NT4Publisher(actLikeAKit: bool = False)`                                                                                                                                                                          | **PyKit has strictly more here** — an explicit interop toggle to mirror data under the `/AdvantageKit` NT table name (matching AdvantageKit's own default) instead of `/PyKit`, specifically to let AdvantageScope layouts built for AdvantageKit work unmodified against a PyKit robot. AdvantageKit's own `NT4Publisher` has no reason to need an equivalent flag. |
| `rlog.RLOGServer(int port)` / `RLOGServer()` — serves AdvantageKit's own binary **RLOG** protocol (see `RLOG-SPEC.md`) for AdvantageScope's live socket connection | —                                                                                                                                                                                                                                | **Total gap.** PyKit has no RLOG implementation at all; live viewing in AdvantageScope must go through `NT4Publisher` instead. Since NT4 live-viewing works for both frameworks, this is a lower-priority gap in practice (RLOG appears to mainly exist as an alternative/legacy transport), but it is a real, unported piece of the public API surface.             |

### 1.6 Dashboard/network inputs

| AdvantageKit                                                                                            | PyKit                                                                                                                 | Δ                                                                                                                                                                                       |
|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LoggedNetworkInput` (abstract, `periodic()`)                                                           | `LoggedNetworkInput` (base class, `periodic()`, plus a static `removeSlash(key)` helper)                              | Same, PyKit adds one small key-normalization helper not present on the Java base class.                                                                                                 |
| `LoggedNetworkBoolean(String key)` / `(String key, boolean defaultValue)`, implements `BooleanSupplier` | `LoggedNetworkBoolean(key, defaultValue: bool = False)`, implements `BooleanSupplier`-equivalent via `getAsBoolean()` | Same.                                                                                                                                                                                   |
| `LoggedNetworkNumber` / `LoggedNetworkString`                                                           | `LoggedNetworkNumber` / `LoggedNetworkString`                                                                         | Same shapes (`get`/`set`/`setDefault`, `DoubleSupplier`/`Supplier<String>` equivalents).                                                                                                |
| `LoggedDashboardChooser<V>(String key)` / `(String key, SendableChooser<V> chooser)`                    | `LoggedDashboardChooser[T](key: str)` (no "wrap an existing chooser" constructor found)                               | **Minor gap** — AdvantageKit lets you wrap a pre-built `SendableChooser`; PyKit's constructor only takes a key (it builds/owns the chooser itself, exposed via `getSendableChooser()`). |
| `addOption` / `addDefaultOption` / `get()` / `onChange(Consumer<V>)`                                    | `addOption` / `setDefaultOption` / `getSelected()` / `onChange(Callable[[T], None])`                                  | Same intent, two casing/naming differences (`addDefaultOption`→`setDefaultOption`, `get()`→`getSelected()`).                                                                            |

### 1.7 Mechanism visualization

| AdvantageKit                                                                                                                       | PyKit | Δ                                                                        |
|------------------------------------------------------------------------------------------------------------------------------------|-------|--------------------------------------------------------------------------|
| `mechanism.LoggedMechanism2d(width, height[, backgroundColor])`, `.getRoot(...)`, `.logOutput(LogTable)`, `.generate3dMechanism()` | —     | **Total gap.** No mechanism-visualization module exists in PyKit at all. |
| `LoggedMechanismRoot2d`, `.append(...)`, `.setPosition(...)`, `.generate3dMechanism()`                                             | —     | **Total gap** (follows from the above).                                  |
| `LoggedMechanismLigament2d` / `LoggedMechanismObject2d`                                                                            | —     | **Total gap** (follows from the above).                                  |

This is the single largest unported feature area between the two released versions — any team wanting WPILib
`Mechanism2d`-style (or AdvantageKit's newer 3D-mechanism) visualization logged/replayed through PyKit today has no
built-in path to do so.

### 1.8 System/robot state & alerts

| AdvantageKit                                                                                                                         | PyKit                                                                                                                                                                                           | Δ                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|--------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LoggedDriverStation` — **package-private**, `saveToLog(LogTable)` / `replayFromLog(LogTable)`, private constructor                  | `inputs.loggableds.LoggedDriverStation` — **public**, `saveToTable(cls, table)` / `loadFromTable(cls, table)`                                                                                   | Functionally equivalent capture/replay of DS + joystick state. The naming (`saveToLog`/`replayFromLog` vs. `saveToTable`/`loadFromTable`) differs, and — more importantly — **AdvantageKit does not expose this as public API at all**; PyKit does. Not a capability gap, but a documented-surface-area difference worth flagging if `lib_6107` is trying to match AdvantageKit's *intended* public/private boundary rather than just its method names. |
| `LoggedPowerDistribution.getInstance()` (no-arg) / `getInstance(int moduleID, PowerDistribution.ModuleType moduleType)` — **public** | `inputs.loggablepowerdistribution.LoggedPowerDistribution.getInstance()` (no-arg only; module ID/type set via the private constructor with defaults `moduleId=1, moduleType=kRev`) — **public** | **Minor gap at this release** (before the 2027 `busID` change catalogued separately) — PyKit has no public way to select a non-default module ID/type; a caller must reach into the constructor directly since `getInstance()` takes no arguments (AdvantageKit's 2-arg overload has no PyKit counterpart). Both frameworks' no-arg `getInstance()` behave the same way at this release (lazily construct a default instance if none exists yet).       |
| `LoggedSystemStats` — **package-private**, `saveToLog(LogTable)`                                                                     | `inputs.loggablesystemstats.LoggedSystemStats` — **public**, `saveToTable(cls, table)`                                                                                                          | Same pattern as `LoggedDriverStation` above: PyKit exposes as public API something AdvantageKit deliberately keeps internal.                                                                                                                                                                                                                                                                                                                            |
| `AlertLogger` — **package-private**, `periodic()`                                                                                    | `alertlogger.AlertLogger` — **public**, `periodic()` / `registerGroup(group: str)`                                                                                                              | Same pattern again — PyKit's version is public and additionally exposes an explicit `registerGroup` call not present (or not needed) on AdvantageKit's internal version.                                                                                                                                                                                                                                                                                |
| `RadioLogger` — **package-private**, `periodic(LogTable)` (robot radio/OpenMesh connectivity logging)                                | —                                                                                                                                                                                               | **Gap.** No PyKit equivalent for radio-connectivity telemetry at all (regardless of public/private status).                                                                                                                                                                                                                                                                                                                                             |

### 1.9 Console capture

| AdvantageKit                                                                                                                                                                                                                                                                          | PyKit                                                                                                                                                             | Δ                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ConsoleSource` — **public interface**, pluggable, with two shipped implementations: `ConsoleSource.Simulator` (in-process `SplitStream` capture) and `ConsoleSource.RoboRIO` (tails `/home/lvuser/FRC_UserProgram.log`); selectable via `Logger.AdvancedHooks.setConsoleSource(...)` | `_ConsoleRecorder` — **private** (leading underscore), single hardcoded implementation wrapping `sys.stdout`/`sys.stderr` directly in-process, not user-pluggable | **Architectural gap.** AdvantageKit treats console capture as an extension point (different implementation needed per target: sim vs. roboRIO, and — per `docs/akit-changes-to-date.md` — SystemCore in 2027); PyKit hardcodes one approach with no seam for swapping it. In practice PyKit's single approach is simpler and arguably more portable (it never depended on roboRIO-specific file-tailing to begin with), but it cannot be replaced/extended by a consumer the way AdvantageKit's can. |

### 1.10 Misc tooling

| AdvantageKit                                                                                                                                                                                                             | PyKit                                                                                                                                                                                                        | Δ                                                                                                                                                                                                                                                                                                  |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `LogFileUtil.addPathSuffix(path, suffix)` / `LogFileUtil.findReplayLog()` — static helpers for replay-log file discovery/naming                                                                                          | —                                                                                                                                                                                                            | **Gap.** No equivalent helper class found in `src/pykit` at `v1.0.5`.                                                                                                                                                                                                                              |
| `ReplayWatch` — standalone CLI tool (`public static void main(...)`) that watches a directory and (per its file-visitor logic) reacts to new/changed log files, used for auto-triggering replay/AdvantageScope workflows | — (not present in the `v1.0.5` release tree; a "replay watch on its own project" commit exists only on the unmerged, out-of-scope `origin/real-hardware` branch — see `docs/2027-akit-v-pykit-deltas.md` §3) | **Gap at the released-version level.** Some equivalent capability may be under early development upstream (unreleased branch), but nothing shipped in `v1.0.5`.                                                                                                                                    |
| `RecordStruct` — adapts a Java `Record` type to WPILib's `Struct<T>` serialization interface via reflection                                                                                                              | —                                                                                                                                                                                                            | **Not portable / not applicable.** Python has no direct analog to Java's `Record` type; this is a language-specific implementation detail of how AdvantageKit supports `recordOutput(String, R value)` for record types, not a missing "feature" so much as a missing "reason to exist" in Python. |

---

## 2. Detailed differences

### 2.1 The single biggest structural difference: one `recordOutput`/`put`, not fifty

AdvantageKit's `Logger.recordOutput` and `LogTable.put`/`get` are each implemented as roughly **50 individually-typed
overloads** — one per primitive, primitive array, primitive 2D array, `Struct<T>` (single + array + 2D array),
`Protobuf`/`ProtoMessage`,
`WPISerializable`, `StructSerializable` (array + 2D array), `Record` (single + array + 2D array), `Enum` (single +
array + 2D array), `Measure<U>`, `LoggedMechanism2d`, and
`Color`. This is only possible because Java resolves overloads at compile time.

PyKit collapses all of this into **one method** —
`recordOutput(key: str, value: Any, unit: Optional[str] = None)` — because Python has no compile-time overload
resolution; instead, `LogValue.__init__` does runtime
`isinstance` type inference. That inference chain currently only recognizes: `bool`,
`int`, `float`, `str`, `bytes`, and homogeneous `list`s of those primitive types. Separately, `LogTable.put()`
special-cases anything exposing a `WPIStruct` attribute (single value or an iterable of them), delegating to
`wpiutil.wpistruct.pack`/
`packArray` — meaning **WPILib geometry types and other struct-serializable RobotPy objects are logged natively,
matching AdvantageKit's `Struct<T>` overloads reasonably closely**. What has **no PyKit equivalent at all** is:
`Protobuf`/`ProtoMessage`
messages, `Color`/`Color8Bit`, `Measure<U>` (WPILib's unit-quantity types), Java
`Record`s (no Python analog), and native `Enum` serialization (an `Enum` member passed to PyKit's `recordOutput` today
would fail type inference rather than being logged by its `.name`, since `LogValue`'s `isinstance` chain has no `Enum`
branch).

**Practical impact:** teams porting AdvantageKit robot code to PyKit/`lib_6107.pykit`
that directly logs enums, `Color`, or unit-`Measure` values need a manual conversion step (e.g. `.name`/`str(value)` for
enums, decompose `Measure` to a raw float + a
`unit` string argument) — there is no drop-in equivalent overload waiting for them.

### 2.2 Mechanism visualization is entirely unported

AdvantageKit's `org.littletonrobotics.junction.mechanism` package — `LoggedMechanism2d`,
`LoggedMechanismRoot2d`, `LoggedMechanismLigament2d`, `LoggedMechanismObject2d` — has no PyKit counterpart whatsoever,
at any file or module path. This includes not just the 2D visualization (a replay-safe drop-in for WPILib's own
`Mechanism2d`) but also the newer `generate3dMechanism()` capability (producing an `ArrayList<Pose3d>` for 3D mechanism
rendering in AdvantageScope). Any team wanting to log/replay mechanism visualizations through PyKit today must either
bypass PyKit for this (e.g. use WPILib's plain `Mechanism2d` + `SmartDashboard`, outside the replay-safe pipeline) or
build the equivalent from scratch.

### 2.3 RLOG is unported; NT4 is the only live-viewing path in PyKit

AdvantageKit ships two live-telemetry transports for AdvantageScope: `NT4Publisher`
(standard NetworkTables 4) and `rlog.RLOGServer` (its own bespoke binary protocol, specified in `RLOG-SPEC.md`, served
over a raw socket). PyKit only has the NT4 path. In practice this is a low-priority gap — NT4 is the more broadly useful
and standards-based of the two transports, and PyKit's `NT4Publisher(actLikeAKit=True)`
flag (see §1.5) shows the PyKit team explicitly designed for AdvantageScope compatibility over NT4 rather than trying to
also speak RLOG — but it means any tooling or workflow that specifically depends on the RLOG protocol (rather than just
"live AdvantageScope viewing" generically) has no PyKit equivalent.

### 2.4 Console capture: pluggable interface vs. one hardcoded implementation

AdvantageKit's `ConsoleSource` is a public interface with target-specific implementations (`Simulator`, `RoboRIO`, and —
per `docs/akit-changes-to-date.md` — a newer `Systemcore` implementation on unreleased `main`) selected automatically by
`Logger.start()` or overridden via `Logger.AdvancedHooks.setConsoleSource(...)`. PyKit's console capture
(`_ConsoleRecorder`, module-private) is a single, hardcoded implementation that wraps `sys.stdout`/`sys.stderr`
in-process — there is no interface to implement or hook to override it with a custom source. This is simpler and,
notably, was never coupled to roboRIO-specific assumptions in the first place (unlike AdvantageKit's original
file-tailing `RoboRIO` implementation), but it does mean PyKit offers no extension point here at all.

### 2.5 `@AutoLogOutput` registration: explicit (Java) vs. automatic (Python)

AdvantageKit requires the user to explicitly tell `AutoLogOutputManager` where to look — either
`addPackage("org.example.robot")` (scan a whole package by name) or
`addObject(someInstance)` (register one object directly), typically called once from
`Robot.robotInit()`. PyKit's `AutoLogOutputManager`/`@autologgable_output` has no equivalent "please register this" call
in its public API; per the architecture notes already captured in `docs/westwood-pykit-changes-to-date.md`, it instead
uses
`gc.get_referrers` to find live instances of registered classes automatically. This is a genuine design trade-off, not
simply "PyKit is missing a feature": Java's approach is more explicit and deterministic (you always know what will be
scanned); Python's approach requires less boilerplate but is a `gc`-reflection-dependent mechanism whose behavior is
less obvious from reading the call site alone — worth being deliberate about whether `lib_6107.pykit` should keep this
"magic"
behavior or move toward an explicit-registration model if determinism becomes a priority (e.g. for unit testing in
isolation).

### 2.6 `WPILOGWriter`: different constructor shape, and AdvantageScope auto-open is unported

AdvantageKit's `WPILOGWriter` constructors take a directory **path** as the primary argument, plus an optional
`AdvantageScopeOpenBehavior` enum controlling whether (and how) the just-written log auto-opens in a running local
AdvantageScope instance — useful for tight edit/test/inspect loops in simulation. PyKit's `WPILOGWriter` takes a
**filename** as its primary argument, with `path` as a distinct, independently optional parameter (a difference already
documented in
`docs/westwood-pykit-changes-to-date.md` as the sole change introduced in PyKit v1.0.5 itself). There is no PyKit
equivalent of `AdvantageScopeOpenBehavior` at all — a PyKit user must manually open AdvantageScope and load the log
themselves.

### 2.7 Visibility model: what AdvantageKit hides, PyKit exposes

Three AdvantageKit classes that "look missing" from a naive method-name comparison —
`LoggedDriverStation`, `LoggedSystemStats`, `AlertLogger` — are not missing at all; PyKit has a same-named or
clearly-corresponding class for each (`inputs.loggableds`,
`inputs.loggablesystemstats`, `alertlogger`). The difference is that AdvantageKit deliberately declares all three
**package-private** (no `public` modifier, not part of its documented API), while every one of PyKit's equivalents is a
fully public, importable class. This is not a functional gap in either direction, but it is worth flagging for anyone
trying to hold `lib_6107.pykit`'s public surface to the same
"what should a consumer be allowed to depend on" boundary AdvantageKit draws — today,
`lib_6107.pykit` (following PyKit's lead) exposes strictly more as "public" than AdvantageKit intends consumers to treat
as stable, even though the underlying behavior is equivalent.

### 2.8 `RadioLogger` and `LogFileUtil`/`ReplayWatch`: real, released-version gaps

Unlike §2.7's classes, `RadioLogger` (robot radio/mesh connectivity telemetry) and
`LogFileUtil`/`ReplayWatch` (replay-log discovery/naming helpers and a directory-watch auto-replay tool) have **no PyKit
counterpart at all** in the `v1.0.5` release tree — these are genuine, unported capability gaps, not naming/visibility
artifacts. Some replay-tooling work does appear to be underway on PyKit's unmerged
`origin/real-hardware` branch (a "replay watch on its own project" commit), but per
`docs/2027-akit-v-pykit-deltas.md` §3, that branch is a stale, pre-1.0 experiment older than the current `main`/`v1.0.5`
release — it should not be treated as in-progress work heading toward a near-term release.

---

## 3. References

**In-repo companion documents**

- `docs/akit-changes-to-date.md` — AdvantageKit's public API as of `main` (post-2027 work) and its delta from `v26.0.2`;
  used here to reconstruct the pre-2027,
  `v26.0.2`-era signatures by reading the tagged source directly rather than subtracting the delta by hand.
- `docs/westwood-pykit-changes-to-date.md` — PyKit's public API "as of v1.0.5" and confirmation that `main` has had no
  commits since that tag; the primary existing source for PyKit's architecture notes referenced throughout §2.
- `docs/2027-akit-v-pykit-deltas.md` — the WPILib-2027/SystemCore-specific comparison (a different, later-stage axis of
  comparison than this document, which is deliberately scoped to both projects' **last released** versions).
- `docs/lib_6107-api-work-todo.md` — prior `lib_6107.pykit`-specific gap list; this document confirms several of those
  gaps (e.g. `runEveryN`) originate upstream in PyKit itself, not from `lib_6107`'s own port.
- `docs/2026-telemetry-examples.md` — real-world example of a team (4572 Barlow Robotics) hand-rolling a `runEveryN`
  -equivalent decimation pattern in the absence of a first-class one (§4.6 there).

**Source repositories inspected directly (local clones, exact tags)**

- [`Mechanical-Advantage/AdvantageKit`](https://github.com/Mechanical-Advantage/AdvantageKit) — tag `v26.0.2` (commit
  `00b1b62`), full `akit/src/main/java/org/littletonrobotics/junction/**`
  tree read via `git show v26.0.2:<path>`.
- [`1757WestwoodRobotics/PyKit`](https://github.com/1757WestwoodRobotics/PyKit) — tag `v1.0.5` (commit `5d70664`), full
  `src/pykit/**` tree read via
  `git show v1.0.5:<path>`.
