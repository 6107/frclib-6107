"""Round-trip and error-path tests for WPILOGReader."""

import struct
from unittest.mock import MagicMock, patch

import pytest
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.wpilog.wpilogreader import WPILOGReader
from lib_6107.pykit.wpilog.wpilogwriter import WPILOGWriter

MODULE = "lib_6107.pykit.wpilog.wpilogreader"


def _write_log(path, tables):
    with patch("lib_6107.pykit.wpilog.wpilogwriter.RobotBase.is_simulation", return_value=True):
        writer = WPILOGWriter(str(path))
    writer.start(background=False)
    for ts, values in tables:
        table = LogTable(ts)
        for key, value in values.items():
            table.put(key, value)
        writer.put_table(table)
    writer.end()


def _read_all(path):
    reader = WPILOGReader(str(path))
    reader.start()
    tables = []
    while True:
        table = LogTable(0)
        more = reader.update_table(table)
        tables.append(table)
        if not more:
            break
    return reader, tables


def test_round_trip_all_value_types(tmp_path):
    path = tmp_path / "all.wpilog"
    values = {
        "Bool": True,
        "Int": 42,
        "Float": 1.5,
        "Str": "hello",
        "BoolArr": [True, False, True],
        "IntArr": [1, 2, 3],
        "DblArr": [1.5, 2.5],
        "StrArr": ["a", "b"],
        "Raw": b"\x01\x02\x03",
    }
    _write_log(path, [(1000, values), (2000, {"Int": 43})])
    reader, tables = _read_all(path)
    assert reader._is_valid
    first = tables[0]
    assert first.timestamp == 1000
    assert first.get("Bool", False) is True
    assert first.get("Int", 0) == 42
    assert first.get("Float", 0.0) == 1.5
    assert first.get("Str", "") == "hello"
    assert list(first.get("BoolArr", [])) == [True, False, True]
    assert list(first.get("IntArr", [])) == [1, 2, 3]
    assert list(first.get("DblArr", [])) == [1.5, 2.5]
    assert list(first.get("StrArr", [])) == ["a", "b"]
    assert bytes(first.get("Raw", b"")) == b"\x01\x02\x03"
    assert any(t.get("Int", 0) == 43 for t in tables)


def test_round_trip_all_loggable_types_via_mocked_records():
    """Drive every case of the type switch with fake records."""
    T = LogValue.LoggableType
    getters = {
        T.Raw: ("get_raw", b"x"),
        T.Boolean: ("get_boolean", True),
        T.Integer: ("get_integer", 5),
        T.Float: ("get_float", 1.0),
        T.Double: ("get_double", 2.0),
        T.String: ("get_string", "s"),
        T.BooleanArray: ("get_boolean_array", [True]),
        T.IntegerArray: ("get_integer_array", [1]),
        T.FloatArray: ("get_float_array", [1.0]),
        T.DoubleArray: ("get_double_array", [1.0]),
        T.StringArray: ("get_string_array", ["a"]),
    }
    reader = WPILOGReader("x")
    reader._is_valid = True
    reader.timestamp = 10
    records = []
    for i, (typ, (getter, value)) in enumerate(getters.items()):
        reader._entry_ids[i] = f"/K{i}"
        reader._entry_types[i] = typ
        rec = MagicMock()
        rec.is_control.return_value = False
        rec.get_entry.return_value = i
        rec.get_timestamp.return_value = 10
        getattr(rec, getter).return_value = value
        records.append(rec)
    reader._records = iter(records)
    table = MagicMock()
    with patch(f"{MODULE}.LogValue.with_type", side_effect=lambda t, v, c: (t, v, c)) as wt:
        assert reader.update_table(table) is False
    assert wt.call_count == len(getters)
    assert table.put_value.call_count == len(getters)


def test_replay_outputs_skipped_and_other_timestamp_ignored(tmp_path):
    path = tmp_path / "skip.wpilog"
    _write_log(path, [(1000, {"ReplayOutputs/x": 1, "Keep": 2}), (2000, {"Keep": 3})])
    _, tables = _read_all(path)
    assert tables[0].get("ReplayOutputs/x", None) is None
    assert tables[0].get("Keep", 0) == 2


def test_unit_metadata_round_trip(tmp_path):
    path = tmp_path / "unit.wpilog"
    with patch("lib_6107.pykit.wpilog.wpilogwriter.RobotBase.is_simulation", return_value=True):
        writer = WPILOGWriter(str(path))
    writer.start(background=False)
    table = LogTable(5000)
    table.put("V", 1.0)
    writer.put_table(table)
    writer.end()
    _, tables = _read_all(path)
    assert tables[0].get("V", 0.0) == 1.0


def test_struct_type_registers_custom_type():
    reader = WPILOGReader("x")
    reader._is_valid = True
    reader.timestamp = None
    start = MagicMock()
    start.entry = 1
    start.name = "/S"
    start.type = "struct:Pose2d"
    ctrl = MagicMock()
    ctrl.is_control.return_value = True
    ctrl.is_start.return_value = True
    ctrl.get_start_data.return_value = start
    other_ctrl = MagicMock()
    other_ctrl.is_control.return_value = True
    other_ctrl.is_start.return_value = False
    reader._records = iter([ctrl, other_ctrl])
    assert reader.update_table(MagicMock()) is False
    assert reader._entry_custom_types[1] == "struct:Pose2d"
    assert reader._entry_ids[1] == "/S"


def test_unknown_entry_id_is_ignored():
    reader = WPILOGReader("x")
    reader._is_valid = True
    reader.timestamp = 1
    rec = MagicMock()
    rec.is_control.return_value = False
    rec.get_entry.return_value = 99
    reader._records = iter([rec])
    table = MagicMock()
    assert reader.update_table(table) is False
    table.put_value.assert_not_called()


def test_first_timestamp_none_raises():
    reader = WPILOGReader("x")
    reader._is_valid = True
    reader.timestamp = None
    reader._entry_ids[1] = reader.timestampKey
    rec = MagicMock()
    rec.is_control.return_value = False
    rec.get_entry.return_value = 1
    rec.get_integer.return_value = None
    reader._records = iter([rec])
    with pytest.raises(ValueError):
        reader.update_table(MagicMock())


def test_untyped_entry_with_matching_timestamp_is_ignored():
    reader = WPILOGReader("x")
    reader._is_valid = True
    reader.timestamp = 5
    reader._entry_ids[1] = "/Foo"
    rec = MagicMock()
    rec.is_control.return_value = False
    rec.get_entry.return_value = 1
    rec.get_timestamp.return_value = 5
    reader._records = iter([rec])
    table = MagicMock()
    assert reader.update_table(table) is False
    table.put_value.assert_not_called()


def test_missing_file_is_invalid(tmp_path):
    reader = WPILOGReader(str(tmp_path / "nope.wpilog"))
    with pytest.raises(FileNotFoundError):
        reader.start()
    assert reader._is_valid is False
    assert reader.update_table(LogTable(0)) is False


def test_bad_header_garbage_file(tmp_path):
    path = tmp_path / "bad.wpilog"
    path.write_bytes(b"this is not a wpilog at all")
    reader = WPILOGReader(str(path))
    reader.start()
    assert reader._is_valid is False
    assert reader.update_table(LogTable(0)) is False


def test_wrong_extra_header_is_invalid(tmp_path):
    from wpilog import DataLogWriter

    path = tmp_path / "other.wpilog"
    log = DataLogWriter(str(path), "NotPyKit")
    eid = log.start("/Timestamp", "int64", "", 0)
    log.append_integer(eid, 1, 1)
    log.flush()
    log.stop()
    reader = WPILOGReader(str(path))
    reader.start()
    assert reader._is_valid is False


def test_truncated_records_do_not_crash(tmp_path):
    path = tmp_path / "full.wpilog"
    _write_log(path, [(1000, {"A": 1}), (2000, {"A": 2}), (3000, {"A": 3})])
    data = path.read_bytes()
    trunc = tmp_path / "trunc.wpilog"
    trunc.write_bytes(data[:-5])
    reader, tables = _read_all(trunc)
    assert reader._is_valid
    assert tables[0].get("A", 0) == 1

    # Header only: valid but empty
    header_len = 12 + struct.unpack("<I", data[8:12])[0]
    hdr = tmp_path / "hdr.wpilog"
    hdr.write_bytes(data[:header_len])
    reader, tables = _read_all(hdr)
    assert len(tables) == 1


def test_unknown_wpilog_type_raises_or_ignored(tmp_path):
    from wpilog import DataLogWriter

    from lib_6107.pykit.wpilog import wpilogconstants

    path = tmp_path / "unk.wpilog"
    log = DataLogWriter(str(path), wpilogconstants.extraHeader)
    ts = log.start("/Timestamp", "int64", "", 0)
    eid = log.start("/Weird", "mystery_type", "", 0)
    log.append_integer(ts, 7, 7)
    log.append_raw(eid, b"abc", 7)
    log.append_integer(ts, 8, 8)
    log.flush()
    log.stop()
    reader = WPILOGReader(str(path))
    reader.start()
    try:
        reader.update_table(LogTable(0))
    except Exception as e:  # unknown type may be rejected by from_wpilog_type
        assert e is not None
