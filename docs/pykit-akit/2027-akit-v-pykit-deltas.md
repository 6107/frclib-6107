# WPILib 2027 / SystemCore Readiness — AdvantageKit vs. Westwood PyKit

> **Status snapshot as of 2026-10-25** (previous snapshot: 2026-07-29 / 2026-08-25).
>
> Audience: senior developers maintaining `lib_6107.pykit` (a Python port of Westwood
> PyKit's design) who need to know whether the upstream Python telemetry ecosystem is
> tracking AdvantageKit's move to **WPILib 2027** and the roboRIO's successor hardware
> target, **SystemCore**. This document does not change any `lib_6107` code — it is a
> status snapshot to inform planning ahead of the January 2027 build season.
>
> **Comparison caveat:** AdvantageKit (akit) is being compared at its *current* `main`
> (a 2027 alpha), while Westwood PyKit has not changed since March 2026 (`v1.0.5`). This is
> effectively a **2027-alpha API vs. a 2026-season API** comparison.

## TL;DR

| Layer                                                        | 2027 / SystemCore work started?                                                                                                                                                                                                   | Change since last snapshot                                                                                                  |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| **AdvantageKit** (Java, `Mechanical-Advantage/AdvantageKit`) | **Yes — substantial and accelerating.** `main` is 70 commits past `v26.0.2` on WPILib `2027.0.0-alpha-7`; tagged alphas `v27.0.0-alpha-4` … `-7` now exist. Four feature branches are in flight, three of them not yet in `main`. | 37 → 70 commits; alpha tags published; `LoggedOpModeRobot` merged; XZ logs, vendor-log capture, thread-safe outputs pending |
| **Westwood PyKit** (`1757WestwoodRobotics/PyKit`)            | **No.** Still `v1.0.5` (2026-03-23). Zero commits in ~7 months, three open issues/PRs with no maintainer response, no 2027/SystemCore reference, no fork with 2027 work (see Appendix A).                                         | Nothing changed                                                                                                             |
| **RobotPy / `mostrobotpy`**                                  | **Yes — actively.** `2027.0.0a7` published to PyPI 2026-09-11 (about a week after WPILib alpha-7); commits landing daily through 2026-10-25. Stable is still `2026.2.2`.                                                          | a6.post4 → a7; Python teams are alpha-testing on Chief Delphi                                                               |
| **`lib_6107.pykit`** (this repository)                       | No — still the PyKit 1.0.x / roboRIO-era shape.                                                                                                                                                                                   | Nothing changed (by design)                                                                                                 |

**Bottom line**

1. **AdvantageKit is pulling away.** Since July it has gone from "migrating to 2027" to "shipping 2027 features":
   OpMode robot base class, built-in alerts, radio logging, receiver-queue protection, loop-overrun configuration,
   Windows ARM64/signed native binaries, and (on branches) XZ-compressed logs, vendor log capture, and thread-safe
   `recordOutput`.
2. **PyKit is not keeping up.** It is a faithful port of the **26.0.x-era** core contract (`processInputs`,
   `recordOutput`, `LogTable`, replay) but is missing roughly 15 post-`v26.0.2` akit features and has had **no
   maintenance since March**. See §6 for the call.
3. **The RobotPy layer underneath is moving**, so the Python 2027 migration is *possible* now; nobody upstream is
   doing the PyKit side. For planning, assume **`lib_6107.pykit` will have to carry its own 2027 port** (§11).
4. **No independent Python AdvantageKit implementation exists** beyond PyKit and `lib_6107` (§8).

---

## 1. What "WPILib 2027 / SystemCore" means (recap)

Per `akit-changes-to-date.md` §3, WPILib's 2027 season introduces coupled changes:

1. A **Java package rename**: `edu.wpi.first.*` → `org.wpilib.*` (Java-only; RobotPy import paths — `wpilib`, `hal`,
   `ntcore`, `wpimath`, `wpiutil` — are unaffected).
2. A **hardware target change**: the roboRIO 2 is succeeded by **SystemCore**, a Linux/systemd-managed platform
   (`linuxsystemcore` replaces `linuxathena`; console logs come from `journalctl`; a richer system-telemetry model —
   faults, per-interface network stats, onboard IMU — replaces the FPGA/rail-voltage stat set).
3. **API replacements** (Chief Delphi thread 519900, §9): the Telemetry / Tunable APIs replace `SmartDashboard` and
   `Sendable`; `SmartDashboard`/`Shuffleboard`/RobotBuilder/PathWeaver are retired; **OpModes** and **Commands v3**
   are introduced; and the **field coordinate origin moves to field center, rotated 180°** (relevant to any
   `lib_6107` code that flips poses between alliances).

As of 2026-10-25 WPILib has published `v2027.0.0-alpha-7` (2026-09-01) as the latest 2027 build; **no 2027 beta has
shipped yet**. AdvantageKit's own beta is explicitly planned for "shortly after the WPILib beta". Alpha builds run
**only on SystemCore**, not roboRIO.

## 2. AdvantageKit `main` — progress since the last snapshot

`main` tip: `dad7620` (2026-10-23); `akit/build.gradle.kts` pins `wpilibVersion = "2027.0.0-alpha-7"`. Tags
`v27.0.0-alpha-4` (06-22), `-5` (09-01), `-6` (09-27), `-7` (10-23) exist; `v26.0.2` (2026-03-19) remains the latest
stable. (AKit's alpha numbering is offset from WPILib's: akit alpha-5 targeted WPILib alpha-7, and later akit alphas
continue to track it.)

Carried over from the previous snapshot (see §2 of the 2026-07 version / `akit-changes-to-date.md`): package migration,
`linuxsystemcore` native target, SystemCore `LoggedSystemStats` schema, `journalctl`-based `ConsoleSource`,
`recordOutputMeasure`/`putMeasure`/`getMeasure` renames, and `LoggedPowerDistribution` `busID`.

**New on `main` since 2026-07-29** (≈33 commits, mostly from Jonah Bonner):

| Area                    | What landed                                                                                                                                                     | Reference               |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| OpMode support          | `LoggedOpModeRobot` (849 lines) alongside `LoggedRobot`                                                                                                         | #283                    |
| WPILib alignment        | Update for WPILib alpha-7; `LoggedDashboardChooser`, `LoggedMechanism2d`, alert-logger updates                                                                  | #277                    |
| Built-in alerts         | Logger, `ConsoleSource`, and `WPILOGWriter` raise their own alerts with fault-state getters; default alert-group sorting                                        | `00ce6d0`               |
| Receiver queue          | Alert with 30 s debounce and initial state; **in replay, block the main thread instead of dropping data** when the queue fills; receiver-thread diagnostics     | `93ef5c6`, `d100dc4`    |
| Loop overruns           | Configurable overrun-warning timeout in `LoggedRobot`/`LoggedOpModeRobot` (off by default because AKit already logs timing); default watchdog timeout fixes     | `565a41b`               |
| System stats            | Unit metadata (including the new IMU), AdvantageKit and WPILib versions logged                                                                                  | `dad7620`               |
| Radio logging           | Works without a configured team number (uses the Ethernet IP)                                                                                                   | `704fb92`               |
| Replay                  | Replay of **nanosecond-timestamp** WPILOGs; **replay disallowed on the real robot**; replay-watch fix for alpha 7                                               | #278, `f588d2e`         |
| NT publishing           | `mutable` NT property set when publishing                                                                                                                       | `7e18b9b`               |
| Log writing             | USB log writing fix on SystemCore (`USBDriveUtil`); WPILOGWriter flush-rate fix; match-log renaming only includes event/match when FMS attached and may repeat | #286, `269ca6e`, `eac1f9b` |
| Platform                | Windows ARM64 builds; macOS/Windows native binary code signing; GitHub Actions update                                                                            | #279, #280, #281        |
| Docs                    | Replay/Gradle-property docs                                                                                                                                      | #284                    |

AKit's "What's New in 2027" outline (on branch `2027-beta-docs`) lists: SystemCore compatibility, OpMode integration,
2027 template projects, **WPILOGXZ** compression, **vendor log capture**, built-in logger alerts, performance
management (receiver diagnostics, configurable overrun, replay waits for receivers), Java 25, Windows ARM64, and
signed binaries. Two of those headline items (**WPILOGXZ**, **vendor log capture**) are **not in `main` yet**, which
leads to §3.

## 3. AdvantageKit branches active in the last ~2 months (since 2026-08-25)

Ahead/behind counts are against `main`. **Merge-detection caveat:** AKit squash-merges, so `git cherry` reports `+`
even for work that landed. "In `main`?" below was determined by checking that the branch's new files exist on `main`
and by matching PR numbers in `main`'s log.

| Branch                | Last commit | Ahead / behind | In `main`?                                          |
|-----------------------|-------------|----------------|-----------------------------------------------------|
| `wpilogxz`            | 2026-10-24  | +10 / 0 ¹      | **No**                                              |
| `2027-beta-docs`      | 2026-10-16  | +5 / −7        | **No**                                              |
| `vendor-log-capture`  | 2026-10-14  | +3 / −7        | **No**                                              |
| `output-multithreading` | 2026-10-14 | +1 / −11       | **No**                                              |
| `wpilog-flush-fix`    | 2026-10-13  | +2 / −18       | **Partly** — squashed as #286; design superseded    |
| `loggedopmoderobot`   | 2026-09-30  | +4 / −22       | **Yes** — #283 (tip differs only by later refinement) |
| `update-actions`      | 2026-09-27  | +1 / −23       | **Yes** — #281                                      |
| `code-signing`        | 2026-09-27  | +4 / −24       | **Yes** — #280                                      |
| `add-windows-arm64`   | 2026-09-27  | +3 / −25       | **Yes** — #279                                      |
| `wpilib-alpha-7`      | 2026-09-01  | +9 / −32       | **Yes** — #277 / tag `v27.0.0-alpha-5`              |

¹ `wpilogxz` has 10 commits ahead but only **5 unique** ones; the rest are "Merge branch 'main' into wpilogxz". It
already contains `main`'s tip, so it is conflict-free and effectively ready to merge.

### 3.1 `wpilogxz` — XZ-compressed WPILOG logs (not merged; most active)

- Adds the **`.wpilogxz`** format: new `WPILOGEncoder` (227 lines) and `QueuedOutputStream` (65 lines), a rewritten
  `WPILOGWriter` (≈564 lines changed), and a reader update (+37).
- API: `withXZCompressionPreset()` (default preset: MIN). Bundles `org.tukaani:xz:1.11` into the jar via Gradle.
- Also: flush WPILOGs by **log timestamps** rather than wall-clock, an expanded receiver-queue warning, buffered
  encoded data, and an FMS-rename fix.
- This pairs with the `main` change that makes replay block rather than drop when the queue is full — the stated
  motivation is slow "compressed log" receivers.
- **Outlook:** listed in What's New, so expect it in the 2027 beta.
- **Relevance to Python:** a `.wpilogxz` log will **not** be readable by PyKit's/`lib_6107`'s `WPILOGReader`.
  Python's stdlib `lzma` can decode XZ, so reader support is cheap; **writer support is optional** (CPU cost on the
  robot is the real concern given the <20 ms loop target).

### 3.2 `vendor-log-capture` — capture CTRE/vendor logs into the AKit log (not merged)

- New `VendorLogCapture.java` (347 lines). A 200 ms `Notifier` tails vendor log files (e.g. CTRE hoot/signal logs)
  staged in a directory such as `/U/logs/`, copying them into the AKit log with a 10 MB queue per log.
- New `Logger.setVendorLogDirectory()` / `disableVendorLogCapture()`, a `Logger/VendorLogMS` timing entry, and "don't
  publish child logs to NT". Vendor logging must be initialized **after** the AK logger.
- Corresponds to the Chief Delphi thread "AdvantageKit logging vs CTRE hoot logging" (§9). Appears intended to replace
  the "just disable `SignalLogger`" workaround that both AKit and `lib_6107` use today.
- **Relevance to Python:** the `Robot` base in `lib_6107` disables `SignalLogger`/`StatusLogger` at startup; this
  feature could change that policy, but it is **Java-only, unmerged, and Phoenix-dependent** — monitor only.

### 3.3 `output-multithreading` — thread-safe `recordOutput` (not merged)

- Background-thread `recordOutput` calls go into an **async queue drained every cycle** (`entry.drainAsyncQueue()`).
  `processInputs` remains main-thread only (other threads get a no-op plus a warning). Adds `ThreadingTest` and
  rewrites the multithreading docs, **reversing the old "not thread-safe" guidance**.
- **Relevance to Python:** high for vision/odometry worker threads. PyKit's `Logger` has **no** such protection (its
  `threading.Lock` guards only the console-capture stream), so any off-thread `recordOutput` is unsafe today in both
  PyKit and `lib_6107`. With Python 3.14's free-threading work, this matters more over time.

### 3.4 `2027-beta-docs` — documentation prep for the beta (not merged)

- Rewrites What's New 2027, removes roboRIO references, updates installation/template-project docs, and fixes
  contributing/Java-version notes plus small `native.gradle` / `system_reader.h` tweaks.
- **Use:** the best single outline of what the 2027 beta will contain. Its existence signals the beta is being staged.

### 3.5 `wpilog-flush-fix` — USB log fix (merged, design superseded)

- Squash-merged as #286 (adds `USBDriveUtil`). The branch's `WPILOGWriter` is more complex than `main`'s (≈41 lines
  larger); `main` adopted a simpler flush-rate fix (`269ca6e`) and match-log renaming (`eac1f9b`) instead. Treat the
  branch as obsolete.

### 3.6 `loggedopmoderobot` — OpMode support (merged)

- `LoggedOpModeRobot` (849 lines) plus `LoggedRobot`/`Logger` changes; merged as #283. jonahb55 (Chief Delphi post
  509227 #32) says it **ships with the 2027 beta, shortly after the WPILib beta**; dev builds are available from the
  GitHub Actions offline Maven repo with the vendordep version set to `dev`.
- **Relevance to Python:** OpModes are a new WPILib robot-structure concept; neither PyKit's `LoggedRobot` nor
  `lib_6107`'s `Robot` has an OpMode path. This is the biggest *structural* gap that will appear.

### 3.7 Platform/CI branches (all merged)

`add-windows-arm64` (#279), `code-signing` (#280), `update-actions` (#281), `wpilib-alpha-7` (#277). No Python
impact.

**Older/idle branches** (no activity in the window; one line each): `update-docusaurus`, `fix-builds-older-clang`
(2026-06-11); `wpilib-alpha-6` (2026-06-18, merged); `fix-mutable-measures`, `check-sim-extensions` (Dec 2025);
`unit-metadata`, `pbtest` (Oct 2025); `debazel` (merged); legacy 2023 `ns-dev*` branches.

## 4. Westwood PyKit's progress (Python) — none

Re-examined 2026-10-25 against fresh clones of `1757WestwoodRobotics/PyKit`:

- `main` is still `v1.0.5` (2026-03-23); **no commits in ~7 months**. PyPI `robotpy-pykit` is `1.0.5`.
- Last releases: 1.0.2 (hang-on-exit fix, Mike Stitt, #14), 1.0.3 (prevent `LoggedDashboardChooser` singleton),
  1.0.4 (WPILOG writer errors no longer crash the robot), 1.0.5.
- **Open, unanswered (0 comments):** #16 missing stub files (2026-02-11); **#17 PR "Get sim, sim replay, deploy and
  deploy replay to work"** (MikeStitt, 2026-04-16); #18 repeated CAN errors with PDP 2.0 (2026-05-22). Older open
  issues (#5–#9: swerve/vision templates, logged radio, `Mechanism2d` logging, usage docs) are also untouched.
- 13 stars, 4 forks (EmDash00, `6107/PyKit`, MikeStitt, agaddis02) — **only one has recent commits** (EmDash00's
  `pythonize` branch: tooling/formatting only, Appendix A), so there is
  no community 2027 work hiding in forks.
- Branches `docs` (2026-01-08) and `real-hardware` (2025-11-11) are unchanged; **no mention of "2027" or
  "SystemCore"** anywhere in any branch or history.
- Maintainer statement (Chief Delphi 508084, 2026-03-06): no MagicBot integration planned for 2026, "maybe as a
  summer project". There is **no public 2027 commitment**.

## 5. The layer underneath both: RobotPy / WPILib-Python bindings

- **Stable `pip install robotpy` / `wpilib` is still `2026.2.2`** (March 2026).
- **2027 alphas are shipping:** `2027.0.0a2`, `a4`, `a5`, `a5.post1`, `a6`, `a6.post1`–`.post4`, and **`a7`
  (uploaded 2026-09-11, ~10 days after WPILib alpha-7)**. `robotpy-commands-v2` carries matching 2027 alpha
  versions.
- `robotpy/mostrobotpy` has commits **every few days through 2026-10-25** (CI/ccache work, SystemCore packaging).
- Chief Delphi 525037 "Python Readiness for Systemcore?": Joe_Ross confirms several Python teams are in the alpha
  test; auscompgeek notes the Phoenix tools preview already generates a 2027 alpha-7 Python project.
- Chief Delphi 522584: virtuald states there are **no plans for asyncio / Commands v3 coroutine support** in
  RobotPy (pointing at mostrobotpy PR #161 and robotpy-commands-v2 PR #12). Python teams stay on Commands v2 shape.
- **Conclusion:** the binding layer is ahead of where this document's previous snapshot left it (a6.post4 → a7) and is
  usable for alpha testing, so "nothing stable underneath to port to" is **no longer a valid reason** for PyKit's
  inactivity. A stable RobotPy 2027 release is still awaiting WPILib's beta/release.

## 6. How well is PyKit keeping up with the AdvantageKit API?

### Verdict

**Not well, and the gap is widening.** PyKit `v1.0.5` is a faithful port of akit's **26.0.x-era core contract**
(`Logger`, `LogTable`, `processInputs`/`recordOutput`, WPILOG reader/writer, NT4 publisher, replay, `AlertLogger`,
unit metadata, DS/PDP/system-stats inputs). Against akit `main` it lacks roughly 15 features added after `v26.0.2`,
and it carries most of the pre-existing deltas catalogued in `2026-akit-v-pykit-deltas.md` (no RLOG, no
`runEveryN`, no `registerURCL`, no console-capture toggle, no `getReceiverQueueFault`, no
`AdvantageScopeOpenBehavior`, `Measure`/Protobuf/enum overloads collapsed into one `recordOutput`).

Rating by layer:

| Layer                                  | Rating                | Rationale                                                                                           |
|----------------------------------------|-----------------------|-----------------------------------------------------------------------------------------------------|
| Core log contract (replay semantics)   | 🟢 Keeping up         | `processInputs`/`recordOutput`/`LogTable`/WPILOG format unchanged in akit's 2027 work.               |
| 2026-season feature parity             | 🟡 Mostly there       | Alerts, unit metadata, FMS rename, overrun print present; several 26.0.x conveniences missing.      |
| 2027 / SystemCore features             | 🔴 Not started        | No SystemCore stats, OpMode, XZ, nanosecond-replay, radio, queue alert, thread safety.              |
| Maintenance / responsiveness           | 🔴 Dormant            | 0 commits in ~7 months; open PR #17 and issues #16/#18 unanswered; no 2027 plans stated.            |

**Planning assumption:** treat PyKit as **unmaintained for the 2027 cycle** unless a commit appears. Do not wait on it.

### Feature-by-feature gap table (akit `main` vs. PyKit `v1.0.5` vs. `lib_6107.pykit`)

| akit feature (post-`v26.0.2` unless noted)                       | PyKit `v1.0.5`                                              | `lib_6107.pykit`                          | Port effort |
|------------------------------------------------------------------|-------------------------------------------------------------|-------------------------------------------|-------------|
| SystemCore `LoggedSystemStats` (faults, network, IMU)            | ❌ pre-2027 FPGA fields                                      | ❌ same                                    | M — blocked on RobotPy HAL surface |
| AdvantageKit/WPILib version in system stats                      | ❌                                                           | ❌                                         | S |
| Unit metadata on outputs                                         | ✅ (`recordOutput(key, value, unit)`)                        | ✅                                         | — |
| `AlertLogger` / alert logging                                    | ✅                                                           | ✅                                         | — |
| **Built-in logger alerts** (Logger/Console/WPILOGWriter)         | ❌                                                           | ❌                                         | S |
| Receiver-queue alert + replay blocks instead of dropping         | ❌ (no queue fault/getter)                                   | ❌                                         | S–M |
| Radio logging (works without team number)                       | ❌ (PyKit issue open)                                        | ❌                                         | S |
| Configurable loop-overrun warning                                | 🟡 `Watchdog` + `printOverrunMessage`, not configurable      | 🟡 same                                    | S |
| Nanosecond-timestamp WPILOG replay                               | ❌ not verified/likely                                       | ❌                                         | S |
| Disallow replay on real robot                                    | ❌                                                           | ❌                                         | XS |
| `mutable` NT property when publishing                            | ❌                                                           | ❌                                         | XS |
| Match-log rename (FMS-only names, repeat renames)                | 🟡 old single-rename logic present                           | 🟡 same                                    | XS |
| **`LoggedOpModeRobot`** (OpMode integration)                     | ❌                                                           | ❌                                         | L — depends on RobotPy OpMode API |
| **WPILOGXZ** (`.wpilogxz`) — branch only                         | ❌                                                           | ❌                                         | M (reader S via `lzma`) |
| **Vendor log capture** — branch only                             | ❌                                                           | ❌                                         | M (Phoenix-dependent) |
| **Thread-safe `recordOutput`** — branch only                     | ❌ (lock only on console stream)                             | ❌                                         | M |
| Tunables integration (planned for 2027 beta)                     | ❌ — no Tunables in RobotPy yet to evaluate                  | ❌                                         | Unknown |
| `LoggedMechanism2d` visualization                                | ❌                                                           | ✅ `LoggedMechanismObject2d`/`Root2d` in `lib_6107` | — (lib_6107 ahead) |
| Windows ARM64 / signed binaries                                  | N/A (pure Python)                                            | N/A                                       | — |

**Notable:** the one area where `lib_6107.pykit` is *ahead* of PyKit is Mechanism2d logging. Everything else on this
list `lib_6107` shares with PyKit.

## 7. Where this leaves `lib_6107.pykit`

Verified against `src/lib_6107/**`: there is still **no** 2027/SystemCore code, comment, or dependency pin.
`lib_6107` is current with PyKit's released shape (version `2026.0.0.6` on PyPI as `lib_6107`/`lib-6107`; requires
Python ≥ 3.14 and WPILib/RobotPy ≥ 2026.2.2).

- `constants.py` `NetworkConstants` models `ROBORIO_STATIC`/`ROBORIO_MDNS` only.
- `pykit/wpilog/wpilogwriter.py` still uses the roboRIO-idiom path name `defaultPathRio` (akit renamed to
  `defaultPathRobot`) — cosmetic, optional, and still the one safe action available today.
- `pykit/inputs/loggablesystemstats.py` logs the FPGA-era field set, matching akit `v26.0.2`, not `main`.
- `pykit/loggedrobot.py` docstring still claims roboRIO-specific timing characteristics.

**What changed vs. July:** the deltas that `lib_6107` would need to port **doubled in number** (§6), and — because
PyKit is dormant — they are now **`lib_6107`'s to own**, not something to inherit from upstream. The previous
snapshot's position ("nothing to port to yet") should be considered obsolete: RobotPy `2027.0.0a7` is installable.

## 8. Other Python implementations of AdvantageKit

**Result: none independent.** Searches of GitHub (code, repositories, topics) for Python `LogTable`, `WPILOGWriter`,
`LoggedNetworkNumber`, `processInputs`, and "AdvantageKit Python" found **no second implementation**. Everything
Python-based is either PyKit itself, a derivative (`lib_6107`), or a PyKit *consumer*.

| Project                                                                       | Relationship                                                                                   |
|-------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| [`1757WestwoodRobotics/PyKit`](https://github.com/1757WestwoodRobotics/PyKit) | The only upstream Python AdvantageKit port (`robotpy-pykit`)                                   |
| `lib_6107` / `6107/frclib-6107` (this repo), `6107/PyKit` fork                | Derivative port with extras (Mechanism2d logging, etc.); fork has no commits beyond upstream   |
| `1757WestwoodRobotics/2026-Rebuilt`                                           | PyKit consumer (author's own team robot)                                                       |
| `SteelRidgeRobotics/2026Rebuilt`                                              | PyKit consumer                                                                                 |
| `spiresfrc9106/romiPyKitSubsystems`, `spiresRobot2026`                        | PyKit consumers (spiresfrc9106 / Mike Stitt, who also authored PyKit PR #17)                   |
| `Barlow-Robotics/Code2026` (branch `pybranch`)                                | PyKit consumer                                                                                 |
| `SenseiNotHere/FRESH-2027`                                                    | PyKit consumer; **pinned to `robotpy==2026.2.2` + `robotpy-pykit==1.0.5`** — not actually 2027 |
| `PickleFace5/Toast`                                                           | PyKit consumer                                                                                 |

Related, but **not** Python AdvantageKit implementations:

- **AtlantisKit** — Java-side library wrapping Sendables with AKit replay (Chief Delphi, 2026); notable because the new
  Tunables API breaks its approach, mirroring the AKit–Tunables issue in §9.
- **Hoot Replay** (CTRE) — vendor-specific, non-deterministic replay; a different problem than AKit's.
- WPILOG analysis tools (FRC Static Log Analyzer, ClaudeScope, WPILOG/NT4 MCP server — threads 518058, 519547,
  517780) read AKit logs but do not log.

Practical implication: **`lib_6107` is not competing with anything**; the only real collaborators are PyKit's
maintainer (Luke Maxwell, "Giant" / `lmaxwell24` on Chief Delphi) and PyKit consumer teams such as Mike Stitt's.
Upstreaming `lib_6107` fixes to PyKit has no response signal today (PR #17 has sat since April).

## 9. Chief Delphi — recent threads of interest (last ~7 months)

Links resolve via topic ID (`https://www.chiefdelphi.com/t/<id>`).

**AdvantageKit / PyKit**

| Thread                                                                                                                  | Date                  | Takeaway                                                                                                                                                              |
|-------------------------------------------------------------------------------------------------------------------------|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [525592 — Integrating WPILib 2027 Tunables with AdvantageKit (replay-safe `TunableBackend`)](https://www.chiefdelphi.com/t/525592) | 2026-10-24            | **Most important for planning.** jonahb55: native Tunables integration expected "sometime in the 2027 beta" with back-compat for logged network inputs; native Telemetry output logging likely *not* officially supported. |
| [509227 — AdvantageKit 2026: Replay, Refined](https://www.chiefdelphi.com/t/509227)                                      | active through 10-05  | `LoggedOpModeRobot` ships with the 2027 beta after the WPILib beta; dev builds via GitHub Actions Maven repo.                                                          |
| [508084 — Introducing PyKit, Log replay for Python!](https://www.chiefdelphi.com/t/508084)                               | 2025-11 → 2026-03-06  | Main PyKit thread (50 posts): release notes 1.0.x, timing/GIL discussion, MagicBot request, `LoggedDashboardChooser` singleton fix. Silent since March.               |
| [522532 — AdvantageKit logging vs CTRE hoot logging](https://www.chiefdelphi.com/t/522532)                               | 2026-07-14            | Background for the `vendor-log-capture` branch (§3.2).                                                                                                                |
| [505988 — AdvantageScope 2026: New Horizons](https://www.chiefdelphi.com/t/505988)                                       | earlier 2026          | Viewer-side features that consume PyKit/`lib_6107` logs.                                                                                                              |
| [525204 — Share your best, and worst Robot Logs!](https://www.chiefdelphi.com/t/525204)                                  | 2026-10-13            | Useful for finding real-world log shapes.                                                                                                                             |
| [524153 — How do I log a Field2d with a struct or AdvantageKit?](https://www.chiefdelphi.com/t/524153)                   | 2026-09-15            | Logging-pattern Q&A; relevant to pose/Field2d logging choices.                                                                                                        |
| [521542 — Parsing the struct definition for structs in wpilog from Python](https://www.chiefdelphi.com/t/521542)         | 2026-06-02            | Python-side WPILOG struct-schema parsing; relevant to the reader/writer.                                                                                              |
| [515927 — Vision system causes >0.2 s input lag (RobotPy / PhotonLib)](https://www.chiefdelphi.com/t/515927)             | March 2026            | PyKit user report of vision-related latency; relevant to the <20 ms loop target.                                                                                      |

**WPILib 2027 / RobotPy**

| Thread                                                                                                              | Date               | Takeaway                                                                                                                                                       |
|---------------------------------------------------------------------------------------------------------------------|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [525037 — Python Readiness for Systemcore?](https://www.chiefdelphi.com/t/525037)                                   | 2026-10-07 → 10-20 | RobotPy 2027a7 exists; Python teams are alpha-testing; Phoenix tools can generate a 2027 alpha-7 Python project.                                                |
| [519900 — Programming / Library changes for 2027](https://www.chiefdelphi.com/t/519900)                             | 2026-05-03 → 10-24 | 113 posts. Telemetry/Tunables replace SmartDashboard/Sendable; OpModes; Commands v3; **field origin moves to field center, rotated 180° (see post #104)**.      |
| [522584 — Robotpy, asyncio, and Commands V3](https://www.chiefdelphi.com/t/522584)                                  | 2026-07-15 → 07-19 | Started by cboling. RobotPy has no asyncio/Commands v3 coroutine plans; PyKit could have been more `TimedCommandRobot`-compatible.                              |
| [519702 — WPILib Commands v3 Championship Conference](https://www.chiefdelphi.com/t/519702)                         | 2026-05-01 → 10-08 | Background on Commands v3 (not available to Python today).                                                                                                      |

Other loosely related: 517780 (WPILOG/NT4 MCP), 519547 (ClaudeScope), 518058 (FRC Static Log Analyzer).

## 10. Head-to-head: who is ahead, who is behind, by area

| Area                                                      | AdvantageKit (Java)                                | Westwood PyKit              | RobotPy (layer under PyKit)               | `lib_6107.pykit`                            |
|-----------------------------------------------------------|----------------------------------------------------|-----------------------------|-------------------------------------------|---------------------------------------------|
| Package/namespace migration for 2027                      | ✅ Done (`org.wpilib.*`)                            | N/A                         | N/A                                       | N/A                                         |
| SystemCore native/cross-compile target                    | ✅ Done (`linuxsystemcore`)                         | ❌ Not started               | 🟡 Alpha-only, active (2027.0.0a7)         | ❌ Not started (no native code)              |
| SystemCore system-telemetry schema                        | ✅ On `main` (+ unit metadata, versions)            | ❌ Not started               | Unclear (HAL surface not confirmed)       | ❌ Pre-2027 FPGA-era fields                  |
| Console capture for systemd/SystemCore                    | ✅ `journalctl`                                     | ❌                           | N/A                                       | ❌ `stdout`/`stderr` wrapping only            |
| Multi-CAN-bus PDP/PDH (`busID`)                           | ✅ Shipped (breaking)                               | ❌                           | Unclear                                   | ❌                                           |
| OpMode robot base class                                   | ✅ `LoggedOpModeRobot` (in `main`; ships w/ beta)   | ❌                           | 🟡 OpMode API status not confirmed        | ❌                                           |
| Built-in alerts / receiver-queue alert                    | ✅ In `main`                                        | ❌                           | N/A                                       | ❌                                           |
| Radio logging without team number                         | ✅ In `main`                                        | ❌ (issue open)              | N/A                                       | ❌                                           |
| Configurable loop-overrun warning                         | ✅ In `main`                                        | 🟡 Fixed print only          | N/A                                       | 🟡 Fixed print only                          |
| Nanosecond-timestamp replay / replay-on-robot guard       | ✅ In `main`                                        | ❌                           | N/A                                       | ❌                                           |
| WPILOGXZ compressed logs                                  | 🟡 Branch `wpilogxz`, ready to merge                | ❌                           | N/A (`lzma` in stdlib)                    | ❌                                           |
| Vendor log capture                                        | 🟡 Branch `vendor-log-capture`                      | ❌                           | N/A                                       | ❌                                           |
| Thread-safe `recordOutput`                                | 🟡 Branch `output-multithreading`                   | ❌                           | N/A                                       | ❌                                           |
| Tunables integration                                      | 🟡 Planned for the 2027 beta                        | ❌                           | ❓ Tunables availability unconfirmed      | ❌                                           |
| Mechanism2d logging                                       | ✅                                                  | ❌                           | N/A                                       | ✅ `LoggedMechanism*2d`                      |
| Maintenance activity (last 60 days)                       | ✅ ~33 commits on `main`, 5 active branches         | ❌ 0 commits, 0 responses    | ✅ Commits every few days                  | n/a                                          |
| Stable, tagged 2027 release                               | ❌ Alpha only (`v27.0.0-alpha-7`)                   | ❌ None                      | ❌ Alpha only (`2027.0.0a7`; stable 2026.2.2) | ❌ None                                    |

**Reading the table:** AdvantageKit is ahead of the whole Python stack, and its lead grew between snapshots. Within
Python, RobotPy is the only layer with live 2027 momentum; PyKit and `lib_6107.pykit` are both on 2026 shape. Unlike
July, there is now an installable RobotPy 2027 alpha to develop against.

## 11. Recommendations

- **Re-baseline the plan:** the July position ("no urgent action — wait for PyKit/RobotPy") is **obsolete**. With
  RobotPy `2027.0.0a7` installable, PyKit dormant, and build season starting January 2027, `lib_6107.pykit` must
  assume it owns its own 2027 port.
- **Stand up a 2027-alpha test environment now** (SystemCore + `robotpy==2027.0.0a7` +
  `robotpy-commands-v2==2027.0.0a7`) and identify what breaks in `lib_6107` before any feature work. This is the
  cheapest, highest-value step and is independent of PyKit.
- **Candidate backlog, in rough priority** (effort from §6 table):
  1. SystemCore `LoggedSystemStats` schema + AdvantageKit/WPILib versions — blocked on confirming the RobotPy HAL
     surface for faults/network/IMU.
  2. Thread-safe `recordOutput` queue (borrowing the `output-multithreading` design) — protects vision/odometry
     worker threads.
  3. Small, low-risk parity items: radio logging without team number, replay-on-real-robot guard, `mutable` NT
     property, nanosecond-timestamp replay, built-in/receiver-queue alerts.
  4. `.wpilogxz` **reader** support via `lzma` (writer optional — profile the CPU cost against the <20 ms target).
  5. OpMode-aware `Robot` base class — wait for RobotPy's OpMode API and AKit's beta to stabilize `LoggedOpModeRobot`.
  6. Pose-flipping review for the 2027 field-origin change (center origin, 180° rotation) in `lib_6107.util` flipping
     helpers and `SimulationConstants` starting poses.
  7. Tunables strategy (replacement for `LoggedNetwork*` inputs) — wait for AKit's beta integration.
- **Also available today, cosmetic:** `defaultPathRio` → `defaultPathRobot` rename.
- **Upstream engagement:** consider offering PyKit's maintainer a coordination point (or joining Mike Stitt's PR #17
  discussion). Given 7 months of silence, plan for `lib_6107` to be the de-facto continuation, with any upstreaming
  as a bonus.
- **Watch list (re-check ~monthly and at each akit/RobotPy tag):**
  1. WPILib **2027 beta** release (gates AKit's beta and `LoggedOpModeRobot` release).
  2. AKit merging `wpilogxz` / `vendor-log-capture` / `output-multithreading` to `main`, and cutting `v27.x`.
  3. AKit Tunables integration (Chief Delphi 525592) and any Telemetry-logging guidance.
  4. RobotPy non-alpha `2027.x` on PyPI, plus OpMode/Tunables bindings.
  5. Any commit, release, or reply in `1757WestwoodRobotics/PyKit`.
  6. A first independent Python AdvantageKit port (none exists today).

## 12. References

**In-repo companion documents**

- `akit-changes-to-date.md` — AdvantageKit `v26.0.2` → `main` delta as of 2026-07-29 (§2/§3 background; §2 here
  supersedes its commit counts).
- `westwood-pykit-changes-to-date.md` — PyKit's public API and (lack of) changes since `v1.0.5`.
- `2026-akit-v-pykit-deltas.md` — API-level `v26.0.2` vs. `v1.0.5` baseline underlying the §6 gap table.
- `lib_6107-pykit-and-westwood-pykit-comparison.md` — `lib_6107.pykit` vs. PyKit comparison.
- `../lib_6107-api-work-todo.md` — `lib_6107` API TODO list; its note that RobotPy has not migrated to the 2027
  layout is superseded by §5 here.

**External sources consulted (2026-10-25)**

- [`Mechanical-Advantage/AdvantageKit`](https://github.com/Mechanical-Advantage/AdvantageKit) — blobless clone;
  branch/tag enumeration, `git log`, `git cherry`, per-branch diffs, `main` file-existence checks, PR numbers.
  Branches: `wpilogxz`, `2027-beta-docs`, `vendor-log-capture`, `output-multithreading`, `wpilog-flush-fix`,
  `loggedopmoderobot`, `add-windows-arm64`, `code-signing`, `update-actions`, `wpilib-alpha-7`.
- [`1757WestwoodRobotics/PyKit`](https://github.com/1757WestwoodRobotics/PyKit) — clone, commits, issues/PRs, forks,
  `git grep` of `v1.0.5` for feature parity; [PyPI `robotpy-pykit`](https://pypi.org/project/robotpy-pykit/).
- [`robotpy/mostrobotpy`](https://github.com/robotpy/mostrobotpy) — tags and recent commits;
  [PyPI `robotpy`](https://pypi.org/pypi/robotpy/json), [`wpilib`](https://pypi.org/pypi/wpilib/json), and
  [`robotpy-commands-v2`](https://pypi.org/pypi/robotpy-commands-v2/json) release lists.
- [`wpilibsuite/allwpilib`](https://github.com/wpilibsuite/allwpilib/releases) — `v2027.0.0-alpha-7` is the latest
  2027 build; no beta yet.
- Chief Delphi topics listed in §9 (Discourse JSON API).
- GitHub code/repository searches for Python AdvantageKit implementations and PyKit consumers (§8).

**Not verified / caveats**

- Chief Delphi links use topic IDs only; Discourse redirects to the canonical slug. Posts within threads were read via
  the JSON API; post numbers cited (#32 in 509227, #104 in 519900) should be spot-checked before quoting.
- Whether PyKit's nanosecond-timestamp replay and the exact RobotPy HAL surface for SystemCore faults/network/IMU
  stats exist was **not** confirmed.
- "In `main`?" status for squash-merged AKit branches is inferred from file existence and PR numbers, not from git
  ancestry.
- No `lib_6107` code was changed as part of this document.

---

## Appendix A. Are other FRC developers improving PyKit for 2027? (fork activity search)

**Purpose:** a search to see whether other FRC developers are working on PyKit improvements for the 2027 season, by
checking every public fork of `1757WestwoodRobotics/PyKit` for commits on **any branch** in the last six months
(2026-04-26 → 2026-10-26).

**Method (2026-10-26, GitHub REST API, unauthenticated):** `GET /repos/1757WestwoodRobotics/PyKit/forks` (4 forks,
matching the repository's `forks_count`; all public), then for each fork `GET /branches` and
`GET /commits?sha=<branch>&since=2026-04-26T00:00:00Z` per branch, and
`GET /compare/main...<fork>:<branch>` for any hit.

**Answer: 1 of 4 public forks (excluding our own `6107/PyKit`, now 2 of 4) has had commits on any branch in the last 6
months, and none of the others relate to 2027.**

| Fork              | Created    | Last push  | Branches checked                                                                                | Commits since 2026-04-26                                      | 2027-related? |
|-------------------|------------|------------|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------|---------------|
| `EmDash00/PyKit`  | 2026-10-09 | 2026-10-14 | `main`, `pythonize`                                                                             | **12** (all on `pythonize`)                                   | No            |
| `6107/PyKit`      | 2026-04-02 | 2026-10-26 | `main`, `2027-support`                                                                          | **3** (all on `2027-support`; see update below)               | Yes (ours)    |
| `MikeStitt/PyKit` | 2026-01-23 | 2026-04-16 | `main`, `fixHangOnExit_robotpy_sim_and_robotpy_test`, `get-replay-sim-and-robotpy-test-working` | 0 (last push 04-16, before window; source of upstream PR #17) | No            |
| `agaddis02/PyKit` | 2025-11-15 | 2025-11-15 | `main`, `feature/2-type-checking-cicd`                                                          | 0                                                             | No            |

**The one active fork — `EmDash00/PyKit`, branch `pythonize`** (author "Wispy Daydream", commits 2026-10-09 → 10-14,
12 ahead / 0 behind upstream `main`, 64 files, ≈ +1,507 / −827 lines):

- Contents are **developer-tooling and style modernization only**: `.editorconfig`, pre-commit hooks, `ruff`
  check/format, `docformatter`, `pyproject-fmt`, `basedpyright` typing fixes, "Modernize typing", docs formatting, and
  line-length fixes. Touches 20 files in `src/pykit`, plus the `diff_drive`, `kitbot_2025`, and `skeleton` template
  projects and `uv.lock`.
- A search of the diff for `systemcore`, `2027`, `opmode`, and `tunable` found **no matches**. The latest commit is
  titled "placeholder will be rewritten later", so the branch looks like work in progress.
- It is a **fork, not an upstream PR**; nothing has been proposed back to Westwood. It is a possible sign of
  community interest in a more actively maintained PyKit, and a potential merge-conflict source if `lib_6107` ever
  reconciles with PyKit's file layout (large mechanical reformatting of `src/pykit`).

**Update 2026-10-26: `6107/PyKit` (this team's own fork), branch `2027-support`.** Since the search above, the
`lib_6107.pykit` changes were ported into the fork: 3 commits on 2026-10-26 (`36b3860`, `0d75f20`, `1926611`) ahead of
upstream `main` (`5d70664`, v1.0.5), 69 files, ≈ +16,193 / −1,417 lines. `main` is unchanged.

- Snake_case renames (`put_table`, `start_receiver`, `to_log`/`from_log`, `LogDataReceiver`, ...) with deprecated
  camelCase and "receiver" shims (`_legacy.py`, `_compat.py`) so existing PyKit users keep working. Per the latest
  commit, the shims do not yet emit warnings by default.
- New modules from `lib_6107`: `LoggedMechanism2d` family, `LogTracer`, `LoggedNetworkButton` (optional
  `commands` extra).
- Python 3.14+ required; the 513-test suite was ported; templates and Sphinx docs were updated.
- Fixed `LoggedNetworkValue.from_log` (`_defaultValue` → `_default`) in the fork; still present in `lib_6107`.

This is a port of existing `lib_6107` work, not new 2027/SystemCore functionality, so it does not change the conclusion
below. It is the only public fork carrying the 2027-era API.

**Conclusion:** no *other* public fork contains 2027, SystemCore, OpMode, or Tunables work. This reinforces §8 and §11:
`lib_6107` should assume it is carrying its own 2027 port. **Limits:** private forks and non-fork copies (code
re-uploaded as a new repository, such as `lib_6107` itself) are invisible to this method. Forks created from forks
(second-level) are not included by the API listing.
