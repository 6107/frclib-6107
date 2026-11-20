"""Unit tests for FieldSource / load_layout."""

import shutil
from pathlib import Path

import pytest
from wpimath import Pose3d

from lib_6107.field.layout import FieldLayout, FieldTag
from lib_6107.field.sources import DEPLOY_SUBDIRECTORY, FieldSource, load_layout

DATA = Path(__file__).parent / "data"


@pytest.fixture
def deploy_dir(tmp_path):
    target = tmp_path / DEPLOY_SUBDIRECTORY
    target.mkdir(parents=True)
    shutil.copy(DATA / "legacy_layout.json", target / "legacy_layout.json")
    return tmp_path


def _factory_layout():
    return FieldLayout("Factory", 10.0, 5.0, tags=[FieldTag(1, Pose3d())])


def test_key_is_required():
    with pytest.raises(ValueError):
        FieldSource(key="", name="x")


def test_factory_wins_over_everything(deploy_dir):
    src = FieldSource("a", "A", field_id=object(), deploy_file="legacy_layout.json", factory=_factory_layout)
    assert load_layout(src, deploy_dir).name == "Factory"


def test_failing_factory_falls_through(deploy_dir):
    def boom():
        raise RuntimeError("nope")

    src = FieldSource("a", "A", deploy_file="legacy_layout.json", factory=boom)
    assert load_layout(src, deploy_dir).name == "legacy_layout"


def test_library_id_used_before_file(deploy_dir):
    robotpy_fields = pytest.importorskip("robotpy_fields")
    src = FieldSource(
        "w", "Welded", field_id=robotpy_fields.FieldId.FRC_2026_REBUILT_WELDED, deploy_file="legacy_layout.json"
    )
    layout = load_layout(src, deploy_dir)
    assert len(layout) == 32


def test_bad_library_id_falls_back_to_file(deploy_dir):
    src = FieldSource("a", "A", field_id="not-a-field-id", deploy_file="legacy_layout.json")
    layout = load_layout(src, deploy_dir)
    assert layout is not None and layout.tag_ids == [1, 2]


def test_everything_fails_returns_none(tmp_path):
    assert load_layout(FieldSource("a", "A", field_id="bad", deploy_file="missing.json"), tmp_path) is None
    assert load_layout(FieldSource("a", "A"), tmp_path) is None


def test_missing_deploy_directory_does_not_raise(tmp_path):
    src = FieldSource("a", "A", deploy_file="legacy_layout.json")
    assert load_layout(src, tmp_path / "does-not-exist") is None


def test_default_deploy_directory_is_used(monkeypatch, deploy_dir):
    monkeypatch.setattr("wpilib.get_deploy_directory", lambda: str(deploy_dir))
    assert load_layout(FieldSource("a", "A", deploy_file="legacy_layout.json")) is not None
