import argparse
from datetime import date, datetime, timedelta

import config
from calendars import ICSFeeds
from devices import InkyDisplay, RefreshButton
from render import DAYS, render

def get_feed():
    if config.ICS_FEEDS:
        return ICSFeeds()
    raise SystemExit("No calendar(s) found. Add a calendar to ICS_FEEDS in config.py")


def seconds_until_next_check() -> float:
    now = datetime.now()
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return min(config.CHECK_MINUTES * 60, (midnight - now).total_seconds() + 5)


def refresh(source, display, shown: bytes | None) -> bytes:
    """ fetch events and draw the picture in memory; only change it differs from current """
    today = date.today()
    events, calendars = source.events(today, today + timedelta(days=DAYS))
    panel = render(today, events, calendars)
    if panel.tobytes() == shown:
        return shown
    display.show(panel)
    return panel.tobytes()


def run(source, display, button):
    shown = None
    while True:
        try:
            shown = refresh(source, display, shown)
            wait = seconds_until_next_check()
        except Exception as error:
            print(f"Update failed, retrying: {error}")
        if button.wait(60):
            print("Button pressed, refreshing now")


def main():
    source = get_feed()

    try:
        run(source, InkyDisplay(), RefreshButton())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
