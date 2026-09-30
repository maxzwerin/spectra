from dataclasses import dataclass
from datetime import date, datetime, time
import re
from urllib.parse import urlparse
import emoji
import config


@dataclass
class Calendar:
    id: str
    name: str
    color: str


@dataclass
class Event:
    title: str
    start: datetime # timezone-aware, local time
    end: datetime
    all_day: bool
    calendar: str # Calendar.id


def at(day: date, hour: int = 0, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute)).astimezone()


def clean(text: str) -> str:
    text = emoji.replace_emoji(text, replace="")
    return re.sub(r"\s{2,}", " ", text).strip()


DEFAULT_HEXES = ("#039be5", "#33b679", "#d50000", "#f6bf26")
HEX_FOR_INK = {"blue": "#039be5", "green": "#33b679", "red": "#d50000", "yellow": "#f6bf26", "black": "#616161"}


class ICSFeeds:
    def events(self, first: date, end: date) -> tuple[list[Event], list[Calendar]]:
        import requests
        import recurring_ical_events
        from icalendar import Calendar as ICalendar

        found, calendars = [], []

        for n, feed in enumerate(config.ICS_FEEDS):

            forced = feed.get("color") or None
            hex_color = HEX_FOR_INK.get(forced, DEFAULT_HEXES[n % len(DEFAULT_HEXES)])
            cal = Calendar(feed["url"], clean(feed["name"]), hex_color)
            calendars.append(cal)

            response = requests.get(feed["url"], timeout=30)
            response.raise_for_status()

            parsed = ICalendar.from_ical(response.content)

            for item in recurring_ical_events.of(parsed).between(first, end):
                if str(item.get("STATUS", "")) == "CANCELLED":
                    continue

                start, all_day = ics_when(item["DTSTART"].dt)
                end_, _ = ics_when(item["DTEND"].dt)

                title = clean(str(item.get("SUMMARY", "") or "")) or "(No title)"

                found.append(Event(title, start, end_, all_day, cal.id))

        return found, calendars


def ics_when(value) -> tuple[datetime, bool]:
    if isinstance(value, datetime):
        return value.astimezone(), False
    return at(value), True  # no time means an all-day event
