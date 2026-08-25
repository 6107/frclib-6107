# WPILib 2027 / SystemCore Readiness — AdvantageKit vs. Westwood PyKit

> Audience: senior developers maintaining `lib_6107.pykit` (a Python port of Westwood
> PyKit's design) who need to know whether the upstream Python telemetry ecosystem is
> tracking AdvantageKit's move to **WPILib 2027** and the roboRIO's successor hardware
> target, **SystemCore**. This document does not change any `lib_6107` code — it is a
> status snapshot to inform planning.

## TL;DR

| Layer                                                                                            | 2027 / SystemCore work started?                                                                                                                                                                  | Evidence                                                   |
|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| **AdvantageKit** (Java, `Mechanical-Advantage/AdvantageKit`)                                     | **Yes — substantial, already merged to `main`.** 37 commits since `v26.0.2` migrating package names, native build target, and telemetry schema.                                                  | `akit-changes-to-date.md` (this repo, prepared 2026-07-29) |
| **Westwood PyKit** (`1757WestwoodRobotics/PyKit`, the library `lib_6107.pykit` ports)            | **No.** Zero commits on `main` since `v1.0.5`; no 2027/SystemCore reference anywhere in any branch, including the two unmerged experimental branches.                                            | Verified directly against local clone, see §3              |
| **RobotPy / `mostrobotpy`** (the WPILib-Python bindings PyKit and `lib_6107` both run on top of) | **Yes — in progress upstream, but not yet the default install.** Alpha tags `2027.0.0a2` … `2027.0.0a6.post4` exist; dedicated SystemCore CI and native packaging commits date back over a year. | GitHub API evidence, see §4                                |
| **`lib_6107.pykit`** (this repository)                                                           | No — matches PyKit's current (pre-2027) shape throughout; still entirely roboRIO-oriented (`ROBORIO_STATIC`, `defaultPathRio`, FPGA-era `LoggedSystemStats` fields).                             | Verified directly against `src/lib_6107/**`, see §5        |

**Bottom line:** AdvantageKit (Java) is meaningfully **ahead**. Westwood PyKit — the project `lib_6107.pykit` is modeled
on — has done **no work at all** toward WPILib 2027/SystemCore, and isn't yet blocked on doing so, because the RobotPy
packages it depends on haven't shipped a stable 2027 release either (only alpha tags exist, not yet installable via a
plain `pip install robotpy`). PyKit is not "behind" AdvantageKit in the sense of missing a deadline — the whole Python
side of the ecosystem is simply one layer further from the migration than the Java side, because RobotPy's C++/native
HAL bindings must land 2027 support before any pure-Python framework built on top of
`wpilib`/`hal`/`ntcore` (PyKit or `lib_6107.pykit`) has anything to react to.

---

## 1. What "WPILib 2027 / SystemCore" means (recap)

Per `akit-changes-to-date.md` §3, WPILib's 2027 season introduces two coupled changes:

1. A **Java package rename**: `edu.wpi.first.*` → `org.wpilib.*` (Java-only; Python package names are unaffected since
   RobotPy's import paths — `wpilib`, `hal`,
   `ntcore`, `wpimath`, `wpiutil` — were never namespaced under `edu.wpi.first`).
2. A **hardware target change**: the roboRIO 2 is being succeeded by **SystemCore**, a Linux/systemd-managed compute
   platform (native cross-compile target
   `linuxsystemcore` replacing `linuxathena`; console logs now come from
   `journalctl`/`robot.service` instead of file-tailing; a richer system-telemetry model — faults, per-interface network
   stats, onboard IMU — replaces the old FPGA/rail-voltage stat set).

Both changes are still "alpha" as of this writing: AdvantageKit's `main` branch tracks
`wpilibVersion = 2027.0.0-alpha-6`; it has not yet cut a `v27.x` tagged release.

## 2. AdvantageKit's progress (Java) — already substantial

Already documented in full in `akit-changes-to-date.md`; summarized here for direct comparison:

- Package imports migrated throughout (`edu.wpi.first.wpilibj.*` →
  `org.wpilib.framework.*`/`org.wpilib.system.*`/`org.wpilib.hardware.*`).
- Native cross-compilation retargeted to `linuxsystemcore`; `linuxarm32` dropped.
- `LoggedSystemStats`' schema rewritten for SystemCore (fault/fault-count model, per-interface network stats, onboard
  IMU) — **not** backward compatible with old roboRIO-era log field names.
- `ConsoleSource` rewritten to shell out to `journalctl` for the `robot.service`
  systemd unit instead of tailing a roboRIO log file.
- Three breaking Java API renames forced by WPILib's `Measure` types becoming
  `Record`s in 2027: `recordOutput`→`recordOutputMeasure`, `LogTable.put`→`putMeasure`,
  `LogTable.get`→`getMeasure` (`MutableMeasure` support dropped entirely).
- `LoggedPowerDistribution.getInstance(...)` gained a `busID` parameter for multi-CAN-bus SystemCore hardware, and its
  no-arg overload no longer lazily creates a default instance.

This is a coordinated, deliberate migration effort — not incidental drift — carried out by the same team (6328
Mechanical Advantage) that also builds AdvantageKit, giving them first-party visibility into WPILib's 2027 direction.

## 3. Westwood PyKit's progress (Python) — none found

The local clone of `1757WestwoodRobotics/PyKit` was re-examined specifically for any 2027/SystemCore activity, across
**every** branch and the full commit history:

```
git log --all --oneline -i --grep="systemcore"   → (no matches)
git log --all --oneline -i --grep="2027"         → (no matches)
git grep -il "systemcore" origin/main -- .       → (no matches)
git grep -il "systemcore" origin/real-hardware -- .  → (no matches)
```

`main` is still exactly at the `v1.0.5` tag (as previously reported in
`westwood-pykit-changes-to-date.md`), with dependencies pinned to
`>=2026.1.1` (2026-season WPILib) — no `2027`-anything appears in `../../pyproject.toml`.

The two unmerged remote branches were re-checked with this question specifically in mind:

- **`origin/docs`** (tip `b25dc99`, "usage docs") — a small, older documentation branch; no relation to 2027/SystemCore.
- **`origin/real-hardware`** (tip `7d2be3e`, "hacky log stop") — previously flagged as
  "exploratory/early-stage work." Re-examined here: its tip commit is dated **2025-11-11**, i.e. **older than `main`'s
  tip** (2026-03-23), and its
  `../../pyproject.toml` pins `wpilib>=2025.3.2.2` (2025-season WPILib) at version
  `0.1.3b3` — an earlier, lower version number than the released `1.0.5`. This branch is a stale pre-1.0 experiment
  (moving the package out of `../../src`, dropping template projects/doc scaffolding), not forward-looking 2027 work. It
  should not be read as
  "PyKit's SystemCore branch" — it predates the current release entirely.

**Conclusion: PyKit (the upstream project) has not started any 2027/SystemCore work, on any branch, as of this
writing.**

## 4. The layer underneath both: RobotPy / WPILib-Python bindings

This is the most important nuance for planning purposes. PyKit and `lib_6107.pykit`
are pure-Python frameworks built **on top of** `wpilib`/`hal`/`ntcore`/`wpimath`
(the RobotPy project, repository `robotpy/mostrobotpy`) — they do not talk to hardware or the native HAL directly. So
the relevant question isn't just "has PyKit started 2027 work" but "*could* it have, yet" — i.e., has the layer
underneath it started.

Checked directly against the public `robotpy/mostrobotpy` GitHub repository:

- **`pip install robotpy` today resolves to `2026.2.2`** (confirmed via the PyPI JSON API) — there is no `2027` release
  available as the default/stable install.
- **However, alpha tags already exist and are actively being cut**: `2027.0.0a2`,
  `2027.0.0a3`, `2027.0.0a4`, `2027.0.0a5`, `2027.0.0a5.post1`, `2027.0.0a6`,
  `2027.0.0a6.post1` through `.post4` — i.e. RobotPy is iterating through 2027 alphas in lockstep with mainline WPILib's
  own alpha cadence, just not yet promoting one to a stable/default release.
- **A live GitHub issue (`robotpy/mostrobotpy#297`, filed 2026-07-28, two days before this document) explicitly
  reproduces a bug "with both RobotPy 2026 and 2027 alpha 6"** — confirming RobotPy 2027 alpha builds are already
  installable and being dogfooded by RobotPy's own maintainers today, even though most teams are still on
    2026.
- **SystemCore-specific native/CI work has been underway for over a year**:
  a commit titled **"Add Systemcore CI"** (authored 2025-05-25, committed 2025-07-23) added continuous-integration
  coverage for the SystemCore native target, and a more recent commit, **"Add no-op .pc file for mrclib on systemcore"**
  (2026-06-15), continues that native-packaging work — both roughly a year and about six weeks before this document,
  respectively, i.e. this has been a sustained, ongoing effort, not a one-off.
- No evidence of a Python-side equivalent to AdvantageKit's `Measure`→`Record`
  collision (that is a Java-specific consequence of `Measure` becoming a `Record`); Python has no analogous
  type-collision risk to migrate around.

**Conclusion: the WPILib-Python native/binding layer (RobotPy) is already actively tracking WPILib 2027 and SystemCore —
it is not idle — but it has not yet reached a stable, default-install release.** This is analogous to where
AdvantageKit's own
`main` branch sits (alpha-tracking, pre-release) — the two ecosystems' *underlying platform* layers are roughly
contemporaneous. What differs is that AdvantageKit **is** the framework doing the migration work itself, whereas for
Python, the migration work is happening one layer down (in RobotPy), and PyKit — the layer that would need to react to
schema/API changes analogous to AdvantageKit's — simply hasn't needed to yet, because RobotPy hasn't shipped anything
requiring a reaction.

## 5. Where this leaves `lib_6107.pykit`

Directly verified against `src/lib_6107/**` in this repository: there is currently **no** 2027/SystemCore-related code,
comment, or dependency pin anywhere in
`lib_6107` — it mirrors PyKit's pre-2027 shape exactly:

- `constants.py`'s `NetworkConstants` still models `ROBORIO_STATIC`/`ROBORIO_MDNS`
  addressing only (no SystemCore equivalent hostname/IP scheme is known yet).
- `pykit/wpilog/wpilogwriter.py`'s path constant is still named in the roboRIO idiom (mirroring PyKit's pre-rename
  `defaultPathRio`, itself the same name AdvantageKit only recently renamed to `defaultPathRobot` per
  `akit-changes-to-date.md`). This is a **cheap, safe, purely cosmetic change** `lib_6107` could make now, ahead of
  PyKit itself, if desired — renaming is zero-risk and doesn't require SystemCore to exist. It is not part of this
  document's scope (no code changes are being made here).
- `pykit/inputs/loggablesystemstats.py` still logs the FPGA/rail-voltage-era field set (FPGA version/revision, serial
  number, brownout, RSL state) — the same
  "pre-2027" shape as AdvantageKit's `v26.0.2`, not its current `main`. This tracks cleanly with §4's finding: neither
  PyKit nor RobotPy has shipped a stable SystemCore telemetry schema for `lib_6107` to port yet.
- `pykit/loggedrobot.py`'s docstring explicitly still claims roboRIO-specific timing characteristics ("±0.1ms jitter on
  real roboRIO").

None of this represents `lib_6107` "falling behind" its own upstream (PyKit) — it is current with PyKit's actual
released shape. It does mean that **when** PyKit (or RobotPy) eventually does SystemCore work, `lib_6107.pykit` will
have a reasonably large, mostly mechanical porting task waiting (schema rename, new fault/network/IMU system-stats
fields, possible `WPILOGWriter` path-constant rename), similar in shape to the Java delta already fully catalogued in
`akit-changes-to-date.md` §3.1.

## 6. Head-to-head: who is ahead, who is behind, by area

| Area                                                    | AdvantageKit (Java)                                         | Westwood PyKit                                     | RobotPy (the layer under PyKit)                                                             | `lib_6107.pykit`                                                                                   |
|---------------------------------------------------------|-------------------------------------------------------------|----------------------------------------------------|---------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| Package/namespace migration for 2027                    | ✅ Done (`org.wpilib.*` throughout)                         | N/A (Python has no equivalent namespace collision) | N/A                                                                                         | N/A                                                                                                |
| SystemCore native/cross-compile target                  | ✅ Done (`linuxsystemcore`)                                 | ❌ Not started                                     | 🟡 In progress since 2025-05, alpha-only                                                    | ❌ Not started (no native code of its own)                                                         |
| SystemCore system-telemetry schema (faults/network/IMU) | ✅ Shipped on `main`                                        | ❌ Not started                                     | Unclear — not confirmed from public evidence examined                                       | ❌ Still logs pre-2027 FPGA-era fields                                                             |
| Console log capture for systemd/SystemCore              | ✅ Shipped (`journalctl`)                                   | ❌ Not started                                     | N/A (not PyKit's layer)                                                                     | ❌ Still `stdout`/`stderr` wrapping only (portable either way, see `../lib_6107-api-work-todo.md`) |
| Multi-CAN-bus PDP/PDH addressing (`busID`)              | ✅ Shipped (breaking change)                                | ❌ Not started                                     | Unclear                                                                                     | ❌ Not started                                                                                     |
| Stable, tagged 2027 release available to consumers      | ❌ Still alpha (`2027.0.0-alpha-6`, not yet tagged `v27.x`) | ❌ N/A — no 2027 work of any kind                  | ❌ Alpha tags only (`2027.0.0a6.post4`); `pip install robotpy` still resolves to `2026.2.2` | ❌ N/A                                                                                             |

**Reading the table**: AdvantageKit is ahead of *everyone* in the Python stack on 2027/SystemCore readiness, but it is
itself still pre-release (alpha) for this work — so even AdvantageKit's own users can't fully rely on this yet either.
Within the Python stack, RobotPy is the only layer showing any 2027/SystemCore activity at all; PyKit and (by
inheritance) `lib_6107.pykit` are both still squarely targeting the 2026/roboRIO-era world, and have no visible blocker
or in-progress work to change that today, because there is nothing stable underneath them yet to port to.

## 7. Recommendations

- **No urgent action is needed.** There is nothing in `lib_6107.pykit` to "catch up"
  on yet — PyKit itself, the project it mirrors, hasn't started, and the Python runtime layer (RobotPy) hasn't shipped a
  stable target to build against.
- **Treat this as a "watch list" item, re-checked periodically** (e.g. alongside the existing
  `akit-changes-to-date.md` refresh cadence), specifically watching for:
    1. A `robotpy`/`wpilib` release on PyPI with a `2027.x` (non-alpha) version.
    2. Any commit or branch in `1757WestwoodRobotics/PyKit` referencing `2027` or
       `systemcore`.
    3. AdvantageKit cutting an actual `v27.x.y` tagged release (currently still on
       `main`/alpha) — a strong signal the schema in §5 has stabilized enough to port.
- **When PyKit/RobotPy do start this work**, expect the porting effort for
  `lib_6107.pykit` to closely resemble the already-documented AdvantageKit delta in
  `akit-changes-to-date.md` §3.1 — i.e. a `LoggedSystemStats`-equivalent schema rewrite (`loggablesystemstats.py`)
  and a cosmetic path-constant rename (`wpilogwriter.py`), with the core `Logger`/`LogTable`/`processInputs` contract
  expected to remain stable (AdvantageKit's own §4 recommendation notes this same core abstraction survived its 2027
  migration unchanged).
- **The one thing that *could* be done today, independent of SystemCore actually existing**, is the cosmetic
  `defaultPathRio`→`defaultPathRobot`-style rename already adopted by AdvantageKit — purely a naming clean-up with no
  behavioral dependency on SystemCore hardware being available. Flagged here for awareness only; no code changes were
  made as part of this document per the request scope.

## 8. References

**In-repo companion documents**

- `akit-changes-to-date.md` — full detail on AdvantageKit's `v26.0.2` → `main`
  delta, the primary source for §2 and §6 of this document.
- `westwood-pykit-changes-to-date.md` — full detail on PyKit's public API and its (lack of) changes since `v1.0.5`,
  the primary source for §3.
- `../lib_6107-api-work-todo.md` — prior API-level comparison of `lib_6107.pykit`
  against both PyKit and AdvantageKit, including the pre-existing note (§5 there)
  that "RobotPy/WPILib-Python has not migrated to the 2027 package layout" — refined and superseded in nuance by §4 of
  this document (RobotPy *has* alpha-stage 2027 work, just not a stable release).

**External sources consulted directly for this document**

- [`1757WestwoodRobotics/PyKit`](https://github.com/1757WestwoodRobotics/PyKit) — local clone; `git log --all`,
  `git branch -a`, `git grep` across `origin/main`,
  `origin/docs`, `origin/real-hardware`; `../../pyproject.toml` on each branch.
- [`Mechanical-Advantage/AdvantageKit`](https://github.com/Mechanical-Advantage/AdvantageKit)
  — local clone underlying `akit-changes-to-date.md`.
- [`robotpy/mostrobotpy`](https://github.com/robotpy/mostrobotpy) — GitHub REST API:
  `/branches`, `/tags`, `/search/commits?q=systemcore`, and issue
  [`#297`](https://github.com/robotpy/mostrobotpy/issues/297) (filed 2026-07-28, reproduces a bug against "RobotPy 2026
  and 2027 alpha 6").
- [PyPI `robotpy` package JSON API](https://pypi.org/pypi/robotpy/json) and
  [PyPI `wpilib` package JSON API](https://pypi.org/pypi/wpilib/json) — confirms
  `2026.2.2` as the latest stable/default-installable release as of this writing.
