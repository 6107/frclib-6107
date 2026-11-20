"""Unit tests for FieldLayout / FieldTag."""

import json
import math
from pathlib import Path

import pytest
from wpimath import Pose3d, Rotation3d

from lib_6107.field.coordinates import FieldCoordinates
from lib_6107.field.layout import FieldLayout, FieldTag

DATA = Path(__file__).parent / "data"


def _layout() -> FieldLayout:
    return FieldLayout(
        name="Test",
        length=16.0,
        width=8.0,
        tags=[FieldTag(1, Pose3d(1, 2, 0.5, Rotation3d(0, 0, math.pi))), FieldTag(5, Pose3d(3, 4, 1, Rotation3d()))],
        season="2026",
        game="Rebuilt",
    )


def test_tag_lookup():
    layout = _layout()
    assert layout.tag_ids == [1, 5]
    assert len(layout) == 2
    assert layout.has_tag(1) and not layout.has_tag(2)
    assert layout.get_tag_pose(5).x == pytest.approx(3)
    assert layout.get_tag_pose(99) is None
    assert [t.tag_id for t in layout] == [1, 5]


def test_defaults_and_accepts_mapping():
    layout = FieldLayout("Empty", 1.0, 2.0)
    assert len(layout) == 0
    assert layout.coordinates is FieldCoordinates.BLUE_ORIGIN_2026

    mapped = FieldLayout("Mapped", 1.0, 2.0, tags={7: FieldTag(7, Pose3d())})
    assert mapped.has_tag(7)


def test_duplicate_ids_keep_last():
    layout = FieldLayout("Dup", 1, 1, tags=[FieldTag(1, Pose3d(1, 0, 0, Rotation3d())), FieldTag(1, Pose3d(2, 0, 0, Rotation3d()))])
    assert len(layout) == 1
    assert layout.get_tag_pose(1).x == pytest.approx(2)


def test_layout_is_immutable():
    layout = _layout()
    with pytest.raises(TypeError):
        layout.tags[9] = FieldTag(9, Pose3d())  # read-only mapping
    with pytest.raises(AttributeError):
        layout.name = "other"  # frozen


def test_from_field_id_rebuilt_welded():
    robotpy_fields = pytest.importorskip("robotpy_fields")
    layout = FieldLayout.from_field_id(robotpy_fields.FieldId.FRC_2026_REBUILT_WELDED)

    assert len(layout) == 32
    assert layout.length == pytest.approx(16.541)
    assert layout.width == pytest.approx(8.069)
    assert layout.season == "2026"
    assert layout.get_tag_pose(1).x == pytest.approx(11.87798, abs=1e-4)


def test_from_robotpy_field_matches_library_tag_poses():
    robotpy_fields = pytest.importorskip("robotpy_fields")
    rf_field = robotpy_fields.get_field(robotpy_fields.FieldId.FRC_2026_REBUILT_ANDY_MARK)
    layout = FieldLayout.from_robotpy_field(rf_field)

    for tag_id in layout.tag_ids:
        expected = rf_field.get_tag_pose(tag_id)
        assert layout.get_tag_pose(tag_id).translation().distance(expected.translation()) < 1e-9


def test_from_legacy_json():
    layout = FieldLayout.from_json(DATA / "legacy_layout.json")

    assert layout.name == "legacy_layout"  # no name in legacy files; derived from the file name
    assert (layout.length, layout.width) == (16.0, 8.0)
    assert layout.tag_ids == [1, 2]
    assert layout.get_tag_pose(1).rotation().z == pytest.approx(math.pi)
    assert layout.get_tag_pose(2).z == pytest.approx(1.0)


def test_json_round_trip(tmp_path):
    layout = _layout()
    path = tmp_path / "out.json"
    text = layout.to_json(path)

    assert json.loads(text)["field-dimensions"] == {"length": 16.0, "width": 8.0}
    again = FieldLayout.from_json(path)

    assert again.name == "Test" and again.season == "2026" and again.game == "Rebuilt"
    assert again.tag_ids == layout.tag_ids
    for tag_id in layout.tag_ids:
        a, b = layout.get_tag_pose(tag_id), again.get_tag_pose(tag_id)
        assert a.translation().distance(b.translation()) < 1e-9
        assert a.rotation().z == pytest.approx(b.rotation().z)


def test_to_robotpy_field():
    pytest.importorskip("robotpy_fields")
    rf_field = _layout().to_robotpy_field()

    assert rf_field.get_length() == pytest.approx(16.0)
    assert rf_field.get_tag_pose(5).y == pytest.approx(4)
    assert rf_field.get_tag_pose(99) is None


def test_coordinates_are_passed_through(tmp_path):
    layout = FieldLayout.from_json(DATA / "legacy_layout.json", coordinates=FieldCoordinates.BLUE_ORIGIN_2026)
    assert layout.coordinates is FieldCoordinates.BLUE_ORIGIN_2026


def test_from_json_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        FieldLayout.from_json(tmp_path / "missing.json")

    bad = tmp_path / "bad.json"
    bad.write_text("{ not json")
    with pytest.raises(ValueError, match="not valid JSON"):
        FieldLayout.from_json(bad)

    not_obj = tmp_path / "list.json"
    not_obj.write_text("[]")
    with pytest.raises(ValueError):
        FieldLayout.from_json(not_obj)

    missing = tmp_path / "missing_data.json"
    missing.write_text('{"name": "x"}')
    with pytest.raises(ValueError, match="invalid or missing"):
        FieldLayout.from_json(missing)

    zero_q = tmp_path / "zero_q.json"
    zero_q.write_text(
        json.dumps(
            {
                "field": {"length": 1, "width": 1},
                "tags": [
                    {
                        "ID": 1,
                        "pose": {
                            "translation": {"x": 0, "y": 0, "z": 0},
                            "rotation": {"quaternion": {"W": 0, "X": 0, "Y": 0, "Z": 0}},
                        },
                    }
                ],
            }
        )
    )
    with pytest.raises(ValueError):
        FieldLayout.from_json(zero_q)
