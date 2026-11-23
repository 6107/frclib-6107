"""
Bridge from the 2027 WPILib ``telemetry`` API into the pykit LogTable.

Anything logged through ``telemetry.log`` (including WPILib-native ``TelemetryLoggable``
objects) is routed here so it lands in ``RealOutputs`` and therefore in the PyKit WPILOG and
the ``/AdvantageKit`` NT4 tree.

Threading: ``telemetry.log`` may be called from any thread, but ``LogTable`` is not thread-safe.
Each call therefore only appends to a ``queue.SimpleQueue``. The main thread merges the queue
into the cycle's output table once per cycle via ``BufferedPykitBackend.drain_into``
(called from ``Logger.periodic_after_user``). Within a cycle the last value for a key wins.

See ``docs/2027-telemetry-and-tunables-tutorial.md`` sections 8.3 and 9.
"""

import json
import queue
import threading
from collections.abc import Callable
from typing import Any

from telemetry import TelemetryBackend, TelemetryEntry

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue

T = LogValue.LoggableType

# telemetry log_* method name -> (pykit type, converter applied on the calling thread)
_SCALARS: dict[str, tuple[T, Callable[[Any], Any]]] = {
    "log_boolean": (T.Boolean, bool),
    "log_int8": (T.Integer, int),
    "log_int16": (T.Integer, int),
    "log_int32": (T.Integer, int),
    "log_int64": (T.Integer, int),
    "log_float": (T.Float, float),
    "log_double": (T.Double, float),
}
_ARRAYS: dict[str, tuple[T, Callable[[Any], Any]]] = {
    "log_boolean_array": (T.BooleanArray, bool),
    "log_int8_array": (T.IntegerArray, int),
    "log_int16_array": (T.IntegerArray, int),
    "log_int32_array": (T.IntegerArray, int),
    "log_int64_array": (T.IntegerArray, int),
    "log_float_array": (T.FloatArray, float),
    "log_double_array": (T.DoubleArray, float),
    "log_string_array": (T.StringArray, str),
}


class BufferedPykitEntry(TelemetryEntry):
    """A telemetry entry that queues its values for the pykit backend."""

    def __init__(self, backend: BufferedPykitBackend, key: str) -> None:
        super().__init__()
        self._backend = backend
        self._key = key
        self._unit: str | None = None

    def set_property(self, key: str, value: str) -> None:
        """``log_unit`` arrives as a JSON-encoded ``unit`` property."""
        if key == "unit":
            try:
                self._unit = json.loads(value)
            except TypeError, ValueError:
                self._unit = str(value)

    def _put(self, kind: T, value: Any, type_str: str = "") -> None:
        self._backend.pending.put((self._key, kind, value, type_str, self._unit))

    def log_string(self, value: str, type_string: str = "string", timestamp: int = 0) -> None:
        self._put(T.String, str(value))

    def log_raw(self, value: Any, type_string: str = "raw", timestamp: int = 0) -> None:
        self._put(T.Raw, bytes(value), "" if type_string == "raw" else type_string)


def _scalar_override(kind: T, convert: Callable[[Any], Any]) -> Callable[..., None]:
    def log(self: BufferedPykitEntry, value: Any, timestamp: int = 0) -> None:
        self._put(kind, convert(value))

    return log


def _array_override(kind: T, convert: Callable[[Any], Any]) -> Callable[..., None]:
    def log(self: BufferedPykitEntry, value: Any, timestamp: int = 0) -> None:
        # Copy here so the caller can keep mutating its own buffer
        self._put(kind, [convert(v) for v in value])

    return log


for _name, (_kind, _conv) in _SCALARS.items():
    setattr(BufferedPykitEntry, _name, _scalar_override(_kind, _conv))
for _name, (_kind, _conv) in _ARRAYS.items():
    setattr(BufferedPykitEntry, _name, _array_override(_kind, _conv))


def log_table_to_telemetry(source: LogTable, table: Any) -> None:
    """
    Emit every entry of a pykit ``LogTable`` through a ``telemetry.TelemetryTable``.

    Lets objects that already know how to fill a ``LogTable`` (``log_output``) also act as
    ``TelemetryLoggable``. Keys are relative to the source table's own entries; the ``.type``
    entry is skipped because the telemetry framework writes it from ``get_telemetry_type``.

    Args:
        source: The table holding the values (typically a fresh ``LogTable(0)``).
        table: The destination ``telemetry.TelemetryTable``.
    """
    array_types = {
        T.BooleanArray: bool,
        T.IntegerArray: int,
        T.FloatArray: float,
        T.DoubleArray: float,
        T.StringArray: str,
    }
    for full_key, log_value in source.get_all().items():
        key = full_key.lstrip("/")
        if key == ".type" or key.endswith("/.type"):
            continue
        if log_value.log_type in array_types:
            table.log(key, list(log_value.value), element_type=array_types[log_value.log_type])
        elif log_value.log_type == T.Raw:
            table.log(key, bytes(log_value.value), type_string=log_value.custom_type)
        else:
            table.log(key, log_value.value)


class BufferedPykitBackend(TelemetryBackend):
    """
    Telemetry backend that buffers values and merges them into a pykit ``LogTable`` on the main thread.

    Register with ``TelemetryRegistry.register_backend("", backend)`` (REAL/SIM). Call
    ``drain_into(output_table)`` once per cycle from the main thread.
    """

    def __init__(self) -> None:
        super().__init__()
        self.pending: queue.SimpleQueue = queue.SimpleQueue()
        self._schemas: dict[str, tuple[str, bytes]] = {}
        self._lock = threading.Lock()

    def get_entry(self, path: str) -> TelemetryEntry:
        return BufferedPykitEntry(self, path.lstrip("/"))

    def remove_entry(self, path: str) -> None:
        """Nothing to release: entries hold no per-path state in the backend."""

    def add_schema(self, name: str, type: str, schema: Any) -> None:
        data = schema.encode() if isinstance(schema, str) else bytes(schema)
        with self._lock:
            if name in self._schemas:
                return
            self._schemas[name] = (type, data)
        self.pending.put((f".schema/{name}", T.Raw, data, "structschema", None))

    def has_schema(self, name: str) -> bool:
        with self._lock:
            return name in self._schemas

    def drain_into(self, outputs: LogTable, root: LogTable | None = None) -> int:
        """
        Merge all buffered values into ``outputs`` (main thread only).

        Args:
            outputs: The cycle's output table (``RealOutputs``) that receives values.
            root: The root table that receives ``.schema/*`` entries, which pykit keeps at the
                top level. If None, schemas are written into ``outputs``.

        Returns:
            int: The number of values merged.
        """
        count = 0
        while True:
            try:
                key, kind, value, type_str, unit = self.pending.get_nowait()
            except queue.Empty:
                return count
            target = root if (root is not None and key.startswith(".schema/")) else outputs
            target.put_value(key, LogValue.with_type(kind, value, type_str, unit))
            count += 1
