import datetime
import logging
import os
import random
from os.path import abspath, basename, dirname, exists, join
from tempfile import gettempdir
from typing import TYPE_CHECKING

from hal import MatchType
from lib_6107.pykit.logdatareceiver import LogDataReceiver
from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.wpilog import wpilogconstants
from wpilib import RobotBase, RobotController
from wpiutil import DataLogWriter

if TYPE_CHECKING:
    from wpiutil.log import DataLog

ASCOPE_FILENAME = "ascope-log-path.txt"

logger = logging.getLogger(__name__)


class WPILOGWriter(LogDataReceiver):
    """
    A data receiver that writes log data to a `.wpilog` file.

    This class handles the creation and writing of log files in the standard
    WPILib format, including automatic file naming and handling of data types.
    """

    log: "DataLog"
    defaultPathRio: str = "/U/logs"
    defaultPathSim: str = "pyLogs"

    folder: str
    filename: str
    randomIdentifier: str
    dsAttachedTime: int = 0
    autoRename: bool
    logDate: datetime.datetime | None
    logMatchText: str

    isOpen: bool = False
    lastTable: LogTable
    timestampId: int
    entryIds: dict[str, int]
    entryTypes: dict[str, LogValue.LoggableType]
    entryUnits: dict[str, str]

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
        if RobotBase.isSimulation():
            actual_path = self.defaultPathSim
        else:
            actual_path = self.defaultPathRio if path is None else path

        self.randomIdentifier = f"{random.randint(0, 0xFFFF):04X}"

        if path is None:
            self.folder = abspath(dirname(filename) if filename is not None else actual_path)
        else:
            # need to combine if both are specified
            self.folder = abspath(join(actual_path, dirname(filename))
                                  if filename is not None else actual_path)

        self.filename = basename(filename) if filename is not None else f"pykit_{self.randomIdentifier}.wpilog"
        self.autoRename = filename is None

    def start(self) -> None:
        """
        Initializes the writer by creating the log file and preparing to write data.
        """
        # Create folder if necessary
        if not exists(self.folder):
            try:
                os.makedirs(self.folder)

            except PermissionError as e:
                logger.exception(f"[WPILogWriter] Failed to create log folder! ({e})")
                return

        # Initialize the WPILOG file
        full_path = join(self.folder, self.filename)
        logger.info("[WPILogWriter] Creating WPILOG file at %s", full_path)

        if exists(full_path):
            logger.warning("[WPILogWriter] File exists, overwriting: %s", full_path)
            os.remove(full_path)
        try:
            self.log = DataLogWriter(full_path, wpilogconstants.extraHeader)

        except PermissionError as e:
            logger.exception(f"[WPILogWriter] Failed to open WPILOG file! ({e})")
            return

        self.isOpen = True
        self.timestampId = self.log.start(self.timestampKey,
                                          LogValue.LoggableType.Integer.getWPILOGType(),
                                          wpilogconstants.entryMetadata,
                                          0)
        self.lastTable = LogTable(0)

        self.entryIds: dict[str, int] = {}
        self.entryTypes: dict[str, LogValue.LoggableType] = {}
        self.entryUnits: dict[str, str] = {}
        self.logDate = None
        self.logMatchText = ""

    def end(self) -> None:
        """
        Closes the log file and performs cleanup.
        In simulation, it can also trigger AdvantageScope to open the log.
        """
        print("[WPILogWriter] Shutting down")
        self.log.flush()
        self.log.stop()

        if RobotBase.isSimulation() and Logger.isReplay():
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
        if not self.isOpen:
            return

        if self.autoRename:
            # Auto-rename log file based on timestamp and match info
            if self.logDate is None:
                if (table.get("DriverStation/DSAttached", False) and
                    table.get("SystemStats/SystemTimeValid", False)) or RobotBase.isSimulation():
                    if self.dsAttachedTime == 0:
                        self.dsAttachedTime = RobotController.getFPGATime() / 1e6

                    elif (RobotController.getFPGATime() / 1e6 - self.dsAttachedTime) > 5 or RobotBase.isSimulation():
                        self.logDate = datetime.datetime.now()
                else:
                    self.dsAttachedTime = 0

                match_type: MatchType
                match table.get("DriverStation/MatchType", 0):
                    case 1:
                        match_type = MatchType.practice
                    case 2:
                        match_type = MatchType.qualification
                    case 3:
                        match_type = MatchType.elimination
                    case _:
                        match_type = MatchType.none

                # Build match text prefix (p/q/e + match number)
                if self.logMatchText == "" and match_type != MatchType.none:
                    match match_type:
                        case MatchType.practice:
                            self.logMatchText = "p"
                        case MatchType.qualification:
                            self.logMatchText = "q"
                        case MatchType.elimination:
                            self.logMatchText = "e"
                        case _:
                            self.logMatchText = "u"
                    self.logMatchText += str(table.get("DriverStation/MatchNumber", 0))

                # Generate new filename with timestamp, event, and match info
                filename = "pykit_"
                if self.logDate is not None:
                    filename += self.logDate.strftime("%Y%m%d_%H%M%S")
                else:
                    filename += self.randomIdentifier

                event_name = table.get("DriverStation/EventName", "").lower().replace(" ", "_")
                if event_name != "":
                    filename += f"_{event_name}"

                if self.logMatchText != "":
                    filename += f"_{self.logMatchText}"

                filename += ".wpilog"

                if self.filename != filename:
                    # Rename log file by closing current and opening new
                    print(f"[WPILogWriter] Renaming log to {filename}")
                    full_path = join(self.folder, self.filename)
                    os.rename(full_path, join(self.folder, filename))

                    self.filename = filename

        # Write timestamp entry
        self.log.appendInteger(self.timestampId, table.getTimestamp(), table.getTimestamp())

        # Get current and previous data for change detection
        new_map = table.getAll()
        old_map = self.lastTable.getAll()

        # Write changed entries to log
        for key, newValue in new_map.items():
            field_type = newValue.log_type
            field_unit = newValue.unit
            append_data = False

            # Register new field or detect changes
            if key not in self.entryIds:
                # New field - create entry in log
                entry_id = self.log.start(
                    key,
                    newValue.getWPILOGType(),
                    (
                        wpilogconstants.entryMetadata
                        if field_unit is None
                        else wpilogconstants.entryMetadataUnits.replace(
                            "$UNITSTR", field_unit
                        )
                    ),
                    table.getTimestamp(),
                )
                self.entryIds[key] = entry_id
                self.entryTypes[key] = newValue.log_type
                if field_unit is not None:
                    self.entryUnits[key] = field_unit

                append_data = True
            elif newValue != old_map.get(key):
                # Existing field changed - log new value
                append_data = True

            # Detect and warn about type changes
            elif newValue.log_type != self.entryTypes[key]:
                print(
                    f"[WPILOGWriter] Type of {key} changed from "
                    f"{self.entryTypes[key]} to {newValue.log_type}, skipping log"
                )
                continue

            if append_data:
                entry_id = self.entryIds[key]
                # check if unit changed
                if field_unit is not None and self.entryUnits.get(key) != field_unit:
                    self.log.setMetadata(
                        entry_id,
                        wpilogconstants.entryMetadataUnits.replace(
                            "$UNITSTR", field_unit
                        ),
                        table.getTimestamp(),
                    )
                    self.entryUnits[key] = field_unit

                match field_type:
                    case LogValue.LoggableType.Raw:
                        self.log.appendRaw(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.Boolean:
                        self.log.appendBoolean(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.Integer:
                        self.log.appendInteger(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.Float:
                        self.log.appendFloat(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.Double:
                        self.log.appendDouble(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.String:
                        self.log.appendString(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.BooleanArray:
                        self.log.appendBooleanArray(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.IntegerArray:
                        self.log.appendIntegerArray(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.FloatArray:
                        self.log.appendFloatArray(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.DoubleArray:
                        self.log.appendDoubleArray(entry_id, newValue.value, table.getTimestamp())

                    case LogValue.LoggableType.StringArray:
                        self.log.appendStringArray(entry_id, newValue.value, table.getTimestamp())

        self.log.flush()
        self.lastTable = table
