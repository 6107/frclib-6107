from typing import Iterator, TypeVar

from wpiutil.log import DataLogReader, DataLogRecord

from lib_6107.pykit.logreplaysource import LogReplaySource
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.wpilog import wpilogconstants

T = TypeVar("T")


def safeNext(val: Iterator[T]) -> None | T:
    """
    Safely gets the next item from an iterator, returning None if the iterator is exhausted.

    This utility function provides a Pythonic way to handle iterator exhaustion without
    raising StopIteration exceptions. Used internally by WPILOGReader to safely advance
    through DataLogRecord streams without exception-based control flow.

    Args:
        val: The iterator to advance. Can be any Iterator[T] type.

    Returns:
        The next item from the iterator if available, or None if StopIteration was raised
        (iterator is exhausted).

    Side Effects:
        None. This is a pure utility function with no side effects.

    Type Parameters:
        T: Generic type parameter allowing any iterator type to be handled uniformly.

    Examples:
        >>> records = iter([1, 2, 3])
        >>> safeNext(records)
        1
        >>> safeNext(records)
        2
        >>> safeNext(records)
        3
        >>> safeNext(records)  # Returns None instead of raising StopIteration
        None
    """
    try:
        return next(val)
    except StopIteration:
        return None


class WPILOGReader(LogReplaySource):
    """
    Reads a `.wpilog` file and provides the data as a replay source for the logger.
    """
    timestamp: int | None

    def __init__(self, filename: str) -> None:
        """
        Initializes the WPILOGReader.

        :param filename: The path to the `.wpilog` file.
        """
        self._filename = filename
        # Predeclare records to satisfy typing before start() initializes it
        self._records: Iterator[DataLogRecord] = iter(())
        self._reader = None
        self._is_valid = False
        self._entry_ids: dict[int, str] = {}
        self._entry_types: dict[int, LogValue.LoggableType] = {}
        self._entry_custom_types: dict[int, str] = {}

    def start(self) -> None:
        """
        Initializes the reader by opening the log file and preparing to read records.
        """
        self._reader = DataLogReader(self._filename)
        self._is_valid = (
                self._reader.isValid()
                and self._reader.getExtraHeader() == wpilogconstants.extraHeader
        )
        self._records = iter(())

        if self._is_valid:
            # Create a new iterator for the initial entry scan
            self._records = iter(self._reader)
            self._entry_ids: dict[int, str] = {}
            self._entry_types: dict[int, LogValue.LoggableType] = {}
            self.timestamp = None
            self._entry_custom_types: dict[int, str] = {}

        else:
            print(
                "[WPILogReader] invalid data log!\n"
                + "WPILogReader MUST use a WPILog generated with a WPILOGWriter"
            )

    def updateTable(self, table: LogTable) -> bool:
        """
        Updates a LogTable with the next record from the log file.

        This method iterates through the log records, populating the provided
        `LogTable` with data corresponding to a single timestamp.

        :param table: The `LogTable` to update.
        :return: True if the table was updated and there may be more data,
                 False if the end of the log was reached.
        """
        if not self._is_valid:
            return False

        if self.timestamp is not None:
            table.setTimestamp(self.timestamp)

        keep_logging = False
        while (record := safeNext(self._records)) is not None:
            if record.isControl():
                if record.isStart():
                    start_data = record.getStartData()
                    self._entry_ids[start_data.entry] = start_data.name
                    type_str = start_data.type
                    self._entry_types[start_data.entry] = (
                        LogValue.LoggableType.fromWPILOGType(type_str)
                    )
                    if type_str.startswith("struct:") or type_str == "structschema":
                        self._entry_custom_types[start_data.entry] = type_str
            else:
                entry = self._entry_ids.get(record.getEntry())
                if entry is not None:
                    if entry == self.timestampKey:
                        first_timestamp = self.timestamp is None
                        self.timestamp = record.getInteger()
                        if first_timestamp:
                            if self.timestamp is None:
                                raise ValueError("First timestamp is None")

                            table.setTimestamp(self.timestamp)
                        else:
                            keep_logging = True  # we still have a timestamp, just need to wait until next iter
                            break
                    elif (
                            self.timestamp is not None
                            and record.getTimestamp() == self.timestamp
                    ):
                        entry = entry[1:]
                        if entry.startswith("ReplayOutputs"):
                            continue
                        custom_type = self._entry_custom_types.get(record.getEntry())
                        entry_type = self._entry_types.get(record.getEntry())
                        if custom_type is None:
                            custom_type = ""

                        match entry_type:
                            case LogValue.LoggableType.Raw:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getRaw(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.Boolean:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getBoolean(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.Integer:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getInteger(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.Float:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getFloat(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.Double:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getDouble(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.String:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getString(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.BooleanArray:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getBooleanArray(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.IntegerArray:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getIntegerArray(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.FloatArray:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getFloatArray(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.DoubleArray:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getDoubleArray(), custom_type
                                    ),
                                )
                            case LogValue.LoggableType.StringArray:
                                table.put_value(
                                    entry,
                                    LogValue.withType(
                                        entry_type, record.getStringArray(), custom_type
                                    ),
                                )

        return keep_logging
