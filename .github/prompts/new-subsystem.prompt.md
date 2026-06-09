# New Subsystem – frclib-6107

Create a new subsystem called `${input:name}` in `src/lib_6107/subsystems/${input:name}/`.

## Steps

1. Create directory `src/lib_6107/subsystems/${input:name}/`
2. Create `src/lib_6107/subsystems/${input:name}/__init__.py` (empty or with public exports)
3. Create `src/lib_6107/subsystems/${input:name}/${input:name}.py` with this structure:

```python
import logging
from typing import Optional

from wpilib import RobotBase
from wpimath.units import seconds

from lib_6107.pykit.logger import Logger
from lib_6107.subsystems.subsystem import SubsystemBase

logger = logging.getLogger(__name__)


class ${input:name}Subsystem(SubsystemBase):
    """TODO: Describe this subsystem."""

    def __init__(self, container: 'RobotContainer') -> None:
        self._initialized = False                          # MUST be first
        super().__init__(container, "${input:name}", "${input:name}/subsystem")

        # Hardware init goes here (motors, sensors, encoders)
        # ...

        self._initialized = True                           # MUST be last

    def periodic(self) -> None:
        if not self._initialized:
            return
        Logger.recordOutput("${input:name}/ExampleValue", 0.0)

    def stop(self) -> None:
        """Zero all motor/actuator power."""
        pass  # TODO: stop motors

    def fault_detection(self, state: str, clear: Optional[bool] = True,
                        notify: Optional[bool] = True) -> None:
        """Read and optionally clear device faults."""
        pass  # TODO: read device faults, call logger.warning() if found

    def record_metadata(self) -> None:
        """Log firmware versions and device info at startup."""
        Logger.recordMetadata("${input:name}/FirmwareVersion", "unknown")

    def sim_init(self, physics_controller) -> None:
        super().sim_init(physics_controller)
        # TODO: simulation-only setup

    def update_sim(self, now: float, tm_diff: float):
        return None  # Return ampere draw if applicable
```

4. Register the subsystem in the team's `RobotContainer.subsystem_init()`:

```python
self._${input:name} = ${input:name}Subsystem(self)
```

5. Create a test file at `tests/subsystems/${input:name}/test_${input:name}.py`.

## Reference

See `src/lib_6107/subsystems/gyro/` for a complete real + simulation example.

