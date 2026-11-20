# lib_6107.field

Year-independent support for **the field** and **AprilTags**. Season specific data (which fields exist, game
logic such as zones/scoring locations) lives in the team's robot project and is handed to these objects.

> **Status:** The unit tests (`tests/field`) pass, but nothing here has run on a robot or with real vision
> hardware yet. The 2027 field coordinate system has changed but field data is not currently available, so
> the **2026 coordinates are in use** (see [Coordinate systems](#coordinate-systems)).

## Terminology

The word "field" meant three different things in the old code. Use these names:

| Name                    | What it is                                                                                      |
|-------------------------|-------------------------------------------------------------------------------------------------|
| `field2d`               | The WPILib `Field2d` dashboard widget showing the robot pose (`Robot.field2d`). Display only.   |
| `GameField`             | The long lived object that knows *which field we play on*. Owns the current `FieldLayout`.      |
| `FieldLayout`           | Immutable data: field name, length, width, origin, and the AprilTags (`FieldTag`).              |
| `FieldTag`              | One AprilTag: `tag_id` and its `Pose3d` on the field.                                           |
| `FieldSource`           | A *recipe* to obtain a layout (library id, deploy JSON file, or factory). One per field variant.|
| `robotpy_fields.Field`  | The 2027 library class. It replaces `AprilTagFieldLayout`. We convert to/from it; we do not pass it around. |

AprilTag ids are called `tag_id` everywhere (not `fiducial_id`, `april_tag_id`, ...).

## Objects

```
            +--------------------+   FieldSource list (year specific, given at init)
            |     GameField      |<----------------------------------------------+
            |  (year subclass)   |                                               |
            +---+------------+---+   load_layout()        +-------------------+  |
   periodic()   |            +--------------------------> |   FieldSource     |--+
 FieldSelector -+  owns                                   |    field_id       | file | factory
 (sim chooser)  v                                         +-------------------+
            +--------------------+
            |    FieldLayout     |-- FieldTag(tag_id, Pose3d) ...
            +--------------------+
                    |  register_callback(fn)  -> fn(FieldChange) on every set_*
                    v
          vision subsystems, estimators, dashboards, ...
```

| File              | Contents                                                                                      |
|-------------------|-----------------------------------------------------------------------------------------------|
| `game_field.py`   | `GameField`, `FieldChange`: current field, set/get, callbacks, alliance, periodic selector     |
| `layout.py`       | `FieldLayout`, `FieldTag`: data, JSON/robotpy_fields conversion                                |
| `sources.py`      | `FieldSource`, `load_layout()`: how to find the data (never raises, returns `None` on failure) |
| `selector.py`     | `FieldSelector`: simulation dashboard chooser of field variants                                |
| `flip.py`         | `FlipUtil`: mirror poses for the red alliance                                                  |
| `coordinates.py`  | `FieldCoordinates`, mirror helpers: the one place that knows the coordinate convention         |

## Quick start (year specific code)

Create a `GameField` subclass in your robot project, pass the season's sources, add the game logic:

```python
from lib_6107.field import FieldSource, GameField
from robotpy_fields import FieldId

SOURCES = [
    FieldSource("welded", "Welded", field_id=FieldId.FRC_2026_REBUILT_WELDED, deploy_file="2026-rebuilt-welded.json"),
    FieldSource(
        "andymark", "AndyMark", field_id=FieldId.FRC_2026_REBUILT_ANDY_MARK, deploy_file="2026-rebuilt-andymark.json"
    ),
]


class RebuiltField(GameField):
    def __init__(self, **kwargs):
        super().__init__(SOURCES, default="welded", default_length=16.54, default_width=8.07, **kwargs)

    def in_blue_alliance_zone(self, x):  # year specific game logic
        return x < 4.0
```

Then use it:

```python
game_field = RebuiltField()
game_field.field_length, game_field.field_width
game_field.get_tag_pose(10)  # Pose3d | None
game_field.layout  # FieldLayout (None only if even the default failed to load)
game_field.alliance  # wpilib Alliance | None
container.game_field  # RobotContainer exposes it; DriveSubsystem/Vision read it
```

Call `game_field.periodic()` every loop (the container does this) so the simulation chooser is polled.

### Loading order of a `FieldSource`

`load_layout()` tries, in order, the first that works: **`factory`** -> **`field_id`** (robotpy_fields) -> **`deploy_file`**
under `<deploy dir>/fields/apriltags/`. Each failure is logged and the next is tried. If all fail the result is
`None`; `GameField` then keeps the previous layout (or reports `default_length`/`default_width` at startup) so
the robot code keeps running. Provide a `deploy_file` as a fallback for when the library lacks a field.

`FieldLayout.from_json()` reads both the legacy `{"tags": ..., "field": ...}` (2026 deploy files) and the 2027
`{"field-tags": ..., "field-dimensions": ...}` formats.

## Changing the field at runtime

```python
game_field.set_field("andymark")  # a source key; returns True if it changed
game_field.set_field(FieldSource(...))  # or a source that was not in the initial list
game_field.set_layout(my_layout)  # your own FieldLayout (for example, new season data)
game_field.reload()  # re-read the current source and always notify
```

A failed load keeps the previous field and logs an error. In simulation, `FieldSelector` adds a **"Field
Selector"** dashboard chooser and `periodic()` applies the choice. It is off on a real robot
(`enable_selector=True/False` overrides).

## Callbacks

Anything that caches field data (vision, estimators) should register and not keep its own copy:

```python
unsubscribe = game_field.register_callback(self._on_field_change, notify_now=True)


def _on_field_change(self, change: FieldChange) -> None:
    change.previous_source, change.source  # FieldSource
    change.previous_layout, change.layout  # FieldLayout (previous_* is None for the notify_now call)
    self._estimator.update_tags(change.layout)


unsubscribe()  # or game_field.unregister_callback(fn)
```

* Fired after `set_field` / `set_layout` change something, and always after `reload`.
* `notify_now=True` also calls you immediately with the current field.
* A callback that raises is logged and does not stop other callbacks. Callbacks may (un)register callbacks.
* Use from the robot thread only.

`VisionSubsystem` registers `_on_field_change()` for you; override it. Vendor hooks: `FieldLayout.to_json()` (e.g.
Limelight `upload_fieldmap`) and `FieldLayout.to_robotpy_field()`.

## Coordinate systems

The coordinate system changes in 2027. `coordinates.py` is the single place that describes the convention and how
to mirror for the red alliance. Currently only `FieldCoordinates.BLUE_ORIGIN_2026` exists. When 2027 data is
released: add a member, add one `match` arm in each `mirror_*` function, and pass it as `coordinates=` to the
season's `GameField`. Always go through `game_field.coordinates` / `FlipUtil`; do not hard-code mirroring.

```python
flip = FlipUtil(game_field)
flip.field_pose(Pose2d(...))  # mirrored when we are red, unchanged when blue
```

## Testing

```
cd lib_6107
.venv\Scripts\python -m pytest tests\field -q
```

Tests use injected alliance providers, selectors and tiny fake layouts; no Driver Station or dashboard is needed.
`GameField(..., alliance_provider=lambda: Alliance.RED, enable_selector=False)` is the usual test setup.

## Known limits

* Untested with real vision: Limelight (`upload_fieldmap` expects Limelight's own `.fmap` format, `to_json()` may
  need a converter) and PhotonVision (`photonlibpy` 2027.0.0a2 still imports the removed `AprilTagFieldLayout`).
* 2027 coordinates, field sizes and tag data are not available yet.
* Zone helpers `in_blue_alliance_zone` / `in_red_alliance_zone` must be implemented by the season subclass.
