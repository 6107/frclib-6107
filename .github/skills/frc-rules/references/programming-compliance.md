# Programming Compliance Guidance (Green Field — Season Independent)

This file covers **evergreen** FRC control-system and programming concepts that recur every season, mapped to robotpy
and this repository's (`frclib-6107`) conventions. For 2026-specific rule numbers, see
`2026-rebuilt-robot-and-control-rules.md`.

## The FRC Control System, at a Glance

- **roboRIO**: the only permitted onboard robot controller; runs the team's compiled/deployed robot code (robotpy → a
  Python process on a Linux-based RT image).
- **Radio**: FMS/DS-issued wireless bridge; the only wireless link into/out of the robot during a MATCH.
- **Driver Station (DS) software**: runs on a laptop at the event; sends joystick/mode data to the roboRIO and receives
  status. Not user-modifiable — a **Dashboard** (e.g. Shuffleboard, Elastic, AdvantageScope) is the customizable UI
  layer, and is separate from the DS software itself.
- **Field Management System (FMS)**: governs MATCH timing, mode transitions (Disabled → Autonomous → Teleop → Disabled),
  and enable/disable signals — user code never controls its own enable state.

## Mode Transitions Map to Rules, Not Just Code

Every season's Game Manual defines MATCH periods (see the year-specific arena/game reference for exact durations).
Regardless of season, the general compliance pattern is:

1. **Disabled**: all actuators must go to a safe, neutral state. WPILib's motor-safety watchdog and this library's
   `SubsystemBase.stop()` hook (invoked on `disabledInit()` / `teleopExit()`) exist specifically to satisfy this.
2. **Autonomous**: robots must act without driver input — never read joystick/controller state inside autonomous command
   logic; only sensor feedback and pre-programmed sequences are legitimate inputs.
3. **Teleop**: driver control is active; button bindings (`CommandXboxController` in this repo, never raw
   `XboxController`) should be the only path from human input to actuator commands.
4. **Test**: used for diagnostics; the same control-system rules (single roboRIO, allowed radio, no unauthorized
   wireless links) still apply whenever connected to a field or practice field.

## Common Pitfalls (Any Season)

- **Adding unauthorized wireless links** (Bluetooth telemetry dongles, phone-based dashboards, extra WiFi radios) —
  almost every season's manual restricts wireless communication to the FMS-issued radio plus a narrow allow-list (e.g.
  location tags, RFID/NFC used only within the robot). Cameras and non-RF sensors are not considered wireless
  communication devices.
- **Exceeding bandwidth caps** — high-resolution/uncompressed camera streams or verbose NetworkTables/logging traffic
  can violate per-season bandwidth limits enforced by the wireless bridge. Prefer structured, low-rate telemetry via
  this library's `Logger.recordOutput()` pipeline over raw high-bandwidth streaming.
- **Missing current limiting / unsafe neutral modes** — always configure current limits and brake/coast modes
  appropriate to the mechanism in subsystem constructors; this is both a "Code Generation Rule" for this repo and a
  practical defense against brownouts and mechanism damage that can also cause rule violations (e.g. uncontrolled
  extension beyond size limits).
- **Hard-coding size/weight/extension limits as magic numbers** — always define them as named constants (with units)
  so a single source of truth exists and future season changes are easy to update. See
  `templates/rebuilt_2026_game_constants.py` for the pattern this repo expects (`wpimath.units` types,
  `@dataclass(slots=True)`, Google-style docstrings).
- **Blocking calls in periodic methods** — `Thread.sleep()`-equivalents or long blocking I/O inside
  `robotPeriodic()`/`*Periodic()` risk loop overruns and can cause a robot to miss safe-state transitions during mode
  changes; this repo targets a strict **<20 ms** main loop (see `LogTracer`).
- **Treating Q&A answers as manual amendments** — official Q&A responses clarify but do not supersede manual text; only
  Team Updates amend the manual itself.

## robotpy / Command-Based Quick Reference

- Install & deploy: `pip install robotpy`, then `python -m robotpy sim` (desktop simulation) or
  `python -m robotpy deploy` (to a physical roboRIO).
- Architecture: `commands2` Command-Based v2 — Subsystems own hardware I/O and state; Commands own sequencing/logic and
  declare subsystem `requirements` to prevent resource conflicts.
- In this repository specifically: always extend `lib_6107.subsystems.subsystem.SubsystemBase` (never
  `commands2.Subsystem`) and `lib_6107.commands.command.BaseCommand` (never `commands2.Command`) — see
  `.github/instructions/subsystems.instructions.md` and `.github/instructions/commands.instructions.md` for the
  mandatory structure (e.g. the `self._initialized` guard, required lifecycle hook calls).
- Telemetry always flows through `Logger.recordOutput(path, value)` — never `SmartDashboard.putXXX()` directly — per
  `AGENTS.md` and this repo's copilot instructions.

## When Rule Text and Code Behavior Conflict

If a user describes robot behavior that appears to violate a rule (e.g. a mechanism that can extend past `R105`'s limit
under certain fault conditions), the correct response is to:

1. Identify the specific rule at risk and cite it.
2. Suggest a concrete, in-code mitigation (soft limits, sensor interlocks, `stop()` overrides) as an example only.
3. Recommend the team verify the fix satisfies inspection before competing, and consult official FRC channels for edge
   cases this skill cannot resolve with confidence.
