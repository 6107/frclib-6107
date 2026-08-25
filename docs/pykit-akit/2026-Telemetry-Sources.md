# 2026 Season Telemetry/Logging Sources — AdvantageKit & PyKit Adoption

> Audience: senior developers supporting a Python port of AdvantageKit's capabilities
> (i.e. `lib_6107.pykit`) who also need to ensure their own team's robot code uses the
> telemetry API correctly. This document catalogs real-world 2026-season examples of
> teams using **AdvantageKit** (Java) or **PyKit** (Python) for telemetry/logging,
> found via the FRC "Open Alliance" community, Chief Delphi's technical archives, and
> GitHub, plus dedicated sections on the two specific reference robots the requester
> asked for by name: **1757 Westwood Robotics** and **6328 Mechanical Advantage**.

## 1. Methodology & a note on "Open Alliance Framework"

Searches were performed against:

- **Chief Delphi** (`chiefdelphi.com`) — using its public Discourse search API (`/search.json?q=...`) and per-topic JSON
  endpoints (`/t/<id>.json`), rather than the JS-rendered HTML search page (which does not return results to a
  non-browser client).
- **GitHub** — repository/organization metadata via the public REST API (`api.github.com/repos/...`,
  `api.github.com/orgs/.../repos`) and a local clone of
  `1757WestwoodRobotics/2026-Rebuilt` for direct source verification. (Unauthenticated GitHub *code* search returns HTTP
  401, so specific-file matches were confirmed by cloning/grepping directly instead.)
- **AdvantageKit's own documentation site** (`docs.advantagekit.org`), which as of the 2026 release directly recommends
  PyKit to Python teams (see §3).

**On "Open Alliance Framework":** no standalone website at a distinct domain (e.g.
`openalliance.org`/`.dev`/`.info`) could be located — those domains are unregistered, parked, or non-resolving. **The
Open Alliance is organized entirely through Chief Delphi**, as a `#openalliance` tag/category where teams post public
season "build threads" pledging to openly share code, CAD, and reasoning as they design and program their robots (a
practice popularized by teams like 6328, 1678, 2910, and others over the past several seasons). This document treats
Chief Delphi's Open Alliance build threads as the practical proxy for "the Open Alliance Framework website" referenced
in the request, since no separate site exists. This is consistent with how AdvantageKit's own 2026 build thread (§4) and
PyKit's own introduction thread (§3) were both posted directly under that tag.

**Limitation on "attended 2026 Worlds" verification:** The Blue Alliance's public API requires an authenticated key not
available in this environment, so exact World Championship attendance rosters could not be queried directly. Where a
team's Worlds attendance is asserted below, it is backed by a direct Chief Delphi citation (e.g. event results/division
standings posted by community members), not by TBA data. No 2026-specific FIRST "control system usage report"
(language/framework breakdown) was found to have been published yet at the time of writing — the most recent published
breakdown covers the 2025 season (§2).

---

## 2. Baseline context: how common is AdvantageKit/PyKit?

FIRST periodically publishes anonymized "Control System Usage Reporting" data. The most recent breakdown found (2025
season, shared on Chief Delphi by FIRST's Peter Johnson and re-shared by other users in Jan 2026) shows:

| Language | AdvantageKit | Command-based (other) | RobotBuilder | ROS | Timed | Total                                 |
|----------|--------------|-----------------------|--------------|-----|-------|---------------------------------------|
| Java     | 331          | 2,200                 | 23           | —   | 540   | 3,099                                 |
| C++      | —            | 90                    | 1            | —   | 83    | 176                                   |
| Python   | —            | —                     | —            | —   | 38    | 92 (incl. 45 "New Command" + 9 blank) |
| Kotlin   | 4            | 8                     | —            | —   | 1     | 13                                    |
| LabVIEW  | —            | 4/1                   | —            | 1   | —     | 93                                    |

Key takeaways for this audience:

- **AdvantageKit is Java-only at the framework level** — it never appears in the Python row of FIRST's own usage data,
  because (prior to PyKit) there was no Python equivalent to select.
- **331 AdvantageKit teams (2025 season)** is nearly as large as C++, LabVIEW, and Python combined (361) — AdvantageKit
  is a mainstream, not niche, tool among competitive teams.
- AdvantageKit's own December 2025 season-announcement post states it "grown from just a handful of users to **more than
  600 teams in the 2025 season**" (a self-reported, likely broader count than the anonymized FIRST report captured
  above).
- **Python has historically had no first-party AdvantageKit-style replay tool** — this is precisely the gap PyKit (and,
  in this repository, `lib_6107.pykit`) exists to close.

---

## 3. PyKit: origin, 2026 status, and official recognition

**PyKit** (`1757WestwoodRobotics/PyKit`) was introduced publicly on Chief Delphi on **2025-11-11** by Luke Maxwell (Team
1757 Westwood Robotics) in the thread
["Introducing PyKit, Log replay for Python!"](https://www.chiefdelphi.com/t/introducing-pykit-log-replay-for-python/508084).
Key points from that announcement, directly relevant to comparing it with
`lib_6107.pykit`:

- Explicitly a **from-scratch reimplementation** of AdvantageKit's ideas for Python, not a wrapper or port of
  AdvantageKit's Java code.
- At introduction (Nov 2025), explicitly **not yet supporting**: ProtoBufs, unit strings, Mechanisms, radio logging,
  power distributor logging, direct STDIO hooks, and RLog ("and may never be"). This independently confirms several of
  the gaps already identified in `lib_6107-pykit-and-westwood-pykit-comparison.md` and
  `../lib_6107-api-work-todo.md` — i.e., `lib_6107.pykit`'s Mechanism2d family and power-distribution/radio hardening
  are *ahead* of upstream PyKit as of that date.
- Ecosystem: [`PyKit`](https://github.com/1757WestwoodRobotics/PyKit) (core library),
  [`PyKitWatch`](https://github.com/1757WestwoodRobotics/PyKitWatch) (a "Replay Watch"
  equivalent), and a `robotpy-pykit` package on PyPI.
- A follow-up post in the same thread (2025-12-19) notes PyKit **gained official recognition in the AdvantageKit
  documentation/commit history**
  ([commit
  `029b3b3`](https://github.com/Mechanical-Advantage/AdvantageKit/commit/029b3b37eb63c8f1acd82670ed6cfa97557b7850)).

**This recognition is now permanent and explicit.** As of the 2026 release, the
official [AdvantageKit installation docs](https://docs.advantagekit.org/getting-started/installation/)
open with:

> "Looking to install AdvantageKit in a Python robot project? Consider using
> **PyKit**, an alternative to AdvantageKit developed by Team 1757 that supports
> deterministic replay in Python."

And Team 6328 (AdvantageKit's own authors) wrote in their official
["AdvantageKit 2026: Replay, Refined"](https://www.chiefdelphi.com/t/advantagekit-2026-replay-refined/509227)
announcement (2025-12-17), under a "Bonus: Third-Party Replay in Python" heading:

> "While AdvantageKit is only available in Java, FRC teams developing in Python
> should consider using PyKit instead. This library was developed by Team 1757 and
> supports deterministic log replay in Python. Littleton Robotics is not involved in
> the development..."

This is about as strong an endorsement as exists in this space: **the creators of AdvantageKit itself point Python teams
to PyKit** — the same lineage `lib_6107.pykit`
descends from.

---

## 4. Teams confirmed using AdvantageKit or PyKit during the 2026 season

| Team                                                                     | Framework             | Language | Evidence                                                                                                                                                                                                                                                                | Repo                                                                                                                                                                                                                                                              |
|--------------------------------------------------------------------------|-----------------------|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **6328 Mechanical Advantage**                                            | AdvantageKit (author) | Java     | Official 2026 season build thread; competed in the **Hopper Division at the 2026 FIRST Championship** and advanced to alliance selection (captain, ranked 5th/6th, per community-reported Einstein/Division Finals results)                                             | [`Mechanical-Advantage/RobotCode2026Public`](https://github.com/Mechanical-Advantage/RobotCode2026Public) ("Darwin")                                                                                                                                              |
| **1757 Westwood Robotics**                                               | PyKit (author)        | Python   | Own 2026 Open Alliance build thread; PyKit imported throughout `src/subsystems/**`, `src/commands/**` in their actual competition code (verified directly in a local clone)                                                                                             | [`1757WestwoodRobotics/2026-Rebuilt`](https://github.com/1757WestwoodRobotics/2026-Rebuilt)                                                                                                                                                                       |
| **4572 Barlow Robotics**                                                 | PyKit                 | Python   | Chief Delphi vision-latency troubleshooting thread (2026-03-09) shows `from pykit.logger import Logger as PyKitLogger` directly in their subsystem code; repo actively pushed to through **2026-07-28** (i.e., still active post-Worlds)                                | [`Barlow-Robotics/Code2026`](https://github.com/Barlow-Robotics/Code2026)                                                                                                                                                                                         |
| **9106 Spires**                                                          | PyKit                 | Python   | A dedicated example/teaching repo porting subsystem patterns to run on a **Romi** (small educational robot) using PyKit, referenced in a Chief Delphi command-binding help thread (2026-01-27); created Jan 2026, last pushed Feb 2026                                  | [`spiresfrc9106/romiPyKitSubsystems`](https://github.com/spiresfrc9106/romiPyKitSubsystems)                                                                                                                                                                       |
| **7459 Taubatexas Robotics** (Brazil)                                    | PyKit (evaluating)    | Python   | 2026 Open Alliance build thread explicitly names "the pykit library, which is recommended by the AdvantageKit dev team" as their logging alternative under consideration — presented as a candidate, not yet confirmed shipped                                          | [`FRC 7459 2026 Build Thread`](https://www.chiefdelphi.com/t/taubatexas-robotics-7459-2026-thread-open-alliance/506668) (no dedicated code repo located)                                                                                                          |
| **9106-adjacent education program** (unspecified team, `anyajiang` post) | PyKit                 | Python   | A programming-education Chief Delphi post (2026-01-07) describing office hours that "guide us and inform us about logging with Pykit" as part of a RobotPy curriculum — included as evidence of PyKit's spread into team *training* material, not just competition code | Thread: [`FRC 1757 Wolverines 2026 Build Thread`](https://www.chiefdelphi.com/t/frc-1757-wolverines-2026-build-thread-open-alliance/507563) *(note: this post appeared inside 1757's own build thread, reinforcing PyKit's origin team also teaches it directly)* |

Teams **checked but found not to be examples** (documented for completeness/audit trail): Team 2429
(`aesatchien/FRC2429_2026`) is a well-known, actively maintained RobotPy team, but its code uses
`wpilib.DataLogManager`/`DriverStation` directly, with **no** AdvantageKit or PyKit import found in `comp_bot/`,
`other_robots/`, or
`practicebot/` — i.e., a Python team that has *not* adopted either framework. Team GreenBlitz (4590) expressed interest
in logging tooling on Chief Delphi, but their current public template repo (`GreenBlitz/GB-Robot-Template`) is written
in **Java**, not Python, and doesn't reference PyKit.

---

## 5. Section: 1757 Westwood Robotics — 2026 Robot (`2026-Rebuilt`)

- Repository: **[1757WestwoodRobotics/2026-Rebuilt](https://github.com/1757WestwoodRobotics/2026-Rebuilt)**
  (verified via local clone; `git describe --tags` → `2026RIKIN-62-gfb17093`, latest commit `fb17093` dated 2026-05-10,
  i.e. post-Worlds maintenance).
- **PyKit is used pervasively**, not just referenced — confirmed via direct grep of the actual (non-`venv`) source tree:
  `src/subsystems/drive/drivesubsystem.py`,
  `swervemodule.py`, `swervemoduleio.py`, `swervemoduleiotalonfx.py`,
  `src/subsystems/flywheel/*.py`, `src/subsystems/hood/*.py`,
  `src/subsystems/indexer/*.py`, `src/subsystems/intake/*.py`, and
  `src/commands/drive/drivewaypoint.py`, `fieldrelativeassisteddrive.py`,
  `overridecommands.py` all `from pykit....` import `Logger`/`autolog` machinery. This confirms an IO-layer subsystem
  architecture (`*subsystem.py` +
  `*subsystemio.py` pairs) directly analogous to AdvantageKit's Java IO-interface pattern, ported faithfully to Python
  via PyKit.
- Team's own 2026 season is documented in their Open Alliance build thread,
  ["FRC 1757 Wolverines | 2026 Build Thread | Open Alliance"](https://www.chiefdelphi.com/t/frc-1757-wolverines-2026-build-thread-open-alliance/507563),
  and PyKit itself was announced from the team's programming lead account (§3).
- **Relevance to `lib_6107.pykit`**: this is the *direct upstream* of the fork this library is based on (see
  `lib_6107-pykit-and-westwood-pykit-comparison.md`). The `2026-Rebuilt` repo is a good "real robot" reference for
  how the upstream PyKit API is meant to be consumed end-to-end (subsystem IO pattern, command structure) — useful for
  validating that any future `lib_6107.pykit` API changes remain ergonomic for a real swerve+flywheel+turret-style
  competition robot, not just in isolation.

## 6. Section: Mechanical Advantage / Team 6328 — 2026 Robot

- The `Mechanical-Advantage` GitHub organization **does have a 2026 robot code repository** — no fallback search for
  "Team 6328" elsewhere was necessary. Repo:
  **[Mechanical-Advantage/RobotCode2026Public](https://github.com/Mechanical-Advantage/RobotCode2026Public)**
  — description: *"Public robot code for 'Darwin'"* (their 2026 robot's name), Java, MIT-licensed, tagged
  `first-robotics-competition`, `frc`, `open-alliance`,
  `rebuilt`; 81 stars / 9 forks at time of writing; `pushed_at` 2026-06-27 (i.e. updated after the World Championship).
- Team's own Open Alliance build thread:
  ["FRC 6328 Mechanical Advantage | 2026 Build Thread"](https://www.chiefdelphi.com/t/frc-6328-mechanical-advantage-2026-build-thread/509595)
  — 10th season for the team, competing in NE District (Minuteman, Waterbury) prior to Worlds, alpha/comp robot build
  strategy, links to CAD, GitHub, AdvantageKit, and AdvantageScope from the very first post.
- **Confirmed 2026 World Championship participation**: community-reported alliance selection/results (Chief Delphi,
  2026-04-24 and 2026-05-20) place **"6328-6329" in the Hopper Division**, an alliance that advanced to Division Finals
  (captain, ranked 5th/6th) at the 2026 FIRST Championship — directly satisfying the "teams in the last worlds
  competition (2026)" criterion from the request for this specific, explicitly-named team.
- **Relevance to this project**: `RobotCode2026Public` is the *reference implementation* for AdvantageKit's Java API as
  actually used in a competitive 2026 robot (not just docs/API surface) — useful ground-truth for confirming which
  AdvantageKit v26.0.2/2026-era features (unit logging, NT client logging, 3D mechanism generation, improved console
  logging — see AdvantageKit's
  ["What's New in 2026"](https://docs.advantagekit.org/whats-new/) page, also used in
  `../lib_6107-api-work-todo.md` §A/§B) are actually exercised by the framework's own authors in anger, versus
  features that exist but see little real-world use.

---

## 7. Cross-reference to this repository's other comparison docs

This document is intended to be read alongside two companion documents already in
`..`:

- **`lib_6107-pykit-and-westwood-pykit-comparison.md`** — detailed API-level diff between `lib_6107.pykit` and
  upstream Westwood PyKit (v1.0.5). Team 1757's
  `2026-Rebuilt` repo (§5 above) is the real-world robot that upstream PyKit version was built for.
- **`../lib_6107-api-work-todo.md`** — detailed API-level diff between
  `lib_6107.pykit`/PyKit and AdvantageKit (both `v26.0.2` and current `main`). Team 6328's `RobotCode2026Public` repo
  (§6 above) is the real-world robot AdvantageKit's 2026 feature set was built for and validated against.

Together, all three documents give a senior developer (a) the exact API delta between this project's fork and its
nearest Python ancestor, (b) the exact API delta between this project's fork and its Java role model, and (c)
**concrete, currently maintained, 2026-season robot code** demonstrating both frameworks in actual competitive use —
useful both as upgrade-path inspiration and as regression-test reference material ("does our robot code still
look/behave like a sane, idiomatic consumer of this API after a proposed change?").

---

## 8. References

**FRC/FIRST community & usage data**

- FIRST Robotics Competition Control System Usage Reporting — 2025-season language/framework pivot table, originally
  posted by Peter Johnson
  ([chiefdelphi.com/t/473179](https://www.chiefdelphi.com/t/frc-blog-control-system-beta-testing-and-usage-reporting/473179/4)),
  re-shared 2026-01-07
  ([chiefdelphi.com/t/509871, post #13](https://www.chiefdelphi.com/t/anyone-using-python/509871/13)).
- ["Anyone using Python?"](https://www.chiefdelphi.com/t/anyone-using-python/509871) — Chief Delphi thread, Jan 2026,
  general Python-in-FRC discussion (context for §2).

**PyKit**

- ["Introducing PyKit, Log replay for Python!"](https://www.chiefdelphi.com/t/introducing-pykit-log-replay-for-python/508084)
  — Luke Maxwell (Team 1757), Chief Delphi, 2025-11-11 (+ follow-up posts through 2026-03-06).
- [`1757WestwoodRobotics/PyKit`](https://github.com/1757WestwoodRobotics/PyKit) — core library.
- [`1757WestwoodRobotics/PyKitWatch`](https://github.com/1757WestwoodRobotics/PyKitWatch) — replay-watch tool.
- [`robotpy-pykit` on PyPI](https://pypi.org/project/robotpy-pykit/).
- [AdvantageKit commit recognizing PyKit](https://github.com/Mechanical-Advantage/AdvantageKit/commit/029b3b37eb63c8f1acd82670ed6cfa97557b7850).
- [AdvantageKit installation docs](https://docs.advantagekit.org/getting-started/installation/)
  — current official recommendation of PyKit for Python teams.

**AdvantageKit**

- ["AdvantageKit 2026: Replay, Refined"](https://www.chiefdelphi.com/t/advantagekit-2026-replay-refined/509227)
  — Jonah Bonner (Team 6328), Chief Delphi, 2025-12-17.
- [AdvantageKit "What's New in 2026"](https://docs.advantagekit.org/whats-new/).
- [Mechanical-Advantage/AdvantageKit](https://github.com/Mechanical-Advantage/AdvantageKit) (GitHub repo).

**Example team repositories/build threads (2026 season)**

- [Mechanical-Advantage/RobotCode2026Public](https://github.com/Mechanical-Advantage/RobotCode2026Public)
  ("Darwin", Team
  6328) + [team build thread](https://www.chiefdelphi.com/t/frc-6328-mechanical-advantage-2026-build-thread/509595).
- [1757WestwoodRobotics/2026-Rebuilt](https://github.com/1757WestwoodRobotics/2026-Rebuilt)
  (Team
  1757) + [team build thread](https://www.chiefdelphi.com/t/frc-1757-wolverines-2026-build-thread-open-alliance/507563).
- [Barlow-Robotics/Code2026](https://github.com/Barlow-Robotics/Code2026) (Team 4572)
    + [Chief Delphi vision-latency thread](https://www.chiefdelphi.com/t/515927) referencing `pykit.logger`.
- [spiresfrc9106/romiPyKitSubsystems](https://github.com/spiresfrc9106/romiPyKitSubsystems)
  (Team 9106) + [Chief Delphi reference thread](https://www.chiefdelphi.com/t/512895).
- [Taubatexas Robotics 7459 2026 Open Alliance build thread](https://www.chiefdelphi.com/t/taubatexas-robotics-7459-2026-thread-open-alliance/506668)
  (evaluating PyKit).
- [aesatchien/FRC2429_2026](https://github.com/aesatchien/FRC2429_2026) (Team 2429 — checked, does **not** use
  AdvantageKit/PyKit; included for audit-trail completeness).
- [GreenBlitz/GB-Robot-Template](https://github.com/GreenBlitz/GB-Robot-Template)
  (Team 4590 — checked, Java template, no PyKit; included for audit-trail completeness).

**2026 World Championship results (community-reported)**

- Chief
  Delphi, ["Einstein/Division Finals Predictions for 2026 Rebuilt"](https://www.chiefdelphi.com/t/einstein-division-finals-predictions-for-2026-rebuilt-2026-frc-game-presented-by-haas/519265),
  post #26 (2026-04-24) — Hopper Division results listing "6328-6329."
- Chief
  Delphi, [Team 5000 Hammerheads 2026 build thread](https://www.chiefdelphi.com/t/frc-5000-hammerheads-2026-build-thread-open-alliance/507502),
  post #1046 (2026-05-20) — "Week 9 - WORLD CHAMPIONSHIP HOPPER Rank 5 ... Shout out to my bros over at 6328!"

**In-repo companion documents**

- `lib_6107-pykit-and-westwood-pykit-comparison.md`
- `../lib_6107-api-work-todo.md`
- `westwood-pykit-changes-to-date.md`
- `akit-changes-to-date.md`
