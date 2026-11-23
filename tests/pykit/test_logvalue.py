import pytest

from lib_6107.pykit.logvalue import LogValue


def test_infers_boolean_type_correctly_for_true():
    lv = LogValue(True)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.value is True


def test_infers_boolean_type_correctly_for_false():
    lv = LogValue(False)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.value is False


def test_infers_integer_type_correctly():
    lv = LogValue(42)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 42


def test_infers_integer_type_for_negative_numbers():
    lv = LogValue(-100)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == -100


def test_infers_integer_type_for_zero():
    lv = LogValue(0)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 0


def test_infers_double_type_correctly():
    lv = LogValue(3.14)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 3.14


def test_infers_double_type_for_negative_floats():
    lv = LogValue(-2.5)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == -2.5


def test_infers_double_type_for_zero_float():
    lv = LogValue(0.0)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 0.0


def test_infers_string_type_correctly():
    lv = LogValue("test")
    assert lv.log_type == LogValue.LoggableType.String
    assert lv.value == "test"


def test_infers_string_type_for_empty_string():
    lv = LogValue("")
    assert lv.log_type == LogValue.LoggableType.String
    assert lv.value == ""


def test_infers_raw_type_for_bytes():
    lv = LogValue(b"\x00\x01")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == b"\x00\x01"


def test_infers_raw_type_for_empty_bytes():
    lv = LogValue(b"")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == b""


def test_infers_boolean_array_type():
    lv = LogValue([True, False, True])
    assert lv.log_type == LogValue.LoggableType.BooleanArray
    assert lv.value == [True, False, True]


def test_infers_boolean_array_with_single_element():
    lv = LogValue([False])
    assert lv.log_type == LogValue.LoggableType.BooleanArray
    assert lv.value == [False]


def test_infers_integer_array_type():
    lv = LogValue([1, 2, 3])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [1, 2, 3]


def test_infers_integer_array_with_negative_numbers():
    lv = LogValue([-1, 0, 42])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [-1, 0, 42]


def test_infers_integer_array_with_single_element():
    lv = LogValue([5])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [5]


def test_infers_double_array_type():
    lv = LogValue([1.0, 2.5, 3.14])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [1.0, 2.5, 3.14]


def test_infers_double_array_with_negative_floats():
    lv = LogValue([-1.5, 0.0, 2.7])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [-1.5, 0.0, 2.7]


def test_infers_double_array_with_single_element():
    lv = LogValue([3.14])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [3.14]


def test_infers_string_array_type():
    lv = LogValue(["a", "b", "c"])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["a", "b", "c"]


def test_infers_string_array_with_empty_strings():
    lv = LogValue(["", "test", ""])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["", "test", ""]


def test_infers_string_array_with_single_element():
    lv = LogValue(["hello"])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["hello"]


def test_empty_list_defaults_to_integer_array():
    lv = LogValue([])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == []


def test_list_value_is_copied_from_caller():
    src = [1.0, 2.0]
    lv = LogValue(src)
    src.append(3.0)
    assert lv.value == [1.0, 2.0]


def test_with_type_copies_list():
    src = [1.0]
    lv = LogValue.with_type(LogValue.LoggableType.DoubleArray, src)
    src.append(2.0)
    assert lv.value == [1.0]


def test_put_value_does_not_mutate_empty_array_argument():
    from lib_6107.pykit.logtable import LogTable

    table = LogTable(0)
    table.put_value("a", LogValue([1.0, 2.0]))
    empty = LogValue([])
    table.put_value("a", empty)
    assert empty.log_type == LogValue.LoggableType.IntegerArray
    assert table.get_all()["/a"].log_type == LogValue.LoggableType.DoubleArray


def test_raises_type_error_for_mixed_int_and_float_list():
    try:
        LogValue([1, 2.0, 3])
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported list type" in str(e)


def test_raises_type_error_for_mixed_int_and_string_list():
    try:
        LogValue([1, "two", 3])
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported list type" in str(e)


def test_mixed_bool_and_int_list_is_treated_as_integer_array():
    # bool is a subclass of int, so a mixed list falls through to the all-int branch
    lv = LogValue([True, 1, False])
    assert lv.log_type == LogValue.LoggableType.IntegerArray


def test_raises_type_error_for_dict_value():
    try:
        LogValue({"key": "value"})
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)


def test_raises_type_error_for_tuple_value():
    try:
        LogValue((1, 2, 3))
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)


def test_raises_type_error_for_set_value():
    try:
        LogValue({1, 2, 3})
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)


def test_raises_type_error_for_none_value():
    try:
        LogValue(None)
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)


def test_stores_custom_type_string():
    lv = LogValue(42, type_str="custom_type")
    assert lv.custom_type == "custom_type"


def test_stores_empty_custom_type_string():
    lv = LogValue(42, type_str="")
    assert lv.custom_type == ""


def test_stores_unit_parameter():
    lv = LogValue(5.0, unit="meters")
    assert lv.unit == "meters"


def test_stores_none_unit_by_default():
    lv = LogValue(3.14)
    assert lv.unit is None


def test_combines_custom_type_and_unit():
    lv = LogValue(10.0, type_str="struct:Pose2d", unit="radians")
    assert lv.custom_type == "struct:Pose2d"
    assert lv.unit == "radians"
    assert lv.log_type == LogValue.LoggableType.Double


def test_withtype_creates_logvalue_with_explicit_type():
    lv = LogValue.with_type(LogValue.LoggableType.Double, 42)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 42


def test_withtype_creates_raw_type_with_bytes():
    raw_data = b"\x00\x01\x02"
    lv = LogValue.with_type(LogValue.LoggableType.Raw, raw_data, type_str="struct:Pose2d")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == raw_data
    assert lv.custom_type == "struct:Pose2d"


def test_withtype_sets_unit():
    lv = LogValue.with_type(LogValue.LoggableType.Double, 3.14, unit="degrees")
    assert lv.unit == "degrees"
    assert lv.log_type == LogValue.LoggableType.Double


def test_withtype_with_all_parameters():
    lv = LogValue.with_type(LogValue.LoggableType.Integer, 100, type_str="custom", unit="counts")
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 100
    assert lv.custom_type == "custom"
    assert lv.unit == "counts"


def test_getwpilogtype_returns_custom_type_when_set():
    lv = LogValue(42, type_str="struct:Pose2d")
    assert lv.get_wpilog_type() == "struct:Pose2d"


def test_getwpilogtype_returns_boolean_for_boolean_type():
    lv = LogValue(True)
    assert lv.get_wpilog_type() == "boolean"


def test_getwpilogtype_returns_int64_for_integer_type():
    lv = LogValue(42)
    assert lv.get_wpilog_type() == "int64"


def test_getwpilogtype_returns_float_for_float_type():
    lv = LogValue.with_type(LogValue.LoggableType.Float, 1.5)
    assert lv.get_wpilog_type() == "float"


def test_getwpilogtype_returns_double_for_double_type():
    lv = LogValue(3.14)
    assert lv.get_wpilog_type() == "double"


def test_getwpilogtype_returns_string_for_string_type():
    lv = LogValue("test")
    assert lv.get_wpilog_type() == "string"


def test_getwpilogtype_returns_raw_for_raw_type():
    lv = LogValue(b"\x00")
    assert lv.get_wpilog_type() == "raw"


def test_getwpilogtype_returns_boolean_array():
    lv = LogValue([True, False])
    assert lv.get_wpilog_type() == "boolean[]"


def test_getwpilogtype_returns_int64_array():
    lv = LogValue([1, 2, 3])
    assert lv.get_wpilog_type() == "int64[]"


def test_getwpilogtype_returns_double_array():
    lv = LogValue([1.0, 2.0])
    assert lv.get_wpilog_type() == "double[]"


def test_getwpilogtype_returns_string_array():
    lv = LogValue(["a", "b"])
    assert lv.get_wpilog_type() == "string[]"


def test_getnt4type_returns_custom_type_when_set():
    lv = LogValue(42, type_str="struct:Robot")
    assert lv.get_nt4_type() == "struct:Robot"


def test_getnt4type_returns_boolean_for_boolean_type():
    lv = LogValue(True)
    assert lv.get_nt4_type() == "boolean"


def test_getnt4type_returns_int_for_integer_type():
    lv = LogValue(42)
    assert lv.get_nt4_type() == "int"


def test_getnt4type_returns_float_for_float_type():
    lv = LogValue.with_type(LogValue.LoggableType.Float, 1.5)
    assert lv.get_nt4_type() == "float"


def test_getnt4type_returns_double_for_double_type():
    lv = LogValue(3.14)
    assert lv.get_nt4_type() == "double"


def test_getnt4type_returns_string_for_string_type():
    lv = LogValue("test")
    assert lv.get_nt4_type() == "string"


def test_getnt4type_returns_raw_for_raw_type():
    lv = LogValue(b"\x00")
    assert lv.get_nt4_type() == "raw"


def test_getnt4type_returns_boolean_array():
    lv = LogValue([True, False])
    assert lv.get_nt4_type() == "boolean[]"


def test_getnt4type_returns_int_array():
    lv = LogValue([1, 2, 3])
    assert lv.get_nt4_type() == "int[]"


def test_getnt4type_returns_double_array():
    lv = LogValue([1.0, 2.0])
    assert lv.get_nt4_type() == "double[]"


def test_getnt4type_returns_string_array():
    lv = LogValue(["a", "b"])
    assert lv.get_nt4_type() == "string[]"


def test_nt4_and_wpilog_types_differ_for_integer():
    lv = LogValue(42)
    assert lv.get_wpilog_type() == "int64"
    assert lv.get_nt4_type() == "int"


def test_nt4_and_wpilog_types_differ_for_integer_array():
    lv = LogValue([1, 2, 3])
    assert lv.get_wpilog_type() == "int64[]"
    assert lv.get_nt4_type() == "int[]"


def test_loggabletype_getwpilogtype_for_all_types():
    type_map = {
        LogValue.LoggableType.Raw: "raw",
        LogValue.LoggableType.Boolean: "boolean",
        LogValue.LoggableType.Integer: "int64",
        LogValue.LoggableType.Float: "float",
        LogValue.LoggableType.Double: "double",
        LogValue.LoggableType.String: "string",
        LogValue.LoggableType.BooleanArray: "boolean[]",
        LogValue.LoggableType.IntegerArray: "int64[]",
        LogValue.LoggableType.FloatArray: "float[]",
        LogValue.LoggableType.DoubleArray: "double[]",
        LogValue.LoggableType.StringArray: "string[]",
    }
    for log_type, expected_str in type_map.items():
        assert log_type.get_wpilog_type() == expected_str


def test_loggabletype_getnt4type_for_all_types():
    type_map = {
        LogValue.LoggableType.Raw: "raw",
        LogValue.LoggableType.Boolean: "boolean",
        LogValue.LoggableType.Integer: "int",
        LogValue.LoggableType.Float: "float",
        LogValue.LoggableType.Double: "double",
        LogValue.LoggableType.String: "string",
        LogValue.LoggableType.BooleanArray: "boolean[]",
        LogValue.LoggableType.IntegerArray: "int[]",
        LogValue.LoggableType.FloatArray: "float[]",
        LogValue.LoggableType.DoubleArray: "double[]",
        LogValue.LoggableType.StringArray: "string[]",
    }
    for log_type, expected_str in type_map.items():
        assert log_type.get_nt4_type() == expected_str


def test_fromwpilogtype_reconstructs_type_from_valid_string():
    assert LogValue.LoggableType.from_wpilog_type("double") == LogValue.LoggableType.Double
    assert LogValue.LoggableType.from_wpilog_type("int64") == LogValue.LoggableType.Integer
    assert LogValue.LoggableType.from_wpilog_type("boolean") == LogValue.LoggableType.Boolean
    assert LogValue.LoggableType.from_wpilog_type("string") == LogValue.LoggableType.String
    assert LogValue.LoggableType.from_wpilog_type("raw") == LogValue.LoggableType.Raw


def test_fromwpilogtype_reconstructs_array_types():
    assert LogValue.LoggableType.from_wpilog_type("int64[]") == LogValue.LoggableType.IntegerArray
    assert LogValue.LoggableType.from_wpilog_type("double[]") == LogValue.LoggableType.DoubleArray
    assert LogValue.LoggableType.from_wpilog_type("boolean[]") == LogValue.LoggableType.BooleanArray
    assert LogValue.LoggableType.from_wpilog_type("string[]") == LogValue.LoggableType.StringArray


def test_fromwpilogtype_defaults_to_raw_for_unknown_type():
    assert LogValue.LoggableType.from_wpilog_type("unknown_type") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.from_wpilog_type("") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.from_wpilog_type("struct:CustomType") == LogValue.LoggableType.Raw


def test_fromnt4type_reconstructs_type_from_valid_string():
    assert LogValue.LoggableType.from_nt4_type("double") == LogValue.LoggableType.Double
    assert LogValue.LoggableType.from_nt4_type("int") == LogValue.LoggableType.Integer
    assert LogValue.LoggableType.from_nt4_type("boolean") == LogValue.LoggableType.Boolean
    assert LogValue.LoggableType.from_nt4_type("string") == LogValue.LoggableType.String
    assert LogValue.LoggableType.from_nt4_type("raw") == LogValue.LoggableType.Raw


def test_fromnt4type_reconstructs_array_types():
    assert LogValue.LoggableType.from_nt4_type("int[]") == LogValue.LoggableType.IntegerArray
    assert LogValue.LoggableType.from_nt4_type("double[]") == LogValue.LoggableType.DoubleArray
    assert LogValue.LoggableType.from_nt4_type("boolean[]") == LogValue.LoggableType.BooleanArray
    assert LogValue.LoggableType.from_nt4_type("string[]") == LogValue.LoggableType.StringArray


def test_fromnt4type_defaults_to_raw_for_unknown_type():
    assert LogValue.LoggableType.from_nt4_type("unknown_type") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.from_nt4_type("") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.from_nt4_type("struct:CustomType") == LogValue.LoggableType.Raw


def test_logvalue_stores_value_correctly_for_all_types():
    values = [
        (True, LogValue.LoggableType.Boolean),
        (42, LogValue.LoggableType.Integer),
        (3.14, LogValue.LoggableType.Double),
        ("text", LogValue.LoggableType.String),
        (b"bytes", LogValue.LoggableType.Raw),
        ([True], LogValue.LoggableType.BooleanArray),
        ([1], LogValue.LoggableType.IntegerArray),
        ([1.0], LogValue.LoggableType.DoubleArray),
        (["s"], LogValue.LoggableType.StringArray),
    ]
    for val, expected_type in values:
        lv = LogValue(val)
        assert lv.value == val
        assert lv.log_type == expected_type


def test_bool_checked_before_int_for_type_inference():
    lv = LogValue(True)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.log_type != LogValue.LoggableType.Integer
