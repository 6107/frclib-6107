"""
Auto-Logging Module for FRC Robot Telemetry

This module provides decorators and manager classes for automatic hierarchical logging of dataclass
fields and class members to WPILib LogTable. It enables:

- Automatic serialization/deserialization of dataclass instances to log tables via @autolog decorator
- Automatic logging of class member outputs via @autolog_output decorator and @autologgable_output class decorator
- Management of logged class instances via AutoLogInputManager and AutoLogOutputManager
- Support for nested autologged dataclasses and WPILib struct types
- Type-aware logging with custom type strings and unit information

Key Components:
    - AutoLogInputManager: Manages registration and retrieval of autologged dataclass instances
    - AutoLogOutputManager: Manages automatic publishing of decorated class members to log tables
    - autolog: Class decorator for dataclasses enabling auto log serialization/deserialization
    - autolog_output: Member decorator for methods/fields to automatically log their values
    - autologgable_output: Class decorator to enable @autolog_output member discovery and registration
"""

import dataclasses
import gc
import inspect
import typing

from wpiutil import wpistruct

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue


class _HasAutoLogInfo(typing.Protocol):
    """
    Protocol defining objects that have autolog output metadata.
    
    Used as a type hint for objects decorated with @autolog_output that carry
    metadata about how they should be logged.
    
    Attributes:
        autolog_output_info (dict): Dictionary containing autolog configuration with keys:
            - 'is_method' (bool): Whether the member is a method
            - 'log_type' (LogValue.LoggableType): The type to log as
            - 'custom_type' (str): Custom type string for logging
            - 'key' (str): The logging key to use
            - 'unit' (str): Unit string for the logged value
    """
    # pylint: disable=too-few-public-methods
    autolog_output_info: typing.Dict[str, typing.Any]


class AutoLogInputManager:
    """
    Manager for automatic input loading of dataclass fields from log tables.
    
    This singleton class maintains a registry of dataclass instances that have been
    decorated with @autolog. It allows centralized tracking of all logged dataclasses
    for loading/replay operations.
    
    Class Attributes:
        logged_classes (list[Any]): Registry of dataclass instances decorated with @autolog.
    """

    logged_classes: typing.List[typing.Any] = []
    """Registry of all logged dataclass instances for input loading."""

    @classmethod
    def register_class(cls, class_to_register: typing.Any):
        """
        Registers a dataclass instance for automatic input loading.
        
        Called during @autolog decoration to register instances that support
        from_log() deserialization from WPILib logs.

        Args:
            class_to_register (Any): A dataclass instance to register for tracking.
        """
        cls.logged_classes.append(class_to_register)

    @classmethod
    def getInputs(cls) -> typing.List[typing.Any]:
        """
        Retrieves all registered dataclass instances for input loading.

        Returns:
            list[Any]: A list of all registered dataclass instances that support
                logging and replays via from_log().
        """
        return cls.logged_classes


class AutoLogOutputManager:
    """
    Manager for automatic output logging of decorated class members.
    
    This singleton class discovers and tracks all class members (fields/methods)
    decorated with @autolog_output and manages their periodic publication to
    WPILib LogTable. It supports:
    
    - Lazy subscriber creation: Subscribers created on first publish, not registration
    - Instance tracking: Uses garbage collector to find instances of registered classes
    - Hierarchical logging: Recursively publishes nested autologged objects
    - Caching: Caches root instances to avoid repeated GC scans
    
    Class Attributes:
        logged_members (dict): Maps class types to lists of decorated member metadata dictionaries.
            Each metadata dict contains:
                - 'name' (str): Name of the field or method
                - 'is_method' (bool): True if a method, False if a field
                - 'log_type' (LogValue.LoggableType): The type to log as
                - 'key' (str): The logging key (defaults to member name)
                - 'custom_type' (str): Custom WPILib type string
                - 'unit' (str): Unit string for the value
        root_cache (list): Cached root instances of registered classes to optimize
            repeated publish_all() calls.
    """

    logged_members: typing.Dict[
        typing.Type, typing.List[typing.Dict[str, typing.Any]]
    ] = {}
    """
    Registry mapping class types to lists of decorated members.
    
    Structure: {ClassType: [{'name': str, 'is_method': bool, 'log_type': LogValue.LoggableType, ...}, ...]}
    """

    root_cache: typing.List[typing.Any] = []
    """Cached root instances of registered classes to avoid repeated garbage collection scans."""

    @classmethod
    def publish_all(cls, table: LogTable, root_instance = None):
        """
        Publishes all registered members of all registered class instances.

        This method discovers instances of classes registered with @autologgable_output
        and publishes their decorated members to the provided LogTable. It recursively
        traverses nested autologged objects to publish their members as well.
        
        Instance discovery uses Python's garbage collector if no root instances are provided,
        and caches results for subsequent calls to improve performance.

        Args:
            table (LogTable): The LogTable to publish member values to.
            root_instance (list[Any], optional): List of root instances to start publishing from.
                If None, scans registered class types using gc.get_referrers() to find
                all existing instances. Defaults to None.
                
        Note:
            The root_cache is populated on first call with no root_instance argument,
            so the cache should be cleared if the object topology changes.
        """
        # Build root instance list from cache or by scanning for registered class instances
        if root_instance is None:
            if cls.root_cache:
                root_instance = cls.root_cache
            else:
                root_instance = []
                for clS in cls.logged_members:
                    # At runtime, find all instances that exist of registered classes
                    # using garbage collector to locate all objects that reference the class
                    for instance in gc.get_referrers(clS):
                        if instance.__class__ == clS:
                            root_instance.append(instance)
                cls.root_cache = root_instance

        # Publish each instance and recurse into nested autologged objects
        for instance in root_instance:
            cls.publish(instance, table)
            if (
                    hasattr(instance, "_do_autolog")
                    and getattr(instance, "_do_autolog")
                    and hasattr(instance, "__dict__")
                    and not isinstance(instance, staticmethod)
            ):
                # Recursively publish sub-members for classes marked for autolog
                vals = list(instance.__dict__.values())
                if instance in vals:
                    vals.remove(instance)  # Avoid infinite recursion on self-referential objects
                cls.publish_all(table, vals)

    @classmethod
    def register_member(cls,  # pylint: disable=too-many-positional-arguments
                        class_type: typing.Type,
                        member_name: str,
                        is_method: bool,
                        log_type: typing.Optional[LogValue.LoggableType],
                        key: str = "",
                        custom_type: str = "",
                        unit: typing.Optional[str] = None,
    ):
        """
        Registers a class member (field or method) for automatic output logging.
        
        This is the primary registration point called by @autologgable_output class decorator
        to register individual members discovered from @autolog_output decorators.

        Args:
            class_type (Type): The class to which the member belongs.
            member_name (str): The name of the member (field or method name).
            is_method (bool): True if the member is a method, False if it's a field.
            log_type (LogValue.LoggableType | None): The LogValue type to log the member as.
                If None, type is inferred from the value.
            key (str, optional): The logging key to use in LogTable. If empty string (default),
                uses the member_name as the key.
            custom_type (str, optional): A custom WPILib type string for the log entry.
                Defaults to empty string.
            unit (str, optional): The unit string for the logged value (e.g., "meters", "RPM").
                Defaults to None.
        """
        if class_type not in cls.logged_members:
            cls.logged_members[class_type] = []
        cls.logged_members[class_type].append(
            {
                "name"       : member_name,
                "is_method"  : is_method,
                "log_type"   : log_type,
                "key"        : key,
                "custom_type": custom_type,
                "unit"       : unit,
            }
        )

    @classmethod
    def publish(cls, instance: typing.Any, table: LogTable):
        """
        Publishes the values of all registered members of a single instance to a LogTable.
        
        For each registered member of the instance's class:
        - Retrieves the value (calling the method if necessary)
        - Handles WPILib struct types specially via table.put()
        - Wraps other values in LogValue with optional custom type/unit overrides
        - Publishes to the LogTable with the configured key

        Args:
            instance (Any): The instance whose members are to be published.
            table (LogTable): The LogTable to publish member values to.
        """
        class_type = type(instance)
        if class_type in cls.logged_members:
            for member_info in cls.logged_members[class_type]:
                member_name = member_info["name"]
                is_method = member_info["is_method"]
                log_type = member_info["log_type"]
                custom_type = member_info["custom_type"]
                unit = member_info["unit"]

                key = member_info["key"] or member_name

                # Get the value from the instance (call if method, access if field)
                value = None
                if is_method:
                    value = getattr(instance, member_name)()
                else:
                    value = getattr(instance, member_name)

                # Handle WPILib struct types specially
                if hasattr(value, "WPIStruct") or (
                        hasattr(value, "__iter__")
                        and len(value) > 0
                        and hasattr(value[0], "WPIStruct")
                ):
                    table.put(key, value)
                else:
                    # Wrap value in LogValue and override type if specified
                    log_value = LogValue(value, custom_type, unit)
                    if log_type is not None:
                        log_value.log_type = log_type
                    table.put_value(key, log_value)


def autolog_output(
        key: str,
        log_type: typing.Optional[LogValue.LoggableType] = None,
        custom_type: str = "",
        unit: typing.Optional[str] = None,
):
    """
    Decorator for class methods or fields to automatically log their output.
    
    This decorator marks a method or field for automatic logging. The decorated
    member will be published to a LogTable when the class is also decorated with
    @autologgable_output.
    
    The decorator stores metadata on the member which is later discovered by
    @autologgable_output during class decoration.

    Args:
        key (str): The logging key to use in the LogTable (e.g., "Drivetrain/speed").
        log_type (LogValue.LoggableType | None, optional): The type to log the value as.
            If None (default), the type is inferred from the value at runtime.
        custom_type (str, optional): A custom WPILib type string for the log entry.
            Defaults to empty string (no custom type).
        unit (str, optional): The unit string for the logged value. Examples: "meters",
            "RPM", "degrees", "volts". Defaults to None (no unit).

    Returns:
        Callable: A decorator function that wraps the member and attaches metadata.

    Example:
        ```python
        @autologgable_output
        class Drivetrain:
            def __init__(self):
                self._speed = 0.0
            
            @autolog_output("Drivetrain/speed", unit="m/s")
            def get_speed(self):
                return self._speed
        ```
    """

    def decorator(member: typing.Any):
        """
        Inner decorator that attaches autolog metadata to the member.
        
        For methods (inspect.isfunction), stores metadata directly.
        For fields/properties, stores metadata for later discovery by @autologgable_output.
        """
        # This part is tricky because Python decorators for methods/fields
        # don't directly give you the class at definition time.
        # We'll store a temporary attribute and process it in a class decorator.
        if inspect.isfunction(member):
            # It's a method
            print(f"[AugoLogOutput] DEBUG: Setting up log for {key}")
            typing.cast(_HasAutoLogInfo, member).autolog_output_info = {
                "is_method"  : True,
                "log_type"   : log_type,
                "custom_type": custom_type,
                "key"        : key,
                "unit"       : unit,
            }
        else:
            # It's a field (this case is harder to handle directly with a decorator
            # on the field itself, usually done via a class decorator or metaclass)
            # For now, we'll assume it's a method or a property-like descriptor.
            # If it's a simple field, the class decorator approach is more robust.
            # Let's assume for now that direct field decoration will be handled
            # by a class decorator that scans for these attributes.
            # For direct field decoration, we might need a descriptor.
            # For simplicity, let's focus on methods first, or assume a class
            # decorator will pick up field annotations.
            # For now, let's make it work for methods and properties.
            typing.cast(_HasAutoLogInfo, member).autolog_output_info = {
                "is_method"  : False,  # This will be true for properties too
                "log_type"   : log_type,
                "custom_type": custom_type,
                "key"        : key,
                "unit"       : unit,
            }
        return member

    return decorator


def autologgable_output(cls):
    """
    Class decorator that discovers and registers methods/fields decorated with @autolog_output.
    
    This decorator scans the target class for all members carrying autolog_output_info metadata
    (set by @autolog_output) and registers them with AutoLogOutputManager for automatic
    periodic publishing to LogTable.
    
    The class is also marked with _do_autolog attribute to enable hierarchical recursion
    during AutoLogOutputManager.publish_all().

    Args:
        cls (Type): The class to decorate and scan for @autolog_output decorated members.

    Returns:
        Type: The decorated class with members registered and _do_autolog flag set.

    Example:
        ```python
        @autologgable_output
        class Drivetrain:
            @autolog_output("Drivetrain/speed", unit="m/s")
            def get_speed(self):
                return 5.0
        ```
    """
        for name in dir(cls):
        member = getattr(cls, name)
        info = getattr(member, "autolog_output_info", None)
        if isinstance(info, dict):
            AutoLogOutputManager.register_member(
                cls,
                name,
                bool(info.get("is_method", False)),
                info.get("log_type"),
                info.get("key", name),
                info.get("custom_type", ""),
                info.get("unit", "")
            )

    setattr(cls, "_do_autolog", True)
    return cls


def autolog(cls = None, /):
    """
    Class decorator that adds to_log() and from_log() methods to a dataclass for auto-logging.
    
    This decorator enables automatic hierarchical serialization and deserialization of
    dataclass instances to/from WPILib LogTable format. It supports:
    
    - Recursive logging of nested @autolog-decorated dataclasses
    - Type-aware loading and unpacking of primitives (bool, int, float, str)
    - WPILib struct type support via wpistruct.pack/unpack
    - Array types (list[T]) with proper element type handling
    - Post-initialization registration with AutoLogInputManager for replay
    
    The decorator generates:
    1. to_log(table, prefix) - Serializes dataclass fields to LogTable with optional nesting
    2. from_log(table, prefix) - Deserializes dataclass fields from LogTable with type inference
    3. __post_init__() hook - Registers the instance with AutoLogInputManager
    
    Args:
        cls (Type, optional): The dataclass to decorate. If None, returns a wrapper
            for use with or without parentheses.

    Returns:
        Type: The decorated dataclass with to_log, from_log, and __post_init__ methods added.

    Example:
        ```python
        @dataclass
        @autolog
        class DriveConfig:
            max_speed: float = 3.0
            gear_ratio: float = 6.0
        
        config = DriveConfig()
        config.to_log(table, "DriveConfig")
        config.from_log(table, "DriveConfig")
        ```
    """

    def wrap(cls):
        """
        Inner wrapper that adds logging methods to the dataclass.
        
        Args:
            cls (Type): The dataclass to wrap.
            
        Returns:
            Type: The decorated dataclass.
        """
        # Get type hints for all fields
        resolved_hints = typing.get_type_hints(cls)
        # Extract dataclass field names in definition order
        field_names = [field.name for field in dataclasses.fields(cls)]

        def to_log(self, table: LogTable, prefix: str):
            """
            Recursively serializes the dataclass fields to a LogTable.
            
            Nested @autolog-decorated dataclasses are recursively serialized via
            their to_log() methods. Primitive types are logged directly.

            Args:
                table (LogTable): The LogTable instance to write field data to.
                prefix (str): The prefix for all log entries (e.g., "Robot/Drive").
            """
            for name in field_names:
                value = getattr(self, name)
                field_prefix = f"{prefix}/{name}"
                # Recursively log nested autolog dataclasses
                if hasattr(value, "to_log"):
                    value.to_log(table, field_prefix)
                else:
                    table.put(field_prefix, value)

        def from_log(self, table: LogTable, prefix: str):
            """
            Recursively deserializes dataclass fields from a LogTable.
            
            Supports nested @autolog-decorated dataclasses via recursive from_log() calls,
            primitive types with automatic type conversion, arrays of primitives/structs,
            and WPILib struct types with automatic unpacking.

            Args:
                table (LogTable): The LogTable instance to read field data from.
                prefix (str): The prefix for field log entries (must match to_log prefix).
            """
            for name in field_names:
                field_prefix = f"{prefix}/{name}"

                value = getattr(self, name)
                # Recursively load nested autolog dataclasses
                if hasattr(value, "from_log"):
                    value.from_log(table, field_prefix)
                else:
                    # Load primitive types and arrays from log table
                    field_type = resolved_hints[name]
                    new_value: typing.Any = None

                    origin = typing.get_origin(field_type)
                    if origin is list:
                        # Handle list types: list[bool], list[int], list[float], list[str], list[WPIStruct]
                        list_type = typing.get_args(field_type)[0]
                        if list_type is bool:
                            new_value = table.get_boolean_array(field_prefix, value)
                        elif list_type is int:
                            new_value = table.get_integer_array(field_prefix, value)
                        elif list_type is float:
                            new_value = table.get_double_array(field_prefix, value)
                        elif list_type is str:
                            new_value = table.get_string_array(field_prefix, value)
                        elif hasattr(list_type, "WPIStruct"):
                            # Unpack array of WPILib structs (e.g., list[Pose2d])
                            new_value = wpistruct.unpackArray(
                                list_type, table.get_raw(field_prefix, b"")
                            )
                        else:
                            print(
                                f"[AutoLog] Failed to read of type {field_type} with value {list_type}"
                            )
                    else:
                        # Handle scalar types: bool, int, float, str, WPIStruct
                        if field_type is bool:
                            new_value = table.get_boolean(field_prefix, value)
                        elif field_type is int:
                            new_value = table.get_integer(field_prefix, value)
                        elif field_type is float:
                            new_value = table.get_double(field_prefix, value)
                        elif field_type is str:
                            new_value = table.get_string(field_prefix, value)
                        elif hasattr(field_type, "WPIStruct"):
                            # Unpack WPILib struct (e.g., Pose2d, Rotation2d)
                            new_value = wpistruct.unpack(
                                field_type, table.get_raw(field_prefix, b"")
                            )
                        else:
                            print(f"[AutoLog] Failed to read of type {field_type}")

                    if new_value is not None:
                        setattr(self, name, new_value)

        def register_autologged(self) -> None:
            """
            Registers the dataclass instance with AutoLogInputManager after initialization.
            
            Called during __post_init__() hook to register the instance for tracking
            and replay support. Allows central registry of all logged dataclasses.
            """
            print(f"[AutoLog] registering {self.name}")
            AutoLogInputManager.register_class(self)

        setattr(cls, "to_log", to_log)
        setattr(cls, "from_log", from_log)
        # https://docs.python.org/3/library/dataclasses.html#dataclasses.__post_init__
        # https://docs.python.org/3/reference/expressions.html#private-name-mangling
        # Register the __post_init__ hook for use with dataclass __post_init__ mechanism
        setattr(cls, f"_{cls.__class__.__name__}__post_init__", register_autologged)

        return cls

    if cls is None:
        return wrap

    return wrap(cls)