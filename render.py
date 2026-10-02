from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config
from calendars import Calendar, Event, at

import fontpkg

FIRA_DIR = Path(fontpkg.path("Fira Sans")).parent
SERIF_PATH = fontpkg.path("Instrument Serif")

SIZE = (800, 480)
DAYS = 4

INK = {"black": (0, 0, 0), "white": (255, 255, 255), "green": (0, 255, 0), "blue": (0, 0, 255), "red": (255, 0, 0), "yellow": (255, 255, 0)}


LAYOUT = {
    "margin": 14,             # left/right page margin
    "header_height": 80,      # page header (month + legend); day headers start below it
    "day_header_height": 70,  # day name + number block; events start below it
    "bottom_margin": 10,      # space left under the event area
    "event_gap": 6,           # vertical space between events in a column
    "column_inset": 6,        # gap between a column divider and the events on either side of it
    "day_number_offset": 10,  # day number sits this far below the day name
    "more_height": 22,        # room reserved for the "+N more" label
    "more_inset": 4,          # left padding of the "+N more" label
}

FONT_SIZE = {
    "month": 64,
    "day_name": 15,
    "day_number": 42,
    "event_title": 15,
    "event_time": 14,
    "more": 14,
    "legend": 14,
}

DIVIDER = {
    "period": 8,    # distance from one dash to the next
    "dash": 2,      # length of one dash
}

EVENT = {
    "all_day_line_height": 19,
    "all_day_pad_x": 8,
    "all_day_pad_y": 5,
    "timed_line_height": 19,
    "timed_pad_y": 1,       # extra height below the time line
    "bar_width": 5,
    "bar_top_inset": 0,
    "bar_bottom_inset": 3,
    "text_indent": 12,      # text starts this far right of the bar's left edge
    "max_lines": 2,
    "compact_max_lines": 1,
}

LEGEND = {
    "swatch": 14,
    "swatch_radius": 3,
    "swatch_outline": 2,
    "swatch_text_gap": 6,
    "item_gap": 16,
    "name_max_width": 90,
    "reserved_width": 300,
    "center_y": 12,
}

COLUMN_WIDTH = (SIZE[0] - 2 * LAYOUT["margin"]) // DAYS
EVENT_WIDTH = COLUMN_WIDTH - 2 * LAYOUT["column_inset"]
EVENTS_TOP = LAYOUT["header_height"] + LAYOUT["day_header_height"]
EVENTS_BOTTOM = SIZE[1] - LAYOUT["bottom_margin"]


@lru_cache
def serif(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(SERIF_PATH), size)

@lru_cache
def sans(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Bold" if bold else "Regular"
    return ImageFont.truetype(str(FIRA_DIR / f"FiraSans-{name}.ttf"), size)


def draw_text(d, xy, text, fnt, ink="black", anchor="la"):
    d.text(xy, text, font=fnt, fill=INK[ink], anchor=anchor)


def wrap(text: str, fnt, width: int, max_lines: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if fnt.getlength(candidate) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and fnt.getlength(last + "…") > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def column_x(index: int) -> int:
    return LAYOUT["margin"] + index * COLUMN_WIDTH


def text_on(ink: str) -> str:
    return "black" if ink == "yellow" else "white"


def clock_parts(t: datetime) -> tuple[str, str]:
    minutes = f":{t.minute:02d}" if t.minute else ""
    return f"{t.hour % 12 or 12}{minutes}", ("am" if t.hour < 12 else "pm")


def clock(t: datetime) -> str:
    if config.CLOCK_24H:
        return t.strftime("%H:%M")
    number, period = clock_parts(t)
    return f"{number}{period}"


def span(e: Event) -> str:
    if e.end <= e.start:
        return clock(e.start)
    if config.CLOCK_24H:
        return f"{clock(e.start)}-{clock(e.end)}"
    start_num, start_period = clock_parts(e.start)
    end_num, end_period = clock_parts(e.end)
    if start_period == end_period:
        return f"{start_num}-{end_num}{end_period}"
    return f"{start_num}{start_period}-{end_num}{end_period}"


def overlaps(e: Event, day: date) -> bool:
    return e.start < at(day + timedelta(days=1)) and e.end > at(day)


def timed_on_day(events: list[Event], day: date) -> list[Event]:
    return sorted((e for e in events if not e.all_day and overlaps(e, day)), key=lambda e: e.start)


def event_item(e: Event, max_lines: int, columns: int = 1):
    title_font = sans(FONT_SIZE["event_title"], bold=True)

    if e.all_day:
        line_h, pad_x, pad_y = EVENT["all_day_line_height"], EVENT["all_day_pad_x"], EVENT["all_day_pad_y"]
        lines = wrap(e.title, title_font, EVENT_WIDTH - 2 * pad_x, max_lines)
        height = 2 * pad_y + line_h * len(lines)
        box_width = EVENT_WIDTH + (columns - 1) * COLUMN_WIDTH

        def paint(d, x, y):
            d.rectangle((x, y, x + box_width, y + height), fill=INK[e.ink])
            for n, line in enumerate(lines):
                draw_text(d, (x + pad_x, y + pad_y + line_h * n), line, title_font, text_on(e.ink))
        return height, paint

    line_h = EVENT["timed_line_height"]
    lines = wrap(e.title, title_font, EVENT_WIDTH - EVENT["text_indent"], max_lines)
    height = line_h * (len(lines) + 1) + EVENT["timed_pad_y"]

    def paint(d, x, y):
        bar = (x, y + EVENT["bar_top_inset"], x + EVENT["bar_width"], y + height - EVENT["bar_bottom_inset"])
        d.rectangle(bar, fill=INK[e.ink])
        text_x = x + EVENT["text_indent"]
        for n, line in enumerate(lines):
            draw_text(d, (text_x, y + line_h * n), line, title_font)
        draw_text(d, (text_x, y + line_h * len(lines)), span(e), sans(FONT_SIZE["event_time"]))
    return height, paint


def all_day_rows(events: list[Event], days: list[date], max_lines: int) -> list[list]:
    spans = []
    for e in events:
        if not e.all_day:
            continue
        cols = [i for i, day in enumerate(days) if overlaps(e, day)]
        if cols:
            spans.append((cols[0], cols[-1], e))
    spans.sort(key=lambda s: (s[0], s[0] - s[1], s[2].start))  # earliest first, longest first

    rows, last_used = [], []
    for first, last, e in spans:
        row = next((r for r, end in enumerate(last_used) if end < first), None)
        if row is None:
            row = len(rows)
            rows.append([])
            last_used.append(-1)
        rows[row].append((first, last, event_item(e, max_lines, last - first + 1)))
        last_used[row] = last
    return rows


def column_tops(rows: list[list], row_heights: list[int]) -> list[int]:
    tops = [EVENTS_TOP] * DAYS
    y = EVENTS_TOP
    for row, height in zip(rows, row_heights):
        y += height + LAYOUT["event_gap"]
        for first, last, _ in row:
            for col in range(first, last + 1):
                tops[col] = y
    return tops


def fits(items: list, gap: int, available: int) -> bool:
    if not items:
        return True
    return sum(h for h, _ in items) + gap * (len(items) - 1) <= available


def stack(d, x: int, items: list, top: int):
    gap = LAYOUT["event_gap"]
    y = top
    for i, (height, paint) in enumerate(items):
        is_last = i == len(items) - 1
        room = EVENTS_BOTTOM - (0 if is_last else LAYOUT["more_height"])
        if y + height > room:
            label = f"+{len(items) - i} more"
            draw_text(d, (x + LAYOUT["more_inset"], y), label, sans(FONT_SIZE["more"], bold=True))
            return
        paint(d, x, y)
        y += height + gap


def heading_text(first: date, last: date) -> str:
    if first.month == last.month:
        return f"{first:%b %Y}".upper()
    if first.year == last.year:
        return f"{first:%b}-{last:%b %Y}"
    return f"{first:%b %Y}-{last:%b %Y}"


def draw_legend_key(d, x: int, cy: int, name: str, ink: str):
    size = LEGEND["swatch"]
    half = size // 2
    d.rounded_rectangle((x, cy - half, x + size, cy + half), LEGEND["swatch_radius"],
                        fill=INK[ink], outline=INK["black"], width=LEGEND["swatch_outline"])
    text_x = x + size + LEGEND["swatch_text_gap"]
    draw_text(d, (text_x, cy), name, sans(FONT_SIZE["legend"]), "black", "lm")


def draw_legend(d, calendars: list[Calendar]):
    font = sans(FONT_SIZE["legend"])
    chrome = LEGEND["swatch"] + LEGEND["swatch_text_gap"] + LEGEND["item_gap"]
    names = [wrap(c.name, font, LEGEND["name_max_width"], 1)[0] for c in calendars]
    widths = [chrome + font.getlength(n) for n in names]
    available = SIZE[0] - 2 * LAYOUT["margin"] - LEGEND["reserved_width"]
    while sum(widths) > available:
        names.pop()
        widths.pop()
    # The last item's trailing gap hangs past the margin so its text lines up with it.
    x = SIZE[0] - LAYOUT["margin"] + LEGEND["item_gap"] - sum(widths)
    for cal, name, width in zip(calendars, names, widths):
        draw_legend_key(d, x, LEGEND["center_y"], name, cal.ink)
        x += width


def draw_page_header(d, days: list[date], calendars: list[Calendar]):
    draw_text(d, (LAYOUT["margin"], 0), heading_text(days[0], days[-1]), serif(FONT_SIZE["month"]))
    if len(calendars) >= 2:
        draw_legend(d, calendars)


def draw_day_headers(d, days: list[date]):
    number_y = LAYOUT["header_height"] + LAYOUT["day_number_offset"]
    for i, day in enumerate(days):
        center = column_x(i) + COLUMN_WIDTH // 2
        draw_text(d, (center, LAYOUT["header_height"]), f"{day:%A}".upper(),
                  sans(FONT_SIZE["day_name"], bold=True), anchor="ma")
        draw_text(d, (center, number_y), str(day.day), serif(FONT_SIZE["day_number"]), anchor="ma")


def draw_event_grid(d):
    start = EVENTS_TOP
    for i in range(1, DAYS):
        x = column_x(i)
        for y in range(start, EVENTS_BOTTOM, DIVIDER["period"]):
            d.line((x, y, x, y + DIVIDER["dash"]), fill=INK["black"])


def draw_events(d, days: list[date], events: list[Event]):
    gap = LAYOUT["event_gap"]
    inset = LAYOUT["column_inset"]

    for max_lines in (EVENT["max_lines"], EVENT["compact_max_lines"]):
        rows = all_day_rows(events, days, max_lines)
        row_heights = [max(h for _, _, (h, _) in row) for row in rows]
        tops = column_tops(rows, row_heights)
        timed = [[event_item(e, max_lines) for e in timed_on_day(events, day)] for day in days]
        if all(fits(items, gap, EVENTS_BOTTOM - top) for items, top in zip(timed, tops)):
            break  # if even compact doesn't fit, stack() adds "+N more"

    y = EVENTS_TOP
    for row, height in zip(rows, row_heights):
        for first, _, (_, paint) in row:
            paint(d, column_x(first) + inset, y)
        y += height + gap

    for i, (items, top) in enumerate(zip(timed, tops)):
        stack(d, column_x(i) + inset, items, top)


def render(today: date, events: list[Event], calendars: list[Calendar]) -> Image.Image:
    days = [today + timedelta(days=n) for n in range(DAYS)]
    img = Image.new("RGB", SIZE, INK["white"])
    d = ImageDraw.Draw(img)

    draw_page_header(d, days, calendars)
    draw_day_headers(d, days)
    draw_event_grid(d)
    draw_events(d, days, events)

    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for rgb in INK.values() for channel in rgb])
    return img.quantize(palette=palette, dither=Image.Dither.NONE)
