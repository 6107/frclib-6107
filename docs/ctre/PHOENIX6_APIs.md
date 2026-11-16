# Phoenix6 Configuration APIs - Comprehensive List

**Source:** https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html

**Last verified:** 2027 season preparation, against `phoenix6 26.70.0a2` (the version pinned in `pyproject.toml`).
The class names below were checked by introspecting the installed `phoenix6.configs` module. CTRE's hosted docs
(`/stable/`) may lag the pre-release wheel, so when they disagree the installed package is the source of truth
(see [Re-verifying this list](#re-verifying-this-list)).

This file is the lookup table used by `.github/agents/ctre-phoenix-api.chatmode.md.agent.md`.

## Overview

Complete list of all available Phoenix6 configuration classes for FIRST Robotics competition use.
These configurations control motor, sensor, and device behaviors in the Phoenix6 library.

## Device Configuration Containers

Each CTRE device has a top-level `*Configuration` container that aggregates the config groups listed in the next
section. Pass one to `device.configurator.apply(...)`. Not every group exists on every device.

| Device (`phoenix6.hardware`) | Container (`phoenix6.configs`) | Config groups it contains |
|------------------------------|--------------------------------|---------------------------|
| `TalonFX` (Kraken X60/X44, Falcon 500) | **TalonFXConfiguration** | `MotorOutput`, `CurrentLimits`, `Voltage`, `TorqueCurrent`, `Feedback`, `ClosedLoopGeneral`, `ClosedLoopRamps`, `OpenLoopRamps`, `MotionMagic`, `Slot0/1/2`, `HardwareLimitSwitch`, `SoftwareLimitSwitch`, `DifferentialConstants`, `DifferentialSensors`, `Audio`, `CustomParams` |
| `TalonFXS` (Minion, Vortex, brushed/custom) | **TalonFXSConfiguration** | Same as TalonFX except no `Feedback` / `TorqueCurrent`; adds `Commutation`, `CustomBrushlessMotor`, `ExternalFeedback`, `ExternalTemp` |
| `CANcoder` | **CANcoderConfiguration** | `MagnetSensor` |
| `Pigeon2` | **Pigeon2Configuration** | `MountPose`, `GyroTrim`, `Pigeon2Features` |
| `CANdi` | **CANdiConfiguration** | `DigitalInputs`, `Quadrature`, `PWM1`, `PWM2` |
| `CANrange` | **CANrangeConfiguration** | `ProximityParams`, `ToFParams`, `FovParams` |
| `CANdle` | **CANdleConfiguration** | `LED`, `CANdleFeatures` |

All containers also carry `CustomParams`. Container attributes are snake_case (`motor_output`, `current_limits`,
`slot0`, `hardware_limit_switch`, ...). Container URLs follow the same pattern as the entries below, e.g.
https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.TalonFXConfiguration

## Main Configuration Classes

### Motor Output & Control

1. **MotorOutputConfigs** - Motor output behavior configuration
   - Controls inverted status, neutral mode, duty cycle settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.MotorOutputConfigs

2. **CurrentLimitsConfigs** - Current limiting configuration
   - Stator and supply current limit settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.CurrentLimitsConfigs

3. **VoltageConfigs** - Voltage control configuration
   - Supply voltage time constant and peak voltage settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.VoltageConfigs

4. **TorqueCurrentConfigs** - Torque current configuration
   - Torque-based current control settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.TorqueCurrentConfigs

### Feedback & Sensing

5. **FeedbackConfigs** - Feedback sensor configuration
   - Feedback device selection and settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.FeedbackConfigs

6. **QuadratureConfigs** - Quadrature encoder configuration
   - Quadrature feedback settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.QuadratureConfigs

7. **MagnetSensorConfigs** - CTRE Magnet sensor configuration
   - Magnet sensor direction, offset, and discontinuity point
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.MagnetSensorConfigs

8. **ExternalFeedbackConfigs** - External feedback configuration
   - Settings for external feedback sources
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ExternalFeedbackConfigs

9. **DigitalInputsConfigs** - Digital input configuration
   - Digital input pin settings
   - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.DigitalInputsConfigs

### Motion Control

10. **ClosedLoopGeneralConfigs** - Closed-loop general configuration
    - PID controller general settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ClosedLoopGeneralConfigs

11. **ClosedLoopRampsConfigs** - Closed-loop ramp configuration
    - Acceleration/deceleration ramp settings for closed loop
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ClosedLoopRampsConfigs

12. **OpenLoopRampsConfigs** - Open-loop ramp configuration
    - Acceleration/deceleration ramp settings for open loop
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.OpenLoopRampsConfigs

13. **MotionMagicConfigs** - Motion Magic configuration
    - Motion Magic trajectory settings (velocity, acceleration, jerk)
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.MotionMagicConfigs

### PID/Slot Configurations

14. **Slot0Configs** - PID Slot 0 configuration
    - Primary PID slot settings (gains, integral zone, etc.)
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.Slot0Configs

15. **Slot1Configs** - PID Slot 1 configuration
    - Secondary PID slot settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.Slot1Configs

16. **Slot2Configs** - PID Slot 2 configuration
    - Tertiary PID slot settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.Slot2Configs

17. **SlotConfigs** - Generic PID slot configuration
    - Slot-agnostic variant used when the slot number is chosen at runtime
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.SlotConfigs

### Limit Switches

18. **HardwareLimitSwitchConfigs** - Hardware limit switch configuration
    - Limit switch pin assignment and behavior
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.HardwareLimitSwitchConfigs

19. **SoftwareLimitSwitchConfigs** - Software limit switch configuration
    - Speed-based software limit settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.SoftwareLimitSwitchConfigs

### Motor Types & Commutation

20. **CommutationConfigs** - Commutation configuration
    - Motor commutation settings (brushless parameter tuning)
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.CommutationConfigs

21. **CustomBrushlessMotorConfigs** - Custom brushless motor configuration
    - Settings for custom brushless motor definitions
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.CustomBrushlessMotorConfigs

22. **CustomParamsConfigs** - Custom parameters configuration
    - Custom device parameter settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.CustomParamsConfigs

### IMU & Gyro (Pigeon2)

23. **GyroTrimConfigs** - Gyro trim configuration
    - Gyroscope calibration and scalar settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.GyroTrimConfigs

24. **MountPoseConfigs** - Mount pose configuration
    - IMU/Pigeon2 physical mounting orientation (yaw, pitch, roll)
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.MountPoseConfigs

25. **Pigeon2FeaturesConfigs** - Pigeon2 features configuration
    - Pigeon2-specific features (compass, temperature compensation, no-motion calibration)
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.Pigeon2FeaturesConfigs

### Differential Drive (Kraken/TalonFX)

26. **DifferentialConstantsConfigs** - Differential drive constants configuration
    - Gear ratios and mechanical properties for differential drive systems
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.DifferentialConstantsConfigs

27. **DifferentialSensorsConfigs** - Differential drive sensors configuration
    - Sensor configuration for differential drive setups
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.DifferentialSensorsConfigs

### Vision/Distance Sensors

28. **ProximityParamsConfigs** - Proximity sensor parameters configuration
    - Time-of-Flight proximity sensor parameters
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ProximityParamsConfigs

29. **ToFParamsConfigs** - Time-of-Flight parameters configuration
    - Additional ToF sensor configuration parameters
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ToFParamsConfigs

30. **FovParamsConfigs** - Field of View parameters configuration
    - Vision/proximity sensor field of view settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.FovParamsConfigs

### Lighting/Audio

31. **LEDConfigs** - LED configuration
    - LED brightness and effect settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.LEDConfigs

32. **AudioConfigs** - Audio configuration
    - Audio/speaker settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.AudioConfigs

### PWM I/O

33. **PWM1Configs** - PWM channel 1 configuration
    - Programmable PWM output channel 1 settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.PWM1Configs

34. **PWM2Configs** - PWM channel 2 configuration
    - Programmable PWM output channel 2 settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.PWM2Configs

### External Temperature

35. **ExternalTempConfigs** - External temperature sensor configuration
    - External thermistor settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.ExternalTempConfigs

### CANdle LED

36. **CANdleFeaturesConfigs** - CANdle LED features configuration
    - CTRE CANdle LED strip feature settings
    - https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html#phoenix6.configs.CANdleFeaturesConfigs

## Summary

**Total Configuration Classes:** 36 configuration group APIs, plus the 7 per-device `*Configuration` containers
listed above (43 classes in total in `phoenix6.configs`; the module also exports `*Configurator` classes and
`SupportsSerialization`).

These configurations provide comprehensive control over:
- **Motor behavior** (output, current, voltage, torque)
- **Feedback systems** (encoders, magnet sensors, external feedback)
- **Motion control** (PID, Motion Magic, ramps)
- **Sensors & I/O** (limit switches, PWM, temperature, proximity)
- **Special devices** (Pigeon2 IMU, CANdle LED)

## Usage Pattern

All configurations follow a builder pattern in Phoenix6. In the 2027 / Systemcore release, device constructors take
a `CANBus` object (not a bare string), and enum-valued settings use `phoenix6.signals`:

```python
from phoenix6 import CANBus, configs, hardware, signals

# Create a TalonFX on a CAN bus ("" selects the default bus; use a name such as "canivore" for others)
talon = hardware.TalonFX(1, CANBus(""))

# Build configuration
motor_config = configs.TalonFXConfiguration()
motor_config.motor_output.with_inverted(signals.InvertedValue.COUNTER_CLOCKWISE_POSITIVE)
motor_config.motor_output.with_neutral_mode(signals.NeutralModeValue.BRAKE)
motor_config.current_limits.with_stator_current_limit(40)
motor_config.voltage.with_peak_forward_voltage(12)
motor_config.slot0.with_k_p(0.24)

# Apply configuration (returns a StatusCode; check it or retry)
status = talon.configurator.apply(motor_config)
```

In `lib_6107`, wrap `apply()` with `try_until_ok()` from `lib_6107.util.phoenix6.utils`, and use
`handle_faults()` from the same module from `SubsystemBase.fault_detection()`. Telemetry goes through
`Logger.record_output(...)`, not Phoenix's `SignalLogger` (disabled at robot startup).

## Re-verifying this list

Run from the repository root to compare this file with the installed `phoenix6` package:

```bash
uv run python - <<'EOF'
import inspect, re
from phoenix6 import configs
actual = {n for n, _ in inspect.getmembers(configs, inspect.isclass) if n.endswith(("Configs", "Configuration"))}
listed = set(re.findall(r"\*\*(\w+)\*\*", open("docs/ctre/PHOENIX6_APIs.md").read()))
print("Missing from doc:", sorted(actual - listed))
print("Stale in doc:", sorted(n for n in listed if n.endswith(("Configs", "Configuration")) and n not in actual))
EOF
```

## Additional Resources

- **Module Documentation**: https://api.ctr-electronics.com/phoenix6/stable/python/autoapi/phoenix6/configs/index.html
- **Phoenix6 Home**: https://api.ctr-electronics.com/phoenix6/stable/python/
- **CTRE Docs**: https://v6.docs.ctr-electronics.com/
- **CTRE Store / Developers**: https://store.ctr-electronics.com/developers/
- **Phoenix 6 release notes**: https://github.com/CrossTheRoadElec/Phoenix-Releases/releases
