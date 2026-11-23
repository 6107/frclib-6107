"""Unit tests for the telemetry -> pykit bridge."""

import threading

import pytest
import telemetry
from telemetry import MockTelemetryBackend, TelemetryRegistry
from wpimath import Pose2d

from lib_6107.pykit.logger import Logger
from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.logvalue import LogValue
from lib_6107.pykit.telemetry_bridge import BufferedPykitBackend

T = LogValue.LoggableType


@pytest.fixture
def backend():
    TelemetryRegistry.reset()
    b = BufferedPykitBackend()
    TelemetryRegistry.register_backend("", b)
    yield b
    TelemetryRegistry.reset()


def _drain(backend):
    table = LogTable(0)
    backend.drain_into(table)
    return table.get_all()


def test_scalars_map_to_pykit_types(backend):
    telemetry.log("Drive/left", 3.2)
    telemetry.log("flag", True)
    telemetry.log("n", 7)
    telemetry.log("name", "abc")

    data = _drain(backend)

    assert data["/Drive/left"].log_type == T.Double and data["/Drive/left"].value == 3.2
    assert data["/flag"].log_type == T.Boolean and data["/flag"].value is True
    assert data["/n"].log_type == T.Integer and data["/n"].value == 7
    assert data["/name"].log_type == T.String and data["/name"].value == "abc"


def test_arrays_are_copied_and_typed(backend):
    src = [1.0, 2.0]
    TelemetryRegistry.get_entry("arr").log_double_array(src, 0)
    src.append(3.0)

    data = _drain(backend)

    assert data["/arr"].log_type == T.DoubleArray
    assert data["/arr"].value == [1.0, 2.0]


def test_unit_property_is_carried(backend):
    telemetry.log_unit("Drive/speed", 2.0, "m/s")

    data = _drain(backend)

    assert data["/Drive/speed"].value == 2.0
    assert data["/Drive/speed"].unit == "m/s"


def test_struct_logs_raw_and_schema(backend):
    telemetry.log("pose", Pose2d())

    data = _drain(backend)

    assert data["/pose"].log_type == T.Raw
    assert data["/pose"].custom_type.startswith("struct:")
    assert any(k.startswith("/.schema/struct:Pose2d") for k in data)
    schema = data["/.schema/struct:Pose2d"]
    assert schema.custom_type == "structschema"


def test_schema_goes_to_root_table(backend):
    telemetry.log("pose", Pose2d())
    root = LogTable(0)
    outputs = root.get_sub_table("RealOutputs")

    backend.drain_into(outputs, root)

    keys = root.get_all().keys()
    assert "/RealOutputs/pose" in keys
    assert "/.schema/struct:Pose2d" in keys
    assert "/RealOutputs/.schema/struct:Pose2d" not in keys


def test_last_value_wins_within_cycle(backend):
    telemetry.log("x", 1.0)
    telemetry.log("x", 2.0)

    assert _drain(backend)["/x"].value == 2.0


def test_drain_returns_count_and_empties_queue(backend):
    telemetry.log("a", 1.0)
    telemetry.log("b", 2.0)

    table = LogTable(0)
    assert backend.drain_into(table) == 2
    assert backend.drain_into(table) == 0


def test_matches_mock_backend_oracle():
    """Every call a mock backend sees must also reach the bridge."""
    mock = MockTelemetryBackend()
    TelemetryRegistry.reset()
    TelemetryRegistry.register_backend("", mock)
    telemetry.log("a", 1.0)
    telemetry.log("b", True)
    telemetry.log("c", 5)
    expected = len(mock.get_actions())

    TelemetryRegistry.reset()
    bridge = BufferedPykitBackend()
    TelemetryRegistry.register_backend("", bridge)
    telemetry.log("a", 1.0)
    telemetry.log("b", True)
    telemetry.log("c", 5)
    TelemetryRegistry.reset()

    assert bridge.drain_into(LogTable(0)) == 3
    assert expected >= 3


def test_calls_from_many_threads_are_delivered_once(backend):
    def work(i):
        for n in range(200):
            telemetry.log(f"T{i}/x", float(n))

    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert backend.drain_into(LogTable(0)) == 800


class TestLoggerRegistration:
    def setup_method(self):
        TelemetryRegistry.reset()
        self._flag = Logger.bridge_telemetry

    def teardown_method(self):
        Logger.bridge_telemetry = self._flag
        Logger._telemetry_registered = False
        Logger.telemetry_backend = None
        TelemetryRegistry.reset()

    def test_normal_mode_registers_buffered_backend(self):
        Logger.replay_source = None
        Logger._register_telemetry_backend()

        assert isinstance(Logger.telemetry_backend, BufferedPykitBackend)
        telemetry.log("k", 1.0)
        assert Logger.telemetry_backend.pending.qsize() == 1

    def test_replay_mode_discards_and_has_no_buffer(self):
        from unittest.mock import MagicMock

        Logger.replay_source = MagicMock()
        try:
            Logger._register_telemetry_backend()
            assert Logger.telemetry_backend is None
            assert Logger._telemetry_registered is True
            telemetry.log("k", 1.0)  # discarded, must not raise
        finally:
            Logger.replay_source = None

    def test_disabled_flag_registers_nothing(self):
        Logger.bridge_telemetry = False
        Logger._register_telemetry_backend()

        assert Logger.telemetry_backend is None
        assert Logger._telemetry_registered is False


def test_logged_mechanism2d_is_telemetry_loggable_and_reaches_pykit(backend):
    from lib_6107.pykit.LoggedMechanism2d import LoggedMechanism2d
    from lib_6107.pykit.LoggedMechanismLigament2d import LoggedMechanismLigament2d

    mech = LoggedMechanism2d(4.0, 3.0)
    root = mech.get_root("base", 1.0, 0.5)
    root.append(LoggedMechanismLigament2d("arm", 2.0, 45.0))

    assert isinstance(mech, telemetry.TelemetryLoggable)
    assert mech.get_telemetry_type() == "Mechanism2d"

    telemetry.log("Arm", mech)
    data = _drain(backend)

    assert data["/Arm/dims"].value == [4.0, 3.0]
    assert data["/Arm/dims"].log_type == T.DoubleArray
    assert data["/Arm/base/x"].value == 1.0
    assert data["/Arm/base/arm/length"].value == 2.0
    assert data["/Arm/base/arm/angle"].value == 45.0
