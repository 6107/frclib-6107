"""Unit tests for loggednetworkinput module."""

from lib_6107.pykit.networktables.loggednetworkinput import LoggedNetworkInput


def test_loggednetworkinput_default_prefix():
    """Verify default prefix is NetworkInputs."""
    assert LoggedNetworkInput.prefix == "NetworkInputs"


def test_loggednetworkinput_init():
    """Verify LoggedNetworkInput initialization."""
    input_obj = LoggedNetworkInput()
    assert isinstance(input_obj, LoggedNetworkInput)


def test_remove_slash_with_leading_slash():
    """Verify remove_slash removes leading slash."""
    result = LoggedNetworkInput.remove_slash("/Key")
    assert result == "Key"


def test_remove_slash_without_leading_slash():
    """Verify remove_slash handles strings without leading slash."""
    result = LoggedNetworkInput.remove_slash("Key")
    assert result == "Key"


def test_remove_slash_with_nested_path():
    """Verify remove_slash only removes leading slash."""
    result = LoggedNetworkInput.remove_slash("/Key/Sub/Path")
    assert result == "Key/Sub/Path"


def test_remove_slash_empty_string():
    """Verify remove_slash handles empty string."""
    result = LoggedNetworkInput.remove_slash("")
    assert result == ""


def test_remove_slash_smartdashboard_path():
    """Verify remove_slash works with SmartDashboard paths."""
    result = LoggedNetworkInput.remove_slash("/SmartDashboard/Auto")
    assert result == "SmartDashboard/Auto"


def test_loggednetworkinput_subclass_inherits_prefix():
    """Verify subclasses inherit prefix."""
    class CustomInput(LoggedNetworkInput):
        pass

    input_obj = CustomInput()
    assert input_obj.prefix == "NetworkInputs"


def test_loggednetworkinput_periodic_exists():
    """Verify periodic method exists."""
    input_obj = LoggedNetworkInput()
    assert hasattr(input_obj, "periodic")
    assert callable(input_obj.periodic)


def test_remove_slash_defensive_programming():
    """Verify remove_slash works in defensive programming."""
    user_inputs = ["/NetworkInputs/Auto", "NetworkInputs/Auto"]
    normalized = [LoggedNetworkInput.remove_slash(x) for x in user_inputs]
    assert normalized[0] == normalized[1]


def test_remove_slash_single_char():
    """Verify remove_slash works with single character."""
    result = LoggedNetworkInput.remove_slash("/A")
    assert result == "A"


def test_remove_slash_multiple_trailing_slashes():
    """Verify remove_slash preserves trailing slashes."""
    result = LoggedNetworkInput.remove_slash("/Key//")
    assert result == "Key//"


def test_loggednetworkinput_periodic_callable():
    """Verify periodic method is callable."""
    input_obj = LoggedNetworkInput()
    # Should not raise
    result = input_obj.periodic()
    assert result is None


def test_loggednetworkinput_class_attribute():
    """Verify prefix is a class attribute."""
    assert hasattr(LoggedNetworkInput, 'prefix')
    assert isinstance(LoggedNetworkInput.prefix, str)

