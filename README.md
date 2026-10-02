# Spectra

A four-day calendar dashboard for a [Pimoroni Inky Impression 7.3"](https://shop.pimoroni.com/products/inky-impression-7-3) e-ink display on a Raspberry Pi. No backlight, almost no power draw between updates.

![Preview](preview.png)

## How it works

- **Four day calendar.** With today the left, followed by the next three days.
- **No sign-in needed.** Each calendar is a private iCal link from Google Calendar, fetched over HTTPS. No OAuth, no expiring tokens.
- **Color-coded.** Every calendar gets its own color.
- **Redraws only when something changed.** It checks every `CHECK_MINUTES`.
- **On demand.** Press button A on the display to force refresh immediately.

## Hardware

- Raspberry Pi (tested on a Pi Zero 2 W)
- Pimoroni Inky Impression 7.3"

## Setup

### 1. Install the Inky library

Check out the [Pimoroni getting started guide](https://learn.pimoroni.com/article/getting-started-with-inky-impression), or run:

```bash
sudo apt update && sudo apt upgrade
git clone https://github.com/pimoroni/inky
cd inky
./install.sh
sudo reboot
```

### 2. Get Spectra + dependencies

```bash
git clone https://github.com/maxzwerin/spectra.git
cd spectra
source ~/.virtualenvs/pimoroni/bin/activate
pip install -r requirements.txt
```

### 3. Get your calendar links

1. Open [Google Calendar](https://calendar.google.com) on a computer, click the gear icon, then **Settings**.
2. Under **Settings for my calendars**, click the calendar you want.
3. Scroll to **Integrate calendar** and copy the **Secret address in iCal format**. It ends in `basic.ics`.
4. Repeat for each calendar you want to show.

> **Treat these links like passwords.** Anyone with the link can read that calendar. Don't share or commit them.

### 4. Configure

```bash
cp config.example.py config.py
nano config.py    # or: sudo apt install vim && vim config.py
```

```python
# config.py
CLOCK_24H = False      # False: 9:30am   True: 09:30
CHECK_MINUTES = 15     # how often to check for changes

# colors: blue, green, red, yellow, black
ICS_FEEDS = [
    {"name": "Work",   "url": "https://calendar.google.com/calendar/ical/.../private-xxxx/basic.ics", "color": "blue"},
    {"name": "Family", "url": "https://calendar.google.com/calendar/ical/.../private-yyyy/basic.ics", "color": "red"},
]
```

`config.py` is gitignored because it holds your private links.

### 5. Run it

```bash
python main.py
```

If all goes well, nothing prints and the display updates.

### 6. Start on boot

Install it as a systemd service:

```bash
sed "s/USER/$(whoami)/g" calendar.service | sudo tee /etc/systemd/system/calendar.service
sudo systemctl daemon-reload
sudo systemctl enable --now calendar
```

Check that it's running:

```bash
systemctl status calendar
```

If your project folder, username, or virtual environment path differ from `~/inky/spectra`, `USER`, and `~/.virtualenvs/pimoroni`, edit `calendar.service` to match before installing it. In particular, check that `WorkingDirectory` points at your clone, or systemd will fail with `status=200/CHDIR`.

## Files

| File | Purpose |
|---|---|
| `main.py` | Run loop: fetch, compare, redraw, wait or refresh on a button press |
| `render.py` | Draws the four-day picture |
| `calendars.py` | Fetches and parses each calendar in `ICS_FEEDS` |
| `devices.py` | The physical display and the refresh button |
| `config.py` | Your calendars and settings (not in git) |
| `config.example.py` | Template for `config.py` |
| `calendar.service` | systemd unit for running on boot |
