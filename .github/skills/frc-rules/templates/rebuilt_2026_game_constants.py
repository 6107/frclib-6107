"""Starter FRC 2026 REBUILT field, game element, and ROBOT-limit constants.

This is a **template**, not part of `lib_6107`. Copy it into your own team's robot project (e.g.
`myrobot/constants_2026.py`) and adjust as needed — do not add game-season-specific values to
`src/lib_6107/constants.py` in this library, since those defaults must stay season-independent per
`.github/instructions/constants.instructions.md`.

All dimensions are transcribed from the official 2026 FRC Game Manual (REBUILT), Sections 5 (ARENA) and 8 (ROBOT
Construction Rules). See `.github/skills/frc-rules/references/2026-rebuilt-arena-and-game.md` and
`2026-rebuilt-robot-and-control-rules.md` for rule citations and additional context. Always confirm current values
against the live manual/Team Updates before relying on them for competition — this file is a convenience starting
point, not an authoritative source.
"""

from dataclasses import dataclass
from enum import Enum

from wpimath.units import inchesToMeters, kilograms, lbsToKilograms, meters, seconds


class TowerRungLevel(Enum):
    """TOWER climb LEVELs recognized for MATCH scoring (2026 REBUILT, Section 6.5.2).

    Attributes:
        LEVEL_1: ROBOT no longer touching carpet or TOWER BASE. Only LEVEL achievable in AUTO
            (max 2 ROBOTS per ALLIANCE).
        LEVEL_2: ROBOT positioned with BUMPER covers completely above the LOW RUNG.
        LEVEL_3: ROBOT positioned with BUMPER covers completely above the MID RUNG.
    """

    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


@dataclass(slots=True)
class Rebuilt2026FieldConstants:
    """FIELD and game element dimensions for the 2026 REBUILT game (Game Manual Section 5).

    Attributes:
        FIELD_LENGTH (meters): Long dimension of the carpeted FIELD (~651.2 in).
        FIELD_WIDTH (meters): Short dimension of the carpeted FIELD (~317.7 in).
        HUB_WIDTH (meters): HUB footprint, 47 in square.
        HUB_OPENING_DIAMETER (meters): Hexagonal top scoring opening diameter, 41.7 in.
        HUB_OPENING_HEIGHT (meters): Height of the HUB opening's front edge above the carpet, 72 in.
        HUB_DISTANCE_FROM_ALLIANCE_WALL (meters): Distance from an ALLIANCE HUB to its ALLIANCE WALL, 158.6 in.
        BUMP_WIDTH (meters): BUMP width, 73.0 in.
        BUMP_DEPTH (meters): BUMP depth, 44.4 in.
        BUMP_HEIGHT (meters): BUMP height, 6.513 in.
        BUMP_RAMP_ANGLE_DEGREES (float): BUMP ramp angle, 15 degrees.
        TRENCH_WIDTH (meters): TRENCH width, 65.65 in.
        TRENCH_DEPTH (meters): TRENCH depth, 47.0 in.
        TRENCH_HEIGHT (meters): TRENCH height, 40.25 in.
        TRENCH_CLEARANCE_WIDTH (meters): Drivable clearance width underneath a TRENCH arm, 50.34 in.
        TRENCH_CLEARANCE_HEIGHT (meters): Drivable clearance height underneath a TRENCH arm, 22.25 in.
        DEPOT_WIDTH (meters): DEPOT width, 42.0 in.
        DEPOT_DEPTH (meters): DEPOT depth, 27.0 in.
        TOWER_WIDTH (meters): TOWER width, 49.25 in.
        TOWER_DEPTH (meters): TOWER depth, 45.0 in.
        TOWER_HEIGHT (meters): TOWER height, 78.25 in.
        TOWER_UPRIGHT_SPACING (meters): Distance between TOWER UPRIGHTS, 32.25 in.
        TOWER_RUNG_SPACING (meters): Center-to-center spacing between TOWER RUNGS, 18.0 in.
        TOWER_LOW_RUNG_HEIGHT (meters): LOW RUNG center height off the floor, 27.0 in.
        TOWER_MID_RUNG_HEIGHT (meters): MID RUNG center height off the floor, 45.0 in.
        TOWER_HIGH_RUNG_HEIGHT (meters): HIGH RUNG center height off the floor, 63.0 in.
        FUEL_DIAMETER (meters): FUEL game piece diameter, 5.91 in.
        FUEL_MASS (kilograms): FUEL game piece mass, ~0.5 lb.
        FUEL_COUNT_PER_FIELD (int): Total FUEL pieces per FIELD, 504.
        FUEL_MAX_PRELOAD (int): Maximum FUEL a ROBOT may start a MATCH preloaded with, 8.
    """

    FIELD_LENGTH: meters = inchesToMeters(651.2)
    FIELD_WIDTH: meters = inchesToMeters(317.7)

    HUB_WIDTH: meters = inchesToMeters(47.0)
    HUB_OPENING_DIAMETER: meters = inchesToMeters(41.7)
    HUB_OPENING_HEIGHT: meters = inchesToMeters(72.0)
    HUB_DISTANCE_FROM_ALLIANCE_WALL: meters = inchesToMeters(158.6)

    BUMP_WIDTH: meters = inchesToMeters(73.0)
    BUMP_DEPTH: meters = inchesToMeters(44.4)
    BUMP_HEIGHT: meters = inchesToMeters(6.513)
    BUMP_RAMP_ANGLE_DEGREES: float = 15.0

    TRENCH_WIDTH: meters = inchesToMeters(65.65)
    TRENCH_DEPTH: meters = inchesToMeters(47.0)
    TRENCH_HEIGHT: meters = inchesToMeters(40.25)
    TRENCH_CLEARANCE_WIDTH: meters = inchesToMeters(50.34)
    TRENCH_CLEARANCE_HEIGHT: meters = inchesToMeters(22.25)

    DEPOT_WIDTH: meters = inchesToMeters(42.0)
    DEPOT_DEPTH: meters = inchesToMeters(27.0)

    TOWER_WIDTH: meters = inchesToMeters(49.25)
    TOWER_DEPTH: meters = inchesToMeters(45.0)
    TOWER_HEIGHT: meters = inchesToMeters(78.25)
    TOWER_UPRIGHT_SPACING: meters = inchesToMeters(32.25)
    TOWER_RUNG_SPACING: meters = inchesToMeters(18.0)
    TOWER_LOW_RUNG_HEIGHT: meters = inchesToMeters(27.0)
    TOWER_MID_RUNG_HEIGHT: meters = inchesToMeters(45.0)
    TOWER_HIGH_RUNG_HEIGHT: meters = inchesToMeters(63.0)

    FUEL_DIAMETER: meters = inchesToMeters(5.91)
    FUEL_MASS: kilograms = lbsToKilograms(0.5)
    FUEL_COUNT_PER_FIELD: int = 504
    FUEL_MAX_PRELOAD: int = 8

    def rung_height(self, level: TowerRungLevel) -> meters | None:
        """Get the TOWER RUNG center height associated with a climb LEVEL.

        Args:
            level (TowerRungLevel): The climb LEVEL to look up. LEVEL_1 has no associated RUNG height
                (it only requires leaving the carpet/TOWER BASE), so it returns None.

        Returns:
            meters | None: RUNG center height in meters, or None for LEVEL_1.
        """
        match level:
            case TowerRungLevel.LEVEL_1:
                return None
            case TowerRungLevel.LEVEL_2:
                return self.TOWER_LOW_RUNG_HEIGHT
            case TowerRungLevel.LEVEL_3:
                return self.TOWER_MID_RUNG_HEIGHT
        raise ValueError(f"Unknown TowerRungLevel: {level}")


@dataclass(slots=True)
class Rebuilt2026MatchPeriods:
    """MATCH period durations for the 2026 REBUILT game (Game Manual Section 6.4, Table 6-2).

    Attributes:
        AUTO_PERIOD (seconds): Duration of the Autonomous Period. 20 seconds.
        TRANSITION_SHIFT (seconds): Duration of the TELEOP Transition Shift. 10 seconds.
        ALLIANCE_SHIFT_DURATION (seconds): Duration of each individual ALLIANCE SHIFT. 25 seconds.
        ALLIANCE_SHIFT_COUNT (int): Number of ALLIANCE SHIFTS per MATCH. 4.
        END_GAME_PERIOD (seconds): Duration of END GAME. 30 seconds.
    """

    AUTO_PERIOD: seconds = 20.0
    TRANSITION_SHIFT: seconds = 10.0
    ALLIANCE_SHIFT_DURATION: seconds = 25.0
    ALLIANCE_SHIFT_COUNT: int = 4
    END_GAME_PERIOD: seconds = 30.0

    @property
    def TELEOP_PERIOD(self) -> seconds:
        """Total TELEOP duration: Transition Shift + all ALLIANCE SHIFTS + End Game.

        Returns:
            seconds: Total TELEOP period length (140 seconds for 2026 REBUILT).
        """
        return self.TRANSITION_SHIFT + (self.ALLIANCE_SHIFT_DURATION * self.ALLIANCE_SHIFT_COUNT) + \
            self.END_GAME_PERIOD

    @property
    def MATCH_DURATION(self) -> seconds:
        """Total MATCH duration: AUTO + TELEOP.

        Returns:
            seconds: Total MATCH length (160 seconds / 2:40 for 2026 REBUILT).
        """
        return self.AUTO_PERIOD + self.TELEOP_PERIOD


@dataclass(slots=True)
class Rebuilt2026RobotLimits:
    """ROBOT construction size/weight/extension limits (Game Manual Section 8.1, rules R103-R107).

    Attributes:
        MAX_WEIGHT (kilograms): Maximum ROBOT weight excluding BUMPERS, battery, and location tags (R103).
            115.0 lb.
        MAX_STARTING_PERIMETER (meters): Maximum ROBOT PERIMETER in STARTING CONFIGURATION (R104). 110.0 in.
        MAX_STARTING_HEIGHT (meters): Maximum ROBOT height in STARTING CONFIGURATION (R104). 30.0 in.
        MAX_HORIZONTAL_EXTENSION (meters): Maximum horizontal extension beyond the ROBOT PERIMETER, in a
            single direction at a time (R105, R106). 12.0 in.
        MAX_ROBOT_HEIGHT (meters): Absolute maximum ROBOT height at any time, even when extended (R107).
            30.0 in — same limit as MAX_STARTING_HEIGHT, but enforced continuously, not just at MATCH start.
    """

    MAX_WEIGHT: kilograms = lbsToKilograms(115.0)
    MAX_STARTING_PERIMETER: meters = inchesToMeters(110.0)
    MAX_STARTING_HEIGHT: meters = inchesToMeters(30.0)
    MAX_HORIZONTAL_EXTENSION: meters = inchesToMeters(12.0)
    MAX_ROBOT_HEIGHT: meters = inchesToMeters(30.0)
