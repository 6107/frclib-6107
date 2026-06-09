---
applyTo: "**/*.py"
---

## Python Style – frclib-6107

- Python 3.14+ required. Use type hints on all public methods and class attributes.
- Line length: 120 characters (matches `[tool.ruff] line-length = 120` in `pyproject.toml`).
- Use `wpimath.units` type aliases in signatures: `meters`, `seconds`, `kilograms`, `meters_per_second`,
  `radians_per_second`, etc.
- Use `wpimath.units` conversion helpers in constants: `inchesToMeters()`, `lbsToKilograms()`, `rotationsToRadians()`.
- Each module must have a module-level docstring describing its purpose.
- Use `logging.getLogger(__name__)` — never use bare `print()` for debug output; pykit intercepts `print()` but it
  degrades performance.
- Use `Optional[T]` or `T | None` for nullable types; prefer `T | None` in Python 3.14.
- All constants dataclasses use `@dataclass(slots=True)` for performance.
- Import order: stdlib → third-party (wpilib, commands2, phoenix6, rev) → local (`lib_6107.*`).
- Prefer `match ROBOT_MODE:` over if/elif chains for mode-specific logic.

