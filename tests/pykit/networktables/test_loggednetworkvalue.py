"""Unit tests for LoggedNetworkValue (tunables-backed base class)."""

from unittest.mock import MagicMock, patch

import pytest
import tunables
from tunables import TunableRegistry

from lib_6107.pykit.logtable import LogTable
from lib_6107.pykit.networktables.loggednetworkvalue import LoggedNetworkValue

MODULE = "lib_6107.pykit.networktables.loggednetworkvalue"


class DoubleValue(LoggedNetworkValue[float]):
    """Minimal concrete subclass used to exercise the base class."""

    def _publish(self, name, default):
        return tunables.add_double(name, default)


@pytest.fixture
def logger():
    with patch(f"{MODULE}.Logger") as mock_logger:
        mock_logger.is_replay.return_value = False
        yield mock_logger


@pytest.fixture
def table():
    return MagicMock(spec=LogTable)


def test_base_class_requires_publish(logger, tunables_backend):
    with pytest.raises(NotImplementedError):
        LoggedNetworkValue("Key", 1)


def test_init_publishes_default_and_registers_with_logger(logger, tunables_backend):
    value = DoubleValue("Speed", 5.0)
    assert value.value == 5.0
    assert value() == 5.0
    assert tunables_backend.get_value("/Speed") == 5.0
    logger.register_tunable_input.assert_called_once_with(value)


def test_leading_slash_is_removed_from_tunable_name(logger, tunables_backend):
    value = DoubleValue("/Drive/Speed", 1.0)
    assert tunables_backend.get_value("/Drive/Speed") == 1.0
    assert value._key == "/Drive/Speed"


def test_periodic_reads_remote_write(logger, tunables_backend):
    value = DoubleValue("Speed", 5.0)
    tunables_backend.set_double("/Speed", 7.5)
    TunableRegistry.update()
    assert value.value == 5.0  # cached until periodic()
    value.periodic()
    assert value.value == 7.5


def test_periodic_processes_inputs_through_logger(logger, tunables_backend):
    value = DoubleValue("Speed", 5.0)
    value.periodic()
    logger.process_inputs.assert_called_once_with(value.prefix, value)


def test_replay_mode_does_not_read_tunable(logger, tunables_backend):
    logger.is_replay.return_value = True
    value = DoubleValue("Speed", 5.0)
    tunables_backend.set_double("/Speed", 9.0)
    TunableRegistry.update()
    value.periodic()
    assert value.value == 5.0


def test_setter_writes_through_to_tunable(logger, tunables_backend):
    value = DoubleValue("Speed", 5.0)
    value.value = 2.5
    assert value.value == 2.5
    assert value._tunable.get() == 2.5


def test_set_default_changes_replay_fallback_only(logger, tunables_backend, table):
    value = DoubleValue("Speed", 5.0)
    value.set_default(1.0)
    assert value.value == 5.0
    table.get.return_value = 1.0
    value.from_log(table, "NetworkInputs")
    table.get.assert_called_once_with("NetworkInputs/Speed", 1.0)


def test_to_log_uses_prefix_and_normalized_key(logger, tunables_backend, table):
    value = DoubleValue("/Drive/Speed", 5.0)
    value.to_log(table, "NetworkInputs")
    table.put.assert_called_once_with("NetworkInputs/Drive/Speed", 5.0)


def test_from_log_restores_value_with_default_fallback(logger, tunables_backend, table):
    value = DoubleValue("Drive/Speed", 5.0)
    table.get.return_value = 8.0
    value.from_log(table, "NetworkInputs")
    table.get.assert_called_once_with("NetworkInputs/Drive/Speed", 5.0)
    assert value.value == 8.0


def test_duplicate_key_does_not_crash(logger, tunables_backend):
    first = DoubleValue("Same", 1.0)
    second = DoubleValue("Same", 2.0)
    assert first.value == 1.0
    assert second.value == 2.0
