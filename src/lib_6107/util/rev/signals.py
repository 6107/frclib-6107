"""
REVLib 2027 signal helpers.

REVLib 2027 getters return ``Signal`` wrappers that carry a value, an error code and a timestamp.
Status frames are only transmitted for signals that something has asked for, so the frame periods
should be set once at configuration time and each signal read once per cycle.
"""

from __future__ import annotations

from rev import REVLibError, SparkBaseConfig

DEFAULT_PERIOD_MS = 20
SLOW_PERIOD_MS = 250


def read_signal(signal: object, default: float = 0.0) -> tuple[float, bool]:
    """
    Read a REV Signal once.

    Returns:
        (value, valid): ``value`` is ``default`` when the signal has no valid data, so callers can log a
        stable number while still reporting the validity separately.
    """
    if signal.is_valid():
        return signal.get(), True
    return default, False


def signal_error(signal: object) -> int:
    """Return the REVLibError of a signal as an int suitable for a pykit input field."""
    error: REVLibError = signal.get_error()
    return int(error.value)


def apply_signal_periods(
    config: SparkBaseConfig,
    period_ms: int = DEFAULT_PERIOD_MS,
    slow_period_ms: int = SLOW_PERIOD_MS,
) -> SparkBaseConfig:
    """
    Configure the status frames for the signals logged by ``RevRpmSubsystem.update_inputs``.

    Velocity, position, applied output, bus voltage and output current ride at ``period_ms``.
    Faults, warnings and temperature are slow-changing and use ``slow_period_ms``. The
    ``always_on`` flags keep the frames enabled before the first read so the first cycle has data.
    """
    signals = config.signals
    signals.primary_encoder_velocity_period_ms(period_ms).primary_encoder_velocity_always_on(True)
    signals.primary_encoder_position_period_ms(period_ms).primary_encoder_position_always_on(True)
    signals.applied_output_period_ms(period_ms)
    signals.bus_voltage_period_ms(period_ms)
    signals.output_current_period_ms(period_ms)
    signals.motor_temperature_period_ms(slow_period_ms)
    signals.faults_period_ms(slow_period_ms).faults_always_on(True)
    signals.warnings_period_ms(slow_period_ms).warnings_always_on(True)
    return config
