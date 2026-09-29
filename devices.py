from datetime import timedelta

class InkyDisplay:
    def __init__(self):
        from inky.auto import auto

        self.inky = auto()  # detects the panel from its EEPROM

    def show(self, panel):
        self.inky.set_image(panel)
        self.inky.show()  # takes 10-30 seconds


class RefreshButton:
    GPIO = 5

    def __init__(self):
        import gpiod
        import gpiodevice
        from gpiod.line import Bias, Direction, Edge

        chip = gpiodevice.find_chip_by_platform()
        offset = chip.line_offset_from_id(self.GPIO)
        settings = gpiod.LineSettings(
            direction=Direction.INPUT, bias=Bias.PULL_UP, edge_detection=Edge.FALLING,
            debounce_period=timedelta(milliseconds=50),
        )
        self.lines = chip.request_lines(consumer="calendar-dashboard", config={offset: settings})

    def wait(self, seconds: float) -> bool:
        pressed = self.lines.wait_edge_events(timedelta(seconds=seconds))
        if pressed:
            self.lines.read_edge_events()  # clear the event so it isn't reported again next time
        return bool(pressed)
