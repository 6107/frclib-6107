"""Unit tests for GameField (sources, set/get, callbacks, selector, alliance)."""

import shutil
from pathlib import Path

import pytest
from wpilib import Alliance
from wpimath import Pose3d, Rotation3d, Translation3d

from lib_6107.field.game_field import FieldChange, GameField
from lib_6107.field.layout import FieldLayout, FieldTag
from lib_6107.field.sources import DEPLOY_SUBDIRECTORY, FieldSource

DATA = Path(__file__).parent / "data"


def _layout(name: str, length: float = 10.0, width: float = 5.0, tag_ids=(1, 2)) -> FieldLayout:
    return FieldLayout(name, length, width, tags=[FieldTag(i, Pose3d(Translation3d(float(i), 0.0, 0.0), Rotation3d())) for i in tag_ids])


def _source(key: str, **layout_args) -> FieldSource:
    layout = _layout(key, **layout_args)
    return FieldSource(key, key.title(), factory=lambda: layout)


class FakeSelector:
    def __init__(self):
        self.pending = None

    def poll(self):
        key, self.pending = self.pending, None
        return key


@pytest.fixture
def sources():
    return [_source("a"), _source("b", length=20.0, width=9.0, tag_ids=(7,))]


@pytest.fixture
def game_field(sources):
    return GameField(sources, enable_selector=False, alliance_provider=lambda: Alliance.BLUE)


def test_requires_sources():
    with pytest.raises(ValueError):
        GameField([], enable_selector=False)


def test_duplicate_keys_rejected(sources):
    with pytest.raises(ValueError):
        GameField([sources[0], sources[0]], enable_selector=False)


def test_unknown_default_rejected(sources):
    with pytest.raises(KeyError):
        GameField(sources, default="zzz", enable_selector=False)


def test_first_source_is_default(game_field):
    assert game_field.source.key == "a"
    assert game_field.get_field().key == "a"
    assert game_field.field_length == 10.0
    assert game_field.field_width == 5.0
    assert [t.tag_id for t in game_field.tags] == [1, 2]
    assert game_field.get_tag_pose(2).x == 2.0
    assert game_field.get_tag_pose(99) is None


def test_explicit_default(sources):
    gf = GameField(sources, default="b", enable_selector=False)
    assert gf.source.key == "b"
    assert gf.field_length == 20.0


def test_failed_default_load_uses_fallback_sizes():
    bad = FieldSource("bad", "Bad", deploy_file="missing.json")
    gf = GameField([bad], default_length=16.5, default_width=8.0, enable_selector=False, deploy_dir="nowhere")
    assert gf.layout is None
    assert (gf.field_length, gf.field_width) == (16.5, 8.0)
    assert gf.origin is None
    assert gf.tags == []
    assert gf.get_tag_pose(1) is None


def test_set_field_switches_and_notifies(game_field):
    seen: list[FieldChange] = []
    game_field.register_callback(seen.append)

    assert game_field.set_field("b") is True
    assert game_field.source.key == "b"
    assert game_field.field_length == 20.0
    assert len(seen) == 1
    assert seen[0].previous_source.key == "a"
    assert seen[0].source.key == "b"
    assert seen[0].layout is game_field.layout
    assert seen[0].previous_layout.name == "a"


def test_set_field_same_source_is_noop(game_field):
    seen = []
    game_field.register_callback(seen.append)
    assert game_field.set_field("a") is False
    assert seen == []


def test_set_field_unknown_key(game_field):
    with pytest.raises(KeyError):
        game_field.set_field("nope")


def test_set_field_failed_load_keeps_previous(game_field):
    seen = []
    game_field.register_callback(seen.append)
    bad = FieldSource("bad", "Bad", deploy_file="missing.json")
    assert game_field.set_field(bad) is False
    assert game_field.source.key == "a"
    assert seen == []


def test_set_layout_custom(game_field):
    seen = []
    game_field.register_callback(seen.append)
    custom = _layout("mine", tag_ids=(5,))

    assert game_field.set_layout(custom) is True
    assert game_field.layout is custom
    assert game_field.source.key == "custom"
    assert len(seen) == 1
    assert game_field.set_layout(custom, game_field.source) is False
    assert len(seen) == 1


def test_reload_always_notifies(game_field):
    seen = []
    game_field.register_callback(seen.append)
    assert game_field.reload() is True
    assert game_field.reload() is True
    assert len(seen) == 2


def test_reload_failure_keeps_layout(tmp_path):
    state = {"ok": True}

    def factory():
        if not state["ok"]:
            raise RuntimeError("gone")
        return _layout("x")

    gf = GameField([FieldSource("x", "X", factory=factory)], enable_selector=False, deploy_dir=str(tmp_path))
    before = gf.layout
    state["ok"] = False
    assert gf.reload() is False
    assert gf.layout is before


def test_notify_now_and_unsubscribe(game_field):
    seen = []
    unsubscribe = game_field.register_callback(seen.append, notify_now=True)
    assert len(seen) == 1
    assert seen[0].previous_source is None
    assert seen[0].source.key == "a"

    unsubscribe()
    game_field.set_field("b")
    assert len(seen) == 1

    game_field.unregister_callback(seen.append)  # unknown callbacks ignored


def test_raising_callback_is_isolated(game_field):
    seen = []

    def boom(_):
        raise RuntimeError("bad callback")

    game_field.register_callback(boom)
    game_field.register_callback(seen.append)
    assert game_field.set_field("b") is True
    assert len(seen) == 1


def test_callback_may_unregister_itself(game_field):
    calls = []

    def once(change):
        calls.append(change)
        game_field.unregister_callback(once)

    game_field.register_callback(once)
    game_field.set_field("b")
    game_field.set_field("a")
    assert len(calls) == 1


def test_periodic_applies_selector_choice(sources):
    selector = FakeSelector()
    gf = GameField(sources, selector=selector)
    gf.periodic()
    assert gf.source.key == "a"

    selector.pending = "b"
    gf.periodic()
    assert gf.source.key == "b"


def test_periodic_without_selector_is_safe(game_field):
    game_field.periodic()


def test_alliance_helpers(sources):
    alliance = {"v": Alliance.RED}
    gf = GameField(sources, enable_selector=False, alliance_provider=lambda: alliance["v"])
    assert gf.is_red_alliance and not gf.is_blue_alliance
    alliance["v"] = Alliance.BLUE
    assert gf.is_blue_alliance and not gf.is_red_alliance
    alliance["v"] = None
    assert not gf.is_blue_alliance and not gf.is_red_alliance


def test_zone_hooks_must_be_overridden(game_field):
    with pytest.raises(NotImplementedError):
        game_field.in_blue_alliance_zone(1.0)
    with pytest.raises(NotImplementedError):
        game_field.in_red_alliance_zone(1.0)


def test_deploy_file_source(tmp_path):
    target = tmp_path / DEPLOY_SUBDIRECTORY
    target.mkdir(parents=True)
    shutil.copy(DATA / "legacy_layout.json", target / "legacy_layout.json")
    gf = GameField(
        [FieldSource("legacy", "Legacy", deploy_file="legacy_layout.json")],
        enable_selector=False,
        deploy_dir=str(tmp_path),
    )
    assert gf.layout is not None
    assert len(gf.tags) == 2
