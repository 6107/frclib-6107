from lib_6107.pykit.logvalue import LogValue

def infers_boolean_type_correctly_for_true():
    lv = LogValue(True)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.value is True

def infers_boolean_type_correctly_for_false():
    lv = LogValue(False)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.value is False

def infers_integer_type_correctly():
    lv = LogValue(42)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 42

def infers_integer_type_for_negative_numbers():
    lv = LogValue(-100)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == -100

def infers_integer_type_for_zero():
    lv = LogValue(0)
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 0

def infers_double_type_correctly():
    lv = LogValue(3.14)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 3.14

def infers_double_type_for_negative_floats():
    lv = LogValue(-2.5)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == -2.5

def infers_double_type_for_zero_float():
    lv = LogValue(0.0)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 0.0

def infers_string_type_correctly():
    lv = LogValue("test")
    assert lv.log_type == LogValue.LoggableType.String
    assert lv.value == "test"

def infers_string_type_for_empty_string():
    lv = LogValue("")
    assert lv.log_type == LogValue.LoggableType.String
    assert lv.value == ""

def infers_raw_type_for_bytes():
    lv = LogValue(b"\x00\x01")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == b"\x00\x01"

def infers_raw_type_for_empty_bytes():
    lv = LogValue(b"")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == b""

def infers_boolean_array_type():
    lv = LogValue([True, False, True])
    assert lv.log_type == LogValue.LoggableType.BooleanArray
    assert lv.value == [True, False, True]

def infers_boolean_array_with_single_element():
    lv = LogValue([False])
    assert lv.log_type == LogValue.LoggableType.BooleanArray
    assert lv.value == [False]

def infers_integer_array_type():
    lv = LogValue([1, 2, 3])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [1, 2, 3]

def infers_integer_array_with_negative_numbers():
    lv = LogValue([-1, 0, 42])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [-1, 0, 42]

def infers_integer_array_with_single_element():
    lv = LogValue([5])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == [5]

def infers_double_array_type():
    lv = LogValue([1.0, 2.5, 3.14])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [1.0, 2.5, 3.14]

def infers_double_array_with_negative_floats():
    lv = LogValue([-1.5, 0.0, 2.7])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [-1.5, 0.0, 2.7]

def infers_double_array_with_single_element():
    lv = LogValue([3.14])
    assert lv.log_type == LogValue.LoggableType.DoubleArray
    assert lv.value == [3.14]

def infers_string_array_type():
    lv = LogValue(["a", "b", "c"])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["a", "b", "c"]

def infers_string_array_with_empty_strings():
    lv = LogValue(["", "test", ""])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["", "test", ""]

def infers_string_array_with_single_element():
    lv = LogValue(["hello"])
    assert lv.log_type == LogValue.LoggableType.StringArray
    assert lv.value == ["hello"]

def empty_list_defaults_to_integer_array():
    lv = LogValue([])
    assert lv.log_type == LogValue.LoggableType.IntegerArray
    assert lv.value == []

def raises_type_error_for_mixed_int_and_float_list():
    try:
        LogValue([1, 2.0, 3])
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported list type" in str(e)

def raises_type_error_for_mixed_int_and_string_list():
    try:
        LogValue([1, "two", 3])
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported list type" in str(e)

def raises_type_error_for_mixed_bool_and_int_list():
    try:
        LogValue([True, 1, False])
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported list type" in str(e)

def raises_type_error_for_dict_value():
    try:
        LogValue({"key": "value"})
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)

def raises_type_error_for_tuple_value():
    try:
        LogValue((1, 2, 3))
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)

def raises_type_error_for_set_value():
    try:
        LogValue({1, 2, 3})
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)

def raises_type_error_for_none_value():
    try:
        LogValue(None)
        assert False, "Should raise TypeError"
    except TypeError as e:
        assert "Unsupported type" in str(e)

def stores_custom_type_string():
    lv = LogValue(42, type_str="custom_type")
    assert lv.custom_type == "custom_type"

def stores_empty_custom_type_string():
    lv = LogValue(42, type_str="")
    assert lv.custom_type == ""

def stores_unit_parameter():
    lv = LogValue(5.0, unit="meters")
    assert lv.unit == "meters"

def stores_none_unit_by_default():
    lv = LogValue(3.14)
    assert lv.unit is None

def combines_custom_type_and_unit():
    lv = LogValue(10.0, type_str="struct:Pose2d", unit="radians")
    assert lv.custom_type == "struct:Pose2d"
    assert lv.unit == "radians"
    assert lv.log_type == LogValue.LoggableType.Double

def withtype_creates_logvalue_with_explicit_type():
    lv = LogValue.withType(LogValue.LoggableType.Double, 42)
    assert lv.log_type == LogValue.LoggableType.Double
    assert lv.value == 42

def withtype_creates_raw_type_with_bytes():
    raw_data = b"\x00\x01\x02"
    lv = LogValue.withType(LogValue.LoggableType.Raw, raw_data, type_str="struct:Pose2d")
    assert lv.log_type == LogValue.LoggableType.Raw
    assert lv.value == raw_data
    assert lv.custom_type == "struct:Pose2d"

def withtype_sets_unit():
    lv = LogValue.withType(LogValue.LoggableType.Double, 3.14, unit="degrees")
    assert lv.unit == "degrees"
    assert lv.log_type == LogValue.LoggableType.Double

def withtype_with_all_parameters():
    lv = LogValue.withType(LogValue.LoggableType.Integer, 100, type_str="custom", unit="counts")
    assert lv.log_type == LogValue.LoggableType.Integer
    assert lv.value == 100
    assert lv.custom_type == "custom"
    assert lv.unit == "counts"

def getwpilogtype_returns_custom_type_when_set():
    lv = LogValue(42, type_str="struct:Pose2d")
    assert lv.getWPILOGType() == "struct:Pose2d"

def getwpilogtype_returns_boolean_for_boolean_type():
    lv = LogValue(True)
    assert lv.getWPILOGType() == "boolean"

def getwpilogtype_returns_int64_for_integer_type():
    lv = LogValue(42)
    assert lv.getWPILOGType() == "int64"

def getwpilogtype_returns_float_for_float_type():
    lv = LogValue.withType(LogValue.LoggableType.Float, 1.5)
    assert lv.getWPILOGType() == "float"

def getwpilogtype_returns_double_for_double_type():
    lv = LogValue(3.14)
    assert lv.getWPILOGType() == "double"

def getwpilogtype_returns_string_for_string_type():
    lv = LogValue("test")
    assert lv.getWPILOGType() == "string"

def getwpilogtype_returns_raw_for_raw_type():
    lv = LogValue(b"\x00")
    assert lv.getWPILOGType() == "raw"

def getwpilogtype_returns_boolean_array():
    lv = LogValue([True, False])
    assert lv.getWPILOGType() == "boolean[]"

def getwpilogtype_returns_int64_array():
    lv = LogValue([1, 2, 3])
    assert lv.getWPILOGType() == "int64[]"

def getwpilogtype_returns_double_array():
    lv = LogValue([1.0, 2.0])
    assert lv.getWPILOGType() == "double[]"

def getwpilogtype_returns_string_array():
    lv = LogValue(["a", "b"])
    assert lv.getWPILOGType() == "string[]"

def getnt4type_returns_custom_type_when_set():
    lv = LogValue(42, type_str="struct:Robot")
    assert lv.getNT4Type() == "struct:Robot"

def getnt4type_returns_boolean_for_boolean_type():
    lv = LogValue(True)
    assert lv.getNT4Type() == "boolean"

def getnt4type_returns_int_for_integer_type():
    lv = LogValue(42)
    assert lv.getNT4Type() == "int"

def getnt4type_returns_float_for_float_type():
    lv = LogValue.withType(LogValue.LoggableType.Float, 1.5)
    assert lv.getNT4Type() == "float"

def getnt4type_returns_double_for_double_type():
    lv = LogValue(3.14)
    assert lv.getNT4Type() == "double"

def getnt4type_returns_string_for_string_type():
    lv = LogValue("test")
    assert lv.getNT4Type() == "string"

def getnt4type_returns_raw_for_raw_type():
    lv = LogValue(b"\x00")
    assert lv.getNT4Type() == "raw"

def getnt4type_returns_boolean_array():
    lv = LogValue([True, False])
    assert lv.getNT4Type() == "boolean[]"

def getnt4type_returns_int_array():
    lv = LogValue([1, 2, 3])
    assert lv.getNT4Type() == "int[]"

def getnt4type_returns_double_array():
    lv = LogValue([1.0, 2.0])
    assert lv.getNT4Type() == "double[]"

def getnt4type_returns_string_array():
    lv = LogValue(["a", "b"])
    assert lv.getNT4Type() == "string[]"

def nt4_and_wpilog_types_differ_for_integer():
    lv = LogValue(42)
    assert lv.getWPILOGType() == "int64"
    assert lv.getNT4Type() == "int"

def nt4_and_wpilog_types_differ_for_integer_array():
    lv = LogValue([1, 2, 3])
    assert lv.getWPILOGType() == "int64[]"
    assert lv.getNT4Type() == "int[]"

def loggabletype_getwpilogtype_for_all_types():
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
        assert log_type.getWPILOGType() == expected_str

def loggabletype_getnt4type_for_all_types():
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
        assert log_type.getNT4Type() == expected_str

def fromwpilogtype_reconstructs_type_from_valid_string():
    assert LogValue.LoggableType.fromWPILOGType("double") == LogValue.LoggableType.Double
    assert LogValue.LoggableType.fromWPILOGType("int64") == LogValue.LoggableType.Integer
    assert LogValue.LoggableType.fromWPILOGType("boolean") == LogValue.LoggableType.Boolean
    assert LogValue.LoggableType.fromWPILOGType("string") == LogValue.LoggableType.String
    assert LogValue.LoggableType.fromWPILOGType("raw") == LogValue.LoggableType.Raw

def fromwpilogtype_reconstructs_array_types():
    assert LogValue.LoggableType.fromWPILOGType("int64[]") == LogValue.LoggableType.IntegerArray
    assert LogValue.LoggableType.fromWPILOGType("double[]") == LogValue.LoggableType.DoubleArray
    assert LogValue.LoggableType.fromWPILOGType("boolean[]") == LogValue.LoggableType.BooleanArray
    assert LogValue.LoggableType.fromWPILOGType("string[]") == LogValue.LoggableType.StringArray

def fromwpilogtype_defaults_to_raw_for_unknown_type():
    assert LogValue.LoggableType.fromWPILOGType("unknown_type") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.fromWPILOGType("") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.fromWPILOGType("struct:CustomType") == LogValue.LoggableType.Raw

def fromnt4type_reconstructs_type_from_valid_string():
    assert LogValue.LoggableType.fromNT4Type("double") == LogValue.LoggableType.Double
    assert LogValue.LoggableType.fromNT4Type("int") == LogValue.LoggableType.Integer
    assert LogValue.LoggableType.fromNT4Type("boolean") == LogValue.LoggableType.Boolean
    assert LogValue.LoggableType.fromNT4Type("string") == LogValue.LoggableType.String
    assert LogValue.LoggableType.fromNT4Type("raw") == LogValue.LoggableType.Raw

def fromnt4type_reconstructs_array_types():
    assert LogValue.LoggableType.fromNT4Type("int[]") == LogValue.LoggableType.IntegerArray
    assert LogValue.LoggableType.fromNT4Type("double[]") == LogValue.LoggableType.DoubleArray
    assert LogValue.LoggableType.fromNT4Type("boolean[]") == LogValue.LoggableType.BooleanArray
    assert LogValue.LoggableType.fromNT4Type("string[]") == LogValue.LoggableType.StringArray

def fromnt4type_defaults_to_raw_for_unknown_type():
    assert LogValue.LoggableType.fromNT4Type("unknown_type") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.fromNT4Type("") == LogValue.LoggableType.Raw
    assert LogValue.LoggableType.fromNT4Type("struct:CustomType") == LogValue.LoggableType.Raw

def logvalue_stores_value_correctly_for_all_types():
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

def bool_checked_before_int_for_type_inference():
    lv = LogValue(True)
    assert lv.log_type == LogValue.LoggableType.Boolean
    assert lv.log_type != LogValue.LoggableType.Integer