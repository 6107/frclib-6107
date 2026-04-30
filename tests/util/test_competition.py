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
from datetime import datetime, timezone

from lib_6107.util.competition import Event, EventStartEndTime


def event_creation_with_single_date():
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test Event", EventStartEndTime(start, end))
    assert event.title == "Test Event"
    assert len(event.dates) == 1
    assert event.dates[0].start_time == start
    assert event.dates[0].end_time == end


def event_creation_with_multiple_dates():
    dates = [
        EventStartEndTime(datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)),
        EventStartEndTime(datetime(2026, 4, 28, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc))
    ]
    event = Event("Multi Event", dates)
    assert event.title == "Multi Event"
    assert len(event.dates) == 2


def event_active_during_event(monkeypatch):
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test", EventStartEndTime(start, end))
    now = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert event.active


def event_not_active_before_event(monkeypatch):
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test", EventStartEndTime(start, end))
    now = datetime(2026, 4, 27, 9, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert not event.active


def event_not_active_after_event(monkeypatch):
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test", EventStartEndTime(start, end))
    now = datetime(2026, 4, 27, 16, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert not event.active


def event_active_at_start_time(monkeypatch):
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test", EventStartEndTime(start, end))
    now = start
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert event.active


def event_not_active_at_end_time(monkeypatch):
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    event = Event("Test", EventStartEndTime(start, end))
    now = end
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert not event.active


def event_active_in_one_of_multiple_dates(monkeypatch):
    dates = [
        EventStartEndTime(datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)),
        EventStartEndTime(datetime(2026, 4, 28, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc))
    ]
    event = Event("Multi", dates)
    now = datetime(2026, 4, 27, 11, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr('lib_6107.util.competition.datetime', type('MockDatetime', (datetime,), {'now': classmethod(lambda cls, tz=None: now)}))
    assert event.active


def event_creation_fails_without_timezone_on_start():
    start = datetime(2026, 4, 27, 10, 0, 0)  # no tz
    end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Does not have a timezone defined"):
        Event("Test", EventStartEndTime(start, end))


def event_creation_fails_without_timezone_on_end():
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 15, 0, 0)  # no tz
    with pytest.raises(ValueError, match="Does not have a timezone defined"):
        Event("Test", EventStartEndTime(start, end))


def event_creation_fails_with_start_after_end():
    start = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Start > End"):
        Event("Test", EventStartEndTime(start, end))


def event_creation_fails_with_start_equal_end():
    start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
    end = start
    with pytest.raises(ValueError, match="Start > End"):
        Event("Test", EventStartEndTime(start, end))


def event_creation_with_multiple_dates_validates_each():
    dates = [
        EventStartEndTime(datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)),
        EventStartEndTime(datetime(2026, 4, 28, 15, 0, 0, tzinfo=timezone.utc), datetime(2026, 4, 28, 10, 0, 0, tzinfo=timezone.utc))  # invalid
    ]
    with pytest.raises(ValueError):
        Event("Multi", dates)

