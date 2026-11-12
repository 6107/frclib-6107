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

import logging
from typing import SupportsFloat, SupportsInt

import tunables

logger = logging.getLogger(__name__)


class _NumericEditBox:
    """Base class for a dashboard-editable number published as a 2027 ``tunables`` value.

    Remote edits arrive through ``on_tune``; values that are the wrong type or outside the
    optional min/max range are rejected and the published value is restored.
    """

    _KIND = "NumericEditBox"

    def __init__(self, name: str, initial_value, minimum_value, maximum_value) -> None:
        self._name: str = name
        self._value = None
        self._min = minimum_value
        self._max = maximum_value
        self._tunable = None

        self.set_value(initial_value)
        self._tunable = self._publish(name, self._value if self._value is not None else self._default())

    def _publish(self, name: str, value):
        raise NotImplementedError

    def _default(self):
        raise NotImplementedError

    def _is_valid_type(self, value) -> bool:
        raise NotImplementedError

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{self._KIND}({self._name}, value={self._value}, min={self._min}, max={self._max})"

    @property
    def name(self) -> str:
        """Name of the tunable, relative to the tunables root table."""
        return self._name

    @property
    def value(self):
        """The most recent accepted value, or None if none has been accepted yet."""
        return self._value

    def _on_tune(self, value) -> None:
        self.set_value(value)
        if self._tunable is not None and self._value is not None and value != self._value:
            self._tunable.set(self._value)  # Restore the last accepted value on the dashboard

    def set_value(self, value) -> None:
        """Validate and store a new value.

        Args:
            value: Candidate value. Invalid types or out-of-range values are logged and ignored.
        """
        if not self._is_valid_type(value):
            logger.error(f"{self._name} {self._KIND}: Invalid type {type(value)}")
        elif self._min is not None and value < self._min:
            logger.error(f"{self._name} {self._KIND}: Value too small. {value} < {self._min}")
        elif self._max is not None and value > self._max:
            logger.error(f"{self._name} {self._KIND}: Value too large. {value} > {self._max}")
        else:
            self._value = value
            if self._tunable is not None:
                self._tunable.set(value)


class IntegerEditBox(_NumericEditBox):
    """Integer value that can be edited from a dashboard via ``tunables``."""

    _KIND = "IntegerEditBox"

    def __init__(
        self,
        name: str,
        initial_value: int | None = None,
        minimum_value: int | None = None,
        maximum_value: int | None = None,
    ) -> None:
        super().__init__(name, initial_value, minimum_value, maximum_value)

    def _publish(self, name: str, value: int):
        return tunables.add_int(name, value, on_tune=self._on_tune)

    def _default(self) -> int:
        return 0

    def _is_valid_type(self, value: SupportsInt) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)


class FloatEditBox(_NumericEditBox):
    """Floating point value that can be edited from a dashboard via ``tunables``."""

    _KIND = "FloatEditBox"

    def __init__(
        self,
        name: str,
        initial_value: float | None = None,
        minimum_value: float | None = None,
        maximum_value: float | None = None,
    ) -> None:
        super().__init__(name, initial_value, minimum_value, maximum_value)

    def _publish(self, name: str, value: float):
        return tunables.add_double(name, value, on_tune=self._on_tune)

    def _default(self) -> float:
        return 0.0

    def _is_valid_type(self, value: SupportsFloat) -> bool:
        return isinstance(value, float)
