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

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, call

from lib_6107.util.elastic_utils import (
    NotificationLevel,
    Notification,
    send_notification,
    select_tab,
    select_tab_index,
)


class TestNotificationLevel:
    def notification_level_has_info_value(self):
        assert NotificationLevel.INFO.value == "INFO"

    def notification_level_has_warning_value(self):
        assert NotificationLevel.WARNING.value == "WARNING"

    def notification_level_has_error_value(self):
        assert NotificationLevel.ERROR.value == "ERROR"

    def notification_level_members_are_strings(self):
        for member in NotificationLevel:
            assert isinstance(member.value, str)


class TestNotification:
    def notification_with_default_values(self):
        notif = Notification()
        assert notif.level == NotificationLevel.INFO
        assert notif.title == ""
        assert notif.description == ""
        assert notif.display_time == 3000
        assert notif.width == 350
        assert notif.height == -1

    def notification_with_custom_values(self):
        notif = Notification(
            level=NotificationLevel.ERROR,
            title="Test Title",
            description="Test Description",
            display_time=5000,
            width=400,
            height=200,
        )
        assert notif.level == NotificationLevel.ERROR
        assert notif.title == "Test Title"
        assert notif.description == "Test Description"
        assert notif.display_time == 5000
        assert notif.width == 400
        assert notif.height == 200

    def notification_with_empty_strings(self):
        notif = Notification(title="", description="")
        assert notif.title == ""
        assert notif.description == ""

    def notification_with_zero_display_time(self):
        notif = Notification(display_time=0)
        assert notif.display_time == 0

    def notification_with_large_display_time(self):
        notif = Notification(display_time=999999)
        assert notif.display_time == 999999

    def notification_with_zero_width(self):
        notif = Notification(width=0)
        assert notif.width == 0

    def notification_with_negative_width(self):
        notif = Notification(width=-100)
        assert notif.width == -100

    def notification_with_zero_height(self):
        notif = Notification(height=0)
        assert notif.height == 0

    def notification_with_large_height(self):
        notif = Notification(height=1500)
        assert notif.height == 1500

    def notification_partial_custom_values(self):
        notif = Notification(title="Alert", level=NotificationLevel.WARNING)
        assert notif.title == "Alert"
        assert notif.level == NotificationLevel.WARNING
        assert notif.description == ""
        assert notif.display_time == 3000


class TestSendNotification:
    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_publishes_to_networktables(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif = Notification(
            level=NotificationLevel.INFO,
            title="Test",
            description="Test Description",
        )
        send_notification(notif)

        mock_nt_instance.getDefault.assert_called()
        mock_nt_instance.getDefault.return_value.getStringTopic.assert_called_with(
            "/Elastic/RobotNotifications"
        )
        mock_publisher.set.assert_called_once()

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_serializes_to_json(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif = Notification(
            level=NotificationLevel.WARNING,
            title="Warning Title",
            description="Warning Description",
            display_time=5000,
            width=400,
            height=300,
        )
        send_notification(notif)

        call_args = mock_publisher.set.call_args[0][0]
        data = json.loads(call_args)

        assert data["level"] == "WARNING"
        assert data["title"] == "Warning Title"
        assert data["description"] == "Warning Description"
        assert data["displayTime"] == 5000
        assert data["width"] == 400
        assert data["height"] == 300

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_uses_camel_case_keys(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif = Notification(display_time=4000)
        send_notification(notif)

        call_args = mock_publisher.set.call_args[0][0]
        data = json.loads(call_args)

        assert "displayTime" in data
        assert "display_time" not in data

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_with_all_notification_levels(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        for level in NotificationLevel:
            mock_publisher.reset_mock()
            notif = Notification(level=level, title=f"Test {level.value}")
            send_notification(notif)

            call_args = mock_publisher.set.call_args[0][0]
            data = json.loads(call_args)
            assert data["level"] == level.value

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_handles_serialization_error(self, mock_nt_instance, capsys):
        mock_publisher = Mock()
        mock_publisher.set.side_effect = Exception("Serialization error")
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif = Notification(title="Test")
        send_notification(notif)

        captured = capsys.readouterr()
        assert "Error serializing notification" in captured.out

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_initializes_topic_once(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif1 = Notification(title="First")
        notif2 = Notification(title="Second")

        send_notification(notif1)
        send_notification(notif2)

        assert mock_nt_instance.getDefault.return_value.getStringTopic.call_count == 1

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_initializes_publisher_once(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif1 = Notification(title="First")
        notif2 = Notification(title="Second")

        send_notification(notif1)
        send_notification(notif2)

        assert mock_topic.publish.call_count == 1

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def send_notification_with_empty_title_and_description(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        notif = Notification(title="", description="")
        send_notification(notif)

        call_args = mock_publisher.set.call_args[0][0]
        data = json.loads(call_args)

        assert data["title"] == ""
        assert data["description"] == ""


class TestSelectTab:
    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_publishes_tab_name(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Drivetrain")

        mock_publisher.set.assert_called_once_with("Drivetrain")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_publishes_numeric_index(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("0")

        mock_publisher.set.assert_called_once_with("0")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_uses_correct_network_table_topic(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Test")

        mock_nt_instance.getDefault.return_value.getStringTopic.assert_called_with(
            "/Elastic/SelectedTab"
        )

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_initializes_topic_once(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Tab1")
        select_tab("Tab2")

        assert mock_nt_instance.getDefault.return_value.getStringTopic.call_count == 1

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_initializes_publisher_once(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Tab1")
        select_tab("Tab2")

        assert mock_topic.publish.call_count == 1

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_with_empty_string(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("")

        mock_publisher.set.assert_called_once_with("")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_with_special_characters_in_name(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Tab-Name_123")

        mock_publisher.set.assert_called_once_with("Tab-Name_123")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_with_spaces_in_name(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab("Tab Name")

        mock_publisher.set.assert_called_once_with("Tab Name")


class TestSelectTabIndex:
    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_with_zero(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(0)

        mock_publisher.set.assert_called_once_with("0")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_with_positive_integer(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(5)

        mock_publisher.set.assert_called_once_with("5")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_with_large_index(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(999)

        mock_publisher.set.assert_called_once_with("999")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_with_negative_index(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(-1)

        mock_publisher.set.assert_called_once_with("-1")

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_converts_int_to_string(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(3)

        call_args = mock_publisher.set.call_args[0][0]
        assert isinstance(call_args, str)
        assert call_args == "3"

    @patch("lib_6107.util.elastic_utils.NetworkTableInstance")
    def select_tab_index_multiple_calls(self, mock_nt_instance):
        mock_publisher = Mock()
        mock_topic = Mock()
        mock_topic.publish.return_value = mock_publisher
        mock_nt_instance.getDefault.return_value.getStringTopic.return_value = (
            mock_topic
        )

        select_tab_index(0)
        select_tab_index(1)
        select_tab_index(2)

        assert mock_publisher.set.call_count == 3
        calls = [call("0"), call("1"), call("2")]
        mock_publisher.set.assert_has_calls(calls)
