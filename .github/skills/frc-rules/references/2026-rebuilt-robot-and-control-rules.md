# 2026 REBUILT — ROBOT Construction & Control System Rules Reference

Source: [2026 FRC Game Manual](https://firstfrc.blob.core.windows.net/frc2026/Manual/2026GameManual.pdf), Section 8
"ROBOT Construction Rules (R)" (consolidated through Team Update 22). Rule IDs (`R1xx`, `R4xx`, `R5xx`, `R7xx`) are
cited directly from the manual — always confirm current wording there before treating a summary as authoritative.

## 8.1 General ROBOT Design — Size & Weight (`R101`–`R108`)

| Rule   | Requirement                                                                                                                                                                                                                |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `R101` | ROBOT PERIMETER (excluding BUMPERS) must be fixed — formed by non-articulated structural elements, measured with a taut string around the ROBOT at the BUMPER ZONE in STARTING CONFIGURATION.                              |
| `R102` | In STARTING CONFIGURATION, no part may extend outside the vertical projection of the ROBOT PERIMETER (except BUMPERS / minor protrusions).                                                                                 |
| `R103` | **Weight limit: 115.0 lb (52.16 kg)** max, excluding BUMPERS, battery + its Anderson cable half, and event-provided location tags.                                                                                         |
| `R104` | STARTING CONFIGURATION max size: ROBOT PERIMETER ≤ **110.0 in (2.794 m)**; height ≤ **30 in (0.762 m)**.                                                                                                                   |
| `R105` | Horizontal extension limit: may not extend more than **12 in (0.3048 m)** beyond the ROBOT PERIMETER. Enforceable via hardware or **software** soft-limits.                                                                |
| `R106` | May only extend beyond the ROBOT PERIMETER in **one direction (one side) at a time** — violations are penalized under `G413`, with an exception for brief/momentary, non-strategic excursions (e.g. a swinging cable tie). |
| `R107` | Total ROBOT height may **never exceed 30.0 in (0.762 m)**, even when mechanisms are extended — not just in STARTING CONFIGURATION.                                                                                         |

**Programming implication:** where a mechanism (elevator, arm, intake) could physically exceed `R105`/`R106`/`R107`
limits, implement software soft-limits (e.g. clamp setpoints, limit-switch cutoffs) in the subsystem, and treat the
limit values as named constants (never magic numbers) per this repo's constants conventions.

## 8.4 BUMPER Rules (`R401`+)

- `R401`: BUMPERS must protect (almost) the entire ROBOT PERIMETER; gaps < 1.25 in (3.17 cm) are allowed between
  segments if corners are filled; one larger gap is allowed only if ≥ 5.0 in (12.7 cm) of PERIMETER on each side of
  every corner is still protected.
- `R402`: BUMPER cross-section must include padding (≥ 2.25 in deep, ≥ 4.5 in tall closed-cell foam), a backing (≥ 4.5
  in tall), and a cover, per specified material lists.
- BUMPERS are also the reference surface for TOWER climb scoring (`LEVEL 2`/`LEVEL 3` require BUMPER covers above a
  given RUNG) — see `references/2026-rebuilt-arena-and-game.md`.

## 8.5 Motors & Actuators (`R501`+)

Only an explicit allow-list of motors/actuators may be used (any quantity), including for 2026:

- AndyMark 9015, NeveRest, PG (gearmotor assemblies), RedLine, Snow Blower Motor
- Banebots RS775/RS550, CIM, PM25R KOP motors
- CTR Electronics **Minion**, CTRE/VEX **Falcon 500**
- Automotive KOP motors (Denso, Bosch, Johnson Electric)
- Playing With Fusion Venom, REV **HD Hex**, **NEO**, **NEO 550**, **NEO Vortex**
- Thrifty Bot Pulsar 775, VEX BAG/Mini-CIM
- West Coast Products **Kraken X44**, **Kraken X60**, RS775 Pro
- Small COTS fans (≤120 mm, ≤10 W @ 12 V), COTS PWM servos under stated stall-current/power limits, COTS sensor motors
  (LIDAR, etc.) unmodified, 1 compressor, and COTS 12 V (or 24 V-rated) brushed motors/solenoids/electromagnets wired
  downstream of a ≤20 A breaker.
- Note: the roboRIO 6 V servo rail is limited to **2.2 A (12.4 W)** total — size servo usage accordingly.

**Programming implication:** always apply current limiting (`setSmartCurrentLimit`/`configCurrentLimit` equivalents)
and a safe neutral/idle mode (brake/coast as appropriate) in subsystem constructors, per this repo's existing
"Safety First" code generation rule — this also helps avoid brownouts from the allow-listed high-power motors above.

## 8.7 Control, Command & Signals System (`R701`–`R710`)

| Rule   | Requirement                                                                                                                                                                                                                                          | Programming implication                                                                                                                                                                                                   |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `R701` | ROBOT must be controlled by exactly 1 **roboRIO** or **roboRIO 2.0**, image `2026_v1.2`+. Co-processors are allowed, but all power-regulating commands must originate from the roboRIO.                                                              | Robot code is the single source of truth for enabling/disabling actuators — a co-processor (e.g. vision Pi) must never directly drive motors.                                                                             |
| `R702` | Only a **Vivid Hosting VH-109** wireless bridge (or OpenMesh OM5P for China events), configured per-team, may communicate to/from the ROBOT during a MATCH.                                                                                          | No substituting other radios/WiFi hardware.                                                                                                                                                                               |
| `R703` | roboRIO Ethernet port must connect to the radio per specified wiring (varies by radio version/port).                                                                                                                                                 | Wiring/hardware concern, not software — but relevant when debugging DS connectivity.                                                                                                                                      |
| `R704` | Communication ROBOT↔Operator Console capped at **7.0 Mbit/s** (Vivid Hosting) or **4.0 Mbit/s** (OpenMesh); restricted to specific network ports (camera streams, SmartDashboard, NT, CTRE diagnostics, team-use ports 5800–5810).                   | Keep telemetry/vision bandwidth within budget — avoid uncompressed high-res camera streams or excessive NT traffic; prefer the pykit `Logger` pipeline for structured telemetry rather than raw high-bandwidth streaming. |
| `R705` | roboRIO, DS software, and radio must be configured with the correct team number.                                                                                                                                                                     | Standard deploy/config step — verify each season/robot.                                                                                                                                                                   |
| `R706` | All signals must originate from the Operator Console and go through the ARENA Ethernet network — no bypassing.                                                                                                                                       | No direct robot-to-robot or off-network links during a MATCH.                                                                                                                                                             |
| `R707` | Only limited wireless allowed: the required radio link, event-provided location-detection tags, and RFID/NFC used **exclusively within the ROBOT**. Cameras and non-RF sensors (e.g. beam-break, IR) are not "wireless communication" for this rule. | Do not add Bluetooth/WiFi peripherals, phone-based telemetry apps, or any other wireless control/telemetry channel to the robot.                                                                                          |
| `R708` | Wireless bridge must be mounted with diagnostic lights visible to FIELD STAFF.                                                                                                                                                                       | Hardware/mounting concern.                                                                                                                                                                                                |
| `R709` | ROBOT must have 1–2 Robot Signal Lights (RSL), wired to the roboRIO's RSL terminals.                                                                                                                                                                 | Hardware requirement; RSL blink pattern is driven automatically by the roboRIO firmware based on robot state — no user code needed.                                                                                       |
| `R710` | Only specified, listed modifications to control-system hardware are permitted (e.g. user-programmable roboRIO code, motor-controller calibration/firmware updates) — no tampering otherwise.                                                         | User code on the roboRIO is explicitly the customizable layer; do not attempt to modify Driver Station Software itself (separate from the Dashboard, which *is* customizable).                                            |

## Match Periods & Programming Mode Mapping

See `references/2026-rebuilt-arena-and-game.md` for full MATCH period timing (AUTO 20 s / TELEOP 140 s). These map
directly to the standard robotpy/WPILib lifecycle hooks:

- **AUTO** → `autonomousInit()` / `autonomousPeriodic()` — no driver input permitted per Game Rules; this repository
  disallows using `commands2.Command` directly, so autonomous routines should be built from `BaseCommand` /
  `SequentialCommandGroup` compositions registered with PathPlanner where applicable.
- **TELEOP** (Transition Shift + 4 Alliance Shifts + End Game) → `teleopInit()` / `teleopPeriodic()` — driver control is
  active; `SubsystemBase.stop()` is invoked on `teleopExit()` to zero mechanisms between MATCH periods.
- **DISABLED** (pre-match, between AUTO/TELEOP if applicable, post-match) → `disabledInit()` / `disabledPeriodic()`
  — all actuator outputs must go to a safe/neutral state; this is enforced automatically by WPILib's motor safety and
  this library's `stop()` lifecycle hook.
- **TEST** → `testInit()` / `testPeriodic()` — used for on-demand diagnostics, not MATCH play; still subject to the same
  control-system rules above (single roboRIO, allowed radio, etc.) when connected to the field or a practice field.
