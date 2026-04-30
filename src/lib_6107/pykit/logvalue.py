"""
Log Value Module for Type-Safe Telemetry

This module provides LogValue, a wrapper class for robot telemetry values that enforces
type safety and maps between different logging backend type systems. It enables seamless
conversion between Python types and the formats expected by WPILib logging systems.

Key Features:
- Automatic type inference: Detects Python type and maps to LoggableType
- Dual backend support: Maintains mappings for both WPILOG (USB/local storage) and NT4 (NetworkTables)
- Type consistency: Prevents silent type mismatches in logged data
- Custom types: Supports WPILib struct types and custom domain-specific types
- Unit support: Stores physical units for visualization in dashboards

Type System:
LogValue bridges three type representations:
1. Python types (bool, int, float, str, bytes, list) - Runtime representation
2. WPILib types ("boolean", "int64", "double", etc.) - USB log file format
3. NetworkTables types ("boolean", "int", "double", etc.) - NT4 protocol format

A single LogValue instance tracks all three representations to enable cross-platform
logging and replay with AdvantageScope and SmartDashboard.
"""

from dataclasses import dataclass
from enum import auto, Enum
from typing import Any, Optional

#: Mapping from LoggableType enum values to WPILib WPILOG type strings.
#: Used when writing to .wpilog files (USB storage or local replay logs).
#: Index order matches LoggableType enum values (Raw=1, Boolean=2, etc.).
_WPILOG_TYPES = [
    "raw",
    """...existing type mappings..."""
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

#: Mapping from LoggableType enum values to NetworkTables (NT4) type strings.
#: Used when publishing to NetworkTables (real-time dashboard streaming).
#: Differences from WPILOG: "int" instead of "int64", "float[]" instead of "float[]".
#: Index order matches LoggableType enum values (Raw=1, Boolean=2, etc.).
_NT4_TYPES = [
    "raw",
    """...existing type mappings..."""
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
    A type-safe wrapper for telemetry values with support for multiple logging backends.
    
    LogValue encapsulates a value along with its type information for use in the pykit
    logging system. It maintains bidirectional conversion between Python runtime types
    and the type formats required by WPILib's WPILOG and NetworkTables (NT4) backends.
    
    Key Design:
    - Type Safety: The log_type is inferred at construction and locked to prevent
      accidental type mismatches. Once a LogValue is created with a given type,
      that type is definitive for that entry.
    - Custom Types: Supports custom_type strings for specialized types (e.g., WPILib
      structs like "struct:Pose2d", domain-specific types like "geometry" or "motor_state").
    - Units: Stores physical units (e.g., "meters", "RPM") for dashboard visualization.
    - Backend Agnostic: Methods exist to get type strings for both WPILOG and NT4,
      allowing the same LogValue to be published to different backends.
    
    Supported Value Types:
    - Primitives: bool, int, float, str, bytes
    - Arrays: list[bool], list[int], list[float], list[str]
    - Empty Arrays: Supported (type inferred as IntegerArray by default)
    - Custom: WPILib structs via custom_type override
    
    Attributes:
        log_type (LoggableType): The inferred or assigned type of the value.
            Determines how the value is serialized and interpreted during replay.
        custom_type (str): An optional custom type string for specialized types.
            Examples: "struct:Pose2d" for WPILib structs, "bitmask" for bitwise fields.
            If non-empty, overrides the default type strings from log_type.
        value (Any): The actual data to be logged. Type must match log_type.
        unit (Optional[str]): Optional unit string for physical quantities.
            Examples: "meters", "meters/second", "RPM", "degrees", "volts".
            Used for dashboard display and automatic unit conversion.
    
    Example:
        ```python
        # Auto-infer type from Python value
        lv1 = LogValue(3.5)  # Creates Double type
        lv2 = LogValue([1, 2, 3])  # Creates IntegerArray type
        lv3 = LogValue(True)  # Creates Boolean type
        
        # Create with custom type and unit
        lv4 = LogValue(5.0, unit="meters")
        
        # Create with explicit type (advanced)
        lv5 = LogValue.withType(LogValue.LoggableType.Double, 3.14, 
                                 custom_type="struct:Pose2d", unit="radians")
        
        # Get backend-specific type strings
        wpilog_type = lv1.getWPILOGType()  # "double"
        nt4_type = lv1.getNT4Type()  # "double"
        ```
    """

    log_type: "LogValue.LoggableType"
    """The inferred or assigned LoggableType enum value. Determines serialization format."""
    
    custom_type: str
    """Optional custom type string (e.g., "struct:Pose2d"). Overrides default type strings."""
    
    value: Any
    """The actual value to be logged. Must be compatible with log_type."""
    
    unit: Optional[str] = None
    """Optional unit string for physical quantities (e.g., "meters/second")."""

    def __init__(self, value: Any, type_str: str = "", unit: Optional[str] = None) -> None:
        """
        Initialize a LogValue with automatic type inference.
        
        Constructs a LogValue by analyzing the Python type of the provided value
        and mapping it to a corresponding LoggableType. The type is locked at
        construction time to ensure type consistency throughout the value's lifetime.
        
        Type Inference Rules:
        1. bool() → Boolean (checked before int because bool is a subclass of int)
        2. int() → Integer
        3. float() → Double
        4. str() → String
        5. bytes() → Raw
        6. list() → Inspects all elements:
           - Empty list → IntegerArray (default for ambiguous case)
           - All bools → BooleanArray
           - All ints → IntegerArray
           - All floats → DoubleArray
           - All strs → StringArray
           - Mixed types → Raises TypeError
        
        Special Cases:
        - Empty arrays default to IntegerArray since type cannot be inferred
        - The order of type checks is critical: bool before int (bool is int subclass)
        - Mixed-type arrays are rejected with TypeError

        Args:
            value (Any): The value to be logged. Must be one of the supported types
                (bool, int, float, str, bytes, or list of primitives).
            type_str (str, optional): A custom type string to override the default
                type identifier. Useful for WPILib structs (e.g., "struct:Pose2d") or
                domain-specific types. If empty (default), the type string is derived
                from the inferred log_type. Defaults to "".
            unit (str, optional): Physical unit string for the value. Examples:
                "meters", "m/s", "RPM", "degrees", "volts". Used for dashboard
                visualization and automatic unit conversion in replay. Defaults to None.

        Raises:
            TypeError: If value type is not one of the supported types, or if a list
                contains mixed types (e.g., [1, 2.0, "mixed"]). Error message includes
                the unsupported type for debugging.
                
        Example:
            ```python
            # Scalar values
            lv_bool = LogValue(True)  # Boolean
            lv_int = LogValue(42)  # Integer
            lv_float = LogValue(3.14)  # Double
            lv_str = LogValue("enabled")  # String
            lv_raw = LogValue(b"\\x00\\x01")  # Raw
            
            # Array values
            lv_bool_arr = LogValue([True, False, True])  # BooleanArray
            lv_int_arr = LogValue([1, 2, 3])  # IntegerArray
            lv_double_arr = LogValue([1.0, 2.0])  # DoubleArray
            lv_str_arr = LogValue(["a", "b"])  # StringArray
            lv_empty = LogValue([])  # IntegerArray (default)
            
            # With unit
            lv_speed = LogValue(5.5, unit="m/s")
            
            # With custom type
            lv_custom = LogValue(b"data", type_str="struct:Pose2d")
            ```
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
        Create a LogValue with an explicitly specified type (advanced use).
        
        This factory method allows bypassing automatic type inference to explicitly
        assign a LoggableType. Use this when the inferred type doesn't match the
        desired type, or when working with raw serialized data.
        
        Typical Use Cases:
        - Logging raw bytes with a struct type: withType(Raw, struct_bytes, "struct:Pose2d")
        - Forcing a specific numeric type when inference might be ambiguous
        - Reconstructing a LogValue during log replay from stored type information
        
        Implementation Note:
        This method creates a temporary LogValue with a dummy integer value
        (to trigger type inference for the Integer type), then overwrites its
        type and value fields. This is an implementation detail and may be
        simplified in future versions.

        Args:
            log_type (LoggableType): The LoggableType enum value to assign explicitly.
                This bypasses automatic type inference entirely.
            data (Any): The actual data value. Should be compatible with the specified
                log_type (though this is not validated by the factory method).
            type_str (str, optional): Custom type string override. Defaults to "".
            unit (str, optional): Physical unit string. Defaults to None.

        Returns:
            LogValue: A new LogValue instance with the specified type, data, and metadata.
            
        Example:
            ```python
            # Log raw struct bytes with explicit struct type
            pose_bytes = b"\\x00\\x01\\x02..."  # Serialized Pose2d
            lv = LogValue.withType(LogValue.LoggableType.Raw, pose_bytes,
                                    type_str="struct:Pose2d")
            
            # Force Double type for a numeric value
            lv = LogValue.withType(LogValue.LoggableType.Double, 42, unit="counts")
            ```
        """
        val = LogValue(1, type_str)
        val.log_type = log_type
        val.value = data
        val.unit = unit
        return val

    def getWPILOGType(self) -> str:
        """
        Get the WPILOG type string for this value.
        
        WPILOG is the file format used for .wpilog files stored on the robot's
        USB drive or local filesystem for log replay and analysis. This method
        returns the type string suitable for that format.
        
        Type String Selection:
        - If custom_type is non-empty, returns that (takes precedence)
        - Otherwise, looks up the WPILOG type string for log_type in _WPILOG_TYPES
        - Custom types override to enable special type representations
        
        Common WPILOG Types:
        - "boolean", "int64", "float", "double", "string"
        - "boolean[]", "int64[]", "float[]", "double[]", "string[]"
        - "raw" (for serialized structs or binary data)
        - Custom: "struct:Pose2d", "struct:Transform3d", etc.

        Returns:
            str: The WPILOG type string for this value (e.g., "double", "int64[]",
                "struct:Pose2d"). Always non-empty.
        """
        return self.custom_type if self.custom_type else self.log_type.getWPILOGType()

    def getNT4Type(self) -> str:
        """
        Get the NetworkTables (NT4) type string for this value.
        
        NT4 is the protocol used to stream telemetry to NetworkTables in real-time
        during robot operation. This method returns the type string suitable for
        that protocol format.
        
        Type String Selection:
        - If custom_type is non-empty, returns that (takes precedence)
        - Otherwise, looks up the NT4 type string for log_type in _NT4_TYPES
        - Custom types override to enable special type representations
        
        NT4 vs WPILOG Type Differences:
        - NT4 uses "int" where WPILOG uses "int64"
        - Both share the same type strings for most other types
        - Custom types are preserved identically across both formats
        
        Common NT4 Types:
        - "boolean", "int", "float", "double", "string"
        - "boolean[]", "int[]", "float[]", "double[]", "string[]"
        - "raw" (for serialized structs or binary data)
        - Custom: "struct:Pose2d", etc.

        Returns:
            str: The NT4 type string for this value (e.g., "double", "int[]",
                "struct:Pose2d"). Always non-empty.
        """
        return self.custom_type if self.custom_type else self.log_type.getNT4Type()

    class LoggableType(Enum):
        """
        Enumeration of all supported loggable value types.
        
        This enum defines the complete set of types that can be logged by the pykit
        system. Each type has corresponding representations in WPILOG and NT4 formats
        accessible via getWPILOGType() and getNT4Type().
        
        Family Groups:
        - Scalar primitives: Raw, Boolean, Integer, Float, Double, String
        - Array types: BooleanArray, IntegerArray, FloatArray, DoubleArray, StringArray
        
        Note: Float and Double are separate types despite both being floating-point
        (Float = 32-bit, Double = 64-bit). Preserve this distinction during logging.
        
        Enum Values (in definition order):
            Raw: Serialized binary data (bytes). Used for WPILib structs and custom.
            Boolean: Single boolean value (true/false).
            Integer: 64-bit signed integer (int64 in WPILOG, int in NT4).
            Float: 32-bit floating-point value.
            Double: 64-bit floating-point value.
            String: Unicode text string.
            BooleanArray: Array of boolean values.
            IntegerArray: Array of 64-bit integers.
            FloatArray: Array of 32-bit floats.
            DoubleArray: Array of 64-bit doubles.
            StringArray: Array of strings.
        """

        Raw = auto()
        """Serialized binary data (bytes). Used for WPILib structs and custom binary types."""
        
        Boolean = auto()
        """Single boolean value (true/false)."""
        
        Integer = auto()
        """64-bit signed integer (int64)."""
        
        Float = auto()
        """32-bit IEEE 754 floating-point value."""
        
        Double = auto()
        """64-bit IEEE 754 floating-point value."""
        
        String = auto()
        """Unicode text string."""
        
        BooleanArray = auto()
        """Array of boolean values."""
        
        IntegerArray = auto()
        """Array of 64-bit signed integers."""
        
        FloatArray = auto()
        """Array of 32-bit floating-point values."""
        
        DoubleArray = auto()
        """Array of 64-bit floating-point values."""
        
        StringArray = auto()
        """Array of Unicode text strings."""

        def getWPILOGType(self) -> str:
            """
            Get the WPILOG type string for this enum value.
            
            WPILOG is the WPILib log file format used for replay analysis.
            This method returns the standard type identifier as it appears in
            .wpilog files and AdvantageScope.
            
            Returns:
                str: The WPILOG type string (e.g., "double", "int64[]"). 
                    Corresponds to one of the values in _WPILOG_TYPES.
            """
            return _WPILOG_TYPES[self.value - 1]

        def getNT4Type(self) -> str:
            """
            Get the NetworkTables (NT4) type string for this enum value.
            
            NT4 is the NetworkTables protocol used for real-time telemetry streaming
            to SmartDashboard and other dashboards.
            
            Returns:
                str: The NT4 type string (e.g., "double", "int[]").
                    Corresponds to one of the values in _NT4_TYPES.
            """
            return _NT4_TYPES[self.value - 1]

        @staticmethod
        def fromWPILOGType(type_str: str) -> "LogValue.LoggableType":
            """
            Convert a WPILOG type string to the corresponding LoggableType.
            
            Used during log replay to reconstruct LogValue objects from stored
            type metadata. Maps standard WPILOG type strings back to enum values.
            
            Reverse Mapping:
            Looks up type_str in _WPILOG_TYPES and returns the corresponding
            enum value. If not found, safely defaults to Raw to avoid crashes
            on unknown types.

            Args:
                type_str (str): A WPILOG type string (e.g., "double", "int64[]",
                    "struct:Pose2d"). Should be one of the values in _WPILOG_TYPES,
                    or a custom type string prefixed with "struct:".

            Returns:
                LoggableType: The corresponding enum value if found in _WPILOG_TYPES,
                    or LoggableType.Raw if the type string is not recognized.
                    
            Note:
                Unknown types default to Raw for robustness. This prevents crashes
                when replaying logs with type strings from newer code versions.
            """
            return LogValue.LoggableType(_WPILOG_TYPES.index(type_str) + 1) if type_str in _WPILOG_TYPES \
                else LogValue.LoggableType.Raw

        @staticmethod
        def fromNT4Type(type_str: str) -> "LogValue.LoggableType":
            """
            Convert a NetworkTables (NT4) type string to the corresponding LoggableType.
            
            Used when reading values from NetworkTables to reconstruct LogValue objects
            with proper type information. Maps NT4 type strings back to enum values.
            
            Reverse Mapping:
            Looks up type_str in _NT4_TYPES and returns the corresponding enum value.
            If not found, safely defaults to Raw to avoid crashes on unknown types.

            Args:
                type_str (str): An NT4 type string (e.g., "double", "int[]").
                    Should be one of the values in _NT4_TYPES, or a custom type
                    string prefixed with "struct:".

            Returns:
                LoggableType: The corresponding enum value if found in _NT4_TYPES,
                    or LoggableType.Raw if the type string is not recognized.
                    
            Note:
                Unknown types default to Raw for robustness. This prevents crashes
                when streaming values with type strings from newer code versions.
            """
            return LogValue.LoggableType(_NT4_TYPES.index(type_str) + 1) if type_str in _NT4_TYPES \
                else LogValue.LoggableType.Raw