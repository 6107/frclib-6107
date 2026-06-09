"""Unit tests for Pigeon2 gyro implementation."""

import math
from unittest.mock import MagicMock, patch

import pytest

from lib_6107.subsystems.gyro.pigeon2 import Pigeon2
from lib_6107.subsystems.pykit.gyro_io import GyroIO


class TestPigeon2Initialization:
    """Tests for Pigeon2 initialization."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_initialization_with_device_id_creates_pigeon2_instance(self, mock_pigeon2_class):
        """Verify Pigeon2 is created with correct device_id when no instance provided."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=5, is_reversed=False, update_frequency=50)

        mock_pigeon2_class.assert_called_once_with(5)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_initialization_with_custom_instance_uses_provided_instance(self, mock_pigeon2_class):
        """Verify custom Pigeon2 instance is used when provided."""
        custom_instance = MagicMock()
        custom_instance.__class__.__name__ = 'Pigeon2'

        pigeon2 = Pigeon2(device_id=0, is_reversed=True, update_frequency=50, inst=custom_instance)

        mock_pigeon2_class.assert_not_called()
        assert pigeon2._gyro is custom_instance

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_initialization_with_custom_instance_forces_is_reversed_false(self, mock_pigeon2_class):
        """Verify is_reversed is forced to False when custom instance provided."""
        custom_instance = MagicMock()
        custom_instance.__class__.__name__ = 'Pigeon2'

        pigeon2 = Pigeon2(device_id=0, is_reversed=True, update_frequency=50, inst=custom_instance)

        assert pigeon2._reversed is False

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_initialization_with_invalid_custom_instance_raises_value_error(self, mock_pigeon2_class):
        """Verify ValueError raised if custom instance is not Pigeon2 type."""
        invalid_instance = "not a pigeon2"

        with pytest.raises(ValueError, match="Invalid object type past in as gyro instance"):
            Pigeon2(device_id=0, is_reversed=False, update_frequency=50, inst=invalid_instance)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.try_until_ok')
    def test_initialization_disables_compass(self, mock_try_until_ok, mock_pigeon2_class):
        """Verify compass is disabled during initialization."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        # Verify try_until_ok was called with configuration
        mock_try_until_ok.assert_called_once()
        call_args = mock_try_until_ok.call_args
        assert call_args[0][0] == "Pigeon2"
        assert call_args[0][1] == 5

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_initialization_stores_update_frequency(self, mock_pigeon2_class):
        """Verify update frequency is stored for configure step."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=100)

        assert pigeon2._update_hz == 100


class TestPigeon2Initialize:
    """Tests for Pigeon2.initialize() method."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.StatusSignal')
    def test_initialize_calls_reset_when_instance_not_supplied(self, mock_status_signal, mock_pigeon2_class):
        """Verify reset is called during initialize when Pigeon2 was created."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.initialize()

        mock_instance.set_yaw.assert_called_once_with(0.0)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.StatusSignal')
    def test_initialize_skips_reset_when_custom_instance_supplied(self, mock_status_signal, mock_pigeon2_class):
        """Verify reset is NOT called when custom instance provided."""
        custom_instance = MagicMock()
        custom_instance.__class__.__name__ = 'Pigeon2'

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50, inst=custom_instance)
        pigeon2.initialize()

        custom_instance.set_yaw.assert_not_called()

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.StatusSignal')
    @patch('lib_6107.subsystems.gyro.pigeon2.Phoenix6Signals')
    def test_initialize_sets_update_frequency_on_status_signals(self, mock_phoenix6_signals, mock_status_signal,
                                                                mock_pigeon2_class):
        """Verify update frequency is applied to all StatusSignals."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=100)
        pigeon2.initialize()

        mock_status_signal.set_update_frequency_for_all.assert_called_once()

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.StatusSignal')
    def test_initialize_optimizes_bus_utilization(self, mock_status_signal, mock_pigeon2_class):
        """Verify bus optimization is called during initialize."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.initialize()

        mock_instance.optimize_bus_utilization.assert_called_once()


class TestPigeon2CalibrationProperties:
    """Tests for calibration-related properties."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_calibrated_always_returns_true(self, mock_pigeon2_class):
        """Verify calibrated property always returns True."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.calibrated is True

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_is_calibrating_always_returns_false(self, mock_pigeon2_class):
        """Verify is_calibrating property always returns False."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.is_calibrating is False


class TestPigeon2Reset:
    """Tests for reset functionality."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_reset_calls_zero_yaw(self, mock_pigeon2_class):
        """Verify reset delegates to zero_yaw."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.reset()

        mock_instance.set_yaw.assert_called_with(0.0)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_zero_yaw_sets_hardware_to_zero(self, mock_pigeon2_class):
        """Verify zero_yaw sets Pigeon2 hardware to 0 degrees."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.zero_yaw()

        mock_instance.set_yaw.assert_called_with(0.0)


class TestPigeon2AngleProperties:
    """Tests for angle/yaw related properties."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_yaw_property_returns_hardware_value_when_not_reversed(self, mock_pigeon2_class):
        """Verify yaw property returns hardware value without modification."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_yaw_signal = MagicMock()
        mock_yaw_signal.value = 45.0
        mock_instance.get_yaw.return_value = mock_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.yaw == 45.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_yaw_property_negates_value_when_reversed(self, mock_pigeon2_class):
        """Verify yaw property is negated when is_reversed is True."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_yaw_signal = MagicMock()
        mock_yaw_signal.value = 45.0
        mock_instance.get_yaw.return_value = mock_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=True, update_frequency=50)

        assert pigeon2.yaw == -45.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_yaw_setter_updates_hardware(self, mock_pigeon2_class):
        """Verify yaw setter calls set_yaw on hardware."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.yaw = 90.0

        mock_instance.set_yaw.assert_called_with(90.0)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_angle_property_equals_yaw(self, mock_pigeon2_class):
        """Verify angle property returns same value as yaw."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_yaw_signal = MagicMock()
        mock_yaw_signal.value = 90.0
        mock_instance.get_yaw.return_value = mock_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.angle == pigeon2.yaw
        assert pigeon2.angle == 90.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_raw_angle_equals_angle(self, mock_pigeon2_class):
        """Verify raw_angle returns same value as angle."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_yaw_signal = MagicMock()
        mock_yaw_signal.value = 45.0
        mock_instance.get_yaw.return_value = mock_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.raw_angle == pigeon2.angle


class TestPigeon2PitchAndRoll:
    """Tests for pitch and roll properties."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_pitch_property_returns_hardware_value(self, mock_pigeon2_class):
        """Verify pitch property returns value from hardware."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_pitch_signal = MagicMock()
        mock_pitch_signal.value = 15.0
        mock_instance.get_pitch.return_value = mock_pitch_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.pitch == 15.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_roll_property_returns_hardware_value(self, mock_pigeon2_class):
        """Verify roll property returns value from hardware."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_roll_signal = MagicMock()
        mock_roll_signal.value = 20.0
        mock_instance.get_roll.return_value = mock_roll_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.roll == 20.0


class TestPigeon2TurnRate:
    """Tests for turn rate properties."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_turn_rate_degrees_per_second_returns_hardware_value_when_not_reversed(self, mock_pigeon2_class):
        """Verify turn rate in degrees per second returns hardware value."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_velocity_signal = MagicMock()
        mock_velocity_signal.value = 45.0
        mock_instance.get_angular_velocity_z_world.return_value = mock_velocity_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        assert pigeon2.turn_rate_degrees_per_second == 45.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_turn_rate_degrees_per_second_negates_when_reversed(self, mock_pigeon2_class):
        """Verify turn rate is negated when is_reversed is True."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_velocity_signal = MagicMock()
        mock_velocity_signal.value = 45.0
        mock_instance.get_angular_velocity_z_world.return_value = mock_velocity_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=True, update_frequency=50)

        assert pigeon2.turn_rate_degrees_per_second == -45.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_turn_rate_converts_degrees_to_radians(self, mock_pigeon2_class):
        """Verify turn_rate property converts degrees per second to radians per second."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_velocity_signal = MagicMock()
        mock_velocity_signal.value = 180.0
        mock_instance.get_angular_velocity_z_world.return_value = mock_velocity_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)

        expected_rad_s = math.radians(180.0)
        assert abs(pigeon2.turn_rate - expected_rad_s) < 0.001


class TestPigeon2UpdateInputs:
    """Tests for updateInputs method for logging."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_update_inputs_populates_yaw_and_timestamp(self, mock_pigeon2_class):
        """Verify updateInputs sets yaw and yaw_timestamp."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        mock_yaw_signal = MagicMock()
        mock_yaw_signal.value_as_double = 45.0
        mock_timestamp = MagicMock()
        mock_timestamp.time = 12345
        mock_yaw_signal.timestamp = mock_timestamp

        mock_instance.get_yaw.return_value = mock_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        inputs = GyroIO.GyroIOInputs()
        pigeon2.updateInputs(inputs)

        assert abs(inputs.yaw - math.radians(45.0)) < 0.001
        assert inputs.yaw_timestamp == 12345

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_update_inputs_populates_yaw_rate_and_timestamp(self, mock_pigeon2_class):
        """Verify updateInputs sets yaw_rate and yaw_rate_timestamp."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        mock_velocity_signal = MagicMock()
        mock_velocity_signal.value_as_double = 90.0
        mock_timestamp = MagicMock()
        mock_timestamp.time = 12346
        mock_velocity_signal.timestamp = mock_timestamp

        mock_instance.get_angular_velocity_z_world.return_value = mock_velocity_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        inputs = GyroIO.GyroIOInputs()
        pigeon2.updateInputs(inputs)

        assert abs(inputs.yaw_rate - math.radians(90.0)) < 0.001

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_update_inputs_populates_pitch_and_roll(self, mock_pigeon2_class):
        """Verify updateInputs sets pitch, roll and timestamps."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        mock_pitch_signal = MagicMock()
        mock_pitch_signal.value_as_double = 10.0
        mock_pitch_timestamp = MagicMock()
        mock_pitch_timestamp.time = 12347
        mock_pitch_signal.timestamp = mock_pitch_timestamp

        mock_roll_signal = MagicMock()
        mock_roll_signal.value_as_double = 20.0
        mock_roll_timestamp = MagicMock()
        mock_roll_timestamp.time = 12348
        mock_roll_signal.timestamp = mock_roll_timestamp

        mock_instance.get_pitch.return_value = mock_pitch_signal
        mock_instance.get_roll.return_value = mock_roll_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        inputs = GyroIO.GyroIOInputs()
        pigeon2.updateInputs(inputs)

        assert abs(inputs.pitch - math.radians(10.0)) < 0.001
        assert abs(inputs.roll - math.radians(20.0)) < 0.001

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    @patch('lib_6107.subsystems.gyro.pigeon2.StatusSignal')
    def test_update_inputs_checks_connection_status(self, mock_status_signal, mock_pigeon2_class):
        """Verify updateInputs checks connection via StatusSignal.is_all_good."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_status_signal.is_all_good.return_value = True

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        inputs = GyroIO.GyroIOInputs()
        pigeon2.updateInputs(inputs)

        assert inputs.connected is True
        mock_status_signal.is_all_good.assert_called_once()


class TestPigeon2SetYaw:
    """Tests for set_yaw helper method."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_set_yaw_converts_radians_to_degrees(self, mock_pigeon2_class):
        """Verify set_yaw converts radian input to degrees before setting."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.set_yaw(math.pi)

        mock_instance.set_yaw.assert_called_with(180.0)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_set_yaw_with_zero_radians(self, mock_pigeon2_class):
        """Verify set_yaw correctly handles zero radians."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        pigeon2.set_yaw(0.0)

        mock_instance.set_yaw.assert_called_with(0.0)


class TestPigeon2Simulation:
    """Tests for simulation support."""

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_sim_init_stores_sim_gyro_reference(self, mock_pigeon2_class):
        """Verify sim_init stores reference to simulated Pigeon2."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        mock_physics = MagicMock()
        pigeon2.sim_init(mock_physics)

        assert pigeon2._sim_gyro is mock_instance

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_sim_init_stores_sim_gyro_state(self, mock_pigeon2_class):
        """Verify sim_init stores reference to SimState."""
        mock_instance = MagicMock()
        mock_sim_state = MagicMock()
        mock_instance.sim_state = mock_sim_state
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        mock_physics = MagicMock()
        pigeon2.sim_init(mock_physics)

        assert pigeon2._sim_gyro_state is mock_sim_state

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_sim_yaw_getter_returns_simulated_value(self, mock_pigeon2_class):
        """Verify sim_yaw property returns simulated gyro value."""
        mock_instance = MagicMock()
        mock_pigeon2_class.return_value = mock_instance
        mock_sim_yaw_signal = MagicMock()
        mock_sim_yaw_signal.value = 135.0
        mock_instance.get_yaw.return_value = mock_sim_yaw_signal

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        mock_physics = MagicMock()
        pigeon2.sim_init(mock_physics)

        assert pigeon2.sim_yaw == 135.0

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_sim_yaw_setter_updates_without_reversal(self, mock_pigeon2_class):
        """Verify sim_yaw setter updates simulation without reversal when not reversed."""
        mock_instance = MagicMock()
        mock_sim_state = MagicMock()
        mock_instance.sim_state = mock_sim_state
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=False, update_frequency=50)
        mock_physics = MagicMock()
        pigeon2.sim_init(mock_physics)

        pigeon2.sim_yaw = 60.0

        mock_sim_state.set_raw_yaw.assert_called_with(60.0)

    @patch('lib_6107.subsystems.gyro.pigeon2.pigeon2.Pigeon2')
    def test_sim_yaw_setter_applies_reversal(self, mock_pigeon2_class):
        """Verify sim_yaw setter negates value when is_reversed is True."""
        mock_instance = MagicMock()
        mock_sim_state = MagicMock()
        mock_instance.sim_state = mock_sim_state
        mock_pigeon2_class.return_value = mock_instance

        pigeon2 = Pigeon2(device_id=0, is_reversed=True, update_frequency=50)
        mock_physics = MagicMock()
        pigeon2.sim_init(mock_physics)

        pigeon2.sim_yaw = 60.0

        mock_sim_state.set_raw_yaw.assert_called_with(-60.0)
