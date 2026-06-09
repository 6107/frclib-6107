---
applyTo: "src/**/commands/**/*.py"
---

## Command Rules – frclib-6107

### Mandatory Structure

- All commands extend `BaseCommand` from `lib_6107.commands.command` — never `commands2.Command` directly.
- `BaseCommand.__init__(target)` accepts either a `RobotContainer` or a `DriveSubsystem` as `target`.
- Always call `super().__init__(container)` in `__init__`.
- Always call `super().initialize()` at the **start** of `initialize()`.
- Always call `super().end(interrupted)` at the **end** of `end()`.

### Command Templates

Copy the appropriate template rather than writing from scratch:

- **Single command:** `src/lib_6107/commands/_command_template.py` → extend `BaseCommand`
- **Sequential group:** `src/lib_6107/commands/_commandgroup_template.py` → extend `commands2.SequentialCommandGroup`

Remove the `raise NotImplementedError(...)` line from the template after copying.

### PathPlanner Registration

If the command should be usable from PathPlanner auto paths, add a static factory:

```python
@staticmethod
def pathplanner_register(container: RobotContainer) -> None:
    NamedCommands.registerCommand(BaseCommand.get_class_name(),
                                  MyCommand(container))
```

Call `MyCommand.pathplanner_register(container)` from `RobotContainer.__init__()`.

### Button Bindings

- Bind to Xbox controller events in `RobotContainer._configure_driver_button_bindings_xbox()` or
  `_configure_operator_button_bindings_xbox()`.
- Use `CommandXboxController` (from `commands2.button`) — not the raw `XboxController`.
- Common triggers: `.onTrue()`, `.whileTrue()`, `.onFalse()`, `.toggleOnTrue()`.

### Telemetry

Command activity is **automatically** tracked by `Robot.robotInit()` via `CommandScheduler` callbacks — no manual Logger
calls needed inside individual commands. `Logger.recordOutput("Commands/<name>", True/False)` is set on
schedule/finish/interrupt.

