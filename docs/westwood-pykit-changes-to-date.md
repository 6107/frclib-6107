# PyKit — Project Layout, Public API, and Changes Since v1.0.5

> Prepared for senior developers maintaining a comparable Python-based
> logging/telemetry/replay framework, to understand PyKit's current shape and
> what has moved since its last tagged release.

## 1. What PyKit is

PyKit (`robotpy-pykit`) is a pure-Python logging, telemetry, and replay framework for FRC robots, built on top of
`wpilib`/`ntcore`/`wpiutil`/`hal`
(RobotPy). It is a Python port of the design pioneered by
[AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit/) (Java):
every robot I/O interaction is funneled through a central `Logger`/`LogTable`
so that the exact same code path can either (a) record live data during a match/test, or (b) replay previously recorded
data deterministically for simulation/debugging, with no changes to user robot code.

## 2. Project layout

```
pyproject.toml            # package metadata (name: robotpy-pykit, build via uv_build)
src/pykit/                 # the library itself (import path: `pykit`)
  __init__.py               # empty — no re-exports; consumers import submodules directly
  logger.py                 # Logger — the central static/classmethod-based orchestrator
  logtable.py                # LogTable — typed key/value store for one timestamp "frame"
  logvalue.py                 # LogValue + LoggableType enum — the type system for logged data
  loggedrobot.py                # LoggedRobot(IterativeRobotBase) — robot main-loop replacement
  autolog.py                     # @autolog / @autolog_output decorators + manager singletons
  alertlogger.py                   # AlertLogger — mirrors WPILib "Alerts" (errors/warnings/info)
  logdatareciever.py                # LogDataReciever — abstract sink interface
  logreplaysource.py                  # LogReplaySource — abstract source interface (for replay)
  inputs/
    loggableds.py                      # LoggedDriverStation — DS state capture/playback
    loggablepowerdistribution.py         # LoggedPowerDistribution — PDP/PDH telemetry
    loggablesystemstats.py                 # LoggedSystemStats — RIO/HAL + NT connection stats
  networktables/
    loggednetworkinput.py                    # LoggedNetworkInput — base for replayable NT inputs
    loggednetworkvalue.py                      # LoggedNetworkValue[T] — generic NT entry wrapper
    loggednetworkboolean.py                      # LoggedNetworkBoolean (BooleanEntry specialization)
    loggednetworknumber.py                         # LoggedNetworkNumber (DoubleEntry specialization)
    loggednetworkstring.py                           # LoggedNetworkString (StringEntry specialization)
    loggeddashboardchooser.py                          # LoggedDashboardChooser[T] — SendableChooser wrapper
    nt4Publisher.py                                      # NT4Publisher(LogDataReciever) — live NT4 mirror
  wpilog/
    wpilogwriter.py                                        # WPILOGWriter(LogDataReciever) — writes .wpilog files
    wpilogreader.py                                          # WPILOGReader(LogReplaySource) — reads .wpilog files
    wpilogconstants.py                                         # shared header/metadata string constants
template_projects/           # 3 starter robot projects (skeleton, kitbot_2025, diff_drive)
docs/                          # Sphinx (readthedocs) API doc scaffolding
```

Design notes for anyone building an equivalent system:

- **No package `__init__.py` re-exports.** Every consumer imports concrete submodules
  (`from pykit.logger import Logger`, `from pykit.wpilog.wpilogwriter
  import WPILOGWriter`, etc.). There is no curated top-level namespace/`__all__`.
- **Class-based singletons instead of instances**, for the core pieces:
  `Logger` and `AlertLogger` are used entirely through `@classmethod`s and class-level mutable state (no instantiation).
  `AutoLogInputManager` /
  `AutoLogOutputManager` follow the same pattern. This makes the framework simple to call from anywhere
  (`Logger.recordOutput(...)`), at the cost of being a global singleton (not safely multi-instance/testable in
  isolation).
- **`LogTable` is the single data model.** It's a flat `dict[str, LogValue]`
  keyed by fully-qualified path (`"/subsystem/field"`); "subtables" are just views sharing the same backing dict with a
  longer prefix. Both the "record"
  and "replay" data paths, and both file (`WPILOGWriter`/`WPILOGReader`) and live (`NT4Publisher`) transports, operate
  purely in terms of `LogTable`s.
- **Pluggable sinks/sources.** `LogDataReciever` (sink, e.g. WPILOG file, NT4) and `LogReplaySource` (source, e.g.
  WPILOG file) are small abstract base classes; multiple receivers can be registered simultaneously.
- **Reflection-based autologging.** `autolog.py` uses `gc.get_referrers` to find live instances of registered classes
  and a decorator system (`@autologgable_output` / `@autolog_output`) to publish arbitrary fields/methods without manual
  wiring — a non-trivial, somewhat "magic"
  mechanism worth studying/critiquing if reimplementing in a stricter ecosystem (mypy typing here is deliberately loose
  around this feature).

## 3. Public API as it stands today (equivalent to v1.0.5)

### `pykit.logger.Logger` (classmethods only; the main entry point)

| Member                                                                                           | Purpose                                                                                                                             |
|--------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `Logger.setReplaySource(replaySource: LogReplaySource)`                                          | Switch the framework into replay mode using the given source.                                                                       |
| `Logger.isReplay() -> bool`                                                                      | True if a replay source has been set.                                                                                               |
| `Logger.recordOutput(key, value, unit=None)`                                                     | Record a value under `RealOutputs`/`ReplayOutputs`. No-op unless started.                                                           |
| `Logger.recordMetadata(key, value)`                                                              | Record a one-time string metadata entry (build info, git hash, etc.). Ignored in replay.                                            |
| `Logger.processInputs(prefix, inputs)`                                                           | Calls `inputs.toLog(...)` (recording) or `inputs.fromLog(...)` (replay) — the core input abstraction used by every `Logged*` class. |
| `Logger.addDataReciever(reciever: LogDataReciever)`                                              | Register an output sink (WPILOG writer, NT4 publisher, custom).                                                                     |
| `Logger.registerDashboardInput(dashboardInput: LoggedNetworkInput)`                              | Register an NT-backed input for periodic servicing.                                                                                 |
| `Logger.start()` / `Logger.startReciever()` / `Logger.end()`                                     | Lifecycle — normally called by `LoggedRobot`, not by user code directly.                                                            |
| `Logger.getTimestamp() -> int`                                                                   | Current logical timestamp (µs); FPGA time when live, replayed value when in replay.                                                 |
| `Logger.periodicBeforeUser()` / `Logger.periodicAfterUser(userCodeLength, periodicBeforeLength)` | Framework hooks bracketing the user's periodic code; called by `LoggedRobot`.                                                       |

Console output (`stdout`/`stderr`) is automatically captured line-by-line into
`Console` output entries while the logger is running.

### `pykit.loggedrobot.LoggedRobot(IterativeRobotBase)`

Drop-in replacement for `wpilib.TimedRobot`. Overrides `startCompetition`/
`endCompetition` to drive the main loop via a HAL notifier and to call
`Logger.periodicBeforeUser()` / `Logger.periodicAfterUser()` around
`self._loopFunc()` each cycle. User code subclasses this exactly as it would
`TimedRobot`.

### `pykit.logtable.LogTable`

The per-timestamp data container. Public surface:
`__init__(timestamp, prefix="/")`, `LogTable.clone(source)` (static),
`getTimestamp()`/`setTimestamp()`, `put(key, value, typeStr="", unit=None)`
(auto-detects WPILib struct/array-of-struct types), `putValue(key, LogValue)`, typed getters — `get`, `getRaw`,
`getBoolean`, `getInteger`, `getFloat`,
`getDouble`, `getString`, and the five `*Array` variants — each taking a
`defaultValue` and returning it on type-mismatch or missing key,
`getAll(subtableOnly=False)`, and `getSubTable(prefix) -> LogTable` (returns a new view sharing the same backing `dict`,
used to build hierarchical keys).

### `pykit.logvalue.LogValue` / `LogValue.LoggableType`

`LogValue(value, typeStr="", unit=None)` infers a `LoggableType` from the Python type (bool → Boolean, int → Integer,
float → Double, str → String, bytes → Raw, homogeneous `list` → one of the `*Array` types); raises
`TypeError` for unsupported types. `LogValue.withType(log_type, data, typeStr,
unit)` bypasses inference. `LoggableType` enum members map to/from WPILOG (`getWPILOGType`/`fromWPILOGType`) and NT4
(`getNT4Type`/`fromNT4Type`) type strings.

### `pykit.logdatareciever.LogDataReciever` / `pykit.logreplaysource.LogReplaySource`

Abstract base classes (no ABC enforcement, just `NotImplementedError` on the source side) with `start()`, `end()`, and
`putTable(table)` /
`updateTable(table) -> bool` respectively. Implement these to add a custom sink or source.

### `pykit.wpilog.wpilogwriter.WPILOGWriter(LogDataReciever)`

`WPILOGWriter(filename: str | None = None, path: str | None = None)`. Writes a `.wpilog` file compatible with
AdvantageScope/WPILib tooling. When
`filename` is omitted, auto-generates and auto-renames the file using timestamp + event name + match number once DS/FMS
data becomes available.
`path` (added in v1.0.5, see below) lets callers redirect the output directory independent of `filename`.

### `pykit.wpilog.wpilogreader.WPILOGReader(LogReplaySource)`

`WPILOGReader(filename: str)`. Reads a `.wpilog` file previously produced by
`WPILOGWriter` (validated via a matching custom "extra header" — logs from other tools/AdvantageKit are rejected) and
feeds it back through
`updateTable` for replay.

### `pykit.networktables.nt4Publisher.NT4Publisher(LogDataReciever)`

`NT4Publisher(actLikeAKit: bool = False)`. Mirrors log output live to NetworkTables under `/PyKit` (or `/AdvantageKit`
for interop with existing AdvantageScope dashboards/layouts when `actLikeAKit=True`). Publishes only changed keys each
cycle and supports a `unit` NT topic property.

### `pykit.networktables.*` input wrappers

- `LoggedNetworkInput` — base class, just a `prefix` and `periodic()` hook.
- `LoggedNetworkValue[T, V]` — generic base wrapping an `ntcore` entry type (`Boolean/Double/String/IntegerEntry`);
  concrete `LoggedNetworkBoolean`,
  `LoggedNetworkNumber`, `LoggedNetworkString` specialize it.
- `LoggedDashboardChooser[T]` — wraps `wpilib.SendableChooser`; `addOption`,
  `setDefaultOption`, `getSelected()`, `onChange(callback)`. Selection is logged/replayed transparently.

### `pykit.inputs.*` — built-in loggable subsystems

- `LoggedDriverStation.saveToTable(table)` / `.loadFromTable(table)` — full DS + joystick (buttons/POV/axes) capture and
  simulation playback.
- `LoggedPowerDistribution` — singleton wrapper (`getInstance()`) around
  `wpilib.PowerDistribution`; `saveToTable(table)` logs voltage/current/ power/energy/temperature and per-channel
  currents.
- `LoggedSystemStats.saveToTable(table)` — HAL system stats (FPGA version/revision, serial number, brownout, RSL, team
  number, etc.) plus live NT client connection tracking.

### `pykit.alertlogger.AlertLogger`

`registerGroup(group: str)` / `periodic(outputTable)` — mirrors WPILib
`Alerts` SmartDashboard entries (errors/warnings/info string arrays per group) into the log.

### `pykit.autolog` — reflection-based auto logging

- `@autolog` — dataclass decorator generating `toLog`/`fromLog` methods that (de)serialize declared fields (including
  nested `@autolog` dataclasses, WPILib structs, and typed lists) and self-registers instances with
  `AutoLogInputManager` for automatic replay handling.
- `@autologgable_output` (class decorator) + `@autolog_output(key, log_type=None,
  custom_type="", unit=None)` (member decorator) — mark specific fields/methods on any class for automatic output
  publishing each cycle;
  `AutoLogOutputManager.publish_all(table)` is called by `Logger` internally.
- `AutoLogInputManager` / `AutoLogOutputManager` — the manager singletons backing the above; generally not called
  directly by user code.

## 4. Changes since v1.0.5

**Finding:** The checked-out `main` branch is byte-for-byte at the `v1.0.5`
tag (`git describe --tags` → `v1.0.5` exactly; `git log v1.0.5..HEAD` and
`git log HEAD..origin/main` are both empty). **No commits have landed on
`main` since the v1.0.5 release** — despite it being ~4 months old, this repository's public API today is identical to
v1.0.5. There is nothing to report as an in-progress/unreleased change on the branch a consumer would actually pull.

Two branches with unmerged work exist on the remote (`origin/real-hardware`,
`origin/docs`) but neither is merged into `main`, and `real-hardware` in particular represents a divergent restructuring
(moves `pykit` out of `src/`, drops the template projects and doc scaffolding) that looks like exploratory/ early-stage
work rather than a drop-in successor. Treat these as **not part of the current public API** — call them out to your team
only as "things to watch," not as adopted behavior.

### For context: what actually changed in the v1.0.5 release itself (vs. v1.0.4)

Since there is no post-release delta, the most recent *real* user-facing change is the one that shipped in v1.0.5
(commit `27a6c98`, "allow custom folder location still with renaming"). Given the audience, this is detailed below as it
is the most recent thing anyone integrating today needs to be aware of:

#### API change: `WPILOGWriter.__init__` gained a `path` parameter

- **Before (v1.0.4):** `WPILOGWriter(filename: str | None = None)`. The only way to control the output directory was to
  pass a `filename` containing a directory component (`os.path.dirname(filename)`); otherwise the hardcoded default
  (`/U/logs` on the RIO, `pyLogs` in sim) was used verbatim.
- **After (v1.0.5, current):**
  `WPILOGWriter(filename: str | None = None, path: str | None = None)`. A caller can now supply `path` independently of
  `filename`:
    - `path` given, `filename` omitted → logs go into `path` using the existing auto-generated/auto-renaming filename
      scheme.
    - `path` given **and** `filename` given → they are joined (`os.path.join(path, os.path.dirname(filename))`), so both
      can be combined (e.g. a base log directory plus a relative subfolder/name).
    - `path` omitted → unchanged legacy behavior (`filename`'s own directory, or the RIO/sim default).
- **Compatibility:** Fully backward compatible — `path` defaults to `None`
  and existing call sites (`WPILOGWriter()`, `WPILOGWriter(filename)`)
  behave exactly as before. This is a pure additive constructor-parameter change, not a breaking change.
- **Why it matters to integrators:** if you maintain a similar logging/replay framework, this is the shape to imitate if
  you want to let users redirect log output to a custom directory (e.g. a mounted USB drive path or a per-event folder)
  without having to hand-build a full file path string themselves each time.

No other public class, method signature, or module was added, removed, or changed in behavior between v1.0.4 and v1.0.5
(the only other file touched was `pyproject.toml`'s version bump and template project dependency pins).

## 5. References

- Repository inspected directly: `1757WestwoodRobotics/PyKit` (local clone, branch `main`, commit `5d70664` = tag
  `v1.0.5`), including:
    - `src/pykit/**/*.py` (full source tree read for this document)
    - `pyproject.toml`
    - `README.md`
    - Git history: `git log`, `git tag --list`, `git diff v1.0.4 v1.0.5`,
      `git diff main origin/real-hardware --stat`
- [AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit/) — the Java framework PyKit is a Python port of;
  referenced in PyKit's own README as the design inspiration (WPILOG format compatibility,
  `/AdvantageKit` NT table naming option in `NT4Publisher`).
- [WPILib Data Logging docs](https://docs.wpilib.org/en/stable/docs/software/telemetry/datalog.html) — referenced in
  PyKit's README as the simpler built-in alternative; also the origin of the `.wpilog` file format read/written by
  `pykit.wpilog.wpilogwriter`/`wpilogreader` (via `wpiutil.log.DataLogWriter`/
  `DataLogReader`).
