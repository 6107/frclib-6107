"""
Log Table Module for WPILib Telemetry

This module provides LogTable, a hierarchical key-value store designed for efficient
robot telemetry logging at discrete timestamps. Each LogTable snapshot represents
all sensor readings, motor outputs, and other state at a specific moment in time.

Key Features:
- Type-safe logging: Enforces consistent types across timestamps to enable replay
- WPILib struct support: Automatically serializes/deserializes WPILib types (Pose2d, etc.)
- Hierarchical namespacing: Supports subtables with nested prefixes (e.g., "Drivetrain/Motors")
- Type-aware getters: Separate typed accessors for each primitive and array type
- Schema registration: Automatically records struct schemas for AdvantageScope replay

The LogTable acts as a temporary buffer during each robot periodic cycle:
- Input phase: Robot code reads sensor values via put()/putValue()
- Output phase: Logger flushes the table to NetworkTables/disk via receivers
- Replay phase: Log entries are restored via get*() methods for deterministic replay

All keys are automatically prefixed to match the table's namespace hierarchy, allowing
logical organization of telemetry without explicit path management by subsystems.
"""

from typing import Any, cast, Optional, Set

from wpiutil import wpistruct

from lib_6107.pykit.logvalue import LogValue


class LogTable:  # pylint: disable=too-many-public-methods
    """
    Hierarchical key-value table for storing robot telemetry at a single timestamp.
    
    LogTable represents a snapshot of all robot state at a specific moment in time
    (captured at microsecond precision via FPGA clock). It stores entries as LogValue
    objects, enabling type-aware access and type-checking across time.
    
    Key Design Principles:
    - Type Consistency: Once a key is used with a type, subsequent writes must use
      the same type. This prevents silent type mismatches during log replay.
    - Prefixing: All keys are stored with the table's prefix prepended. For example,
      table.put("speed", 5.0) on a table with prefix "/Drivetrain/" is stored as
      "/Drivetrain/speed". Subtables extend this prefix hierarchically.
    - Lazy Prefix Application: The prefix is applied during storage (put/get), not
      during table creation, allowing flexible namespace composition.
    - Struct Serialization: WPILib structs (e.g., Pose2d, Rotation2d) are automatically
      packed into bytes with their schema stored for AdvantageScope replay.
    
    Attributes:
        prefix (str): The namespace prefix for all keys in this table. Used to organize
            telemetry hierarchically (e.g., "/Robot/Drivetrain/", "/Robot/Vision/").
            Always includes leading and trailing "/" for consistency.
        depth (int): The nesting level of this subtable. Root tables have depth=0.
            Used for metrics and table introspection.
        timestamp (int): FPGA timestamp in microseconds of when this snapshot was captured.
            All entries in the table share this timestamp.
        data (dict[str, LogValue]): Shared underlying storage of all entries.
            For subtables, this points to the root table's data dict, allowing
            all subtables to read/write a common data structure.
    
    Usage:
        ```python
        # Root table: capture current robot state
        table = LogTable(timestamp_us, "/")
        table.put("match_time", 45.2)
        table.put("robot_pose", pose2d_object)  # WPILib struct auto-serialized
        
        # Subtable: organize subsystem data
        drive_table = table.get_subtable("Drivetrain")
        drive_table.put("speed", 3.5)  # Stored as "/Drivetrain/speed"
        drive_table.put("heading", 90.0)
        
        # Retrieval with type checking
        speed = table.get("/Drivetrain/speed", 0.0)
        speeds = table.getDoubleArray("/Motors/speeds", [])
        ```
    """
    
    prefix: str
    """Namespace prefix for this table (e.g., "/" for root, "/Drivetrain/" for subtable)."""
    
    depth: int
    """Nesting depth: 0 for root, incremented for each subtable level."""
    
    timestamp: int
    """FPGA timestamp in microseconds when this snapshot was created."""
    
    data: dict[str, LogValue]
    """Underlying key-value storage shared across all subtables at this timestamp."""

    def __init__(self, timestamp: int, prefix: str = "/") -> None:
        """
        Initialize a new LogTable for a specific timestamp and namespace.
        
        Creates a root table with its own data storage. Tables created via
        get_subtable() will share the parent's data dict but use an extended prefix.

        Args:
            timestamp (int): FPGA timestamp in microseconds for this snapshot.
                Typically, RobotController.getFPGATime(). Represents the moment
                when all sensor readings in this table were captured.
            prefix (str, optional): The namespace prefix for all keys. Defaults to "/"
                for the root table. Always include leading "/" (e.g., "/Drivetrain/").
        
        Attributes Initialized:
            self.timestamp: Set to the provided timestamp.
            self.prefix: Set to the provided prefix.
            self.depth: Initialized to 0 (root level). Incremented by get_subtable().
            self.data: Empty dict for root tables; populated via put/putValue calls.
        """
        self.timestamp = timestamp
        self.prefix = prefix
        self.depth = 0
        self.data: dict[str, LogValue] = {}

    @staticmethod
    def clone(source: LogTable) -> LogTable:
        """
        Creates a shallow copy of a LogTable with independent data storage.
        
        The clone has the same timestamp and prefix as the source, but with a
        new independent data dict. This is useful for creating snapshots at
        checkpoints or for thread-safe isolation of a table state.
        
        Note: The copy is shallow - LogValue objects themselves are not deep-copied,
        only the dict structure. Modifying a LogValue in the clone will affect the
        original (and vice versa) if both tables are used together.

        Args:
            source (LogTable): The LogTable to clone.

        Returns:
            LogTable: A new LogTable with the same timestamp/prefix but independent data dict.
        """
        data: dict[str, LogValue] = {}
        for item, value in source.data.items():
            data[item] = value

        new_table = LogTable(source.timestamp, source.prefix)
        new_table.data = data
        return new_table

    def getTimestamp(self) -> int:
        """
        Retrieve the FPGA timestamp of this table snapshot.
        
        Returns:
            int: The timestamp in microseconds. Can be compared with other timestamps
                to compute elapsed time or to match log entries across multiple tables.
        """
        return self.timestamp

    def setTimestamp(self, timestamp: int) -> None:
        """
        Update the FPGA timestamp of this table.
        
        Typically called when replaying logs or adjusting time bases. All entries
        in the table will be associated with the new timestamp.

        Args:
            timestamp (int): The new FPGA timestamp in microseconds.
        """
        self.timestamp = timestamp

    def write_allowed(self, key: str, log_type: LogValue.LoggableType, custom_type: str) -> bool:
        """
        Validate that a write operation is type-consistent with existing entries.
        
        This method enforces type safety: if a key already exists in the table,
        the new write must use the same type. This prevents silent type mismatches
        that could corrupt replay data or cause AdvantageScope parsing errors.
        
        If a type mismatch is detected, a warning is printed to console.

        Args:
            key (str): The full key to write (including prefix, e.g., "/Drivetrain/speed").
            log_type (LogValue.LoggableType): The type of the value being written
                (e.g., LogValue.LoggableType.Double).
            custom_type (str): Custom WPILib type string ("" for primitives,
                "struct:Pose2d" for structs, etc.).

        Returns:
            bool: True if the write is allowed (new key or matching type),
                  False if a type mismatch is detected.
                  
        Side Effects:
            Prints a detailed error message to console if a type mismatch is found.
        """
        if (currentVal := self.data.get(self.prefix + key)) is None:
            return True

        if currentVal.log_type != log_type:
            print(f"Failed to write {key}:\nAttempted {log_type} but type is {currentVal.log_type}")
            return False

        if custom_type != currentVal.custom_type:
            print(f"Failed to write {key}:\nAttempted {custom_type} but type is {currentVal.custom_type}")
            return False
        return True

    def add_struct_schema_nest(self, structname: str, schema: str):
        """
        Register the schema definition for a nested WPILib struct type.
        
        Called internally by addStructSchema() to recursively register schemas
        for structs contained within other structs (e.g., Transform2d contains
        Translation2d and Rotation2d). This ensures AdvantageScope has all
        necessary schema information for proper deserialization.

        Args:
            structname (str): The qualified type name of the struct
                (e.g., "frc.geometry.struct.Pose2dStruct").
            schema (str): The WPILib struct schema definition string
                (e.g., "{double x;double y;...}").
        """
        type_string = structname
        key = "/.schema/" + type_string
        if key in self.data.keys():
            return

        self.data[key] = LogValue(schema.encode(), "structschema")

    def add_struct_schema(self, struct: Any, seen: Set[str]):
        """
        Recursively register schemas for a WPILib struct and all nested structs.
        
        Struct schema definitions are required by AdvantageScope and similar log tools
        to parse serialized struct data. This method uses wpistruct introspection to
        discover the struct's schema and all transitively nested struct schemas.
        
        Schemas are stored with keys like "/.schema/struct:Pose2d" to prevent duplication
        across multiple log entries.

        Args:
            struct (Any): An instance of the struct class. Used to extract type information
                via wpistruct.getTypeName() and wpistruct.getSchema().
            seen (Set[str]): Set of already-processed type strings to prevent infinite
                recursion in case of circular struct definitions.

        Side Effects:
            Adds one or more entries to self.data with keys "/.schema/struct:*" containing
            encoded schema strings with custom_type="structschema".
        """
        # Add struct schema definition to log for replay compatibility
        type_string = "struct:" + wpistruct.getTypeName(struct.__class__)
        key = "/.schema/" + type_string
        if key in self.data.keys():
            return
        seen.add(type_string)
        schema = wpistruct.getSchema(struct.__class__)
        self.data[key] = LogValue(schema.encode(), "structschema")

        # Recursively add schemas for nested struct types
        wpistruct.forEachNested(struct.__class__, self.add_struct_schema_nest)
        seen.remove(type_string)

    def put(self, key: str, value: Any, type_str: str = "", unit: Optional[str] = None):
        """
        Put a value into the log table with automatic type handling.
        
        This is the primary method for logging values. It automatically detects
        and handles WPILib structs (e.g., Pose2d, Rotation2d) and struct arrays,
        serializing them to bytes and registering their schemas. For primitive
        types, wraps the value in a LogValue and delegates to putValue().
        
        Supported Input Types:
        - Primitives: int, float, bool, str (auto-wrapped in LogValue)
        - Lists of primitives: list[int], list[float], list[bool], list[str]
        - WPILib structs with WPIStruct attribute (auto-serialized)
        - Arrays of WPILib structs (auto-serialized and packaged)
        
        Type Consistency:
        The key's type is locked on first write. Subsequent writes with that key
        must provide the same type or writeAllowed() will reject the write.

        Args:
            key (str): The unqualified key name (e.g., "speed", "Motors/speeds").
                The table's prefix will be prepended (e.g., "/Drivetrain/speed").
            value (Any): The value to log. Can be primitive, array, or WPILib struct.
            type_str (str, optional): Custom WPILib type string for non-struct values.
                Used for special types. Defaults to "" (infer from value).
                Examples: "structschema" (for manual struct schemas), "bitmask" (NT).
            unit (str, optional): Unit string for physical quantities.
                Examples: "meters", "RPM", "degrees", "volts".
                Stored in LogValue for AdvantageScope visualization.

        Note:
            Exceptions during serialization are silently caught (intended behavior
            to handle corrupt or None values gracefully).
        """
        try:
            if hasattr(value, "WPIStruct"):
                # Handle WPILib struct types - serialize and add schema
                self.add_struct_schema(value, set())
                log_value = LogValue(wpistruct.pack(value),
                                     "struct:" + wpistruct.getTypeName(value.__class__))
            elif (
                    hasattr(value, "__iter__")
                    and len(value) > 0
                    and hasattr(value[0], "WPIStruct")
            ):
                # Handle arrays of struct types
                self.add_struct_schema(value[0], set())
                log_value = LogValue(
                    wpistruct.packArray(value),
                    "struct:" + wpistruct.getTypeName(value[0].__class__) + "[]",
                )
            else:
                log_value = LogValue(value, type_str, unit)

            self.put_value(key, log_value)

        except Exception as e:
            pass                # Get around None Issue

    def put_value(self, key: str, log_value: LogValue):
        """
        Put a LogValue object into the log table with type and consistency checks.
        
        This method handles the actual storage, performing type validation and
        handling special cases like empty arrays (which must inherit type from
        previous entries to avoid type mismatches in replay).
        
        Empty Array Handling:
        If the LogValue contains an empty list and a previous entry exists for that
        key, the type and structure of the new value are adjusted to match. This
        prevents type inconsistencies when a sensor sometimes returns no data
        (e.g., empty tag list when no AprilTags are visible).

        Args:
            key (str): The unqualified key name (e.g., "speed").
                The table's prefix is prepended during storage.
            log_value (LogValue): The value object to store, containing the value,
                type, custom_type, and optional unit.

        Side Effects:
            - Stores the entry in self.data with prefix-qualified key if allowed
            - Prints error to console if type mismatch or write failure occurs
            - May modify log_value.log_type/custom_type/value for empty arrays
        """
        # Handle empty array edge case - match type to previous entry to avoid type mismatch
        if isinstance(log_value.value, list) and len(log_value.value) == 0:
            current_val = self.data.get(self.prefix + key)
            if current_val is not None:
                log_value.log_type = current_val.log_type
                log_value.custom_type = current_val.custom_type
                if current_val.custom_type.startswith("struct"):
                    # Struct logging uses raw bytes, so empty array needs empty bytes
                    log_value.value = b""
            else:
                # Don't log if no previous entry to match type against
                return
        if self.write_allowed(key, log_value.log_type, log_value.custom_type):
            self.data[self.prefix + key] = log_value
        else:
            print(f"Failed to insert {log_value.value}")

    def get(self, key: str, default: Any) -> Any:
        """
        Get a value from the log table without type checking.
        
        This is the generic getter that returns the raw value for any key.
        For type-safe access, use the typed getters (getDouble, getBoolean, etc.)
        which validate the entry's type before returning.

        Args:
            key (str): The unqualified key to retrieve (e.g., "speed").
                Automatically prefixed with the table's namespace.
            default (Any): The value to return if the key is not found.

        Returns:
            Any: The stored value if found and the key exists,
                 or default if the key is not found.
        """
        if (log_value := self.data.get(self.prefix + key)) is not None:
            return log_value.value

        return default

    def get_raw(self, key: str, default: bytes) -> bytes:
        """
        Get a raw (bytes) value from the log table with type validation.
        
        Used for retrieving serialized WPILib struct data. Returns bytes only if
        the entry exists and its type is Raw.

        Args:
            key (str): The unqualified key to retrieve (e.g., "robot_pose").
            default (bytes): The value to return if missing or wrong type.

        Returns:
            bytes: The serialized struct bytes if found with correct type,
                   or default otherwise.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.Raw:
            return cast(bytes, log_value.value)
        return default

    def get_boolean(self, key: str, default: bool) -> bool:
        """
        Get a boolean value from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "is_enabled").
            default (bool): The value to return if missing or wrong type.

        Returns:
            bool: The stored boolean if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.Boolean:
            return cast(bool, log_value.value)
        return default

    def get_integer(self, key: str, default: int) -> int:
        """
        Get an integer value from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "encoder_ticks").
            default (int): The value to return if missing or wrong type.

        Returns:
            int: The stored integer if found with correct type, or default.
        """
        if (log_value := self.data.get(self.prefix + key)) is not None and \
                log_value.log_type == LogValue.LoggableType.Integer:
            return cast(int, log_value.value)
        return default

    def get_float(self, key: str, default: float) -> float:
        """
        Get a 32-bit float value from the log table with type validation.
        
        Use for single-precision float values (e.g., analog sensor outputs).
        For double-precision, use getDouble().

        Args:
            key (str): The unqualified key to retrieve (e.g., "voltage").
            default (float): The value to return if missing or wrong type.

        Returns:
            float: The stored float if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.Float:
            return cast(float, log_value.value)
        return default

    def get_double(self, key: str, default: float) -> float:
        """
        Get a 64-bit double value from the log table with type validation.
        
        Use for high-precision floating-point values (e.g., calculated speeds,
        PID outputs, sensor calibrations). For single-precision, use getFloat().

        Args:
            key (str): The unqualified key to retrieve (e.g., "speed").
            default (float): The value to return if missing or wrong type.

        Returns:
            float: The stored double if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.Double:
            return cast(float, log_value.value)
        return default

    def get_string(self, key: str, default: str) -> str:
        """
        Get a string value from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "state").
            default (str): The value to return if missing or wrong type.

        Returns:
            str: The stored string if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.String:
            return cast(str, log_value.value)
        return default

    def get_boolean_array(self, key: str, default: list[bool]) -> list[bool]:
        """
        Get a boolean array from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "limit_switches").
            default (list[bool]): The value to return if missing or wrong type.

        Returns:
            list[bool]: The stored array if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.BooleanArray:
            return cast(list[bool], log_value.value)
        return default

    def get_integer_array(self, key: str, default: list[int]) -> list[int]:
        """
        Get an integer array from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "encoder_counts").
            default (list[int]): The value to return if missing or wrong type.

        Returns:
            list[int]: The stored array if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.IntegerArray:
            return cast(list[int], log_value.value)
        return default

    def get_float_array(self, key: str, default: list[float]) -> list[float]:
        """
        Get a 32-bit float array from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "accel_x_samples").
            default (list[float]): The value to return if missing or wrong type.

        Returns:
            list[float]: The stored array if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.FloatArray:
            return cast(list[float], log_value.value)
        return default

    def get_double_array(self, key: str, default: list[float]) -> list[float]:
        """
        Get a 64-bit double array from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "trajectory_points").
            default (list[float]): The value to return if missing or wrong type.

        Returns:
            list[float]: The stored array if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.DoubleArray:
            return cast(list[float], log_value.value)
        return default

    def get_string_array(self, key: str, default: list[str]) -> list[str]:
        """
        Get a string array from the log table with type validation.

        Args:
            key (str): The unqualified key to retrieve (e.g., "tag_names").
            default (list[str]): The value to return if missing or wrong type.

        Returns:
            list[str]: The stored array if found with correct type, or default.
        """
        if (
                log_value := self.data.get(self.prefix + key)
        ) is not None and log_value.log_type == LogValue.LoggableType.StringArray:
            return cast(list[str], log_value.value)
        return default

    def get_all(self, subtable_only: bool = False) -> dict[str, LogValue]:
        """
        Retrieve all entries from the log table.
        
        Returns the underlying data dict, optionally filtered to only entries
        within the current table's namespace prefix.

        Args:
            subtable_only (bool, optional): If True, returns only entries whose
                keys start with this table's prefix (i.e., entries added to this
                table or its sub-subtables). If False (default), returns all entries
                from the root table (including entries from other tables or components).

        Returns:
            dict[str, LogValue]: All log entries currently stored.
                - If subtableOnly=False: All entries in the timestamp snapshot
                - If subtableOnly=True: Only entries under this table's namespace
        """
        if not subtable_only:
            return self.data
        return {
            key: value
            for key, value in self.data.items()
            if key.startswith(self.prefix)
        }

    def get_subtable(self, subtable_prefix: str) -> LogTable:
        """
        Create a child LogTable representing a namespace within this table.
        
        Subtables share the same underlying data storage as the parent but present
        a logical namespace boundary. This allows subsystems to put/get values
        without explicitly managing paths, while maintaining hierarchy for
        telemetry organization.
        
        Key Sharing:
        The returned subtable's data dict is the same object as the parent's.
        Writes to the subtable affect the parent's data immediately, and vice versa.
        This enables efficient hierarchical updates without copying.
        
        Prefix Composition:
        The subtable's prefix is the parent's prefix + subtablePrefix + "/".
        When the subtable puts a value with key "speed", it's stored as
        parent_prefix + subtablePrefix + "/speed".

        Args:
            subtable_prefix (str): The namespace segment to add (e.g., "Drivetrain").
                Should not include leading or trailing slashes; they are added
                automatically.

        Returns:
            LogTable: A new LogTable instance representing the subtable with:
                - Same timestamp as parent
                - Extended prefix (parent.prefix + subtablePrefix + "/")
                - Shared data dict (points to parent's data)
                - Depth incremented by 1

        Example:
            ```python
            root = LogTable(timestamp_us, "/")
            drive = root.get_subtable("Drivetrain")
            motor = drive.get_subtable("Motors")
            
            motor.put("speed", 5.0)
            # Stored as "/Drivetrain/Motors/speed" in root.data
            
            assert root.get("/Drivetrain/Motors/speed", 0.0) == 5.0
            ```
        """
        subtable = LogTable(self.getTimestamp(), self.prefix + subtable_prefix + "/")
        subtable.data = self.data
        subtable.depth = self.depth + 1
        return subtable