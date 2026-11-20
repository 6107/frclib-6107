"""Unit tests for LoggedNetworkNumber, LoggedNetworkBoolean and LoggedNetworkString."""

from unittest.mock import patch

import pytest
from tunables import TunableRegistry

from lib_6107.pykit.networktables.loggednetworkboolean import LoggedNetworkBoolean
from lib_6107.pykit.networktables.loggednetworknumber import LoggedNetworkNumber
from lib_6107.pykit.networktables.loggednetworkstring import LoggedNetworkString

LOGGER = "lib_6107.pykit.networktables.loggednetworkvalue.Logger"


@pytest.fixture(autouse=True)
def logger():
    with patch(LOGGER) as mock_logger:
        mock_logger.is_replay.return_value = False
        yield mock_logger


class TestLoggedNetworkNumber:
    def test_default_value_is_zero(self, tunables_backend):
        assert LoggedNetworkNumber("N").value == 0.0

    def test_int_default_is_coerced_to_float(self, tunables_backend):
        number = LoggedNetworkNumber("N", 3)
        assert number.value == 3.0
        assert isinstance(number.value, float)

    def test_int_assignment_is_coerced_to_float(self, tunables_backend):
        number = LoggedNetworkNumber("N", 1.0)
        number.value = 4
        assert isinstance(number.value, float)
        assert number.value == 4.0

    def test_published_as_double_tunable(self, tunables_backend):
        LoggedNetworkNumber("Drive/MaxSpeed", 3.0)
        assert tunables_backend.get_double("/Drive/MaxSpeed") == 3.0

    def test_remote_write_visible_after_periodic(self, tunables_backend):
        number = LoggedNetworkNumber("Drive/MaxSpeed", 3.0)
        tunables_backend.set_double("/Drive/MaxSpeed", 1.25)
        TunableRegistry.update()
        number.periodic()
        assert number.value == 1.25

    def test_negative_and_large_values(self, tunables_backend):
        number = LoggedNetworkNumber("N", -1.5e9)
        assert number.value == -1.5e9


class TestLoggedNetworkBoolean:
    def test_default_is_false(self, tunables_backend):
        assert LoggedNetworkBoolean("B").value is False

    def test_true_default(self, tunables_backend):
        assert LoggedNetworkBoolean("B", True).value is True

    def test_published_as_boolean_tunable(self, tunables_backend):
        LoggedNetworkBoolean("Intake/Enabled", True)
        assert tunables_backend.get_bool("/Intake/Enabled") is True

    def test_remote_toggle_visible_after_periodic(self, tunables_backend):
        flag = LoggedNetworkBoolean("Debug/Enabled", False)
        tunables_backend.set_bool("/Debug/Enabled", True)
        TunableRegistry.update()
        flag.periodic()
        assert flag.value is True

    def test_setter_writes_through(self, tunables_backend):
        flag = LoggedNetworkBoolean("Flag", False)
        flag.value = True
        assert tunables_backend.get_bool("/Flag") is True


class TestLoggedNetworkString:
    def test_default_is_empty(self, tunables_backend):
        assert LoggedNetworkString("S").value == ""

    def test_published_as_string_tunable(self, tunables_backend):
        LoggedNetworkString("Match/GameData", "RBR")
        assert tunables_backend.get_string("/Match/GameData") == "RBR"

    def test_remote_write_visible_after_periodic(self, tunables_backend):
        text = LoggedNetworkString("Robot/State", "Idle")
        tunables_backend.set_string("/Robot/State", "Running")
        TunableRegistry.update()
        text.periodic()
        assert text.value == "Running"

    @pytest.mark.parametrize("text", ["ロボット", "🤖 robot", "Zoë", ""])
    def test_unicode_round_trip(self, tunables_backend, text):
        value = LoggedNetworkString("U", "x")
        value.value = text
        assert value.value == text
        assert value._tunable.get() == text
