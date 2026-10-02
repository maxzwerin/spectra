from dataclasses import dataclass
from datetime import date, datetime, time
import re
import emoji
import config


@dataclass
class Calendar:
    id: str
    name: str
    ink: str


@dataclass
class Event:
    title: str
    start: datetime # timezone-aware, local time
    end: datetime
    all_day: bool
    calendar: str # Calendar.id
    ink: str


def at(day: date, hour: int = 0, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute)).astimezone()


def clean(text: str) -> str:
    text = emoji.replace_emoji(text, replace="")
    return re.sub(r"\s{2,}", " ", text).strip()


DEFAULT_INKS = ("blue", "green", "red", "yellow")
VALID_INKS = {"black", "green", "blue", "red", "yellow"}  # "white" excluded: invisible on the page


class ICSFeeds:
    def events(self, first: date, end: date) -> tuple[list[Event], list[Calendar]]:
        import requests
        import recurring_ical_events
        from icalendar import Calendar as ICalendar

        found, calendars = [], []

        for n, feed in enumerate(config.ICS_FEEDS):

            forced = feed.get("color") or None
            ink = forced if forced in VALID_INKS else DEFAULT_INKS[n % len(DEFAULT_INKS)]
            cal = Calendar(feed["url"], clean(feed["name"]), ink)
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

                found.append(Event(title, start, end_, all_day, cal.id, cal.ink))

        return found, calendars


def ics_when(value) -> tuple[datetime, bool]:
    if isinstance(value, datetime):
        return value.astimezone(), False
    return at(value), True  # no time means an all-day event
