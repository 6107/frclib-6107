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

import logging
from typing import TYPE_CHECKING, Any

from limelight import Limelight
from limelightresults import FiducialResult, GeneralResult, parse_results
from ntcore import (
    DoubleArrayEntry,
    DoubleArrayPublisher,
    DoubleArraySubscriber,
    DoubleEntry,
    DoublePublisher,
    DoubleSubscriber,
    IntegerEntry,
    IntegerPublisher,
)
from wpilib import Timer
from wpimath import Pose3d, Rotation2d, Rotation3d
from wpimath.units import degrees, degrees_to_radians, milliseconds, percent, seconds

from lib_6107.field.game_field import FieldChange, GameField
from lib_6107.field.layout import FieldLayout
from lib_6107.pykit.logger import Logger
from lib_6107.pykit.timeutil import fpga_time_us
from lib_6107.subsystems.pykit.vision_io import PoseObservation, PoseObservationType, TargetObservation, VisionIO
from lib_6107.subsystems.vision.visionsubsystem import VisionSubsystem, VisionTargetData

if TYPE_CHECKING:
    from lib_6107.subsystems.drivetrain.drivesubsystem import DriveSubsystem

logger = logging.getLogger(__name__)


class LimelightVisionSubsystem(VisionSubsystem):  # pylint: disable=too-many-instance-attributes
    def __init__(self, info: dict[str, Any], drivetrain: DriveSubsystem, game_field: GameField):
        super().__init__(info, drivetrain, game_field)

        self._camera: Limelight = Limelight(self._name)
        self._latest_results: GeneralResult | None = None

        self._pipeline_index_request: DoublePublisher = self._network_table.get_double_topic("pipeline").publish()
        self._pipeline_index: DoubleEntry = self._network_table.get_double_topic("getpipe").get_entry(-1)
        # "cl" and "tl" are additional latencies in milliseconds

        self._led_mode: IntegerEntry = self._network_table.get_integer_topic("ledMode").get_entry(-1)
        self._cam_mode: IntegerEntry = self._network_table.get_integer_topic("camMode").get_entry(-1)
        self._tx: DoubleEntry = self._network_table.get_double_topic("tx").get_entry(0.0)
        self._ty: DoubleEntry = self._network_table.get_double_topic("ty").get_entry(0.0)
        self._ta: DoubleEntry = self._network_table.get_double_topic("ta").get_entry(0.0)
        self._hb: IntegerEntry = self._network_table.get_integer_topic("hb").get_entry(0)

        self._last_heartbeat = 0
        self._last_heartbeat_time = 0
        self._heart_beating = False

        self._robot_orientation_set_request: DoubleArrayPublisher | None = None
        self._camera_pose_set_request: DoubleArrayPublisher | None = None
        self._imu_mode_request: IntegerPublisher | None = None  # this is only for Limelight 4

        self._robot_pose: DoubleArrayEntry | None = None
        self._robot_pose_flipped: DoubleArrayEntry | None = None

        if self._estimate:
            # The estimator is used if the drive subsystem does not support a way to add
            # individual pose elements into it's pose estimation. For the CTRE (phoenix6)
            # drives, there is a supported method to add individual elements and so we do
            # not set up our own.
            self.add_localizer()

        # Enable WebSockets
        self._camera.enable_websocket()

        # TODO: If websockets works as expected, minimize the NT4 items below

        # I/O Implementation for real Limelight hardware
        # self.rotationSupplier: Supplier<Rotation2d>     = None
        self.orientation_publisher: DoubleArrayPublisher = self._network_table.get_double_array_topic(
            "robot_orientation_set"
        ).publish()

        self.latency_subscriber: DoubleSubscriber = self._network_table.get_double_topic("tl").subscribe(0.0)
        self.tx_subscriber: DoubleSubscriber = self._network_table.get_double_topic("tx").subscribe(0.0)
        self.ty_subscriber: DoubleSubscriber = self._network_table.get_double_topic("ty").subscribe(0.0)
        self.megatag1_subscriber: DoubleArraySubscriber = self._network_table.get_double_array_topic(
            "botpose_wpiblue"
        ).subscribe([])
        self.megatag2_subscriber: DoubleArraySubscriber = self._network_table.get_double_array_topic(
            "botpose_orb_wpiblue"
        ).subscribe([])

    def add_localizer(self):
        # TODO: Untested. Limelight expects its own ".fmap" JSON format. Verify that layout.to_json()
        #       is accepted, or add a layout -> fmap converter, when we test the Limelight.
        self._upload_layout(self._game_field.layout)
        # if we want MegaTag2 localizer to work, we need to be publishing two things (to the vision):
        #   1. what robot's yaw is ("yaw=0 degrees" means "facing North", "yaw=90 degrees" means "facing West", etc.)
        #   2. where is this vision sitting on the robot (e.g. y=-0.2 meters to the right, x=0.1 meters fwd from center)
        self._robot_orientation_set_request = self._network_table.get_double_array_topic(
            "robot_orientation_set"
        ).publish()
        self._camera_pose_set_request = self._network_table.get_double_array_topic(
            "camerapose_robotspace_set"
        ).publish()
        self._imu_mode_request = self._network_table.get_integer_topic(
            "imumode_set"
        ).publish()  # this is only for Limelight 4

        # and we can then receive the localizer results from the vision back
        self._robot_pose = self._network_table.get_double_array_topic("botpose_orb_wpiblue").get_entry([])
        self._robot_pose_flipped = self._network_table.get_double_array_topic("botpose_orb_wpired").get_entry([])

    def _upload_layout(self, layout: FieldLayout | None) -> None:
        if layout is None:
            logger.warning(f"{self._name}: no field layout to upload")
            return
        self._camera.upload_fieldmap(layout.to_json())

    def _on_field_change(self, change: FieldChange) -> None:
        """
        The GameField switched to a different field or layout (registered by VisionSubsystem).
        """
        if self._estimate:
            self._upload_layout(change.layout)  # TODO: Untested (see add_localizer)

    def _get_latest_results(self) -> GeneralResult | None:
        """
        Get the latest targeting data from the vision via the WebSocket connection
        """
        self._latest_results = parse_results(self._camera.get_latest_results())
        return self._latest_results

    @property
    def pipeline(self) -> int:
        return int(self._pipeline_index.get(-1))

    @pipeline.setter
    def pipeline(self, index: int) -> None:
        self._pipeline_index_request.set(float(index))

    @property
    def latency(self) -> milliseconds | None:
        # TODO: Also have a targeting latency.  See which to use?
        results: GeneralResult | None = self._latest_results or self._get_latest_results()
        return results.targeting_latency if results is not None else None

    @property
    def timestamp(self) -> seconds | None:
        """
        Returns the estimated time the frame was taken, in the Received system's time base
        """
        results: GeneralResult | None = self._latest_results or self._get_latest_results()
        return results.timestamp if results is not None else None

    @staticmethod
    def get_vision_data(results: FiducialResult):
        return VisionTargetData(
            results.target_x_degrees,
            results.target_y_degrees,
            results.target_area,
            results.fiducial_id,
            None,  # TODO: pose ambiguity
            None,  # TODO: best vision to target
            None,
        )  # TODO: alt vision to target

    # self.skew = fiducial_data["skew"]
    # self.camera_pose_target_space = fiducial_data["t6c_ts"]
    # self.robot_pose_field_space = fiducial_data["t6r_fs"]
    # self.robot_pose_target_space = fiducial_data["t6r_ts"]
    # self.target_pose_camera_space = fiducial_data["t6t_cs"]
    # self.target_pose_robot_space = fiducial_data["t6t_rs"]

    @property
    def best_target(self) -> VisionTargetData | None:
        """
        Returns the best target in this pipeline result. If there are no targets, this method will
        return null. The best target is determined by the target sort mode in the PhotonVision UI.
        """
        results: GeneralResult | None = self._latest_results or self._get_latest_results()
        if results is not None and len(results.fiducialResults) > 0:
            return self.get_vision_data(results.fiducialResults[0])

        return None

    @property
    def valid(self) -> bool:
        return self._heart_beating

    @property
    def area(self) -> percent:
        """
        Target Area (0..100] percent of image
        """
        target: VisionTargetData | None = self.best_target
        return target.area if target else 0

    @property
    def x_offset(self) -> degrees:
        """
        Horizontal Offset from Crosshair to Target [-29.9..29.8] degrees
        """
        target: VisionTargetData | None = self.best_target
        return target.yaw if target else 0

    @property
    def y_offset(self) -> degrees:
        """
        Vertical Offset from Crosshair to Target [-24.85..24.85]
        """
        target: VisionTargetData | None = self.best_target
        return target.pitch if target else 0

    @property
    def hb(self) -> float:
        """
        Heartbeat value. Increases once per frame and rolls over at 2 billion.
        """
        return self._hb.get()

    def get_seconds_since_last_heartbeat(self) -> float:
        return Timer.get_timestamp() - self._last_heartbeat_time

    def get_latest_results(self) -> GeneralResult | None:
        return self._latest_results

    def periodic(self) -> None:
        super().periodic()

        if not self._is_simulation:
            # Clear latest_results so we will get new results on the next pass
            self._latest_results = None

        now = Timer.get_timestamp()
        heartbeat = self.hb

        if heartbeat != self._last_heartbeat:
            self._last_heartbeat = heartbeat
            self._last_heartbeat_time = now

        heart_beating = now < self._last_heartbeat_time + 5  # no heartbeat for 5s => stale vision

        if heart_beating != self._heart_beating:
            logger.warning("Camera %s: %s", self._name, "UPDATING" if heart_beating else "NO LONGER UPDATING")

        self._heart_beating = heart_beating

    def dashboard_initialize(self) -> None:
        super().dashboard_initialize()
        Logger.record_output(f"Vision/Camera/{self.name}/Type", "Limelight")

    def dashboard_periodic(self) -> None:
        super().dashboard_periodic()
        Logger.record_output(f"Vision/Camera/{self.name}/Heartbeat", "Alive" if self._heart_beating else "Dead")
        Logger.record_output(f"Vision/Camera/{self.name}/LastHeartbeatTime", self._last_heartbeat_time)

    def simulation_periodic(self):
        """
        This method is called periodically by the CommandScheduler (after the periodic
        function). It is useful for updating subsystem-specific state that needs to be
        maintained for simulations, such as for updating simulation classes and setting
        simulated sensor readings.

        Unlike the physics 'update_sim', it is not called with the current time (now)
        or the amount of time since 'update_sim' was called (tm_diff).  It is called
        just after the 'periodic' call and before the 'update_sim' is called. One other
        'important' difference is 'update_sim' is called at a period >= 10 ms instead
        of the default 20 mS for the CommandScheduler's simulation_periodic (this function).
        """
        super().simulation_periodic()  # TODO: Can we do anything here to support limelight simulation

    def update_inputs(self, inputs: VisionIO.VisionIOInputs) -> None:
        """
        Pykit support for AdvantageScope.  Called from base class's 'periodic' function
        """
        # TODO: Tie in the heartbeat with the determination of 'connected' below
        inputs.connected = (fpga_time_us() - self.latency_subscriber.get_last_change()) / 1000 < 250

        inputs.latest_target_observation = TargetObservation(
            Rotation2d.from_degrees(self.tx_subscriber.get()),
            Rotation2d.from_degrees(self.ty_subscriber.get()),
        )
        # Update orientation for MegaTag 2
        # TODO: self.orientationPublisher.accept({rotationSupplier.get().getDegrees(), 0.0, 0.0, 0.0, 0.0, 0.0});
        # TODO: NetworkTableInstance.get_default().flush(); // Increases network traffic but recommended by Limelight

        # Read new pose observations from NetworkTables
        # TODO: In java version of this, this is a set. We want a set but we need to keep order perhaps?
        inputs.tag_ids = []
        inputs.pose_observations = []

        for rawSample in self.megatag1_subscriber.read_queue():
            sample_len = len(rawSample.value)
            if sample_len == 0:
                continue

            # TODO: Where in the heck does 11 come from and the increment by 7
            for i in range(11, sample_len, 7):
                tag_id = rawSample.value[i]

                if tag_id not in inputs.tag_ids:
                    inputs.tag_ids.append(int(tag_id))  # TODO: Is this an int always

                # Pose contents:
                # - Timestamp, based on server timestamp of publish and latency
                # - 3D pose estimate
                # - Ambiguity, using only the first tag because ambiguity isn't applicable for multitag
                # - Tag Count
                # - Average tag distance
                # - Observation type
                #
                inputs.pose_observations.append(
                    PoseObservation(
                        rawSample.time * 1.0e-6 - rawSample.value[6] * 1.0e-3,
                        self.parse_pose(rawSample.value),
                        rawSample.value[17] if sample_len >= 18 else 0.0,
                        int(rawSample.value[7]),
                        rawSample.value[9],
                        PoseObservationType.MEGATAG_1,
                    )
                )

        for rawSample in self.megatag2_subscriber.read_queue():
            sample_len = len(rawSample.value)
            if sample_len == 0:
                continue

            # TODO: Where in the heck does 11 come from and the increment by 7
            for i in range(11, sample_len, 7):
                tag_id = rawSample.value[i]

                if tag_id not in inputs.tag_ids:
                    inputs.tag_ids.append(int(tag_id))  # TODO: Is this an int always

                inputs.pose_observations.append(
                    PoseObservation(
                        rawSample.time * 1.0e-6 - rawSample.value[6] * 1.0e-3,
                        self.parse_pose(rawSample.value),
                        0.0,
                        int(rawSample.value[7]),
                        rawSample.value[9],
                        PoseObservationType.MEGATAG_2,
                    )
                )

    @staticmethod
    def parse_pose(raw_limlight_array: list[float]) -> Pose3d:
        """
        Parses the 3D pose from a Limelight botpose array
        """
        return Pose3d(
            raw_limlight_array[0],
            raw_limlight_array[1],
            raw_limlight_array[2],
            Rotation3d(
                degrees_to_radians(raw_limlight_array[3]),
                degrees_to_radians(raw_limlight_array[4]),
                degrees_to_radians(raw_limlight_array[5]),
            ),
        )

    def update_sim(self, now: float, tm_diff: float) -> None:
        """
        Called when the simulation parameters for the program need to be updated.
        This function is called from the '_simulationPeriodic' function of the
        robotpy core routine and is called at a period >= 10 mS. Note that the
        CommandScheduler also has an 'simulation_periodic' function that it calls
        into all Command2 based subsystems at its update period which has a
        default rate of 20 mS.

        This is called 'after' the CommandScheduler's 'simulation_periodic', so if
        that function uses pykit's logging method, you should use those values in
        your simulation.

        :param now:     The current time as a float
        :param tm_diff: The amount of time that has passed since the last
                        time that this function was called
        """
        super().update_sim(now, tm_diff)  # TODO: Can we do anything here to support limelight simulation
