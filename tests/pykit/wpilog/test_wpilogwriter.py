"""Unit tests for wpilogwriter module."""

from unittest.mock import MagicMock, patch

import pytest

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.wpilog import wpilogconstants
from lib_6107.pykit.wpilog.wpilogwriter import DEFAULT_FLUSH_PERIOD, WPILOGWriter

MODULE = "lib_6107.pykit.wpilog.wpilogwriter"


def _started_writer(tmp_path, background, rename = False):
    """Create a writer whose DataLog backends are mocked, and start it."""
    with (
        patch(f"{MODULE}.DataLogBackgroundWriter") as bg_cls,
        patch(f"{MODULE}.DataLogWriter") as fg_cls,
        patch(f"{MODULE}.RobotBase.isSimulation", return_value=rename),
    ):
        writer = WPILOGWriter(None, str(tmp_path)) if rename else WPILOGWriter(str(tmp_path / "unit.wpilog"))
        writer.start(background=background)
    return writer, bg_cls, fg_cls


@patch("lib_6107.pykit.wpilog.wpilogwriter.RobotBase")
@patch("lib_6107.pykit.wpilog.wpilogwriter.DataLogBackgroundWriter")
def test_wpilogwriter_init_simulation_mode(mock_writer_class, mock_robot_base):
    """Verify WPILOGWriter accepts filename and path parameters."""
    mock_robot_base.isSimulation.return_value = True

    writer = WPILOGWriter("test.wpilog", None)
    assert writer._is_simulation is True


@patch("lib_6107.pykit.wpilog.wpilogwriter.RobotBase")
@patch("lib_6107.pykit.wpilog.wpilogwriter.DataLogBackgroundWriter")
def test_wpilogwriter_init_real_mode(mock_writer_class, mock_robot_base):
    """Verify WPILOGWriter initializes in real mode."""
    mock_robot_base.isSimulation.return_value = False

    writer = WPILOGWriter("test.wpilog", None)
    assert writer._is_simulation is False


@pytest.mark.parametrize("background", [True, False])
def test_wpilogwriter_end_drains_all_records_to_disk(tmp_path, background):
    """Verify end() writes every record in both background and foreground modes."""
    from wpiutil.log import DataLogReader

    from lib_6107.pykit.logtable import LogTable

    writer = WPILOGWriter(str(tmp_path / "drain.wpilog"))
    writer.start(background=background)

    cycles = 500
    for cycle in range(cycles):
        table = LogTable(cycle * 20_000)
        table.put("Test/Counter", cycle)
        writer.put_table(table)
    writer.end()

    reader = DataLogReader(str(tmp_path / "drain.wpilog"))
    assert reader.isValid()
    counters = sum(1 for record in reader if record.isStart() is False and not record.isControl())
    # One timestamp record plus one counter record per cycle
    assert counters == 2 * cycles


def test_wpilogwriter_start_defaults_to_background_writer(tmp_path):
    """Verify start() uses DataLogBackgroundWriter with the default flush period."""
    writer, bg_cls, fg_cls = _started_writer(tmp_path, background=True)

    bg_cls.assert_called_once_with(writer.folder, "unit.wpilog", DEFAULT_FLUSH_PERIOD, wpilogconstants.extraHeader)
    fg_cls.assert_not_called()
    assert writer._background is True
    assert writer.isOpen is True


def test_wpilogwriter_start_default_argument_is_background(tmp_path):
    """Verify calling start() with no arguments selects background mode."""
    with patch(f"{MODULE}.DataLogBackgroundWriter") as bg_cls, patch(f"{MODULE}.DataLogWriter") as fg_cls:
        writer = WPILOGWriter(str(tmp_path / "default.wpilog"))
        writer.start()

    bg_cls.assert_called_once()
    fg_cls.assert_not_called()
    assert writer._background is True


def test_wpilogwriter_start_background_honors_custom_flush_period(tmp_path):
    """Verify a custom flush_period is forwarded to the background writer."""
    with patch(f"{MODULE}.DataLogBackgroundWriter") as bg_cls, patch(f"{MODULE}.DataLogWriter"):
        writer = WPILOGWriter(str(tmp_path / "flush.wpilog"))
        writer.start(background=True, flush_period=1.5)

    assert bg_cls.call_args.args[2] == 1.5


def test_wpilogwriter_start_foreground_uses_blocking_writer(tmp_path):
    """Verify start(background=False) uses DataLogWriter with the full file path."""
    writer, bg_cls, fg_cls = _started_writer(tmp_path, background=False)

    fg_cls.assert_called_once_with(str(tmp_path / "unit.wpilog"), wpilogconstants.extraHeader)
    bg_cls.assert_not_called()
    assert writer._background is False
    assert writer.isOpen is True


def test_wpilogwriter_start_removes_existing_file_before_creating_log(tmp_path):
    """Verify an existing log file is deleted before starting a new one."""
    existing = tmp_path / "unit.wpilog"
    existing.write_text("old")

    _started_writer(tmp_path, background=True)

    assert not existing.exists()


def test_wpilogwriter_start_permission_error_leaves_writer_closed(tmp_path):
    """Verify a PermissionError while opening the log leaves the writer closed."""
    with patch(f"{MODULE}.DataLogBackgroundWriter", side_effect=PermissionError("denied")):
        writer = WPILOGWriter(str(tmp_path / "denied.wpilog"))
        writer.start(background=True)

    assert writer.isOpen is False


def test_wpilogwriter_put_table_does_not_flush_in_background_mode(tmp_path):
    """Verify the background thread owns flushing, so put_table never calls flush()."""
    writer, _, _ = _started_writer(tmp_path, background=True)
    writer.log = MagicMock()
    writer.log.start.return_value = 1

    table = LogTable(1000)
    table.put("A/Value", 1)
    writer.put_table(table)

    writer.log.flush.assert_not_called()
    writer.log.appendInteger.assert_called()
    assert writer.last_table is table


def test_wpilogwriter_put_table_flushes_in_foreground_mode(tmp_path):
    """Verify foreground mode flushes after every table."""
    writer, _, _ = _started_writer(tmp_path, background=False)
    writer.log = MagicMock()
    writer.log.start.return_value = 1

    table = LogTable(1000)
    table.put("A/Value", 1)
    writer.put_table(table)

    writer.log.flush.assert_called_once()


def test_wpilogwriter_put_table_is_ignored_when_not_open(tmp_path):
    """Verify put_table is a no-op after end() / before start()."""
    writer = WPILOGWriter(str(tmp_path / "closed.wpilog"))
    writer.log = MagicMock()

    writer.put_table(LogTable(0))

    writer.log.appendInteger.assert_not_called()


def test_wpilogwriter_end_background_releases_log_instead_of_stopping(tmp_path):
    """Verify background end() flushes and releases the log; stop() would discard buffered records."""
    writer, _, _ = _started_writer(tmp_path, background=True)
    mock_log = MagicMock()
    writer.log = mock_log

    writer.end()

    mock_log.flush.assert_called_once()
    mock_log.stop.assert_not_called()
    assert writer.isOpen is False
    assert not hasattr(writer, "log")


def test_wpilogwriter_end_foreground_stops_the_log(tmp_path):
    """Verify foreground end() flushes then stops the log."""
    writer, _, _ = _started_writer(tmp_path, background=False)
    mock_log = MagicMock()
    writer.log = mock_log

    writer.end()

    mock_log.flush.assert_called_once()
    mock_log.stop.assert_called_once()
    assert writer.isOpen is False


def test_wpilogwriter_put_table_after_end_is_ignored(tmp_path):
    """Verify tables arriving after end() are dropped instead of touching a released log."""
    writer, _, _ = _started_writer(tmp_path, background=True)
    writer.log = MagicMock()
    writer.end()

    writer.put_table(LogTable(5))


def _rename_on_second_table(writer):
    """Drive put_table twice so the simulation auto-rename logic assigns a log date."""
    writer.log = MagicMock()
    writer.log.start.return_value = 1
    with (
        patch(f"{MODULE}.RobotController.getFPGATime", return_value=1_000_000),
        patch(f"{MODULE}.RobotBase.isSimulation", return_value=True),
    ):
        writer._is_simulation = True
        writer.put_table(LogTable(1000))
        writer.put_table(LogTable(2000))


def test_wpilogwriter_auto_rename_background_uses_set_filename(tmp_path):
    """Verify background mode renames through the native writer rather than the filesystem."""
    writer, _, _ = _started_writer(tmp_path, background=True, rename=True)
    original = writer.filename

    with patch(f"{MODULE}.os.rename") as mock_rename:
        _rename_on_second_table(writer)

    assert writer.filename != original
    writer.log.setFilename.assert_called_once_with(writer.filename)
    mock_rename.assert_not_called()


def test_wpilogwriter_auto_rename_foreground_renames_file_on_disk(tmp_path):
    """Verify foreground mode renames the file with os.rename."""
    writer, _, _ = _started_writer(tmp_path, background=False, rename=True)
    original = writer.filename

    with patch(f"{MODULE}.os.rename") as mock_rename:
        _rename_on_second_table(writer)

    assert writer.filename != original
    mock_rename.assert_called_once()
    assert mock_rename.call_args.args[0].endswith(original)
    assert mock_rename.call_args.args[1].endswith(writer.filename)
    writer.log.setFilename.assert_not_called()


def test_wpilogwriter_no_rename_when_filename_was_explicit(tmp_path):
    """Verify an explicitly named log is never auto-renamed."""
    writer, _, _ = _started_writer(tmp_path, background=True)
    writer.log = MagicMock()
    writer.log.start.return_value = 1

    writer.put_table(LogTable(1000))
    writer.put_table(LogTable(2000))

    writer.log.setFilename.assert_not_called()
    assert writer.filename == "unit.wpilog"


@pytest.mark.parametrize("background", [True, False])
def test_wpilogwriter_auto_rename_real_file_ends_up_with_new_name(tmp_path, monkeypatch, background):
    """Verify the renamed log file exists on disk (and the old name is gone) for both modes."""
    monkeypatch.chdir(tmp_path)

    with patch(f"{MODULE}.RobotBase.isSimulation", return_value=True):
        writer = WPILOGWriter()
        writer.start(background=background)
        original = writer.filename

        with patch(f"{MODULE}.RobotController.getFPGATime", return_value=1_000_000):
            for cycle in range(3):
                table = LogTable(cycle * 20_000)
                table.put("Test/Counter", cycle)
                writer.put_table(table)
        writer.end()

    files = sorted(p.name for p in (tmp_path / "pyLogs").glob("*.wpilog"))
    assert files == [writer.filename]
    assert writer.filename != original


@pytest.mark.parametrize("background", [True, False])
def test_wpilogwriter_only_logs_changed_values(tmp_path, background):
    """Verify unchanged values are not re-appended, in either write mode."""
    from wpiutil.log import DataLogReader

    path = tmp_path / "changes.wpilog"
    writer = WPILOGWriter(str(path))
    writer.start(background=background)
    for cycle, value in enumerate([1, 1, 1, 2]):
        table = LogTable(cycle * 20_000)
        table.put("Test/Value", value)
        writer.put_table(table)
    writer.end()

    reader = DataLogReader(str(path))
    data_records = [r for r in reader if not r.isControl()]
    # Four timestamp records, plus the value written once and once more when it changed
    assert len(data_records) == 4 + 2
