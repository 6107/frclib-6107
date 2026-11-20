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
FieldLayout: the immutable geometry (size, origin and AprilTag poses) of one playing field.

Terminology (see ``lib_6107/field/README.md``):

* ``FieldLayout`` - data only. One instance per field variant (for example 2026 Welded vs AndyMark).
* ``FieldTag``    - one AprilTag (id + ``Pose3d``) on the field.
* ``GameField``   - the long lived object that *owns* the current ``FieldLayout`` (see ``game_field.py``).
* ``Field2d``     - the WPILib dashboard widget. It has nothing to do with this module.

All lengths are in meters. Tag poses are in the field coordinate system (blue alliance origin unless the
source data says otherwise).

NOTE: This module deliberately does not depend on ``robotpy_apriltag`` (``AprilTagFieldLayout`` was removed in
      RobotPy 2027). ``robotpy_fields`` is imported lazily, only by the helpers that need it, so the rest of the
      module can be imported and tested without it.
"""

import json
import logging
import math
import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from wpimath import Pose3d, Quaternion, Rotation3d, Translation3d
from wpimath.units import meters

from lib_6107.field.coordinates import DEFAULT_COORDINATES, FieldCoordinates

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldTag:
    """
    A single AprilTag on the field.

    :param tag_id: The AprilTag id printed on the tag
    :param pose: Pose of the tag in field coordinates (the tag's +X axis points out of the tag face)
    """

    tag_id: int
    pose: Pose3d


@dataclass(frozen=True, eq=False)
class FieldLayout:
    """
    Immutable description of a field: its size, origin and the AprilTags on it.

    Instances compare by identity (``eq=False``) on purpose. ``GameField`` uses identity to decide whether a
    ``set_*`` call really changed the layout, which is cheap and avoids comparing dozens of ``Pose3d`` objects.

    :param name: Human readable name, for example ``"2026 FRC Rebuilt Welded"``
    :param length: Field length (x maximum) in meters
    :param width: Field width (y maximum) in meters
    :param tags: Tags on the field, either a ``{id: FieldTag}`` mapping or any iterable of ``FieldTag``.
                 Duplicate ids keep the last entry
    :param origin: Origin the tag poses are expressed in (informational. It is already applied to the tag poses)
    :param season: Optional season, for example ``"2026"``
    :param game: Optional game name, for example ``"Rebuilt"``
    :param coordinates: Coordinate convention the tag poses use (changes in 2027, see ``coordinates.py``). The
                        loaders cannot detect this from the data, so they assume the 2026 convention unless told
                        otherwise
    """

    name: str
    length: meters
    width: meters
    tags: Mapping[int, FieldTag] = field(default_factory=dict)
    origin: Pose3d = field(default_factory=Pose3d)
    season: str = ""
    game: str = ""
    coordinates: FieldCoordinates = DEFAULT_COORDINATES

    def __post_init__(self) -> None:
        tags = self.tags
        if not isinstance(tags, Mapping):
            tags = {tag.tag_id: tag for tag in tags}

        # Frozen dataclass, so go through object.__setattr__. A read-only view keeps the layout immutable
        object.__setattr__(self, "tags", MappingProxyType(dict(tags)))

    # ------------------------------------------------------------------ #
    # Tag access

    @property
    def tag_ids(self) -> list[int]:
        """Sorted list of all tag ids on this field"""
        return sorted(self.tags)

    def __iter__(self) -> Iterator[FieldTag]:
        return iter(self.tags.values())

    def __len__(self) -> int:
        return len(self.tags)

    def has_tag(self, tag_id: int) -> bool:
        return tag_id in self.tags

    def get_tag_pose(self, tag_id: int) -> Pose3d | None:
        """
        :param tag_id: AprilTag id
        :return: The tag's field-relative pose, or None if this field has no such tag
        """
        tag = self.tags.get(tag_id)
        return tag.pose if tag is not None else None

    # ------------------------------------------------------------------ #
    # Factories

    @classmethod
    def from_robotpy_field(cls, rf_field: Any, coordinates: FieldCoordinates = DEFAULT_COORDINATES) -> FieldLayout:
        """
        Build a layout from a ``robotpy_fields.Field`` (the 2027 replacement for ``AprilTagFieldLayout``).

        :param rf_field: A ``robotpy_fields.Field`` instance
        :param coordinates: Coordinate convention of the data
        """
        # get_tag_pose() applies the field's origin, get_tags() may not. so use the former
        tags = []
        for rf_tag in rf_field.get_tags():
            pose = rf_field.get_tag_pose(rf_tag.id)
            tags.append(FieldTag(int(rf_tag.id), pose if pose is not None else rf_tag.pose))

        return cls(
            name=rf_field.get_name(),
            length=rf_field.get_length(),
            width=rf_field.get_width(),
            tags=tags,
            origin=rf_field.get_origin(),
            season=rf_field.get_season(),
            game=rf_field.get_game(),
            coordinates=coordinates,
        )

    @classmethod
    def from_field_id(cls, field_id: Any, coordinates: FieldCoordinates = DEFAULT_COORDINATES) -> FieldLayout:
        """
        Build a layout from one of the fields shipped with RobotPy (``robotpy_fields.FieldId``).

        :param field_id: For example ``FieldId.FRC_2026_REBUILT_WELDED``
        :param coordinates: Coordinate convention of the data
        :raises Exception: Whatever ``robotpy_fields`` raises if the field is unknown/unavailable
        """
        import robotpy_fields  # Lazy, see module docstring

        return cls.from_robotpy_field(robotpy_fields.get_field(field_id), coordinates)

    @classmethod
    def from_json(cls, path: str | os.PathLike, coordinates: FieldCoordinates = DEFAULT_COORDINATES) -> FieldLayout:
        """
        Load a layout from a JSON file. Two formats are understood:

        * The 2027 ``robotpy_fields`` format (``field-dimensions`` + ``field-tags``)
        * The legacy WPILib ``AprilTagFieldLayout`` format (``field`` + ``tags``), which is what the 2026 robot
          code deployed to ``deploy/fields/apriltags``

        :param path: File to read
        :param coordinates: Coordinate convention of the data
        :raises FileNotFoundError: if the file does not exist
        :raises ValueError: if the file is not valid JSON or is missing required data
        """
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}: not valid JSON: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected a JSON object at the top level")

        try:
            dims = data.get("field-dimensions", data.get("field"))
            raw_tags = data.get("field-tags", data.get("tags"))
            if dims is None or raw_tags is None:
                raise KeyError("field dimensions or tags")

            return cls(
                name=data.get("name") or os.path.splitext(os.path.basename(os.fspath(path)))[0],
                length=float(dims["length"]),
                width=float(dims["width"]),
                tags=[_tag_from_json(t) for t in raw_tags],
                season=str(data.get("season", "")),
                game=str(data.get("game", "")),
                coordinates=coordinates,
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"{path}: invalid or missing field data: {e!r}") from e

    # ------------------------------------------------------------------ #
    # Conversions

    def to_json(self, path: str | os.PathLike | None = None) -> str:
        """
        Serialize to the 2027 ``robotpy_fields`` JSON format.

        :param path: If given, the JSON is also written to this file
        :return: The JSON text
        """
        data = {
            "name": self.name,
            "season": self.season,
            "game": self.game,
            "field-dimensions": {"length": self.length, "width": self.width},
            "program": "frc",
            "field-tags": [_tag_to_json(self.tags[i]) for i in self.tag_ids],
        }
        text = json.dumps(data, indent=2)
        if path is not None:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        return text

    def to_robotpy_field(self) -> Any:
        """
        Convert to a ``robotpy_fields.Field``. This is the hook for vendor adapters (PhotonVision / Limelight)
        that need the library's type or its JSON.
        """
        import robotpy_fields  # Lazy, see module docstring

        tags = []
        for tag in self:
            rf_tag = robotpy_fields.FieldTag()
            rf_tag.id = tag.tag_id
            rf_tag.pose = tag.pose
            tags.append(rf_tag)

        return robotpy_fields.Field(self.name, self.season, self.game, None, self.length, self.width, "frc", tags)

    def __repr__(self) -> str:
        return f"FieldLayout(name={self.name!r}, length={self.length}, width={self.width}, tags={len(self.tags)})"


def _tag_from_json(entry: Mapping[str, Any]) -> FieldTag:
    pose = entry["pose"]
    t = pose["translation"]
    q = pose["rotation"]["quaternion"]
    # Quaternions in the files are only as exact as the writer, so normalize to keep Rotation3d happy
    w, x, y, z = (float(q[k]) for k in ("W", "X", "Y", "Z"))
    norm = math.sqrt(w * w + x * x + y * y + z * z)
    if norm == 0:
        raise ValueError(f"tag {entry['ID']}: zero length quaternion")

    return FieldTag(
        int(entry["ID"]),
        Pose3d(
            Translation3d(float(t["x"]), float(t["y"]), float(t["z"])),
            Rotation3d(Quaternion(w / norm, x / norm, y / norm, z / norm)),
        ),
    )


def _tag_to_json(tag: FieldTag) -> dict[str, Any]:
    t = tag.pose.translation()
    q = tag.pose.rotation().get_quaternion()
    return {
        "ID": tag.tag_id,
        "pose": {
            "translation": {"x": t.x, "y": t.y, "z": t.z},
            "rotation": {"quaternion": {"W": q.w, "X": q.x, "Y": q.y, "Z": q.z}},
        },
    }
