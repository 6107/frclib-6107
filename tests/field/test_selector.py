"""Unit tests for FieldSelector (with an injected chooser)."""

from lib_6107.field.selector import FieldSelector
from lib_6107.field.sources import FieldSource


class FakeChooser:
    def __init__(self, name):
        self.name = name
        self.default = None
        self.options = {}
        self.selected = None

    def set_default_option(self, name, value):
        self.default = (name, value)

    def add_option(self, name, value):
        self.options[name] = value

    def get_selected(self):
        return self.selected


def _make():
    chooser = FakeChooser("x")
    sources = [FieldSource("w", "Welded"), FieldSource("am", "AndyMark")]
    selector = FieldSelector(sources, "w", chooser_factory=lambda name: chooser)
    return chooser, selector


def test_registers_options():
    chooser, _ = _make()
    assert chooser.default == ("Welded", "w")
    assert chooser.options == {"AndyMark": "am"}


def test_poll_reports_only_changes():
    chooser, selector = _make()
    assert selector.poll() is None  # nothing selected yet

    chooser.selected = "w"
    assert selector.poll() is None  # still default

    chooser.selected = "am"
    assert selector.poll() == "am"
    assert selector.poll() is None  # only reported once

    chooser.selected = "w"
    assert selector.poll() == "w"
