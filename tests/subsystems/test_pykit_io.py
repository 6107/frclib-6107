"""Smoke tests for the AdvantageKit-style subsystem IO base classes."""

import dataclasses
import importlib
import inspect

import pytest

IO_MODULES = [
    "dual_mechanism_io",
    "gyro_io",
    "robot_state",
    "rotation_mechanism_io",
    "rpm_mechanism_io",
    "swervedrive_io",
    "vision_io",
]


def _io_classes():
    for name in IO_MODULES:
        module = importlib.import_module(f"lib_6107.subsystems.pykit.{name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue
            for _, nested in inspect.getmembers(cls, inspect.isclass):
                if dataclasses.is_dataclass(nested) and nested.__name__.endswith("Inputs"):
                    yield pytest.param(cls, nested, id=f"{name}.{nested.__name__}")


@pytest.mark.parametrize("io_cls, inputs_cls", list(_io_classes()))
def test_inputs_have_defaults_and_base_io_update_is_noop(io_cls, inputs_cls):
    inputs = inputs_cls()
    assert dataclasses.fields(inputs)
    takes_name = "name" in inspect.signature(io_cls.__init__).parameters
    io = io_cls("test") if takes_name else io_cls()
    if takes_name:
        assert io.name == "test"
    assert io.update_inputs(inputs) is None


def test_target_observation_stores_angles():
    from wpimath import Rotation2d

    from lib_6107.subsystems.pykit.vision_io import TargetObservation

    obs = TargetObservation(Rotation2d(0.1), Rotation2d(0.2))
    assert obs.tx.radians() == pytest.approx(0.1)
    assert obs.ty.radians() == pytest.approx(0.2)


def test_pose_observation_stores_fields():
    from wpimath import Pose3d

    from lib_6107.subsystems.pykit.vision_io import PoseObservation, PoseObservationType

    pose = Pose3d()
    obs = PoseObservation(1.5, pose, 0.1, 2, 3.0, PoseObservationType.MEGATAG_2)
    assert (obs.timestamp, obs.ambiguity, obs.tag_count, obs.avg_tag_distance) == (1.5, 0.1, 2, 3.0)
    assert obs.pose is pose
    assert obs.observation_type is PoseObservationType.MEGATAG_2
