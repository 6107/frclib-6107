# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
"""
WPILib Log Writer Module

This module provides the WPILOGWriter class, which writes telemetry data to
WPILib-compatible .wpilog files. It handles:
- Automatic log file naming with timestamps, event names, and match information
- Data type registration and change detection
- Unit annotation for numeric values
- Simulation and real-robot specific path handling

The writer integrates with the pykit Logger system for centralized telemetry
management and supports both real robot deployment (USB drive) and simulation modes.
"""

import datetime
import logging
import os
import random
from os.path import abspath, basename, dirname, exists, join
from tempfile import gettempdir
from typing import TYPE_CHECKING

from wpilib import MatchType, RobotBase, RobotController
from wpilog import DataLogBackgroundWriter, DataLogWriter
from wpimath.units import seconds

from lib_6107.pykit.logdatareceiver import LogDataReceiver
from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.wpilog import wpilogconstants

if TYPE_CHECKING:
    from wpilog import DataLog

# Temporary file name used to pass log path to AdvantageScope in simulation
ASCOPE_FILENAME = "ascope-log-path.txt"

# Seconds between flushes to disk performed by the native DataLogBackgroundWriter thread
DEFAULT_FLUSH_PERIOD = 0.25

logger = logging.getLogger(__name__)


class WPILOGWriter(LogDataReceiver):
    """
    A data receiver that writes telemetry data to a WPILib-compatible .wpilog file.

    This class is responsible for:
    - Creating and managing .wpilog files on the robot (USB drive) or in simulation
    - Automatically naming log files with timestamps, event names, and match information
    - Registering data fields dynamically as new telemetry is logged
    - Detecting data changes to avoid redundant log entries
    - Handling type conversions and unit metadata for all supported data types

    Attributes:
        log: The underlying DataLogWriter instance that writes to the .wpilog file
        default_path_rio: Default path on roboRIO for log files (/U/logs)
        default_path_sim: Default path in simulation for log files (pyLogs)
        folder: The directory where the log file will be created
        filename: The name of the log file (auto-generated or specified)
        randomIdentifier: A random 4-hex-digit identifier for fallback naming
        dsAttachedTime: Timestamp when Driver Station was first detected (seconds, from RobotController.get_monotonic_time())
        autoRename: Whether to automatically rename logs based on match info
        logDate: The date/time when logging started (used in filename generation)
        logMatchText: Match type and number string (e.g., "q42" for qualification match 42)
        isOpen: Whether the log file is currently open and writable
        last_table: The previous LogTable state (used for change detection)
        timestampId: The entry ID for the timestamp field in the log
        entryIds: Map of field names to their assigned entry IDs in the log
        entryTypes: Map of field names to their LoggableType values
        entryUnits: Map of field names to their unit strings (e.g., "m/s", "rad")
    """

    # ...existing code...

    log: DataLog
    default_path_rio: str = "/U/logs"
    default_path_sim: str = "pyLogs"

    folder: str
    filename: str
    random_identifier: str
    ds_attached_time: seconds = 0
    auto_rename: bool
    log_date: datetime.datetime | None
    log_match_text: str

    is_open: bool = False
    last_table: LogTable
    timestamp_id: int
    entry_ids: dict[str, int]
    entry_types: dict[str, LogValue.LoggableType]
    entry_units: dict[str, str]

    def __init__(self, filename: str | None = None, path: str | None = None) -> None:
        """
        Initializes the WPILOGWriter.

        :param filename: The path to the `.wpilog` file. If None, a default path is used,
                         and the file is named with a random identifier.
        :param path: The directory to save the log file. If None, a default path is used based
                         on whether it's running in simulation or on the robot.

        In the event that both a filename and a path are provided, the combination of the path and
        the filename will be used in determining the location of where to put the log file
        """
        self._is_simulation = RobotBase.is_simulation()

        actual_path = (
            path if path is not None else (self.default_path_sim if self._is_simulation else self.default_path_rio)
        )

        self.random_identifier = f"{random.randint(0, 0xFFFF):04X}"  # nosec: B311

        if path is None:
            self.folder = abspath(dirname(filename) if filename is not None else actual_path)
        else:
            # need to combine if both are specified
            self.folder = abspath(join(actual_path, dirname(filename)) if filename is not None else actual_path)

        self.filename = basename(filename) if filename is not None else f"pykit_{self.random_identifier}.wpilog"
        self.auto_rename = filename is None
        self._background = None

    def start(self, background: bool = True, flush_period: float = DEFAULT_FLUSH_PERIOD) -> None:
        """
        Initializes the writer by creating the log file and preparing to write data.

        :param background: Whether to write data in the background on a separate thread.
        :param flush_period: The period (in seconds) to flush data to disk when writing in the background.
        """
        # Create folder if necessary
        if not exists(self.folder):
            try:
                os.makedirs(self.folder)

            except PermissionError as e:
                logger.exception("[WPILogWriter] Failed to create log folder! (%s)", e)
                return

        # Initialize the WPILOG file
        full_path = join(self.folder, self.filename)
        logger.info("[WPILogWriter] Creating WPILOG file at %s", full_path)

        if exists(full_path):
            logger.warning("[WPILogWriter] File exists, overwriting: %s", full_path)
            os.remove(full_path)

        self._background = background
        try:
            if background:
                # Disk writes happen on the writer's own native thread, outside the robot loop and the GIL
                self.log = DataLogBackgroundWriter(
                    self.folder, self.filename, flush_period, wpilogconstants.extraHeader
                )
            else:
                self.log = DataLogWriter(full_path, wpilogconstants.extraHeader)

        except PermissionError as e:
            logger.exception("[WPILogWriter] Failed to open WPILOG file! (%s)", e)
            return

        self.is_open = True
        self.timestamp_id = self.log.start(
            self.timestamp_key, LogValue.LoggableType.Integer.get_wpilog_type(), wpilogconstants.entryMetadata, 0
        )
        self.last_table = LogTable(0)

        self.entry_ids: dict[str, int] = {}
        self.entry_types: dict[str, LogValue.LoggableType] = {}
        self.entry_units: dict[str, str] = {}
        self.log_date = None
        self.log_match_text = ""

    def end(self) -> None:
        """
        Closes the log file and performs cleanup.
        In simulation, it can also trigger AdvantageScope to open the log.
        """
        is_open, self.is_open = self.is_open, False

        if not is_open:
            return

        logger.info("[WPILogWriter] Shutting down")

        self.log.flush()
        if self._background:
            # DataLogBackgroundWriter.stop() would discard buffered records. Releasing the object runs its destructor,
            # which joins the writer thread after it has drained every pending record to disk.
            del self.log
        else:
            self.log.stop()

        if self._is_simulation and Logger.is_replay():
            # open ascope
            fullpath = join(gettempdir(), ASCOPE_FILENAME)
            if not exists(gettempdir()):
                return

            full_log_path = abspath(join(self.folder, self.filename))

            logger.info("Sending %s to AScope", full_log_path)

            with open(fullpath, "w", encoding="utf-8") as f:
                f.write(full_log_path)

        # DataLogManager.stop()

    def put_table(self, table: LogTable) -> None:
        """
        Writes a `LogTable` to the `.wpilog` file.

        This method handles automatic file renaming, writing timestamp and data entries,
        and ensures that data is only written when it changes.

        :param table: The `LogTable` to write.
        """
        if not self.is_open:
            return

        # Auto-rename log file based on timestamp and match info
        if self.auto_rename and self.log_date is None:
            if (
                table.get("DriverStation/DSAttached", False) and table.get("SystemStats/SystemTimeValid", False)
            ) or self._is_simulation:
                now_seconds: seconds = RobotController.get_monotonic_time() / 1e9

                if self.ds_attached_time == 0:
                    self.ds_attached_time = now_seconds

                elif (now_seconds - self.ds_attached_time) > 5 or self._is_simulation:
                    self.log_date = datetime.datetime.now()
            else:
                self.ds_attached_time = 0

            match_type: MatchType
            match table.get("DriverStation/MatchType", 0):
                case 1:
                    match_type = MatchType.PRACTICE
                case 2:
                    match_type = MatchType.QUALIFICATION
                case 3:
                    match_type = MatchType.ELIMINATION
                case _:
                    match_type = MatchType.NONE

            # Build match text prefix (p/q/e + match number)
            if self.log_match_text == "" and match_type != MatchType.NONE:
                match match_type:
                    case MatchType.PRACTICE:
                        self.log_match_text = "p"
                    case MatchType.QUALIFICATION:
                        self.log_match_text = "q"
                    case MatchType.ELIMINATION:
                        self.log_match_text = "e"
                    case _:
                        self.log_match_text = "u"
                self.log_match_text += str(table.get("DriverStation/MatchNumber", 0))

            # Generate new filename with timestamp, event, and match info
            filename = "pykit_"
            if self.log_date is not None:
                filename += self.log_date.strftime("%Y%m%d_%H%M%S")
            else:
                filename += self.random_identifier

            event_name = table.get("DriverStation/EventName", "").lower().replace(" ", "_")
            if event_name != "":
                filename += f"_{event_name}"

            if self.log_match_text != "":
                filename += f"_{self.log_match_text}"

            filename += ".wpilog"

            if self.filename != filename:
                # Rename log file by closing current and opening new
                logger.info(f"[WPILogWriter] Renaming log to {filename}")

                if self._background:
                    self.log.set_filename(filename)
                else:
                    full_path = join(self.folder, self.filename)
                    os.rename(full_path, join(self.folder, filename))
                self.filename = filename

        # Write timestamp entry
        self.log.append_integer(self.timestamp_id, table.get_timestamp(), table.get_timestamp())

        # Get current and previous data for change detection
        new_map = table.get_all()
        old_map = self.last_table.get_all()

        # Write changed entries to log
        for key, newValue in new_map.items():
            field_type = newValue.log_type
            field_unit = newValue.unit
            append_data = False

            # Register new field or detect changes
            if key not in self.entry_ids:
                # New field - create entry in log
                entry_id = self.log.start(
                    key,
                    newValue.get_wpilog_type(),
                    (
                        wpilogconstants.entryMetadata
                        if field_unit is None
                        else wpilogconstants.entryMetadataUnits.replace("$UNITSTR", field_unit)
                    ),
                    table.timestamp,
                )
                self.entry_ids[key] = entry_id
                self.entry_types[key] = newValue.log_type
                if field_unit is not None:
                    self.entry_units[key] = field_unit

                append_data = True
            elif newValue != old_map.get(key):
                # Existing field changed - log new value
                append_data = True

            # Detect and warn about type changes
            elif newValue.log_type != self.entry_types[key]:
                logger.warning(
                    f"[WPILOGWriter] Type of {key} changed from "
                    f"{self.entry_types[key]} to {newValue.log_type}, skipping log"
                )
                continue

            if append_data:
                entry_id = self.entry_ids[key]
                # check if unit changed
                if field_unit is not None and self.entry_units.get(key) != field_unit:
                    self.log.set_metadata(
                        entry_id, wpilogconstants.entryMetadataUnits.replace("$UNITSTR", field_unit), table.timestamp
                    )
                    self.entry_units[key] = field_unit

                match field_type:
                    case LogValue.LoggableType.Raw:
                        self.log.append_raw(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.Boolean:
                        self.log.append_boolean(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.Integer:
                        self.log.append_integer(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.Float:
                        self.log.append_float(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.Double:
                        self.log.append_double(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.String:
                        self.log.append_string(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.BooleanArray:
                        self.log.append_boolean_array(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.IntegerArray:
                        self.log.append_integer_array(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.FloatArray:
                        self.log.append_float_array(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.DoubleArray:
                        self.log.append_double_array(entry_id, newValue.value, table.get_timestamp())

                    case LogValue.LoggableType.StringArray:
                        self.log.append_string_array(entry_id, newValue.value, table.get_timestamp())

        if not self._background:
            self.log.flush()

        self.last_table = table
