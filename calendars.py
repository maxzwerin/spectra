from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
import re
from urllib.parse import quote

import config

HERE = Path(__file__).parent

_EMOJI = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "\U0001F000-\U0001F0FF"
    "\U00002300-\U000023FF"
    "\U00002B00-\U00002BFF"
    "]"
)
_EMOJI_EXTRAS = re.compile("[\uFE0F\u200D\u20E3\U0001F3FB-\U0001F3FF]")


def clean(text: str) -> str:
    text = _EMOJI_EXTRAS.sub("", _EMOJI.sub("", text))
    return re.sub(r"\s{2,}", " ", text).strip()



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


DEFAULT_HEXES = ("#039be5", "#33b679", "#d50000", "#f6bf26")
HEX_FOR_INK = {"blue": "#039be5", "green": "#33b679", "red": "#d50000", "yellow": "#f6bf26", "black": "#616161"}


def _name(entry: dict) -> str:
    return clean(entry.get("summaryOverride") or entry["summary"])


def _order(entry: dict) -> tuple:
    return (not entry.get("primary", False), _name(entry).lower())


def _hidden(item: dict) -> bool:
    me = next((a for a in item.get("attendees", []) if a.get("self")), {})
    return (
        item.get("status") == "cancelled"
        or item.get("eventType") == "workingLocation"
        or me.get("responseStatus") == "declined"
    )


def _when(stamp: dict) -> tuple[datetime, bool]:
    if "date" in stamp:  # all-day events only have a date
        return at(date.fromisoformat(stamp["date"])), True
    return datetime.fromisoformat(stamp["dateTime"].replace("Z", "+00:00")).astimezone(), False


class ICSFeeds:
    def events(self, first: date, end: date) -> tuple[list[Event], list[Calendar]]:
        import requests
        import recurring_ical_events
        from icalendar import Calendar as ICalendar

        found, calendars = [], []

        for feed in config.ICS_FEEDS:

            hex_color = feed.get("color", "black")
            cal = Calendar(feed["url"], clean(feed["name"]), HEX_FOR_INK[hex_color])
            calendars.append(cal)

            response = requests.get(feed["url"], timeout=30)
            response.raise_for_status()

            parsed = ICalendar.from_ical(response.content)

            for item in recurring_ical_events.of(parsed).between(first, end):
                if str(item.get("STATUS", "")) == "CANCELLED":
                    continue

                start, all_day = _ics_when(item["DTSTART"].dt)
                end_, _ = _ics_when(item["DTEND"].dt)

                title = clean(str(item.get("SUMMARY", "") or "")) or "(No title)"

                found.append(Event(title, start, end_, all_day, cal.id))

        return found, calendars


def _ics_when(value) -> tuple[datetime, bool]:
    if isinstance(value, datetime):
        return value.astimezone(), False
    return at(value), True  # no time means an all-day event
