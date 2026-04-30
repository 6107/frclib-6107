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
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Iterable, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EventStartEndTime:
    """
    Represents a time range for an event or competition.

    This dataclass encapsulates a start and end time for an event, ensuring
    immutability through the frozen=True parameter. Both datetime objects
    must include timezone information.

    Attributes:
        start_time (datetime): The start time of the event. Must have timezone info.
        end_time (datetime): The end time of the event. Must have timezone info.

    Example:
        >>> from datetime import datetime, timezone
        >>> start = datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)
        >>> end = datetime(2026, 4, 27, 15, 0, 0, tzinfo=timezone.utc)
        >>> event_time = EventStartEndTime(start, end)
    """
    start_time: datetime
    end_time: datetime

class Event:
    """
    Represents a single event or competition with associated time ranges.

    An event can have one or more time spans defined by EventStartEndTime objects.
    All datetime objects must include timezone information, as the evaluation is done
    in the timezone of the RoboRIO.

    Note: Start times should be set before turning on the robot for the first time.

    Attributes:
        title (str): The title of the event.
        dates (EventStartEndTime | Tuple[EventStartEndTime, ...]): The time ranges for the event.
        active (bool): Whether the current time is within any of the event's time ranges.
    """
    def __init__(self, title: str, dates: EventStartEndTime | Iterable[EventStartEndTime]) -> None:
        self._title = title

        if isinstance(dates, EventStartEndTime):
            dates = [dates]

        self._dates: Tuple[EventStartEndTime, ...] = tuple(dates)
        self._validate_date_times()

    @property
    def title(self) -> str:
        """
        Returns the title of the event.

        Returns:
            str: The event title.
        """
        return str(self._title)

    @property
    def dates(self) -> Tuple[EventStartEndTime, ...]:
        return self._dates

    @property
    def active(self) -> bool:
        """
        Checks if the current UTC time is within any of the event's time ranges.

        Returns:
            bool: True if the event is currently active, False otherwise.
        """
        now = datetime.now(timezone.utc)
        return any(dt.start_time <= now <= dt.end_time for dt in self._dates)

    def _validate_date_times(self) -> None:
        """
        Check what was provided. Make sure start < end for each time and has a timezone defined.
        """

        def has_timezone(dt_object: datetime):
            """
            Checks if a datetime object has a timezone defined
            """
            return dt_object.tzinfo is not None

        for index, date in enumerate(self._dates):
            if not has_timezone(date.start_time):
                raise ValueError(f"Start time {index} of {self.title} Does not " 
                                 f"have a timezone defined: {date.start_time}")

            if not has_timezone(date.end_time):
                raise ValueError(f"End time {index} of {self.title} Does not " 
                                 f"have a timezone defined: {date.start_time}")

            if date.start_time >= date.end_time:
                raise ValueError("Start > End for item {index} of "   
                                 f"{self.title}. {date.start_time} >= {date.end_time}")

###############################################################################################
# Track the competitions here
__events: Deque[Event] = deque()


def add_event(competition: Event):
    """
    Add an event/competition to the list of events.
    """
    __events.append(competition)


def event_active() -> bool:
    """
    Is a registered event or competition active?
    """
    return any(event.active for event in __events)


competition_active = event_active  # Events and completions are the same
add_competition = add_event  # Events and completions are the same
