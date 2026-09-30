# Spectra

A calendar dashboard for a [Pimoroni Inky Impression 7.3"](https://shop.pimoroni.com/products/inky-impression-7-3) e-ink display on a Raspberry Pi. It shows today and the next three days, color-coded by calendar, and stays on screen with no backlight and almost no power draw between updates.

![Preview](preview.png)

## How it works

- **Four days, today first.** The leftmost column is always today, highlighted, followed by the next three days.
- **Pulls from Google Calendar without a sign-in.** Each calendar you add is a "secret address in iCal format" — a private link Google Calendar gives you per calendar. The dashboard fetches it directly over HTTPS. No OAuth, no token that expires, nothing to re-authorize.
- **Color-coded by calendar.** Give each calendar a color in `config.py`, or leave it unset and let one get picked automatically. All-day events are drawn as a solid chip; timed events get a color bar beside the time and title.
- **Checks periodically, redraws only on a change.** It fetches every `CHECK_MINUTES` and compares the picture it would draw against what's already on screen. The panel is only pushed to when something visible is different, since a full e-ink refresh takes 10–30 seconds and visibly flashes.
- **Refreshes instantly on demand.** Press the top button (button A) on the display to force an immediate check and redraw, regardless of the normal check interval.
- **Rolls over at midnight** without waiting for the next scheduled check, so the four days on screen are never stale after midnight.
- **Strips emoji from titles.** The panel's font has no emoji glyphs, so they're removed rather than left as blank boxes.

## Hardware

- Raspberry Pi (tested on a Pi Zero 2 W)
- Pimoroni Inky Impression 7.3"
- A Pi that can reach the internet

## Software setup

### 1. Enable SPI and I2C, and set the timezone

The display and its buttons need these interfaces on, and the timezone needs to be correct or "today" will be wrong:

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config     # Localisation Options -> Timezone
sudo reboot
```

### 2. Get the code and its dependencies

```bash
cd ~/inky
git clone https://github.com/maxzwerin/spectra.git
```

Use the same virtual environment Pimoroni's own examples use (this repo assumes packages are already installed there rather than creating its own):

```bash
source ~/.virtualenvs/pimoroni/bin/activate
pip install -r requirements.txt
pip install inky gpiod gpiodevice
```

### 3. Add the fonts

Fonts aren't checked into the repo. Download Fira Sans and place it in a `fonts/` folder next to `main.py`:

```bash
mkdir -p fonts
curl -sL -o fonts/FiraSans-Regular.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/firasans/FiraSans-Regular.ttf
curl -sL -o fonts/FiraSans-Bold.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/firasans/FiraSans-Bold.ttf
```

### 4. Get your calendars' secret addresses

1. Open [Google Calendar](https://calendar.google.com) on a computer, click the gear icon, then **Settings**.
2. Under "Settings for my calendars", click the calendar you want.
3. Scroll to **Integrate calendar** and copy **Secret address in iCal format**. It ends in `basic.ics`.
4. Repeat for each calendar you want to show.

**Treat these links like passwords.** Anyone with the link can read that calendar. Don't share or commit them.

### 5. Configure

Copy the example config and fill in your calendars:

```bash
cp config.example.py config.py
```

```python
# config.py
CLOCK_24H = False      # False: 9:30a   True: 09:30
CHECK_MINUTES = 15     # how often to check for changes

# opts: blue, green, red, yellow, black
ICS_FEEDS = [
    {"name": "Work",   "url": "https://calendar.google.com/calendar/ical/.../private-xxxx/basic.ics", "color": "blue"},
    {"name": "Family", "url": "https://calendar.google.com/calendar/ical/.../private-yyyy/basic.ics", "color": "red"},
]
```

`config.py` is gitignored since it holds your private links.

### 6. Run it

```bash
python main.py
```

If all goes well, nothing prints and the display updates.

### 7. Run it automatically on boot

Install it as a systemd service so it starts whenever the Pi powers on:

```bash
sed "s/USER/$(whoami)/g" calendar-dashboard.service | sudo tee /etc/systemd/system/calendar-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable --now calendar-dashboard
```

Check it's running:

```bash
systemctl status calendar-dashboard
journalctl -u calendar-dashboard -f      # live log output
```

If your project folder, username, or virtual environment path differ from `~/inky/cal`, `USER`, and `~/.virtualenvs/pimoroni`, edit `calendar-dashboard.service` (or the `sed` command above) to match before installing it.

## File structure

| File | Purpose |
|---|---|
| `main.py` | The run loop: fetch, compare, redraw, wait or refresh on a button press |
| `render.py` | Draws the four-day picture and assigns each calendar a display color |
| `calendars.py` | Fetches and parses each `ICS_FEEDS` calendar |
| `devices.py` | The physical display and the refresh button |
| `config.py` | Your calendars and settings (not checked into git) |
| `config.example.py` | A template for `config.py` |
| `calendar-dashboard.service` | The systemd unit for running on boot |
