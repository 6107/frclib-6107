from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.logtable import LogTable


def logtable_initializes_with_default_prefix():
    table = LogTable(1000)
    assert table.prefix == "/"
    assert table.timestamp == 1000
    assert table.depth == 0
    assert table.data == {}

def logtable_initializes_with_custom_prefix():
    table = LogTable(2000, "/Drivetrain/")
    assert table.prefix == "/Drivetrain/"
    assert table.timestamp == 2000

def logtable_gettimestamp_returns_stored_timestamp():
    table = LogTable(5000)
    assert table.getTimestamp() == 5000

def logtable_settimestamp_updates_timestamp():
    table = LogTable(1000)
    table.setTimestamp(9999)
    assert table.timestamp == 9999
    assert table.getTimestamp() == 9999

def logtable_put_stores_boolean_value():
    table = LogTable(1000)
    table.put("enabled", True)
    assert table.data["/enabled"].value is True
    assert table.data["/enabled"].log_type == LogValue.LoggableType.Boolean

def logtable_put_stores_integer_value():
    table = LogTable(1000)
    table.put("count", 42)
    assert table.data["/count"].value == 42
    assert table.data["/count"].log_type == LogValue.LoggableType.Integer

def logtable_put_stores_double_value():
    table = LogTable(1000)
    table.put("speed", 3.14)
    assert table.data["/speed"].value == 3.14
    assert table.data["/speed"].log_type == LogValue.LoggableType.Double

def logtable_put_stores_string_value():
    table = LogTable(1000)
    table.put("state", "running")
    assert table.data["/state"].value == "running"
    assert table.data["/state"].log_type == LogValue.LoggableType.String

def logtable_put_stores_bytes_value():
    table = LogTable(1000)
    table.put("raw_data", b"\x00\x01")
    assert table.data["/raw_data"].value == b"\x00\x01"
    assert table.data["/raw_data"].log_type == LogValue.LoggableType.Raw

def logtable_put_stores_boolean_array():
    table = LogTable(1000)
    table.put("flags", [True, False, True])
    assert table.data["/flags"].value == [True, False, True]
    assert table.data["/flags"].log_type == LogValue.LoggableType.BooleanArray

def logtable_put_stores_integer_array():
    table = LogTable(1000)
    table.put("counts", [1, 2, 3])
    assert table.data["/counts"].value == [1, 2, 3]
    assert table.data["/counts"].log_type == LogValue.LoggableType.IntegerArray

def logtable_put_stores_double_array():
    table = LogTable(1000)
    table.put("speeds", [1.0, 2.5, 3.14])
    assert table.data["/speeds"].value == [1.0, 2.5, 3.14]
    assert table.data["/speeds"].log_type == LogValue.LoggableType.DoubleArray

def logtable_put_stores_string_array():
    table = LogTable(1000)
    table.put("names", ["a", "b", "c"])
    assert table.data["/names"].value == ["a", "b", "c"]
    assert table.data["/names"].log_type == LogValue.LoggableType.StringArray

def logtable_put_with_custom_type_string():
    table = LogTable(1000)
    table.put("data", b"struct_bytes", type_str="struct:Pose2d")
    assert table.data["/data"].custom_type == "struct:Pose2d"

def logtable_put_with_unit_string():
    table = LogTable(1000)
    table.put("distance", 5.0, unit="meters")
    assert table.data["/distance"].unit == "meters"

def logtable_get_returns_value_for_existing_key():
    table = LogTable(1000)
    table.put("speed", 3.5)
    assert table.get("speed", 0.0) == 3.5

def logtable_get_returns_default_for_missing_key():
    table = LogTable(1000)
    assert table.get("nonexistent", 99.0) == 99.0

def logtable_get_raw_returns_bytes_for_correct_type():
    table = LogTable(1000)
    table.put("data", b"\x01\x02\x03")
    assert table.get_raw("data", b"") == b"\x01\x02\x03"

def logtable_get_raw_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_raw("value", b"default") == b"default"

def logtable_get_raw_returns_default_for_missing_key():
    table = LogTable(1000)
    assert table.get_raw("missing", b"default") == b"default"

def logtable_get_boolean_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("enabled", True)
    assert table.get_boolean("enabled", False) is True

def logtable_get_boolean_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_boolean("value", False) is False

def logtable_get_integer_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("count", 42)
    assert table.get_integer("count", 0) == 42

def logtable_get_integer_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 3.14)
    assert table.get_integer("value", 0) == 0

def logtable_get_float_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put_value("voltage", LogValue.withType(LogValue.LoggableType.Float, 12.5))
    assert table.get_float("voltage", 0.0) == 12.5

def logtable_get_float_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_float("value", 0.0) == 0.0

def logtable_get_double_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("speed", 3.14)
    assert table.get_double("speed", 0.0) == 3.14

def logtable_get_double_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_double("value", 0.0) == 0.0

def logtable_get_string_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("state", "running")
    assert table.get_string("state", "default") == "running"

def logtable_get_string_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_string("value", "default") == "default"

def logtable_get_boolean_array_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("flags", [True, False])
    assert table.get_boolean_array("flags", []) == [True, False]

def logtable_get_boolean_array_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_boolean_array("value", []) == []

def logtable_get_integer_array_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("counts", [1, 2, 3])
    assert table.get_integer_array("counts", []) == [1, 2, 3]

def logtable_get_integer_array_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", True)
    assert table.get_integer_array("value", []) == []

def logtable_get_float_array_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put_value("samples", LogValue.withType(LogValue.LoggableType.FloatArray, [1.5, 2.5]))
    assert table.get_float_array("samples", []) == [1.5, 2.5]

def logtable_get_float_array_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_float_array("value", []) == []

def logtable_get_double_array_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("positions", [1.0, 2.5, 3.14])
    assert table.get_double_array("positions", []) == [1.0, 2.5, 3.14]

def logtable_get_double_array_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", "string")
    assert table.get_double_array("value", []) == []

def logtable_get_string_array_returns_value_for_correct_type():
    table = LogTable(1000)
    table.put("names", ["a", "b", "c"])
    assert table.get_string_array("names", []) == ["a", "b", "c"]

def logtable_get_string_array_returns_default_for_wrong_type():
    table = LogTable(1000)
    table.put("value", 42)
    assert table.get_string_array("value", []) == []

def logtable_prefixes_keys_with_table_prefix():
    table = LogTable(1000, "/Robot/")
    table.put("speed", 5.0)
    assert "/Robot/speed" in table.data
    assert table.get("speed", 0.0) == 5.0

def logtable_subtable_shares_data_with_parent():
    root = LogTable(1000, "/")
    subtable = root.get_subtable("Drivetrain")
    subtable.put("speed", 5.0)
    assert "/Drivetrain/speed" in root.data
    assert root.get("/Drivetrain/speed", 0.0) == 5.0

def logtable_subtable_extends_prefix():
    root = LogTable(1000, "/")
    subtable = root.get_subtable("Drivetrain")
    assert subtable.prefix == "/Drivetrain/"
    assert subtable.depth == 1

def logtable_nested_subtable_composes_prefixes():
    root = LogTable(1000, "/")
    drivetrain = root.get_subtable("Drivetrain")
    motors = drivetrain.get_subtable("Motors")
    motors.put("speed", 10.0)
    assert "/Drivetrain/Motors/speed" in root.data
    assert root.get("/Drivetrain/Motors/speed", 0.0) == 10.0
    assert motors.depth == 2

def logtable_subtable_timestamp_matches_parent():
    root = LogTable(5000)
    subtable = root.get_subtable("Sub")
    assert subtable.getTimestamp() == 5000

def logtable_clone_creates_independent_data():
    original = LogTable(1000)
    original.put("value", 42)
    cloned = LogTable.clone(original)
    cloned.put("value2", 99)
    assert "//value2" not in original.data
    assert cloned.data["//value"] == original.data["/value"]

def logtable_clone_preserves_timestamp_and_prefix():
    original = LogTable(5000, "/Drivetrain/")
    cloned = LogTable.clone(original)
    assert cloned.timestamp == 5000
    assert cloned.prefix == "/Drivetrain/"

def logtable_get_all_returns_all_entries_by_default():
    table = LogTable(1000)
    table.put("a", 1)
    table.put("b", 2)
    table.put("c", 3)
    all_entries = table.get_all()
    assert len(all_entries) == 3
    assert all_entries["/a"].value == 1
    assert all_entries["/b"].value == 2
    assert all_entries["/c"].value == 3

def logtable_get_all_with_subtable_only_filters_by_prefix():
    root = LogTable(1000)
    drivetrain = root.get_subtable("Drivetrain")
    arm = root.get_subtable("Arm")
    drivetrain.put("speed", 5.0)
    arm.put("angle", 90.0)
    drivetrain_entries = drivetrain.get_all(subtable_only=True)
    assert len(drivetrain_entries) == 1
    assert "/Drivetrain/speed" in drivetrain_entries

def logtable_write_allowed_rejects_type_mismatch():
    table = LogTable(1000)
    table.put("value", 42)
    result = table.write_allowed("value", LogValue.LoggableType.Double, "")
    assert result is False

def logtable_write_allowed_accepts_new_key():
    table = LogTable(1000)
    result = table.write_allowed("new_key", LogValue.LoggableType.Double, "")
    assert result is True

def logtable_write_allowed_accepts_matching_type():
    table = LogTable(1000)
    table.put("value", 42)
    result = table.write_allowed("value", LogValue.LoggableType.Integer, "")
    assert result is True

def logtable_write_allowed_rejects_custom_type_mismatch():
    table = LogTable(1000)
    table.put("data", b"bytes", type_str="struct:Pose2d")
    result = table.write_allowed("data", LogValue.LoggableType.Raw, "struct:Other")
    assert result is False

def logtable_put_value_with_empty_array_matches_previous_type():
    table = LogTable(1000)
    table.put("items", [1, 2, 3])
    table.put_value("items", LogValue([]))
    assert table.data["/items"].log_type == LogValue.LoggableType.IntegerArray

def logtable_put_value_with_empty_array_converts_to_bytes_for_struct():
    table = LogTable(1000)
    table.put("items", b"struct_data", type_str="struct:Item[]")
    table.put_value("items", LogValue([]))
    assert table.data["/items"].value == b""

def logtable_put_value_skips_empty_array_without_previous_entry():
    table = LogTable(1000)
    table.put_value("new_items", LogValue([]))
    assert "/new_items" not in table.data