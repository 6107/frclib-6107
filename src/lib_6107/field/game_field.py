# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
"""
GameField: the one object that knows "which field are we playing on".

It owns the current ``FieldLayout`` (size + AprilTags), tells you the alliance, and notifies interested parties
(vision subsystems, pose estimators, dashboards, ...) when the field changes. It is year independent. A
year-specific subclass (for example ``RebuiltField``) adds game logic (zones, scoring locations, shift timing) and
passes that year's ``FieldSource`` list to ``__init__``.

Not to be confused with ``wpilib.Field2d`` (the dashboard widget, ``field2d`` in our code).

Threading: like the rest of the robot code this is expected to be used from the robot thread only.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from wpilib import Alliance, Field2d
from wpimath import Pose3d
from wpimath.units import meters

from lib_6107.field.coordinates import DEFAULT_COORDINATES, FieldCoordinates
from lib_6107.field.layout import FieldLayout, FieldTag
from lib_6107.field.selector import FieldSelector
from lib_6107.field.sources import FieldSource, load_layout

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldChange:
    """
    Passed to callbacks registered with ``GameField.register_callback()``.

    ``previous_*`` is None the first time (``notify_now=True``) or when no layout was loaded before.
    ``layout`` is None only if the field is now unusable, which currently never happens (a failed load keeps the
    previous layout).
    """

    previous_source: FieldSource | None
    source: FieldSource
    previous_layout: FieldLayout | None
    layout: FieldLayout | None

    #
    # TODO: For the Elastic dashboard, the field orientation is read only. So it cannot
    #       be flipped automatically. Current suggestions is to have a "Blue" and a "Red"
    #       tab for automation or teleop and switch to those tabs automatically.
    #       That would be nice to have.


FieldCallback = Callable[[FieldChange], None]


class GameField:
    """
    Year independent field object. See the module docstring and ``lib_6107/field/README.md``.

    :param sources: Selectable field variants for the year (at least one). The first is the default unless
                    ``default`` is given
    :param default: Key of the default source
    :param default_length: Field length (x) in meters to report when no layout could be loaded
    :param default_width: Field width (y) in meters to report when no layout could be loaded
    :param coordinates: Coordinate convention in use (it changes in 2027, see ``coordinates.py``)
    :param enable_selector: Create the dashboard field selector. None (default) means "only in simulation"
    :param selector: Inject a selector (tests). Overrides ``enable_selector``
    :param alliance_provider: ``() -> Alliance | None``. Defaults to the Driver Station alliance
    :param deploy_dir: Deploy directory for the JSON fallback. Defaults to ``wpilib.get_deploy_directory()``
    """

    def __init__(
        self,
        sources: Sequence[FieldSource],
        default: str | None = None,
        *,
        default_length: meters = 0.0,
        default_width: meters = 0.0,
        coordinates: FieldCoordinates = DEFAULT_COORDINATES,
        enable_selector: bool | None = None,
        selector: FieldSelector | None = None,
        alliance_provider: Callable[[], Alliance | None] | None = None,
        deploy_dir: str | None = None,
    ):
        if not sources:
            raise ValueError("GameField requires at least one FieldSource")

        keys = [s.key for s in sources]
        if len(set(keys)) != len(keys):
            raise ValueError(f"GameField sources must have unique keys: {keys}")

        self._sources: tuple[FieldSource, ...] = tuple(sources)
        self._default_length = default_length
        self._default_width = default_width
        self._coordinates = coordinates
        self._alliance_provider = alliance_provider or _driver_station_alliance
        self._deploy_dir = deploy_dir
        self._callbacks: list[FieldCallback] = []

        default_source = self._find_source(default) if default is not None else self._sources[0]
        self._source: FieldSource = default_source
        self._layout: FieldLayout | None = load_layout(default_source, deploy_dir)

        if selector is None and (enable_selector if enable_selector is not None else _is_simulation()):
            selector = FieldSelector(self._sources, default_source.key)
        self._selector = selector
        self._field2d = Field2d()

    # ------------------------------------------------------------------ #
    # Current field (get)

    @property
    def field2d(self) -> Field2d:
        """2D representation of game field for dashboards."""
        return self._field2d

    @property
    def sources(self) -> tuple[FieldSource, ...]:
        """All selectable field variants"""
        return self._sources

    @property
    def source(self) -> FieldSource:
        """The current field variant"""
        return self._source

    @property
    def layout(self) -> FieldLayout | None:
        """The current layout. None only if even the default source failed to load"""
        return self._layout

    @property
    def coordinates(self) -> FieldCoordinates:
        return self._coordinates

    def get_field(self) -> FieldSource:
        """The current field variant (same as ``source``)"""
        return self._source

    @property
    def field_length(self) -> meters:
        """Field length (x maximum). Falls back to ``default_length`` when there is no layout"""
        return self._layout.length if self._layout else self._default_length

    @property
    def field_width(self) -> meters:
        """Field width (y maximum). Falls back to ``default_width`` when there is no layout"""
        return self._layout.width if self._layout else self._default_width

    @property
    def origin(self) -> Pose3d | None:
        return self._layout.origin if self._layout else None

    @property
    def tags(self) -> list[FieldTag]:
        """All AprilTags on the current field (empty if no layout)"""
        return list(self._layout) if self._layout else []

    def get_tag_pose(self, tag_id: int) -> Pose3d | None:
        """Pose of an AprilTag on the current field, None if unknown tag or no layout"""
        return self._layout.get_tag_pose(tag_id) if self._layout else None

    # ------------------------------------------------------------------ #
    # Alliance

    @property
    def alliance(self) -> Alliance | None:
        """Our alliance, None if the Driver Station/FMS has not told us yet"""
        return self._alliance_provider()

    @property
    def is_red_alliance(self) -> bool:
        return self.alliance == Alliance.RED

    @property
    def is_blue_alliance(self) -> bool:
        return self.alliance == Alliance.BLUE

    # ------------------------------------------------------------------ #
    # Change the field (set)

    def set_field(self, field: str | FieldSource) -> bool:
        """
        Switch to a different field variant and notify callbacks.

        :param field: A source key (one of ``sources``) or a ``FieldSource`` that is not in the list
        :return: True if the field changed. False if it is already the current field or the new one failed
                 to load (the previous field is kept and an error is logged)
        :raises KeyError: for an unknown key
        """
        source = self._find_source(field) if isinstance(field, str) else field
        if source.key == self._source.key and source is self._source:
            return False

        layout = load_layout(source, self._deploy_dir)
        if layout is None:
            logger.error(f"Field '{source.key}' could not be loaded. Staying with '{self._source.key}'")
            return False

        self._apply(source, layout)
        return True

    def set_layout(self, layout: FieldLayout, source: FieldSource | None = None) -> bool:
        """
        Use a layout you built yourself (for example from new season data) and notify callbacks.

        :param layout: The new layout
        :param source: Optional source it belongs to. Defaults to a generated ``"custom"`` source
        :return: True if the layout changed
        """
        if layout is self._layout and (source is None or source is self._source):
            return False

        if source is None:
            source = FieldSource(key="custom", name=layout.name, factory=lambda: layout)

        self._apply(source, layout)
        return True

    def reload(self) -> bool:
        """
        Reload the current source from disk/library and always notify callbacks (the data may have changed).

        :return: True if the reload worked. On failure the previous layout is kept
        """
        layout = load_layout(self._source, self._deploy_dir)
        if layout is None:
            logger.error(f"Reload of field '{self._source.key}' failed. Keeping the previous layout")
            return False

        self._apply(self._source, layout)
        return True

    # ------------------------------------------------------------------ #
    # Callbacks

    def register_callback(self, func: FieldCallback, *, notify_now: bool = False) -> Callable[[], None]:
        """
        Be told whenever the field (source or layout) changes.

        :param func: ``func(change: FieldChange)``. An exception in a callback is logged and does not stop the
                     other callbacks
        :param notify_now: Also call ``func`` immediately with the current field. Handy for subsystems that need
                           to load the field they are created after
        :return: A function that unregisters the callback
        """
        self._callbacks.append(func)
        if notify_now:
            self._notify_one(func, FieldChange(None, self._source, None, self._layout))

        return lambda: self.unregister_callback(func)

    def unregister_callback(self, func: FieldCallback) -> None:
        """Remove a callback. Unknown callbacks are ignored"""
        if func in self._callbacks:
            self._callbacks.remove(func)

    # ------------------------------------------------------------------ #
    # Periodic

    def periodic(self) -> None:
        """Call every robot loop. Applies a new dashboard field selection (if the selector is enabled)"""
        if self._selector is None:
            return

        key = self._selector.poll()
        if key is not None:
            self.set_field(key)

    # ------------------------------------------------------------------ #
    # Year-specific hooks

    def in_blue_alliance_zone(self, x: meters) -> bool:
        raise NotImplementedError("in_blue_alliance_zone: Implement in subclass")

    def in_red_alliance_zone(self, x: meters) -> bool:
        raise NotImplementedError("in_red_alliance_zone: Implement in subclass")

    # ------------------------------------------------------------------ #
    # Internals

    def _find_source(self, key: str) -> FieldSource:
        for source in self._sources:
            if source.key == key:
                return source
        raise KeyError(f"Unknown field '{key}'. Known fields: {[s.key for s in self._sources]}")

    def _apply(self, source: FieldSource, layout: FieldLayout) -> None:
        change = FieldChange(self._source, source, self._layout, layout)
        self._source = source
        self._layout = layout
        logger.info(f"Field is now '{source.key}' ({layout})")

        # Iterate over a copy so callbacks may (un)register callbacks
        for func in list(self._callbacks):
            self._notify_one(func, change)

    @staticmethod
    def _notify_one(func: FieldCallback, change: FieldChange) -> None:
        try:
            func(change)
        except Exception:
            logger.exception(f"Field callback {func!r} failed")


def _driver_station_alliance() -> Alliance | None:
    from wpilib import DriverStationBackend  # Lazy so tests can substitute a provider without a DS

    return DriverStationBackend.get_alliance()


def _is_simulation() -> bool:
    from wpilib import RobotBase

    return RobotBase.is_simulation()


__all__: list[str] = ["FieldCallback", "FieldChange", "GameField"]
