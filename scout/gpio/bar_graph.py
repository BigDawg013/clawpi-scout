"""LED Bar Graph driver — 10 segments driven by direct GPIO."""

import logging

log = logging.getLogger("scout.gpio.bar_graph")

# 10 GPIO pins for bar graph segments (BCM), left-to-right
BAR_PINS = [25, 8, 7, 9, 11, 10, 19, 26, 18, 15]


class BarGraph:
    """Drives a 10-segment LED bar graph as a health gauge.

    set_level(0)  = all off
    set_level(10) = all on
    """

    def __init__(self, handle, lgpio):
        self._handle = handle
        self._gpio = lgpio
        self._available = False
        self._level = 0

    def setup(self):
        try:
            for pin in BAR_PINS:
                self._gpio.gpio_claim_output(self._handle, pin, 0)
            self._available = True
            log.info("bar graph initialized — 10 segments on %s", BAR_PINS)
        except Exception as e:
            log.warning("bar graph not available: %s", e)
            self._available = False

    def set_level(self, level: int):
        """Set bar graph to show 0–10 lit segments."""
        if not self._available:
            return
        level = max(0, min(10, level))
        self._level = level
        for i, pin in enumerate(BAR_PINS):
            self._gpio.gpio_write(self._handle, pin, 1 if i < level else 0)

    @property
    def level(self) -> int:
        return self._level

    def cleanup(self):
        if not self._available:
            return
        for pin in BAR_PINS:
            try:
                self._gpio.gpio_write(self._handle, pin, 0)
            except Exception:
                pass
