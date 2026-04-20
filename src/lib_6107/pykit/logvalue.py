from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Optional

# Mapping of LoggableType enum index to WPILOG/NT4 type strings
_WPILOG_TYPES = [
    "raw",
    "boolean",
    "int64",
    "float",
    "double",
    "string",
    "boolean[]",
    "int64[]",
    "float[]",
    "double[]",
    "string[]",
]

_NT4_TYPES = [
    "raw",
    "boolean",
    "int",
    "float",
    "double",
    "string",
    "boolean[]",
    "int[]",
    "float[]",
    "double[]",
    "string[]",
]


@dataclass(slots=True)
class LogValue:
    """
    Represents a value in the log table, encapsulating its type, a custom type string, and the value itself.
    """

    log_type: "LogValue.LoggableType"
    custom_type: str
    value: Any
    unit: Optional[str] = None

    def __init__(self, value: Any, type_str: str = "", unit: Optional[str] = None) -> None:
        """
        Initializes a LogValue, inferring the loggable type from the value's Python type.

        :param value: The value to be logged.
        :param type_str: An optional custom type string.
        :raises TypeError: If the value type is not supported.
        """
        self.value = value
        self.custom_type = type_str
        self.unit = unit

        # Type inference - bool must be checked before int since bool is subclass of int
        match value:
            case bool():
                self.log_type = LogValue.LoggableType.Boolean
            case int():
                self.log_type = LogValue.LoggableType.Integer
            case float():
                self.log_type = LogValue.LoggableType.Double
            case str():
                self.log_type = LogValue.LoggableType.String
            case bytes():
                self.log_type = LogValue.LoggableType.Raw
            case list():
                if len(value) == 0:
                    self.log_type = LogValue.LoggableType.IntegerArray

                elif all(isinstance(x, bool) for x in value):
                    self.log_type = LogValue.LoggableType.BooleanArray

                elif all(isinstance(x, int) for x in value):
                    self.log_type = LogValue.LoggableType.IntegerArray

                elif all(isinstance(x, float) for x in value):
                    self.log_type = LogValue.LoggableType.DoubleArray

                elif all(isinstance(x, str) for x in value):
                    self.log_type = LogValue.LoggableType.StringArray

                else:
                    raise TypeError("Unsupported list type for LogValue")
            case _:
                raise TypeError(f"Unsupported type for LogValue: {type(value)}")

    @staticmethod
    def withType(log_type: "LogValue.LoggableType",
                 data: Any, type_str: str = "", unit: Optional[str] = None) -> "LogValue":
        """
        Creates a LogValue with a specified loggable type.

        :param log_type: The `LoggableType` to assign.
        :param data: The value.
        :param type_str: An optional custom type string.
        :param unit: An optional custom unit string.

        :return: A new `LogValue` instance.
        """
        val = LogValue(1, type_str)
        val.log_type = log_type
        val.value = data
        val.unit = unit
        return val

    def getWPILOGType(self) -> str:
        """
        Gets the WPILOG type string for this value.

        :return: The custom type string if available, otherwise the default WPILOG type.
        """
        return self.custom_type if self.custom_type else self.log_type.getWPILOGType()

    def getNT4Type(self) -> str:
        """
        Gets the NT4 type string for this value.

        :return: The custom type string if available, otherwise the default NT4 type.
        """
        return self.custom_type if self.custom_type else self.log_type.getNT4Type()

    class LoggableType(Enum):
        """Enum for the different types of loggable values."""

        Raw = auto()
        Boolean = auto()
        Integer = auto()
        Float = auto()
        Double = auto()
        String = auto()
        BooleanArray = auto()
        IntegerArray = auto()
        FloatArray = auto()
        DoubleArray = auto()
        StringArray = auto()

        def getWPILOGType(self) -> str:
            """
            Returns the WPILOG type string corresponding to this loggable type.

            :return: The WPILOG type string.
            """
            return _WPILOG_TYPES[self.value - 1]

        def getNT4Type(self) -> str:
            """
            Returns the NT4 type string corresponding to this loggable type.

            :return: The NT4 type string.
            """
            return _NT4_TYPES[self.value - 1]

        @staticmethod
        def fromWPILOGType(type_str: str) -> "LogValue.LoggableType":
            """
            Converts a WPILOG type string to a `LoggableType`.

            :param type_str: The WPILOG type string.
            :return: The corresponding `LoggableType`, or `Raw` if not found.
            """
            return LogValue.LoggableType(_WPILOG_TYPES.index(type_str) + 1) if type_str in _WPILOG_TYPES \
                else LogValue.LoggableType.Raw

        @staticmethod
        def fromNT4Type(type_str: str) -> "LogValue.LoggableType":
            """
            Converts an NT4 type string to a `LoggableType`.

            :param type_str: The NT4 type string.
            :return: The corresponding `LoggableType`, or `Raw` if not found.
            """
            return LogValue.LoggableType(_NT4_TYPES.index(type_str) + 1) if type_str in _NT4_TYPES \
                else LogValue.LoggableType.Raw
