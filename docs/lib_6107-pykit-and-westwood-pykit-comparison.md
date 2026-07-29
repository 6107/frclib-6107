# `lib_6107.pykit` vs. 1757 Westwood Robotics `PyKit` — Comparison

> Audience: senior developers maintaining (or building) a comparable Python-based FRC
> logging/telemetry/replay framework. This document catalogs how `src/lib_6107/pykit`
> differs from the upstream project it was forked from, both in public API surface and
> in behavior, so the differences can be judged, reused, or reconciled deliberately
> rather than by archaeology.

## 1. Relationship between the two codebases

`lib_6107.pykit` is a **fully vendored, in-tree fork** of
[1757WestwoodRobotics/PyKit](https://github.com/1757WestwoodRobotics/PyKit) (package name `robotpy-pykit`, import path
`pykit`). It is **not** a pip dependency — `pyproject.toml`
lists `wpilib`, `robotpy`, `robotpy-hal`, `robotpy-commands-v2`, etc., but no
`robotpy-pykit` entry. All of `pykit`'s source was copied into
`src/lib_6107/pykit/` and has since been edited directly in this repository.

Two other local facts worth recording for provenance:

- A separate mirror fork, `6107/pykit` (GitHub remote `https://github.com/6107/pykit`), exists but its `main` branch is
  **identical to upstream `v1.0.5`** (same commit
  `5d70664`) — it was never used as the place where the snake_case/PEP 8 rework happened. All divergence described below
  happened directly inside this (`frclib-6107`) monorepo, with no separate commit history to diff against.
- The upstream `PyKit` repository's `main` branch is itself frozen at tag `v1.0.5`
  (confirmed via `git describe --tags` and empty `git log v1.0.5..HEAD`) — see
  `docs/westwood-pykit-changes-to-date.md` for the full prior analysis of that baseline and its module layout. **This
  document treats `v1.0.5` as the upstream baseline** for every comparison below (verified directly against a local
  clone of
  `1757WestwoodRobotics/PyKit` at commit `5d70664`).

## 2. Module inventory

| Module                                                                                                              | In Westwood `v1.0.5`? | In `lib_6107.pykit`? | Notes                                                                                                                                                                                                           |
|---------------------------------------------------------------------------------------------------------------------|-----------------------|----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `logger.py` (`Logger`)                                                                                              | Yes                   | Yes                  | Present in both; see §3 for API diff                                                                                                                                                                            |
| `logtable.py` (`LogTable`)                                                                                          | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `logvalue.py` (`LogValue`)                                                                                          | Yes                   | Yes                  | `lib_6107` upgraded to `@dataclass(slots=True)` (Westwood: plain `@dataclass`, no slots)                                                                                                                        |
| `loggedrobot.py` (`LoggedRobot`)                                                                                    | Yes                   | Yes                  | `lib_6107` adds a configurable `period` constructor argument; Westwood hardcodes `default_period`                                                                                                               |
| `autolog.py`                                                                                                        | Yes                   | Yes                  | Near-identical; Westwood already used `register_class`/`publish_all`/`register_member` (snake_case)                                                                                                             |
| `alertlogger.py` (`AlertLogger`)                                                                                    | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `logdatareciever.py` / `logdatareceiver.py`                                                                         | Yes (misspelled name) | Yes (spelling fixed) | File and class renamed; see §5                                                                                                                                                                                  |
| `logreplaysource.py` (`LogReplaySource`)                                                                            | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `inputs/loggableds.py` (`LoggedDriverStation`)                                                                      | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `inputs/loggablepowerdistribution.py` (`LoggedPowerDistribution`)                                                   | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `inputs/loggablesystemstats.py` (`LoggedSystemStats`)                                                               | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `networktables/loggednetworkinput.py`                                                                               | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `networktables/loggednetworkvalue.py`                                                                               | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `networktables/loggednetworkboolean.py` / `...number.py` / `...string.py`                                           | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `networktables/loggeddashboardchooser.py`                                                                           | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `networktables/nt4Publisher.py` (`NT4Publisher`)                                                                    | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `wpilog/wpilogwriter.py` (`WPILOGWriter`)                                                                           | Yes                   | Yes                  | Both already have the `path` constructor parameter added in Westwood `v1.0.5` (commit `27a6c98`) — no divergence here                                                                                           |
| `wpilog/wpilogreader.py` (`WPILOGReader`)                                                                           | Yes                   | Yes                  |                                                                                                                                                                                                                 |
| `wpilog/wpilogconstants.py`                                                                                         | Yes                   | Yes                  | `extraHeader = "PyKit"` unchanged — `.wpilog` files remain cross-readable between the two implementations                                                                                                       |
| `template_projects/` (3 starter robot projects)                                                                     | Yes                   | **No**               | Not applicable — `lib_6107` ships an `example/` project instead, serving a similar purpose                                                                                                                      |
| Sphinx/readthedocs doc scaffolding                                                                                  | Yes                   | **No**               | `lib_6107` documents itself via `docs/*.md` instead                                                                                                                                                             |
| `LoggedMechanism2d.py` / `LoggedMechanismRoot2d.py` / `LoggedMechanismLigament2d.py` / `LoggedMechanismObject2d.py` | **No**                | Yes                  | **New.** A Python port of AdvantageKit Java's `org.littletonrobotics.junction.mechanism` package — not present in PyKit at all. See §6.                                                                         |
| `LoggedNetworkButton.py` (`NetworkTableButton`)                                                                     | **No**                | Yes                  | **New.** Wraps `LoggedNetworkBoolean` in a `commands2.button.Trigger`. See §6.                                                                                                                                  |
| `logtracer.py` (`LogTracer`)                                                                                        | **No**                | Yes                  | **New**, but *not* derived from the PyKit library — its in-file credit explicitly attributes it to Westwood Robotics' **`2026-Rebuilt` robot-code repository**, a different codebase than PyKit itself. See §6. |

## 3. External API changes: the PEP 8 naming migration

The stated goal for this fork was to move the API toward PEP 8 (snake_case methods/params) and PEP 484 (full type
hints). The migration is **real but incomplete and inconsistent** — some classes are fully converted, others are
untouched, and a few methods ended up in a worse state than before. All rows below were verified directly against both
source trees (Westwood `v1.0.5` clone vs. the current `src/lib_6107/pykit`).

### `Logger` — almost entirely unchanged (still camelCase)

| Westwood `v1.0.5`                                 | `lib_6107`                                        | Status                                                                  |
|---------------------------------------------------|---------------------------------------------------|-------------------------------------------------------------------------|
| `setReplaySource`                                 | `setReplaySource`                                 | Unchanged                                                               |
| `isReplay`                                        | `isReplay`                                        | Unchanged                                                               |
| `recordOutput`                                    | `recordOutput`                                    | Unchanged                                                               |
| `recordMetadata`                                  | `recordMetadata`                                  | Unchanged                                                               |
| `processInputs`                                   | `processInputs`                                   | Unchanged (now dispatches to `to_log`/`from_log`, see below)            |
| `addDataReciever(cls, reciever: LogDataReciever)` | `addDataReciever(cls, reciever: LogDataReceiver)` | **Unchanged name/param, only the type annotation was updated** — see §5 |
| `registerDashboardInput`                          | `registerDashboardInput`                          | Unchanged                                                               |
| `start` / `end`                                   | `start` / `end`                                   | Unchanged                                                               |
| `startReciever`                                   | `start_receiver`                                  | **Renamed** (snake_case *and* typo fixed)                               |
| `getTimestamp`                                    | `getTimestamp`                                    | Unchanged                                                               |
| `periodicBeforeUser` / `periodicAfterUser`        | `periodicBeforeUser` / `periodicAfterUser`        | Unchanged                                                               |

`Logger` — the single most-used class in the framework — has only **one of twelve**
public methods renamed.

### `LogTable` — mostly converted, three notable holdouts

| Westwood `v1.0.5`                                                                             | `lib_6107`                                                                                              | Status                                   |
|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| `put(key, value, typeStr="", unit=None)`                                                      | `put(key, value, type_str="", unit=None)`                                                               | Renamed (method + param)                 |
| `putValue`                                                                                    | `put_value`                                                                                             | Renamed                                  |
| `get(key, defaultValue)`                                                                      | `get(key, default)`                                                                                     | Param renamed                            |
| `getRaw` / `getBoolean` / `getInteger` / `getFloat` / `getDouble` / `getString`               | `get_raw` / `get_boolean` / `get_integer` / `get_float` / `get_double` / `get_string`                   | All renamed (+ `defaultValue`→`default`) |
| `getBooleanArray` / `getIntegerArray` / `getFloatArray` / `getDoubleArray` / `getStringArray` | `get_boolean_array` / `get_integer_array` / `get_float_array` / `get_double_array` / `get_string_array` | All renamed                              |
| `getAll(subtableOnly=False)`                                                                  | `get_all(subtable_only=False)`                                                                          | Renamed                                  |
| `writeAllowed`                                                                                | `write_allowed`                                                                                         | Renamed                                  |
| `addStructSchemaNest` / `addStructSchema`                                                     | `add_struct_schema_nest` / `add_struct_schema`                                                          | Renamed                                  |
| `getTimestamp`                                                                                | `getTimestamp`                                                                                          | **Unchanged**                            |
| `setTimestamp`                                                                                | `setTimestamp`                                                                                          | **Unchanged**                            |
| `getSubTable`                                                                                 | `getSubTable`                                                                                           | **Unchanged**                            |

13 of 16 public methods converted. The 3 exceptions are the most frequently called-by-user-code members (every subsystem
calls `getSubTable()` at least once per cycle), which suggests the remaining rename was deliberately deferred as the
highest blast-radius change rather than simply forgotten.

### `LogValue`

`getWPILOGType()` / `getNT4Type()` — **unchanged** in both. The constructor and
`withType()` already used snake_case-friendly parameter names in Westwood (`typeStr`, `unit`) and gained no further
renames; `lib_6107` did add
`slots=True` to the dataclass (a performance change, not a naming one — see §7).

### `LoggedDriverStation` — fully converted (100%)

| Westwood `v1.0.5` | `lib_6107`        |
|-------------------|-------------------|
| `saveToTable`     | `save_to_table`   |
| `loadFromTable`   | `load_from_table` |

### `LoggedPowerDistribution` — fully converted (100%), plus new hardening

| Westwood `v1.0.5`        | `lib_6107`        |
|--------------------------|-------------------|
| `moduleId` (attribute)   | `module_id`       |
| `moduleType` (attribute) | `module_type`     |
| `getInstance()`          | `get_instance()`  |
| `saveToTable()`          | `save_to_table()` |

Behavioral addition: Westwood's `saveToTable()` has **no exception handling** around the PDP/PDH hardware reads.
`lib_6107`'s `save_to_table()` wraps the entire body in a
`try/except Exception: pass` explicitly commented `# HACK: Exception work around when
in match (FMS Active)`. This is a genuine robustness fix, not present upstream.

### `LoggedSystemStats` — fully converted (100%)

`saveToTable` → `save_to_table`.

### `AlertLogger`

| Westwood `v1.0.5`                                                     | `lib_6107`                                                       |
|-----------------------------------------------------------------------|------------------------------------------------------------------|
| `periodic(cls, outputTable)`                                          | `periodic(cls, output_table)` (param renamed)                    |
| `registerGroup`                                                       | `register_group`                                                 |
| `errorSubscribers` / `warningSubscribers` / `infoSubscribers` (attrs) | `error_subscribers` / `warning_subscribers` / `info_subscribers` |

### `autolog.py` — essentially unchanged (already snake_case upstream)

Verified directly: Westwood's `AutoLogInputManager.register_class` and
`AutoLogOutputManager.publish_all` / `register_member` were **already snake_case in
`v1.0.5`**. Only `AutoLogInputManager.getInputs` remains camelCase, identically, in both versions. There is no
meaningful naming divergence in this module — the bulk of the difference is added docstrings (see §7).

### `LoggedDashboardChooser` — partially converted

| Westwood `v1.0.5`   | `lib_6107`            | Status    |
|---------------------|-----------------------|-----------|
| `addOption`         | `addOption`           | Unchanged |
| `setDefaultOption`  | `setDefaultOption`    | Unchanged |
| `getSelected`       | `get_selected`        | Renamed   |
| `onChange`          | `on_change`           | Renamed   |
| `toLog` / `fromLog` | `to_log` / `from_log` | Renamed   |

`addOption`/`setDefaultOption` are left exactly matching WPILib's own
`SendableChooser.addOption`/`setDefaultOption` Java-derived names — plausibly an intentional parity choice with the
wrapped WPILib type, not an oversight.

### `LoggedNetworkValue` / `Boolean` / `Number` / `String`

| Westwood `v1.0.5`                         | `lib_6107`                                       | Status                                      |
|-------------------------------------------|--------------------------------------------------|---------------------------------------------|
| `__init__(self, key, defaultValue: T)`    | `__init__(self, key: str, default: T)`           | Param renamed + type hint added on `key`    |
| `setDefault`                              | `set_default`                                    | Renamed                                     |
| `toLog` / `fromLog`                       | `to_log` / `from_log`                            | Renamed                                     |
| `periodic`                                | `periodic`                                       | Unchanged                                   |
| `value` property, `__call__`              | `value` property, `__call__`                     | Present in both — not a `lib_6107` addition |
| `LoggedNetworkNumber[float, DoubleEntry]` | `LoggedNetworkNumber[float \| int, DoubleEntry]` | Generic type widened to also accept `int`   |

### `LogDataReceiver` / `LogReplaySource` / `NT4Publisher` / `WPILOGWriter` / `WPILOGReader`

| Westwood `v1.0.5`                                        | `lib_6107`                          | Status                            |
|----------------------------------------------------------|-------------------------------------|-----------------------------------|
| `LogDataReciever.putTable`                               | `LogDataReceiver.put_table`         | Renamed (class fixed too, see §5) |
| `LogReplaySource.updateTable`                            | `LogReplaySource.updateTable`       | **Unchanged**                     |
| `WPILOGReader.updateTable`                               | `WPILOGReader.updateTable`          | **Unchanged**                     |
| `WPILOGWriter.putTable`                                  | `WPILOGWriter.put_table`            | Renamed                           |
| `WPILOGWriter.defaultPathRio` / `defaultPathSim` (attrs) | `defaultPathRio` / `defaultPathSim` | **Unchanged**                     |
| `NT4Publisher(actLikeAKit=False)`                        | `NT4Publisher(act_like_akit=False)` | Renamed                           |
| `NT4Publisher.putTable`                                  | `NT4Publisher.put_table`            | Renamed                           |

### `LoggedRobot`

| Westwood `v1.0.5`                                                 | `lib_6107`                                                                                                    | Status                                       |
|-------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| `__init__(self)` — no period argument, hardcoded `default_period` | `__init__(self, period: seconds = DEFAULT_PERIOD)`                                                            | **New capability**: configurable loop period |
| `self.useTiming`                                                  | `self.use_timing`                                                                                             | Renamed                                      |
| `self._nextCycleUs`                                               | `self._next_cycle_us`                                                                                         | Renamed                                      |
| `self.initEnd`                                                    | `self.init_end`                                                                                               | Renamed                                      |
| —                                                                 | `self._is_simulation` (cached), `period` property                                                             | New                                          |
| `Logger.periodicAfterUser(...)` called unguarded                  | Wrapped in `try/except Exception: pass`, commented `# HACK: Exception work around when in match (FMS Active)` | New robustness fix                           |

## 4. Summary of the naming migration

| Class                                               | Methods renamed                 | Methods unchanged (camelCase)                     | Migration completeness |
|-----------------------------------------------------|---------------------------------|---------------------------------------------------|------------------------|
| `Logger`                                            | 1                               | 11                                                | ~8%                    |
| `LogTable`                                          | 13                              | 3 (`getTimestamp`, `setTimestamp`, `getSubTable`) | ~81%                   |
| `LogValue`                                          | 0                               | 2 (`getWPILOGType`, `getNT4Type`)                 | 0%                     |
| `LoggedDriverStation`                               | 2                               | 0                                                 | 100%                   |
| `LoggedPowerDistribution`                           | 2 (+2 attrs)                    | 0                                                 | 100%                   |
| `LoggedSystemStats`                                 | 1                               | 0                                                 | 100%                   |
| `AlertLogger`                                       | 2 (+3 attrs)                    | 0                                                 | 100%                   |
| `autolog.py` managers                               | 0 (already snake_case)          | 1 (`getInputs`)                                   | n/a (pre-existing)     |
| `LoggedDashboardChooser`                            | 3                               | 2                                                 | 60%                    |
| `LoggedNetworkValue`/Boolean/Number/String          | 2                               | 1 (`periodic`)                                    | ~67%                   |
| `LogDataReceiver` / `NT4Publisher` / `WPILOGWriter` | `putTable`→`put_table` in all 3 | `updateTable`, `defaultPathRio`/`defaultPathSim`  | partial                |
| `LogReplaySource` / `WPILOGReader`                  | 0                               | `updateTable`                                     | 0%                     |

**Net effect**: the current `lib_6107.pykit` public surface is a **mixed-convention API**. Roughly half of the classes
are fully snake_case, `Logger` and `LogValue` (two of the most fundamental, most-imported types) are almost entirely
untouched, and
`updateTable` survives unchanged in every class that has it. Anyone reusing this design in a fresh project should decide
up front whether to finish the migration or revert to a single consistent convention — the current state requires
per-class memorization.

## 5. Bug fixes (beyond naming)

- **Typo fix, half-applied.** Westwood's `LogDataReciever` (misspelled) and its file
  `logdatareciever.py` were corrected to `LogDataReceiver` / `logdatareceiver.py` in
  `lib_6107`. However, `Logger.addDataReciever(cls, reciever: LogDataReceiver)` was **not** updated to match — the
  method name and parameter name still carry the old typo, even though the type they accept was renamed. This is the
  most visible
  "half-finished cleanup" in the fork: a caller today writes
  `Logger.addDataReciever(WPILOGWriter())`, misspelling included, while passing a correctly-spelled `LogDataReceiver`
  instance.
- **`LoggedPowerDistribution.save_to_table()`** gained a `try/except` around all hardware reads (Westwood's version has
  none) — prevents FMS-related PDP/PDH JNI exceptions from crashing user code during a match (see §3).
- **`LoggedRobot.startCompetition()`** gained a `try/except` around the
  `Logger.periodicAfterUser(...)` call for the same FMS-compatibility reason (Westwood's version calls it unguarded).
- **`LoggedRobot.__init__`** gained a configurable `period` argument; Westwood hardcodes `default_period = 0.02` with no
  way to override it per-instance.

## 6. New capabilities beyond Westwood PyKit v1.0.5

- **`LogTracer`** (`logtracer.py`) — a two-level (`resetOuter`/`reset`/`record`/
  `recordTotal`) performance profiler that logs phase and total timings via
  `Logger.recordOutput("LogTracer/{prefix}/{action}MS", ...)`. Its own file header explicitly credits **"1757-Westwood
  Robotics"**, but cites their **`2026-Rebuilt`** robot-code repository
  (`https://github.com/1757WestwoodRobotics/2026-Rebuilt`) — a different codebase from the `PyKit` *library* covered
  everywhere else in this document. PyKit itself has no equivalent timing utility.
- **`LoggedMechanism2d` / `LoggedMechanismRoot2d` / `LoggedMechanismLigament2d` /
  `LoggedMechanismObject2d`** — a Python port of AdvantageKit's Java
  `org.littletonrobotics.junction.mechanism` package (verified present already in AdvantageKit `v26.0.2`:
  `LoggedMechanism2d`, `LoggedMechanismRoot2d`,
  `LoggedMechanismLigament2d`, `LoggedMechanismObject2d`). Method names were adapted to snake_case in the port
  (`getRoot`→`get_root`, `setBackgroundColor`→
  `set_background_color`, `logOutput`→`log_output`, `generate3dMechanism`→
  `generate3d_mechanism`), except `initSendable`, which must keep its exact name to satisfy the `ntcore.NTSendable`
  interface contract. Westwood PyKit v1.0.5 implements no mechanism-visualization capability at all — this closes a real
  feature gap against AdvantageKit (see `docs/akit-changes-to-date.md` and
  `docs/lib_6107-api-work-todo.md` §A for more detail).
- **`NetworkTableButton`** (`LoggedNetworkButton.py`) — wraps a `LoggedNetworkBoolean`
  in a `commands2.button.Trigger`, giving a dashboard-driven boolean that is both a usable `Trigger` (`onTrue`/
  `onFalse`/`whileTrue`) *and* automatically logged/replayed. No equivalent convenience class exists in Westwood PyKit,
  which only exposes the lower-level `LoggedNetworkBoolean`.

## 7. Documentation, type-hint, and performance polish (PEP 484 + general)

- Every public method in `lib_6107.pykit` carries a full Google-style docstring (Args/Returns/Raises/Side
  Effects/Example) — Westwood's originals are typically a one-line summary plus a terse `:param:`/`:return:` list
  (Sphinx/RST style, visible directly in the snippets quoted above). This is a substantial documentation investment
  beyond the naming work, valuable for any team porting this design.
- `LogValue` changed from a plain `@dataclass` (Westwood) to `@dataclass(slots=True)`
  (`lib_6107`) — a genuine memory/attribute-access performance change, consistent with this project's stated "improve
  performance" goal, and independent of the naming migration.
- Full PEP 484 type hints are present throughout `lib_6107.pykit`, including
  `Generic[T, V]` bounds, `Optional[...]`, and union types (e.g.
  `float | int` for `LoggedNetworkNumber`). Westwood's originals already had modest type hints on most signatures (it is
  not an untyped codebase), so this is more a matter of degree/consistency than a totally new capability.

## 8. Compatibility notes

- `.wpilog` file format compatibility is preserved: `wpilogconstants.extraHeader =
  "PyKit"` is byte-identical between the two implementations, so a `WPILOGReader`
  from either side can read a file produced by a `WPILOGWriter` from the other.
- `WPILOGWriter(filename, path)` — `lib_6107` already includes the `path` parameter Westwood added in `v1.0.5` (commit
  `27a6c98`, "allow custom folder location still with renaming"); there is no divergence to reconcile here.

## 9. Recommendations if reconciling with Westwood PyKit

1. **There is nothing to merge in right now.** Westwood's `main` is frozen at
   `v1.0.5` (confirmed empty `git log v1.0.5..HEAD` against the upstream remote). The appropriate process is periodic
   drift-checking against new upstream tags as they appear, not a continuous merge.
2. **Finish or abandon the PEP 8 migration deliberately.** `Logger` (1/12 methods)
   and `LogValue` (0/2) are the biggest outliers relative to the rest of the codebase's ~60-100% conversion rate. Given
   how central `Logger` is, batch this as one explicit, repo-wide rename (with a thin backward-compatible alias layer if
   any external callers exist) rather than letting it drift further.
3. **Fix `addDataReciever` first** — of everything catalogued here, this is the one place where the current code is
   *objectively worse* than either a clean rename or the original: the class was fixed, the entry point that takes it
   was not.
4. **Watch Westwood's unmerged branches** (`origin/real-hardware`,
   `origin/docs` — see `docs/westwood-pykit-changes-to-date.md` §4) for early signals of a future `v1.1.0`, but do not
   treat them as current public API.

## 10. References

- `docs/westwood-pykit-changes-to-date.md` (in-repo) — prior detailed analysis of the Westwood PyKit `v1.0.5` public API
  and upstream branch status.
- `docs/akit-changes-to-date.md` (in-repo) — prior detailed analysis of AdvantageKit's public API and its `v26.0.2` →
  current-`main` delta; used here to source the Mechanism2d provenance claim in §6.
- Source read directly for this comparison:
    - `src/lib_6107/pykit/**/*.py` (this repository, current working tree)
    - `D:\Source\repos\github\pykit` — local clone of
      [1757WestwoodRobotics/PyKit](https://github.com/1757WestwoodRobotics/PyKit),
      `main` @ commit `5d70664` (tag `v1.0.5`)
    - `D:\Source\repos\github\pykit-6107` — local clone of `https://github.com/6107/pykit`
      (confirmed identical to upstream `v1.0.5`, no divergent commits)
    - `D:\Source\repos\github\AdvantageKit` — local clone of
      [Mechanical-Advantage/AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit), used to confirm the
      `mechanism` package existed already at tag `v26.0.2`
    - `pyproject.toml` (this repository) — confirms no `robotpy-pykit` package dependency, i.e. `lib_6107.pykit` is a
      standalone in-tree fork, not a wrapped external dependency
- [1757WestwoodRobotics/PyKit](https://github.com/1757WestwoodRobotics/PyKit) — upstream repository this module was
  forked from.
- [1757WestwoodRobotics/2026-Rebuilt](https://github.com/1757WestwoodRobotics/2026-Rebuilt) — source of the `LogTracer`
  design, per its in-file credit comment (a robot-code repository, not the PyKit library).
- [AdvantageKit (Mechanical Advantage / FRC 6328)](https://github.com/Mechanical-Advantage/AdvantageKit/) — the Java
  framework both PyKit and `lib_6107.pykit`'s Mechanism2d port derive from.
- [WPILib Data Logging docs](https://docs.wpilib.org/en/stable/docs/software/telemetry/datalog.html) — origin of the
  `.wpilog` file format read/written by both implementations.
