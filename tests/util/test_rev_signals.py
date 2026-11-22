"""Unit tests for the REV signal helpers, using real REVLib 2027 Signal objects."""

from rev import REVLibError, Signal_double, SparkFlexConfig, SparkMaxConfig

from lib_6107.util.rev.signals import apply_signal_periods, read_signal, signal_error


def test_read_signal_valid():
    assert read_signal(Signal_double(3.5, REVLibError.OK, 0)) == (3.5, True)


def test_read_signal_invalid_returns_default():
    assert read_signal(Signal_double(3.5, REVLibError.TIMEOUT, 0), default=-1.0) == (-1.0, False)


def test_signal_error_is_int():
    assert signal_error(Signal_double(0.0, REVLibError.OK, 0)) == int(REVLibError.OK.value)
    assert signal_error(Signal_double(0.0, REVLibError.TIMEOUT, 0)) != 0


def test_apply_signal_periods_returns_same_config():
    for cfg in (SparkFlexConfig(), SparkMaxConfig()):
        assert apply_signal_periods(cfg, 10, 200) is cfg


def test_apply_signal_periods_sets_flags():
    cfg = apply_signal_periods(SparkFlexConfig(), 10, 200)
    assert cfg.signals is not None
    # The config must be accepted by the REV bindings after the periods are applied
    assert apply_signal_periods(cfg) is cfg
