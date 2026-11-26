"""Additional unit tests for lib_6107.dashboard.elastic_utils."""

import json
from unittest.mock import MagicMock

import pytest
from lib_6107.dashboard import elastic_utils as eu
from lib_6107.dashboard.elastic_utils import Notification, NotificationLevel

MODULE = "lib_6107.dashboard.elastic_utils"


@pytest.fixture
def nt(monkeypatch):
    inst = MagicMock()
    monkeypatch.setattr(f"{MODULE}.NetworkTableInstance.get_default", lambda: inst)
    for name in ("__notification_topic", "__notification_publisher", "__selected_tab_topic", "__selected_tab_publisher"):
        monkeypatch.setattr(eu, name, None, raising=False)
    return inst


def test_notification_defaults():
    n = Notification()
    assert n.level is NotificationLevel.INFO
    assert (n.title, n.description, n.display_time, n.width, n.height) == ("", "", 3000, 350, -1)


def test_send_notification_publishes_json_and_caches(nt):
    pub = nt.get_string_topic.return_value.publish.return_value
    eu.send_notification(Notification(NotificationLevel.ERROR, "T", "D", 5000, 400, 10))
    eu.send_notification(Notification(NotificationLevel.WARNING, "T2", "D2"))
    nt.get_string_topic.assert_called_once_with("/Elastic/RobotNotifications")
    assert pub.set.call_count == 2
    first = json.loads(pub.set.call_args_list[0].args[0])
    assert first == {
        "level": "ERROR",
        "title": "T",
        "description": "D",
        "displayTime": 5000,
        "width": 400,
        "height": 10,
    }


def test_send_notification_swallows_publish_errors(nt, capsys):
    pub = nt.get_string_topic.return_value.publish.return_value
    pub.set.side_effect = RuntimeError("boom")
    eu.send_notification(Notification())
    assert "Error serializing notification" in capsys.readouterr().out


def test_select_tab_and_index(nt):
    pub = nt.get_string_topic.return_value.publish.return_value
    eu.select_tab("Drive")
    eu.select_tab_index(2)
    nt.get_string_topic.assert_called_once_with("/Elastic/SelectedTab")
    assert [c.args[0] for c in pub.set.call_args_list] == ["Drive", "2"]
