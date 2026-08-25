# 2026 REBUILT — Arena & Game Reference

Source: [2026 FRC Game Manual](https://firstfrc.blob.core.windows.net/frc2026/Manual/2026GameManual.pdf) (consolidated
through Team Update 22). Section numbers below refer to that document. All figures are **nominal**; always confirm exact
tolerances in the manual before treating a value as safety-critical.

> Game name: **REBUILT presented by Haas** — 2026 season, themed around the *FIRST* Age "archaeology" storyline.
> Kickoff: January 10, 2026. Game piece: **FUEL** (foam balls scored into a **HUB**); endgame: climbing a **TOWER**.

## FIELD (Section 5.2)

- Overall carpeted FIELD: **≈317.7 in × 651.2 in (≈8.07 m × 16.54 m)**, bounded by ALLIANCE WALLS, OUTPOSTS, TOWER
  WALLS, and guardrails.
- Guardrails: 20.0 in (50.8 cm) tall transparent polycarbonate; 4 gates, each 38.0 in (96.5 cm) wide when open.
- Surface: low-pile carpet, seams taped with gaffer's tape; robots must tolerate carpet/tape transitions.
- Field elements (per ALLIANCE unless noted): 1 OUTPOST, 1 HUB, 1 TOWER, 2 DEPOTS (shared), 4 BUMPS (shared), 4 TRENCHES
  (shared).

## Areas, Zones & Markings (Section 5.3)

| Zone                | Approx. size                          | Notes                                                                 |
|---------------------|---------------------------------------|-----------------------------------------------------------------------|
| ALLIANCE AREA       | 360 in × 134 in (9.14 m × 3.4 m)      | Behind ALLIANCE WALL/OUTPOST/TOWER WALL to edge of carpet             |
| ALLIANCE ZONE       | 158.6 in × 317.7 in (4.03 m × 8.07 m) | Surrounds an ALLIANCE's TOWER + DEPOT; bounded by ROBOT STARTING LINE |
| NEUTRAL ZONE        | 283 in × 317.7 in (7.19 m × 8.07 m)   | Formed by BUMPS/TRENCHES/HUBS/guardrails; bisected by CENTER LINE     |
| OUTPOST AREA        | 71 in × 134 in (1.8 m × 3.4 m)        | Human player loading area                                             |
| HUMAN STARTING LINE | —                                     | 24.0 in (61.0 cm) from ALLIANCE WALL                                  |
| ROBOT STARTING LINE | —                                     | Edge of ALLIANCE ZONE, in front of 2 BUMPS + the ALLIANCE HUB         |

## HUB (Section 5.4)

- Each HUB: **47 in × 47 in (≈1.19 m × 1.19 m)** rectangular prism, centered between 2 BUMPS, **158.6 in (≈4.03 m)**
  from its ALLIANCE WALL.
- Top scoring opening: **41.7 in (≈1.06 m)** hexagonal opening; front edge **72 in (≈1.83 m)** off the carpet.
- HUB status (active/inactive) toggles during TELEOP ALLIANCE SHIFTS based on AUTO FUEL scoring results (Section
  6.4.1) — only FUEL scored while a HUB is **active** counts for MATCH points.
- HUB lighting communicates status (Table 5-3): full ALLIANCE color = active; pulsing = deactivation warning;
  purple/green = FIELD-safety signaling; off = inactive/pre-match.

## BUMP (Section 5.5)

- **73.0 in wide × 44.4 in deep × 6.513 in tall (1.854 m × 1.128 m × 0.1654 m)**.
- Two ramps per BUMP at a **15°** angle (Orange Peel textured HDPE), one sloping toward NEUTRAL ZONE, one toward
  ALLIANCE ZONE. Robots drive over BUMPS.

## TRENCH (Section 5.6)

- **65.65 in wide × 47.0 in deep × 40.25 in tall (1.668 m × 1.194 m × 1.022 m)** — robots drive *underneath*.
- Clearance underneath each TRENCH arm: **50.34 in wide × 22.25 in tall (1.279 m × 0.5652 m)**.

## DEPOT (Section 5.7)

- **42.0 in wide × 27.0 in deep (1.07 m × 0.686 m)**, one per ALLIANCE, along the ALLIANCE WALL.
- Steel barrier: 3.0 in wide × 1.0 in tall nominal (≈1.125 in / 2.86 cm once secured with hook fastener).

## TOWER (Section 5.8) — Endgame Climb Structure

- Overall: **49.25 in wide × 45.0 in deep × 78.25 in tall (1.251 m × 1.143 m × 1.988 m)**, integrated into the ALLIANCE
  WALL between Driver Stations 2 and 3.
- TOWER BASE: 39.0 in × 45.18 in (0.991 m × 1.148 m) plate on the floor.
- UPRIGHTS: two, 72.1 in (1.831 m) tall, spaced **32.25 in (0.819 m)** apart.
- RUNGS: 1-1/4 in Sch 40 pipe (1.66 in OD), **18.0 in (0.457 m)** apart center-to-center:
    - **LOW RUNG** center height: 27.0 in (0.686 m)
    - **MID RUNG** center height: 45.0 in (1.143 m)
    - **HIGH RUNG** center height: 63.0 in (1.600 m)
- Scoring criteria (Section 6.5.2, rule-referenced as `LEVEL 1/2/3`):
    - LEVEL 1 — robot no longer touching carpet or TOWER BASE (AUTO or TELEOP; max 2 robots score this in AUTO).
    - LEVEL 2 — BUMPER covers completely above the LOW RUNG.
    - LEVEL 3 — BUMPER covers completely above the MID RUNG.
    - Robot must also be contacting a RUNG/UPRIGHT and only TOWER WALL/support structure/FUEL/another robot otherwise.

## FUEL (Game Piece) — Section 5.10

- **504** high-density yellow foam balls per FIELD, manufactured exclusively by AndyMark.
- Diameter: **5.91 in (15.0 cm)**; mass: **≈0.5 lb (≈0.227 kg)** each.
- Distributed mostly in the NEUTRAL ZONE before a MATCH; robots may be preloaded with **up to 8** FUEL.

## MATCH Periods (Section 6.4)

| MATCH Period | Timeframe        | Duration | Timer values |
|--------------|------------------|----------|--------------|
| AUTO         | AUTO             | 20 s     | 0:20 → 0:00  |
| TELEOP       | TRANSITION SHIFT | 10 s     | 2:20 → 2:10  |
| TELEOP       | SHIFT 1          | 25 s     | 2:10 → 1:45  |
| TELEOP       | SHIFT 2          | 25 s     | 1:45 → 1:20  |
| TELEOP       | SHIFT 3          | 25 s     | 1:20 → 0:55  |
| TELEOP       | SHIFT 4          | 25 s     | 0:55 → 0:30  |
| TELEOP       | END GAME         | 30 s     | 0:30 → 0:00  |

- Total MATCH duration: **20 s AUTO + 140 s TELEOP = 160 s (2:40)**.
- There is a 3-second delay between AUTO and TELEOP for scoring-assessment purposes.
- HUB active/inactive status during ALLIANCE SHIFTS alternates based on which ALLIANCE scored more FUEL during AUTO
  (Table 6-3) — both HUBS are active during AUTO, TRANSITION SHIFT, and END GAME.

## Scoring (Section 6.5, Table 6-4) — for context only, verify exact values before relying on them

- FUEL scored in an **active** HUB: 1 MATCH point (AUTO or TELEOP); FUEL in an inactive HUB scores 0.
- TOWER climb points vary by LEVEL and whether achieved in AUTO or TELEOP, plus associated Ranking Point bonuses
  (`ENERGIZED RP`, `SUPERCHARGED RP`). See the manual directly for current point values — these are subject to Team
  Update revision and are not the focus of this skill (which is about rules compliance, not scoring strategy).

## Cross-Reference to This Library

`src/lib_6107/constants.py::SimulationConstants` already assumes a **16.54 m** field width, which matches this season's
FIELD length above — no change needed there. Game-specific dimensions (HUB, TOWER, BUMP, TRENCH, DEPOT, FUEL) are
**not** part of `RobotConstants`/`SimulationConstants` (those are library-wide, season-independent defaults per
`.github/instructions/constants.instructions.md`) — use
`templates/rebuilt_2026_game_constants.py` in a team project instead.
