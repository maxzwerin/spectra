import colorsys
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config
from calendars import Calendar, Event, at

SIZE = (800, 480)
DAYS = 4
MARGIN = 14
COL_W = (SIZE[0] - 2 * MARGIN) // DAYS
TOP, BOTTOM = 124, 470
MORE_H = 22
FONTS = Path(__file__).parent / "fonts"

# Pure colors the panel is asked for. The order matches the original 7.3" driver's
# palette indices; the newer (Spectra 6) driver matches by RGB value instead.
INK = {"black": (0, 0, 0), "white": (255, 255, 255), "green": (0, 255, 0),
       "blue": (0, 0, 255), "red": (255, 0, 0), "yellow": (255, 255, 0)}

EVENT_INKS = ("blue", "green", "red", "yellow", "black")
HUES = {"red": 0, "yellow": 55, "green": 130, "blue": 230}


@lru_cache
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "Bold" if bold else "Regular"
    return ImageFont.truetype(str(FONTS / f"FiraSans-{name}.ttf"), size)


def put(d, xy, text, fnt, ink="black", anchor="la"):
    d.text(xy, text, font=fnt, fill=INK[ink], anchor=anchor)


def wrap(text: str, fnt, width: int, max_lines: int) -> list[str]:
    """Word-wrap `text` to `width` pixels, ending with an ellipsis if it doesn't fit."""
    lines, line = [], ""
    for word in text.split():
        if fnt.getlength(f"{line} {word}".strip()) <= width:
            line = f"{line} {word}".strip()
            continue
        if line:
            lines.append(line)
        line = word
        while fnt.getlength(line) > width and len(line) > 1:  # a single over-long word
            cut = len(line) - 1
            while cut > 1 and fnt.getlength(line[:cut]) > width:
                cut -= 1
            lines.append(line[:cut])
            line = line[cut:]
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and fnt.getlength(last + "…") > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


# ------------------------------------------------------------ calendar colors

def hue_gap(hex_color: str, ink: str) -> float:
    """How far a Google color is from a panel color (lower = closer)."""
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, sat, _ = colorsys.rgb_to_hsv(r, g, b)
    if ink == "black":
        return 0 if sat < 0.2 else 200  # greys go to black, anything else only as a last resort
    if sat < 0.2:
        return 300
    gap = abs(hue * 360 - HUES[ink])
    return min(gap, 360 - gap)


def assign_inks(calendars: list[Calendar]) -> dict[str, str]:
    inks = {}
    used = set(inks.values())
    for cal in calendars:
        if cal.id in inks:
            continue
        if len(used) >= len(EVENT_INKS):
            used = set()  # every color taken: start a second round
        free = [ink for ink in EVENT_INKS if ink not in used]
        inks[cal.id] = min(free, key=lambda ink: hue_gap(cal.color, ink))
        used.add(inks[cal.id])
    return inks


def text_on(ink: str) -> str:
    return "black" if ink == "yellow" else "white"  # yellow is the only fill light enough for black text


def key(d, x, cy, name, ink):
    """Legend entry: a color swatch and a calendar name, vertically centred on `cy`."""
    d.rounded_rectangle((x, cy - 7, x + 14, cy + 7), 3, fill=INK[ink], outline=INK["black"], width=2)
    put(d, (x + 20, cy), name, font(14), "black", "lm")


# ------------------------------------------------------------------- events

def clock(t: datetime) -> str:
    if config.CLOCK_24H:
        return t.strftime("%H:%M")
    minutes = f":{t.minute:02d}" if t.minute else ""
    return f"{t.hour % 12 or 12}{minutes}{'a' if t.hour < 12 else 'p'}"


def span(e: Event) -> str:
    return clock(e.start) if e.end <= e.start else f"{clock(e.start)} – {clock(e.end)}"


def on_day(events: list[Event], day: date) -> list[Event]:
    start, end = at(day), at(day + timedelta(days=1))
    shown = [e for e in events if e.start < end and e.end > start]
    return sorted(shown, key=lambda e: (not e.all_day, e.start))


def event_item(e: Event, ink: str, width: int):
    """(height, paint) for one event: a filled chip if it's all-day, else a color bar beside its time and title."""
    if e.all_day:
        lines = wrap(e.title, font(16, True), width - 16, 2)

        def paint(d, x, y):
            d.rounded_rectangle((x, y, x + width, y + 10 + 19 * len(lines)), 8, fill=INK[ink])
            for n, line in enumerate(lines):
                put(d, (x + 8, y + 5 + 19 * n), line, font(16, True), text_on(ink))
        return 10 + 19 * len(lines), paint

    lines = wrap(e.title, font(18), width - 16, 2)

    def paint(d, x, y):
        d.rectangle((x, y + 1, x + 5, y + 19 + 21 * len(lines)), fill=INK[ink])
        put(d, (x + 13, y), span(e), font(15, True))
        for n, line in enumerate(lines):
            put(d, (x + 13, y + 19 + 21 * n), line, font(18))
    return 22 + 21 * len(lines), paint


def stack(d, x, top, bottom, gap, items):
    """Place (height, paint) items downwards; say how many were left out if they don't fit."""
    y = top
    for i, (height, paint) in enumerate(items):
        room = bottom - (0 if i == len(items) - 1 else MORE_H)
        if y + height > room:
            put(d, (x + 4, y), f"+{len(items) - i} more", font(14, True))
            return
        paint(d, x, y)
        y += height + gap


# -------------------------------------------------------------------- layout

def heading(first: date, last: date) -> str:
    if first.month == last.month:
        return f"{first:%B %Y}"
    if first.year == last.year:
        return f"{first:%B} - {last:%B %Y}"
    return f"{first:%B %Y} - {last:%B %Y}"


def draw_heading(d, days: list[date], calendars: list[Calendar], inks: dict[str, str]):
    put(d, (MARGIN, 10), heading(days[0], days[-1]), font(24, True))
    if len(calendars) < 2:
        return
    names = [wrap(c.name, font(14), 90, 1)[0] for c in calendars]
    widths = [20 + font(14).getlength(n) + 16 for n in names]
    while sum(widths) > SIZE[0] - 2 * MARGIN - 300:  # legend, right-aligned; what doesn't fit is left out
        names.pop()
        widths.pop()
    x = SIZE[0] - MARGIN + 16 - sum(widths)
    for cal, name, width in zip(calendars, names, widths):
        key(d, x, 25, name, inks[cal.id])
        x += width


def draw_day(d, i: int, day: date, events: list[Event], inks: dict[str, str]):
    x = MARGIN + i * COL_W
    ink = "black"
    if i == 0:  # today
        d.rounded_rectangle((x + 2, 46, x + COL_W - 2, 112), 12, fill=INK["black"])
        ink = "white"
    put(d, (x + COL_W // 2, 52), f"{day:%A}".upper(), font(15, True), ink, "ma")
    put(d, (x + COL_W // 2, 70), str(day.day), font(34, True), ink, "ma")

    if i:  # dotted divider
        for y in range(TOP - 2, BOTTOM, 8):
            d.line((x, y, x, y + 2), fill=INK["black"])
    stack(d, x + 6, TOP, BOTTOM, 6, [event_item(e, inks[e.calendar], COL_W - 16) for e in events])


def render(today: date, events: list[Event], calendars: list[Calendar]) -> Image.Image:
    """The finished screen as a palette image (see INK), ready for the display."""
    days = [today + timedelta(days=n) for n in range(DAYS)]
    inks = assign_inks(calendars)
    img = Image.new("RGB", SIZE, INK["white"])
    d = ImageDraw.Draw(img)
    draw_heading(d, days, calendars, inks)
    for i, day in enumerate(days):
        draw_day(d, i, day, on_day(events, day), inks)

    palette = Image.new("P", (1, 1))
    palette.putpalette([channel for rgb in INK.values() for channel in rgb])
    return img.quantize(palette=palette, dither=Image.Dither.NONE)  # snap anti-aliasing to pure colors
