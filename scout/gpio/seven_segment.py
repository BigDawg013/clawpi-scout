"""4-digit 7-segment display driver via 74HC595 + digit select GPIO.

The 74HC595 drives segments a–g + dp (8 bits).
Four GPIO pins select which digit is active (active LOW, common cathode
accent: pull digit pin LOW to enable that digit's common cathode).

Segment encoding (active HIGH):
  bit 0 = a (top)
  bit 1 = b (top-right)
  bit 2 = c (bottom-right)
  bit 3 = d (bottom)
  bit 4 = e (bottom-left)
  bit 5 = f (top-left)
  bit 6 = g (middle)
  bit 7 = dp (decimal point / colon)
"""

import logging

log = logging.getLogger("scout.gpio.seven_segment")

# Digit select pins (BCM) — active LOW
DIGIT_PINS = [12, 16, 20, 21]  # digit 1, 2, 3, 4

# Segment encoding for digits 0-9
SEGMENTS = {
    0: 0b00111111,  # a b c d e f
    1: 0b00000110,  # b c
    2: 0b01011011,  # a b d e g
    3: 0b01001111,  # a b c d g
    4: 0b01100110,  # b c f g
    5: 0b01101101,  # a c d f g
    6: 0b01111101,  # a c d e f g
    7: 0b00000111,  # a b c
    8: 0b01111111,  # a b c d e f g
    9: 0b01101111,  # a b c d f g
}

# Blank digit (all off)
BLANK = 0x00

# Decimal point / colon bit
DP_BIT = 0b10000000


class SevenSegment:
    """4-digit 7-segment display showing HH:MM uptime.

    This class holds the desired display state. The actual multiplexing
    (cycling through digits at ~800Hz) is handled by MultiplexThread.
    """

    def __init__(self, handle, lgpio):
        self._handle = handle
        self._gpio = lgpio
        self._available = False
        # 4 bytes: segment data for each digit
        self._digits = [BLANK, BLANK, BLANK, BLANK]
        self._colon = False

    def setup(self):
        try:
            for pin in DIGIT_PINS:
                # Start with all digits OFF (HIGH = off for common cathode select)
                self._gpio.gpio_claim_output(self._handle, pin, 1)
            self._available = True
            log.info("7-segment digit select initialized — pins %s", DIGIT_PINS)
        except Exception as e:
            log.warning("7-segment not available: %s", e)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def set_time(self, hours: int, minutes: int):
        """Set display to show HH:MM."""
        h_tens = (hours // 10) % 10
        h_ones = hours % 10
        m_tens = (minutes // 10) % 10
        m_ones = minutes % 10
        self._digits[0] = SEGMENTS.get(h_tens, BLANK)
        self._digits[1] = SEGMENTS.get(h_ones, BLANK)
        self._digits[2] = SEGMENTS.get(m_tens, BLANK)
        self._digits[3] = SEGMENTS.get(m_ones, BLANK)

    def set_colon(self, on: bool):
        """Toggle the colon (dp on digit 2)."""
        self._colon = on

    def get_digit_data(self, index: int) -> int:
        """Get segment byte for a given digit (0-3), with colon applied."""
        val = self._digits[index]
        if self._colon and index == 1:
            val |= DP_BIT
        return val

    def select_digit(self, index: int):
        """Activate one digit, deactivate others."""
        if not self._available:
            return
        for i, pin in enumerate(DIGIT_PINS):
            # Active LOW: pull low to enable
            self._gpio.gpio_write(self._handle, pin, 0 if i == index else 1)

    def all_off(self):
        """Deactivate all digits."""
        if not self._available:
            return
        for pin in DIGIT_PINS:
            self._gpio.gpio_write(self._handle, pin, 1)

    def cleanup(self):
        if not self._available:
            return
        self.all_off()
