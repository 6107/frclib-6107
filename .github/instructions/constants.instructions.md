---
applyTo: "**/constants.py"
---

## Constants Rules – frclib-6107

### Core Rule

**Never modify `src/lib_6107/constants.py` default values.** These are library defaults. Teams always create a subclass:

```python
# In team's robot project, NOT in lib_6107
from lib_6107.constants import RobotConstants
from wpimath.units import inchesToMeters

@dataclass(slots=True)
class MyCyberJagzzConstants(RobotConstants):
    ROBOT_MASS: kilograms = lbsToKilograms(130)
    MAX_SPEED: meters_per_second = 4.73       # From Tuner-X characterization
    WHEEL_RADIUS: meters = inchesToMeters(2)
```

Pass to `Robot.__init__()`:

```python
Robot("2026", robot_constants=MyCyberJagzzConstants())
```

### Three Dataclasses

| Class                 | Override for...                                                           |
|-----------------------|---------------------------------------------------------------------------|
| `RobotConstants`      | Physical dimensions, motor limits, loop periods, controller ports         |
| `SimulationConstants` | Alliance starting poses (update for each season's field)                  |
| `NetworkConstants`    | Team number — use `net_constants.team = "NNNN"` setter to cascade all IPs |

### NetworkConstants Team Setter

Setting `network_constants.team = "6107"` automatically updates all derived addresses (`ROBORIO_STATIC`, `ROBORIO_MDMS`,
radio IPs, etc.). Always use the setter, never patch individual fields.

### ROBOT_MODE Global

`ROBOT_MODE` is set **once** at import time:

- `RobotModes.REAL` if `RobotBase.isReal()` is True
- `RobotModes.REPLAY` if `LOG_PATH` env var is set and non-empty
- `RobotModes.SIMULATION` otherwise

Do not reassign `ROBOT_MODE` at runtime. Use `match ROBOT_MODE:` for branching.

