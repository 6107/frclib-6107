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
FieldSource: describes one selectable field variant and knows how to turn it into a ``FieldLayout``.

A year-specific module (for example ``robot_2027/field/field_2026.py``) builds a list of ``FieldSource`` objects and
hands it to ``GameField``. Each source can provide its data in up to three ways. They are tried in this order and
the first one that works wins:

1. ``factory``     - any callable returning a ``FieldLayout`` (custom/hand built or test data)
2. ``field_id``    - a ``robotpy_fields.FieldId`` shipped with RobotPy (preferred for official fields)
3. ``deploy_file`` - a JSON file in ``<deploy dir>/fields/apriltags`` (fallback when the library is missing the
                     field, or has not been updated yet, e.g. a new season alpha)
"""

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from lib_6107.field.coordinates import DEFAULT_COORDINATES, FieldCoordinates
from lib_6107.field.layout import FieldLayout

logger = logging.getLogger(__name__)

#: Sub-directory of the robot's deploy directory that holds fallback AprilTag JSON files
DEPLOY_SUBDIRECTORY = os.path.join("fields", "apriltags")


@dataclass(frozen=True)
class FieldSource:
    """
    One selectable field variant (for example "Rebuilt (Welded)").

    :param key: Short unique id used by ``GameField.set_field()`` and the dashboard selector
    :param name: Human readable name shown on the dashboard
    :param field_id: Optional ``robotpy_fields.FieldId`` for this variant
    :param deploy_file: Optional JSON file name inside ``<deploy>/fields/apriltags``
    :param factory: Optional callable that returns the ``FieldLayout`` directly
    :param coordinates: Coordinate convention the source data uses
    """

    key: str
    name: str
    field_id: Any | None = None
    deploy_file: str | None = None
    factory: Callable[[], FieldLayout] | None = None
    coordinates: FieldCoordinates = DEFAULT_COORDINATES

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("FieldSource requires a non-empty key")


def load_layout(source: FieldSource, deploy_dir: str | os.PathLike | None = None) -> FieldLayout | None:
    """
    Load the layout for a source. This never raises: every failure is logged and the next method is tried.

    :param source: Source to load
    :param deploy_dir: Robot deploy directory. Defaults to ``wpilib.get_deploy_directory()``
    :return: The layout or None if no method worked
    """
    if source.factory is not None:
        try:
            layout = source.factory()
            if layout is not None:
                logger.info(f"Field '{source.key}': layout created by factory")
                return layout
        except Exception as e:
            logger.warning(f"Field '{source.key}': factory failed: {e!r}")

    if source.field_id is not None:
        try:
            layout = FieldLayout.from_field_id(source.field_id, source.coordinates)
            logger.info(f"Field '{source.key}': layout loaded from robotpy_fields ({source.field_id})")
            return layout
        except Exception as e:
            logger.warning(f"Field '{source.key}': robotpy_fields load of {source.field_id} failed: {e!r}")

    if source.deploy_file:
        try:
            directory = deploy_dir if deploy_dir is not None else _default_deploy_dir()
            path = os.path.join(directory, DEPLOY_SUBDIRECTORY, source.deploy_file)
            layout = FieldLayout.from_json(path, source.coordinates)
            logger.info(f"Field '{source.key}': layout loaded from {path}")
            return layout
        except Exception as e:
            logger.warning(f"Field '{source.key}': deploy file '{source.deploy_file}' failed: {e!r}")

    logger.error(f"Field '{source.key}': no layout could be loaded")
    return None


def _default_deploy_dir() -> str:
    from wpilib import get_deploy_directory  # Lazy so the module imports without a robot environment

    return get_deploy_directory()
