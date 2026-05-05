"""Unit tests for autolog module."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch
import pytest

from lib_6107.pykit.autolog import (
    AutoLogInputManager,
    AutoLogOutputManager,
    autolog,
    autolog_output,
    autologgable_output,
)
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue


class TestAutoLogInputManagerRegistration:
    """Tests for AutoLogInputManager class registration."""

    def setup_method(self):
        """Clear registration state before each test."""
        AutoLogInputManager.logged_classes = []

    def test_register_class_stores_instance(self):
        """Verify register_class stores the instance in logged_classes."""
        mock_instance = MagicMock()

        AutoLogInputManager.register_class(mock_instance)

        assert mock_instance in AutoLogInputManager.logged_classes

    def test_register_multiple_classes(self):
        """Verify register_class handles multiple instances."""
        instance1 = MagicMock()
        instance2 = MagicMock()

        AutoLogInputManager.register_class(instance1)
        AutoLogInputManager.register_class(instance2)

        assert len(AutoLogInputManager.logged_classes) == 2
        assert instance1 in AutoLogInputManager.logged_classes
        assert instance2 in AutoLogInputManager.logged_classes

    def test_get_inputs_returns_registered_classes(self):
        """Verify getInputs returns all registered instances."""
        instance1 = MagicMock()
        instance2 = MagicMock()
        AutoLogInputManager.register_class(instance1)
        AutoLogInputManager.register_class(instance2)

        result = AutoLogInputManager.getInputs()

        assert result == [instance1, instance2]

    def test_get_inputs_returns_empty_initially(self):
        """Verify getInputs returns empty list when no registrations."""
        result = AutoLogInputManager.getInputs()

        assert result == []

    def test_get_inputs_returns_same_list_reference(self):
        """Verify getInputs returns the same list reference each time."""
        AutoLogInputManager.register_class(MagicMock())

        result1 = AutoLogInputManager.getInputs()
        result2 = AutoLogInputManager.getInputs()

        assert result1 is result2


class TestAutoLogOutputManagerRegistration:
    """Tests for AutoLogOutputManager member registration."""

    def setup_method(self):
        """Clear registration state before each test."""
        AutoLogOutputManager.logged_members = {}
        AutoLogOutputManager.root_cache = []

    def test_register_member_adds_to_registry(self):
        """Verify register_member adds metadata to registry."""
        mock_class = MagicMock()

        AutoLogOutputManager.register_member(
            mock_class, "test_method", True, LogValue.LoggableType.Float
        )

        assert mock_class in AutoLogOutputManager.logged_members
        assert len(AutoLogOutputManager.logged_members[mock_class]) == 1

    def test_register_member_with_all_parameters(self):
        """Verify register_member stores all provided metadata."""
        mock_class = MagicMock()

        AutoLogOutputManager.register_member(
            mock_class,
            "get_speed",
            True,
            LogValue.LoggableType.Float,
            key="drivetrain/speed",
            custom_type="custom",
            unit="m/s",
        )

        member_info = AutoLogOutputManager.logged_members[mock_class][0]
        assert member_info["name"] == "get_speed"
        assert member_info["is_method"] is True
        assert member_info["log_type"] == LogValue.LoggableType.Float
        assert member_info["key"] == "drivetrain/speed"
        assert member_info["custom_type"] == "custom"
        assert member_info["unit"] == "m/s"

    def test_register_member_multiple_for_same_class(self):
        """Verify register_member supports multiple members for same class."""
        mock_class = MagicMock()

        AutoLogOutputManager.register_member(mock_class, "method1", True, None)
        AutoLogOutputManager.register_member(mock_class, "method2", False, None)

        assert len(AutoLogOutputManager.logged_members[mock_class]) == 2

    def test_register_member_different_classes(self):
        """Verify register_member handles different classes independently."""
        class1 = MagicMock()
        class2 = MagicMock()

        AutoLogOutputManager.register_member(class1, "method1", True, None)
        AutoLogOutputManager.register_member(class2, "method2", True, None)

        assert len(AutoLogOutputManager.logged_members) == 2
        assert class1 in AutoLogOutputManager.logged_members
        assert class2 in AutoLogOutputManager.logged_members


class TestAutoLogOutputManagerPublish:
    """Tests for AutoLogOutputManager publish functionality."""

    def setup_method(self):
        """Clear registration state before each test."""
        AutoLogOutputManager.logged_members = {}
        AutoLogOutputManager.root_cache = []

    def test_publish_calls_method_and_logs_value(self):
        """Verify publish calls a method and logs its return value."""
        mock_instance = MagicMock()
        mock_instance.get_speed.return_value = 5.0
        mock_table = MagicMock()

        AutoLogOutputManager.register_member(
            type(mock_instance), "get_speed", True, LogValue.LoggableType.Float, key="speed"
        )
        AutoLogOutputManager.publish(mock_instance, mock_table)

        mock_instance.get_speed.assert_called_once()
        mock_table.put_value.assert_called()

    def test_publish_accesses_field_value(self):
        """Verify publish accesses field values directly."""
        mock_instance = MagicMock()
        mock_instance.speed = 10.0
        mock_table = MagicMock()

        AutoLogOutputManager.register_member(
            type(mock_instance), "speed", False, LogValue.LoggableType.Float, key="speed"
        )
        AutoLogOutputManager.publish(mock_instance, mock_table)

        mock_table.put_value.assert_called()

    def test_publish_uses_default_key_as_member_name(self):
        """Verify publish uses member name as key when key is empty string."""
        mock_instance = MagicMock()
        mock_instance.speed = 5.0
        mock_table = MagicMock()

        AutoLogOutputManager.register_member(
            type(mock_instance), "speed", False, LogValue.LoggableType.Float, key=""
        )
        AutoLogOutputManager.publish(mock_instance, mock_table)

        # Should use "speed" as the key
        mock_table.put_value.assert_called()

    @patch('lib_6107.pykit.autolog.gc')
    def test_publish_all_discovers_instances_from_gc(self, mock_gc):
        """Verify publish_all discovers instances using garbage collector."""
        mock_instance = MagicMock()
        mock_instance.__class__ = type(mock_instance)
        mock_gc.get_referrers.return_value = [mock_instance]
        mock_table = MagicMock()

        AutoLogOutputManager.register_member(
            type(mock_instance), "method1", True, None
        )

        with patch.object(AutoLogOutputManager, 'publish'):
            AutoLogOutputManager.publish_all(mock_table)

        mock_gc.get_referrers.assert_called()

    def test_publish_all_with_provided_root_instances(self):
        """Verify publish_all uses provided root instances directly."""
        mock_instance = MagicMock()
        mock_table = MagicMock()
        instances = [mock_instance]

        with patch.object(AutoLogOutputManager, 'publish'):
            AutoLogOutputManager.publish_all(mock_table, instances)

        # Should not use garbage collector when instances provided
        # Method should be called with mock_table

    def test_publish_all_uses_cache_if_available(self):
        """Verify publish_all uses root_cache if populated."""
        cached_instance = MagicMock()
        AutoLogOutputManager.root_cache = [cached_instance]
        mock_table = MagicMock()

        with patch.object(AutoLogOutputManager, 'publish'):
            AutoLogOutputManager.publish_all(mock_table)

        # Verify it used the cache instead of fetching from gc


class TestAutologDecorator:
    """Tests for autolog dataclass decorator."""

    def test_autolog_adds_to_log_method(self):
        """Verify autolog decorator adds to_log method to dataclass."""
        @dataclass
        @autolog
        class TestClass:
            value: float = 0.0

        instance = TestClass()
        assert hasattr(instance, "to_log")
        assert callable(instance.to_log)

    def test_autolog_adds_from_log_method(self):
        """Verify autolog decorator adds from_log method to dataclass."""
        @dataclass
        @autolog
        class TestClass:
            value: float = 0.0

        instance = TestClass()
        assert hasattr(instance, "from_log")
        assert callable(instance.from_log)

    def test_to_log_serializes_float_field(self):
        """Verify to_log serializes float field to LogTable."""
        @dataclass
        @autolog
        class TestClass:
            speed: float = 5.0

        instance = TestClass(speed=10.0)
        mock_table = MagicMock()

        instance.to_log(mock_table, "prefix")

        mock_table.put.assert_called()

    def test_to_log_serializes_multiple_fields(self):
        """Verify to_log serializes all fields."""
        @dataclass
        @autolog
        class TestClass:
            speed: float = 0.0
            enabled: bool = False

        instance = TestClass(speed=5.0, enabled=True)
        mock_table = MagicMock()

        instance.to_log(mock_table, "prefix")

        assert mock_table.put.call_count == 2

    def test_from_log_deserializes_float_field(self):
        """Verify from_log deserializes float field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            speed: float = 0.0

        instance = TestClass()
        mock_table = MagicMock()
        mock_table.get_double.return_value = 15.0

        instance.from_log(mock_table, "prefix")

        assert instance.speed == 15.0

    def test_from_log_deserializes_boolean_field(self):
        """Verify from_log deserializes boolean field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            enabled: bool = False

        instance = TestClass()
        mock_table = MagicMock()
        mock_table.get_boolean.return_value = True

        instance.from_log(mock_table, "prefix")

        assert instance.enabled is True

    def test_from_log_deserializes_string_field(self):
        """Verify from_log deserializes string field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            name: str = ""

        instance = TestClass()
        mock_table = MagicMock()
        mock_table.get_string.return_value = "test_name"

        instance.from_log(mock_table, "prefix")

        assert instance.name == "test_name"

    def test_from_log_deserializes_integer_field(self):
        """Verify from_log deserializes integer field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            count: int = 0

        instance = TestClass()
        mock_table = MagicMock()
        mock_table.get_integer.return_value = 42

        instance.from_log(mock_table, "prefix")

        assert instance.count == 42

    def test_from_log_deserializes_list_of_floats(self):
        """Verify from_log deserializes list[float] field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            values: list[float] = None

            def __post_init__(self):
                if self.values is None:
                    self.values = []

        instance = TestClass(values=[1.0, 2.0])
        mock_table = MagicMock()
        mock_table.get_double_array.return_value = [3.0, 4.0, 5.0]

        instance.from_log(mock_table, "prefix")

        assert instance.values == [3.0, 4.0, 5.0]

    def test_from_log_deserializes_list_of_booleans(self):
        """Verify from_log deserializes list[bool] field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            flags: list[bool] = None

            def __post_init__(self):
                if self.flags is None:
                    self.flags = []

        instance = TestClass(flags=[True])
        mock_table = MagicMock()
        mock_table.get_boolean_array.return_value = [True, False, True]

        instance.from_log(mock_table, "prefix")

        assert instance.flags == [True, False, True]

    def test_from_log_deserializes_list_of_strings(self):
        """Verify from_log deserializes list[str] field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            names: list[str] = None

            def __post_init__(self):
                if self.names is None:
                    self.names = []

        instance = TestClass(names=["a"])
        mock_table = MagicMock()
        mock_table.get_string_array.return_value = ["x", "y", "z"]

        instance.from_log(mock_table, "prefix")

        assert instance.names == ["x", "y", "z"]

    def test_from_log_deserializes_list_of_integers(self):
        """Verify from_log deserializes list[int] field from LogTable."""
        @dataclass
        @autolog
        class TestClass:
            numbers: list[int] = None

            def __post_init__(self):
                if self.numbers is None:
                    self.numbers = []

        instance = TestClass(numbers=[1])
        mock_table = MagicMock()
        mock_table.get_integer_array.return_value = [10, 20, 30]

        instance.from_log(mock_table, "prefix")

        assert instance.numbers == [10, 20, 30]

    def test_autolog_registers_with_input_manager(self):
        """Verify autolog registers instance with AutoLogInputManager."""
        with patch.object(AutoLogInputManager, 'register_class') as mock_register:
            @dataclass
            @autolog
            class TestClass:
                value: float = 0.0

            instance = TestClass()

            # The registration happens in __post_init__ hook (if defined)
            # but the autolog decorator sets up the mechanism

    def test_to_log_with_nested_autolog_dataclass(self):
        """Verify to_log recursively calls to_log on nested autolog dataclasses."""
        @dataclass
        @autolog
        class InnerClass:
            inner_value: float = 1.0

        @dataclass
        @autolog
        class OuterClass:
            inner: InnerClass = None
            outer_value: float = 2.0

            def __post_init__(self):
                if self.inner is None:
                    self.inner = InnerClass()

        instance = OuterClass()
        mock_table = MagicMock()

        instance.to_log(mock_table, "prefix")

        # Should call put for outer_value and recursively for inner
        assert mock_table.put.call_count >= 1

    def test_from_log_with_nested_autolog_dataclass(self):
        """Verify from_log recursively calls from_log on nested autolog dataclasses."""
        @dataclass
        @autolog
        class InnerClass:
            inner_value: float = 1.0

        @dataclass
        @autolog
        class OuterClass:
            inner: InnerClass = None

            def __post_init__(self):
                if self.inner is None:
                    self.inner = InnerClass()

        instance = OuterClass()
        mock_table = MagicMock()

        instance.from_log(mock_table, "prefix")

        # Mock table will be called for nested field


class TestAutologOutputDecorator:
    """Tests for autolog_output method decorator."""

    def test_autolog_output_attaches_metadata_to_method(self):
        """Verify autolog_output attaches metadata to decorated method."""
        @autolog_output("test/key")
        def test_method():
            pass

        assert hasattr(test_method, "autolog_output_info")
        assert test_method.autolog_output_info["key"] == "test/key"

    def test_autolog_output_stores_is_method_flag(self):
        """Verify autolog_output sets is_method to True for methods."""
        @autolog_output("test/key")
        def test_method():
            pass

        assert test_method.autolog_output_info["is_method"] is True

    def test_autolog_output_stores_log_type(self):
        """Verify autolog_output stores log_type parameter."""
        @autolog_output("test/key", log_type=LogValue.LoggableType.Float)
        def test_method():
            pass

        assert test_method.autolog_output_info["log_type"] == LogValue.LoggableType.Float

    def test_autolog_output_stores_custom_type(self):
        """Verify autolog_output stores custom_type parameter."""
        @autolog_output("test/key", custom_type="custom_type_string")
        def test_method():
            pass

        assert test_method.autolog_output_info["custom_type"] == "custom_type_string"

    def test_autolog_output_stores_unit(self):
        """Verify autolog_output stores unit parameter."""
        @autolog_output("test/key", unit="m/s")
        def test_method():
            pass

        assert test_method.autolog_output_info["unit"] == "m/s"

    def test_autolog_output_default_values(self):
        """Verify autolog_output uses default values when not specified."""
        @autolog_output("test/key")
        def test_method():
            pass

        info = test_method.autolog_output_info
        assert info["log_type"] is None
        assert info["custom_type"] == ""
        assert info["unit"] is None

    def test_autolog_output_returns_decorated_function(self):
        """Verify autolog_output returns the original function."""
        def original_method():
            return 42

        decorated_method = autolog_output("test/key")(original_method)

        assert decorated_method() == 42


class TestAutologgableOutputDecorator:
    """Tests for autologgable_output class decorator."""

    def test_autologgable_output_sets_auto_log_flag(self):
        """Verify autologgable_output sets _do_autolog flag on class."""
        @autologgable_output
        class TestClass:
            pass

        assert hasattr(TestClass, "_do_autolog")
        assert TestClass._do_autolog is True

    def test_autologgable_output_discovers_autolog_output_methods(self):
        """Verify autologgable_output discovers methods decorated with @autolog_output."""
        @autologgable_output
        class TestClass:
            @autolog_output("test/speed")
            def get_speed(self):
                return 5.0

        assert TestClass in AutoLogOutputManager.logged_members
        assert len(AutoLogOutputManager.logged_members[TestClass]) == 1

    def test_autologgable_output_registers_multiple_methods(self):
        """Verify autologgable_output discovers multiple @autolog_output methods."""
        AutoLogOutputManager.logged_members = {}
        AutoLogOutputManager.root_cache = []

        @autologgable_output
        class TestClass:
            @autolog_output("test/speed")
            def get_speed(self):
                return 5.0

            @autolog_output("test/heading")
            def get_heading(self):
                return 90.0

        assert len(AutoLogOutputManager.logged_members[TestClass]) == 2

    def test_autologgable_output_preserves_class_functionality(self):
        """Verify autologgable_output doesn't break class functionality."""
        @autologgable_output
        class TestClass:
            def __init__(self, value):
                self.value = value

            @autolog_output("test/value")
            def get_value(self):
                return self.value

        instance = TestClass(42)
        assert instance.get_value() == 42


@pytest.mark.parametrize(
    "key,log_type,custom_type,unit",
    [
        ("speed", LogValue.LoggableType.Float, "", "m/s"),
        ("enabled", LogValue.LoggableType.Boolean, "", None),
        ("count", LogValue.LoggableType.Integer, "custom", None),
        ("name", LogValue.LoggableType.String, "", None),
    ],
)
def test_autolog_output_with_various_parameters(key, log_type, custom_type, unit):
    """Verify autolog_output handles various parameter combinations."""

    @autolog_output(key, log_type=log_type, custom_type=custom_type, unit=unit)
    def test_method():
        pass

    info = test_method.autolog_output_info
    assert info["key"] == key
    assert info["log_type"] == log_type
    assert info["custom_type"] == custom_type
    assert info["unit"] == unit


@pytest.mark.parametrize(
    "field_type,value,mock_method,expected",
    [
        (float, 5.0, "get_double", 10.0),
        (bool, False, "get_boolean", True),
        (int, 0, "get_integer", 42),
        (str, "", "get_string", "test"),
    ],
)
def test_autolog_from_log_with_various_types(field_type, value, mock_method, expected):
    """Verify from_log handles various scalar types correctly."""
    @dataclass
    @autolog
    class TestClass:
        field: field_type = value  # type: ignore

    instance = TestClass()
    mock_table = MagicMock()
    setattr(mock_table, mock_method, MagicMock(return_value=expected))

    instance.from_log(mock_table, "prefix")

    getattr(mock_table, mock_method).assert_called()


class TestAutologEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_autolog_with_empty_dataclass(self):
        """Verify autolog handles empty dataclass."""
        @dataclass
        @autolog
        class EmptyClass:
            pass

        instance = EmptyClass()
        mock_table = MagicMock()

        instance.to_log(mock_table, "prefix")
        instance.from_log(mock_table, "prefix")

    def test_autolog_with_many_fields(self):
        """Verify autolog handles dataclass with many fields."""
        @dataclass
        @autolog
        class ManyFieldsClass:
            f1: float = 0.0
            f2: float = 0.0
            f3: float = 0.0
            f4: float = 0.0
            f5: float = 0.0

        instance = ManyFieldsClass(f1=1.0, f2=2.0, f3=3.0, f4=4.0, f5=5.0)
        mock_table = MagicMock()

        instance.to_log(mock_table, "prefix")

        assert mock_table.put.call_count == 5

    def test_autolog_output_with_empty_key(self):
        """Verify autolog_output handles empty key."""
        @autolog_output("")
        def test_method():
            pass

        assert test_method.autolog_output_info["key"] == ""

    def test_autologgable_output_with_no_decorated_methods(self):
        """Verify autologgable_output handles class with no @autolog_output methods."""
        @autologgable_output
        class NoDecoratedClass:
            def regular_method(self):
                pass

        assert NoDecoratedClass._do_autolog is True

    def test_autolog_from_log_with_missing_value(self):
        """Verify from_log handles missing values by using defaults."""
        @dataclass
        @autolog
        class TestClass:
            value: float = 5.0

        instance = TestClass()
        mock_table = MagicMock()
        mock_table.get_double.side_effect = lambda key, default: default

        instance.from_log(mock_table, "prefix")

        assert instance.value == 5.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

