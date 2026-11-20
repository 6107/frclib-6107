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
from collections.abc import Callable
from typing import Any, ClassVar

import tunables

logger = logging.getLogger(__name__)


class _NumericEditBox[N: (int, float)]:
    """Base class for an Elastic-editable number published as a 2027 ``tunables`` value.

    Subclasses only select the numeric type through the class variables below. Remote edits
    arrive through ``on_tune``; values that are the wrong type or outside the optional
    min/max range are rejected and the published value is restored.
    """

    _KIND: ClassVar[str] = "NumericEditBox"
    _TYPE: ClassVar[type]
    _DEFAULT: ClassVar[Any]
    _ADD: ClassVar[Callable[..., Any]]

    def __init__(self, name: str, initial_value: N | None, minimum_value: N | None, maximum_value: N | None) -> None:
        self._name: str = name
        self._value: N | None = None
        self._min = minimum_value
        self._max = maximum_value
        self._tunable = None

        self.set_value(initial_value)
        self._tunable = self._ADD(
            name, self._value if self._value is not None else self._DEFAULT, on_tune=self._on_tune
        )

    def _is_valid_type(self, value) -> bool:
        # bool is an int subclass, and an int is not a float: require the exact numeric kind
        return isinstance(value, self._TYPE) and not isinstance(value, bool)

    def __str__(self) -> str:
        return str(self._value)

    def __repr__(self) -> str:
        return f"{self._KIND}({self._name}, value={self._value}, min={self._min}, max={self._max})"

    @property
    def name(self) -> str:
        """Name of the tunable, relative to the tunables root table."""
        return self._name

    @property
    def value(self) -> N | None:
        """The most recent accepted value, or None if none has been accepted yet."""
        return self._value

    def _on_tune(self, value) -> None:
        self.set_value(value)
        if self._tunable is not None and self._value is not None and value != self._value:
            self._tunable.set(self._value)  # Restore the last accepted value in Elastic

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


class IntegerEditBox(_NumericEditBox[int]):
    """Integer value that can be edited from Elastic via ``tunables``."""

    _KIND = "IntegerEditBox"
    _TYPE = int
    _DEFAULT = 0
    _ADD = staticmethod(tunables.add_int)

    def __init__(
        self,
        name: str,
        initial_value: int | None = None,
        minimum_value: int | None = None,
        maximum_value: int | None = None,
    ) -> None:
        super().__init__(name, initial_value, minimum_value, maximum_value)


class FloatEditBox(_NumericEditBox[float]):
    """Floating point value that can be edited from Elastic via ``tunables``."""

    _KIND = "FloatEditBox"
    _TYPE = float
    _DEFAULT = 0.0
    _ADD = staticmethod(tunables.add_double)

    def __init__(
        self,
        name: str,
        initial_value: float | None = None,
        minimum_value: float | None = None,
        maximum_value: float | None = None,
    ) -> None:
        super().__init__(name, initial_value, minimum_value, maximum_value)
