# New Command – frclib-6107

Create a new command called `${input:name}` in `src/lib_6107/commands/`.

## Single Command

Create `src/lib_6107/commands/${input:name}.py` based on `_command_template.py`:

```python
from commands2 import Command
from pathplannerlib.auto import NamedCommands

from lib_6107.commands.command import BaseCommand


class ${input:name}(BaseCommand):
    """TODO: Describe this command."""

    def __init__(self, container: 'RobotContainer', **_kwargs) -> None:
        super().__init__(container)
        self._container = container
        # TODO: store any needed subsystem references

    @staticmethod
    def pathplanner_register(container: 'RobotContainer') -> None:
        """Register this command with PathPlanner for use in auto routines."""
        def command(**kwargs) -> Command:
            return ${input:name}(container, **kwargs)
        NamedCommands.registerCommand(BaseCommand.get_class_name(), command())

    def initialize(self) -> None:
        super().initialize()  # Logs start time and SmartDashboard alert
        # TODO: setup on first run

    def execute(self) -> None:
        # TODO: main logic, called every cycle while scheduled
        pass

    def isFinished(self) -> bool:
        return True  # TODO: return True when done

    def end(self, interrupted: bool) -> None:
        # TODO: cleanup
        super().end(interrupted)  # Logs end time and SmartDashboard alert — MUST be last
```

## Command Group (Sequential)

Create `src/lib_6107/commands/${input:name}.py` based on `_commandgroup_template.py`:

```python
from typing import Optional
import commands2


class ${input:name}(commands2.SequentialCommandGroup):
    """TODO: Describe this command group."""

    def __init__(self, container, indent: Optional[int] = 0) -> None:
        super().__init__()
        self._name = self.__class__.__name__
        self.setName(self._name)
        self.container = container

        self.addCommands(commands2.PrintCommand(f"{'    ' * indent}** Started {self._name} **"))
        # TODO: self.addCommands(SubCommand(container, indent=indent+1))
        self.addCommands(commands2.PrintCommand(f"{'    ' * indent}** Finished {self._name} **"))
```

## Binding to a Button

In `RobotContainer._configure_driver_button_bindings_xbox()` or `_configure_operator_button_bindings_xbox()`:

```python
self._driver_controller.a().onTrue(${input:name}(self))
```

