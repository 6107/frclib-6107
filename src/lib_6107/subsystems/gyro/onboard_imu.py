# ------------------------------------------------------------------------ #
#      o-o      o                o                                         #
#     /         |                |                                         #
#    O     o  o O-o  o-o o-o     |  oo o--o o-o o-o                        #
#     \    |  | |  | |-' |   \   o | | |  |  /   /                         #
#      o-o o--O o-o  o-o o    o-o  o-o-o--O o-o o-o                        #
#             |                           |                                #
#          o--o                        o--o                                #
#                        o--o      o         o                             #
#                        |   |     |         |  o                          #
#                        O-Oo  o-o O-o  o-o -o-    o-o o-o                 #
#                        |  \  | | |  | | |  |  | |     \                  #
#                        o   o o-o o-o  o-o  o  |  o-o o-o                 #
#                                                                          #
#    Jemison High School - Huntsville Alabama                              #
# ------------------------------------------------------------------------ #
"""Systemcore onboard IMU implementation for frclib-6107.

The Systemcore controller contains an IMU that WPILib (and robotpy's ``wpilib``) exposes as
``wpilib.OnboardIMU``. No extra package is needed beyond ``wpilib``.

Onboard IMU Specific Behavior:
    - Needs no calibration: ``calibrated`` is always True and ``is_calibrating`` always False
    - Yaw is computed from the Systemcore's mounting orientation, which must be supplied:
      ``flat`` (parallel to the ground), ``landscape`` (vertical, long edge parallel to the
      ground) or ``portrait`` (vertical, short edge parallel to the ground)
    - There is no connection status API, so ``connected`` is always reported as True
    - pykit timestamps are the FPGA time of the ``update_inputs`` call; simulated yaw rate is derived
      from ``sim_yaw`` changes
    - ``set_yaw`` is emulated with a software offset (the IMU only supports ``reset_yaw``)
    - WPILib reports radians; this class converts to degrees for the Gyro interface
    - ``wpilib.OnboardIMU`` is looked up at run time. If the installed wpilib does not provide it
      (and no instance is injected), construction raises ``ImportError`` and ``Gyro.create`` returns None

Usage:
    gyro = Gyro.create("onboard", is_reversed=False, mount_orientation="flat")
    gyro.initialize()
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

import wpilib
from wpilib import RobotBase, Timer
from wpimath import Rotation2d
from wpimath.units import degrees, degrees_per_second, radians, radians_per_second

from lib_6107.subsystems.gyro.gyro import Gyro
from lib_6107.subsystems.pykit.gyro_io import GyroIO

if TYPE_CHECKING:
    from lib_6107.physics import PhysicsEngine

logger = logging.getLogger(__name__)


class OnboardImu(Gyro):
    """Systemcore onboard IMU gyro implementation (``wpilib.OnboardIMU``).

    Attributes:
        gyro_type (str): Set to "OnboardIMU" for identification.
        _gyro (wpilib.OnboardIMU): Underlying WPILib IMU object (or an injected stand-in).
        _is_simulation (bool): True if running in simulation; yaw then comes from ``sim_yaw``.
        _sim_yaw (degrees): Simulated yaw, only used in simulation.

    Axis note:
        pitch is read from ``get_angle_y`` and roll from ``get_angle_x``. Which physical tilt those
        axes correspond to depends on the mount orientation, so verify on the robot.

    Example:
        imu = OnboardImu(is_reversed=False, mount_orientation="landscape")
        imu.initialize()
        heading = imu.heading
    """

    gyro_type = "OnboardIMU"

    def __init__(self, is_reversed: bool, mount_orientation: Any = "flat", inst: Any | None = None) -> None:
        """Create the onboard IMU wrapper.

        Args:
            is_reversed (bool): True if all angle measurements should be negated.
            mount_orientation (str | wpilib.OnboardIMU.MountOrientation): How Systemcore is mounted:
                "flat", "landscape" or "portrait" (case insensitive) or the WPILib enum value.
            inst (Optional[Any]): IMU object to use instead of creating a ``wpilib.OnboardIMU``
                (used by tests or custom setups).

        Raises:
            ImportError: If ``inst`` is None and the installed wpilib has no ``OnboardIMU``.
            ValueError: If ``mount_orientation`` is not a known orientation.
        """
        super().__init__(is_reversed)

        if inst is not None:
            self._gyro = inst
        else:
            imu_class = getattr(wpilib, "OnboardIMU", None)

            if imu_class is None:
                raise ImportError("The installed wpilib does not provide OnboardIMU (SystemCore IMU)")

            self._gyro = imu_class(self._parse_mount_orientation(imu_class, mount_orientation))

        self._is_simulation = RobotBase.is_simulation()
        self._sim_yaw: degrees = 0.0
        self._sim_rate: radians_per_second = 0.0
        self._last_sim_yaw: degrees | None = None
        self._last_sim_time: float | None = None
        self._yaw_offset: degrees = 0.0

    @staticmethod
    def _parse_mount_orientation(imu_class: Any, orientation: Any) -> Any:
        """Convert a string (or enum) into an ``OnboardIMU.MountOrientation`` value."""
        if not isinstance(orientation, str):
            return orientation

        members = imu_class.MountOrientation.__members__
        name = orientation.strip().upper()
        if name not in members:
            raise ValueError(f"Invalid mount orientation '{orientation}'. Valid: {sorted(m.lower() for m in members)}")
        return members[name]

    def _signed(self, value: float) -> float:
        return -value if self._reversed else value

    @property
    def calibrated(self) -> bool:
        """Always True; the onboard IMU has no calibration phase."""
        return True

    @property
    def is_calibrating(self) -> bool:
        """Always False; the onboard IMU has no calibration phase."""
        return False

    def reset(self) -> None:
        """Reset the IMU. The only supported operation is zeroing yaw."""
        self.zero_yaw()

    def zero_yaw(self) -> None:
        """Zero the yaw angle (REAL calls ``reset_yaw()``; simulation zeroes ``sim_yaw``)."""
        self._yaw_offset = 0.0

        if self._is_simulation:
            self._sim_yaw = 0.0
            self._last_sim_yaw = None
        else:
            self._gyro.reset_yaw()

    @property
    def yaw(self) -> degrees:
        """Yaw (heading) in degrees, negated when the gyro is reversed."""
        value = self._sim_yaw if self._is_simulation else math.degrees(self._gyro.get_yaw()) + self._yaw_offset
        return self._signed(value)

    @property
    def pitch(self) -> degrees:
        """Pitch in degrees (``get_angle_y``); 0.0 in simulation."""
        return 0.0 if self._is_simulation else math.degrees(self._gyro.get_angle_y())

    @property
    def roll(self) -> degrees:
        """Roll in degrees (``get_angle_x``); 0.0 in simulation."""
        return 0.0 if self._is_simulation else math.degrees(self._gyro.get_angle_x())

    @property
    def raw_angle(self) -> degrees:
        """Yaw in degrees straight from the IMU, with no reversal applied."""
        return self._sim_yaw if self._is_simulation else math.degrees(self._gyro.get_yaw())

    @property
    def angle(self) -> degrees:
        """Heading in degrees relative to the last ``zero_yaw()``; same as ``yaw`` for this IMU."""
        return self.yaw

    @property
    def turn_rate(self) -> radians_per_second:
        """Z-axis angular velocity in radians per second, negated when reversed.

        In simulation this is derived from ``sim_yaw`` changes between ``update_inputs`` calls.
        """
        rate = self._sim_rate if self._is_simulation else self._gyro.get_gyro_rate_z()
        return self._signed(rate)

    @property
    def turn_rate_degrees_per_second(self) -> degrees_per_second:
        """Z-axis angular velocity in degrees per second."""
        return math.degrees(self.turn_rate)

    def update_inputs(self, inputs: GyroIO.GyroIOInputs) -> None:
        """Populate the pykit inputs (radians). ``connected`` is always True; the IMU has no status API."""
        now = Timer.get_timestamp()

        if self._is_simulation:
            self._update_sim_rate(now)

        inputs.connected = True
        inputs.yaw = Rotation2d.from_degrees(self.angle).radians()
        inputs.yaw_rate = self.turn_rate
        inputs.roll = math.radians(self.roll)
        inputs.pitch = math.radians(self.pitch)
        inputs.yaw_timestamp = inputs.yaw_rate_timestamp = now
        inputs.roll_timestamp = inputs.pitch_timestamp = now

    def set_yaw(self, yaw_rad: radians) -> None:
        """Make the reported yaw equal ``yaw_rad`` (a software offset on hardware; the IMU only has reset_yaw)."""
        target = self._signed(math.degrees(yaw_rad))

        if self._is_simulation:
            self._sim_yaw = target
        else:
            self._yaw_offset = target - math.degrees(self._gyro.get_yaw())

    def _update_sim_rate(self, now: float) -> None:
        if self._last_sim_yaw is not None and self._last_sim_time is not None and now > self._last_sim_time:
            self._sim_rate = math.radians(self._sim_yaw - self._last_sim_yaw) / (now - self._last_sim_time)

        self._last_sim_yaw = self._sim_yaw
        self._last_sim_time = now

    # ====================================================================
    # Simulation Support
    # ====================================================================

    def sim_init(self, physics_controller: PhysicsEngine) -> None:
        """Start simulation with a zeroed ``sim_yaw`` (the IMU has no SimDevice to attach to)."""
        super().sim_init(physics_controller)

        self._sim_yaw = 0.0
        self._sim_rate = 0.0
        self._last_sim_yaw = None
        self._last_sim_time = None

    @property
    def sim_yaw(self) -> degrees:
        """Simulated yaw in degrees (physical direction, before reversal)."""
        return self._sim_yaw

    @sim_yaw.setter
    def sim_yaw(self, value: degrees) -> None:
        """Set the simulated yaw in degrees; updated by the physics engine."""
        self._sim_yaw = value
