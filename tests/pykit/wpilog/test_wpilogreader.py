"""Unit tests for wpilogreader module."""

from unittest.mock import MagicMock, patch
from lib_6107.pykit.wpilog.wpilogreader import WPILOGReader, safeNext
from lib_6107.pykit.logtable import LogTable


# ============================================================================
# Tests for safeNext utility function
# ============================================================================

def test_safenext_returns_value_from_iterator():
    """Verify safeNext returns value from iterator."""
    values = iter([1, 2, 3])
    assert safeNext(values) == 1
    assert safeNext(values) == 2


def test_safenext_returns_none_when_exhausted():
    """Verify safeNext returns None when iterator exhausted."""
    values = iter([])
    assert safeNext(values) is None


def test_safenext_handles_none_values():
    """Verify safeNext distinguishes None from StopIteration."""
    values = iter([1, None, 3])
    assert safeNext(values) == 1
    assert safeNext(values) is None  # Actual None
    assert safeNext(values) == 3


# ============================================================================
# Tests for WPILOGReader initialization
# ============================================================================

def test_wpilogreader_init_stores_filename():
    """Verify WPILOGReader stores filename."""
    reader = WPILOGReader("test.wpilog")
    assert reader._filename == "test.wpilog"


def test_wpilogreader_init_initializes_is_valid_false():
    """Verify WPILOGReader initializes is_valid as False."""
    reader = WPILOGReader("test.wpilog")
    assert reader._is_valid is False


def test_wpilogreader_init_creates_empty_dicts():
    """Verify WPILOGReader initializes empty entry dictionaries."""
    reader = WPILOGReader("test.wpilog")
    assert isinstance(reader._entry_ids, dict)
    assert isinstance(reader._entry_types, dict)
    assert isinstance(reader._entry_custom_types, dict)
    assert len(reader._entry_ids) == 0
    assert len(reader._entry_types) == 0
    assert len(reader._entry_custom_types) == 0


def test_wpilogreader_init_reader_none():
    """Verify WPILOGReader initializes reader as None."""
    reader = WPILOGReader("test.wpilog")
    assert reader._reader is None


# ============================================================================
# Tests for WPILOGReader start method
# ============================================================================

@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_start_valid_file(mock_reader_class):
    """Verify start() with valid file sets is_valid to True."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "PyKit"
    mock_reader.__iter__.return_value = iter([])
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()

    assert reader._is_valid is True


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_start_invalid_reader(mock_reader_class):
    """Verify start() with invalid reader sets is_valid to False."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = False
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()

    assert reader._is_valid is False


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_start_header_mismatch(mock_reader_class):
    """Verify start() with header mismatch sets is_valid to False."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "WrongHeader"
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()

    assert reader._is_valid is False


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_start_sets_timestamp_none(mock_reader_class):
    """Verify start() sets timestamp to None."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "PyKit"
    mock_reader.__iter__.return_value = iter([])
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.timestamp = 12345
    reader.start()

    assert reader.timestamp is None


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_start_resets_entry_dicts(mock_reader_class):
    """Verify start() resets entry tracking dictionaries."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "PyKit"
    mock_reader.__iter__.return_value = iter([])
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader._entry_ids = {"old": 1}
    reader._entry_types = {"old": "int"}
    reader.start()

    assert reader._entry_ids == {}
    assert reader._entry_types == {}
    assert reader._entry_custom_types == {}


# ============================================================================
# Tests for WPILOGReader updateTable method
# ============================================================================

@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_updatetable_returns_false_invalid(mock_reader_class):
    """Verify updateTable returns False when reader invalid."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = False
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()
    table = LogTable(0)

    result = reader.updateTable(table)
    assert result is False


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_updatetable_no_records(mock_reader_class):
    """Verify updateTable returns False with no more records."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "PyKit"
    mock_reader.__iter__.return_value = iter([])
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()
    table = LogTable(0)

    result = reader.updateTable(table)
    assert result is False


@patch('lib_6107.pykit.wpilog.wpilogreader.DataLogReader')
def test_wpilogreader_updatetable_sets_timestamp(mock_reader_class):
    """Verify updateTable sets table timestamp."""
    mock_reader = MagicMock()
    mock_reader.isValid.return_value = True
    mock_reader.getExtraHeader.return_value = "PyKit"
    mock_reader.__iter__.return_value = iter([])
    mock_reader_class.return_value = mock_reader

    reader = WPILOGReader("test.wpilog")
    reader.start()
    reader.timestamp = 999999

    table = LogTable(0)
    with patch.object(table, 'setTimestamp') as mock_set:
        reader.updateTable(table)
        mock_set.assert_called_with(999999)

