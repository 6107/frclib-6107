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
FieldSelector: lets an operator pick which field variant (for example Welded or AndyMark) is in use.

This is a thin wrapper around ``LoggedDashboardChooser`` (so the selection is logged and replayable). It is only
created in simulation by default (see ``GameField``); on a real robot the default field is used.

The chooser is injectable so unit tests do not need a Elastic.
"""

import logging
from collections.abc import Callable, Sequence
from typing import Any

from lib_6107.field.sources import FieldSource

logger = logging.getLogger(__name__)

#: Default Elastic name of the chooser
DEFAULT_SELECTOR_NAME = "Field Selector"


def _default_chooser_factory(name: str) -> Any:
    from lib_6107.pykit.networktables.loggeddashboardchooser import LoggedDashboardChooser

    return LoggedDashboardChooser(name)


class FieldSelector:
    """
    Elastic chooser of field variants. Call ``poll()`` periodically (``GameField.periodic()`` does this).

    :param sources: Selectable sources. The one matching ``default_key`` is the Elastic default
    :param default_key: Key of the default source
    :param name: Elastic name of the chooser
    :param chooser_factory: ``name -> chooser`` callable. Anything with ``set_default_option(name, value)``,
                            ``add_option(name, value)`` and ``get_selected()`` works (used for tests)
    """

    def __init__(
        self,
        sources: Sequence[FieldSource],
        default_key: str,
        name: str = DEFAULT_SELECTOR_NAME,
        chooser_factory: Callable[[str], Any] | None = None,
    ):
        self._chooser = (chooser_factory or _default_chooser_factory)(name)
        self._last_key: str = default_key

        for source in sources:
            if source.key == default_key:
                self._chooser.set_default_option(source.name, source.key)
            else:
                self._chooser.add_option(source.name, source.key)

    @property
    def selected_key(self) -> str | None:
        """Key currently selected on the Elastic (None if the chooser has no selection yet)"""
        return self._chooser.get_selected()

    def poll(self) -> str | None:
        """
        :return: The key of the newly selected source if the operator changed the selection since the last
                 call, otherwise None
        """
        selected = self.selected_key
        if selected is None or selected == self._last_key:
            return None

        logger.info(f"Field selector changed: {self._last_key} -> {selected}")
        self._last_key = selected
        return selected
