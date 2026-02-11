"""8x8 LED dot matrix driver via 2x daisy-chained 74HC595.

Two shift registers drive the matrix:
  - SR1 (first in chain): column data (which LEDs are on in the active row)
  - SR2 (second in chain): row select (which row is active, active LOW)

The matrix is scanned row by row at high frequency by MultiplexThread.

Patterns are 8-byte arrays where each byte is one row (MSB = leftmost column).
"""

import logging

log = logging.getLogger("scout.gpio.dot_matrix")

# --- Built-in patterns (8 bytes each, top row first) ---

PATTERN_SMILEY = [
    0b00111100,
    0b01000010,
    0b10100101,
    0b10000001,
    0b10100101,
    0b10011001,
    0b01000010,
    0b00111100,
]

PATTERN_X = [
    0b10000001,
    0b01000010,
    0b00100100,
    0b00011000,
    0b00011000,
    0b00100100,
    0b01000010,
    0b10000001,
]

PATTERN_CHECK = [
    0b00000000,
    0b00000001,
    0b00000010,
    0b00000100,
    0b10001000,
    0b01010000,
    0b00100000,
    0b00000000,
]

PATTERN_EXCLAIM = [
    0b00011000,
    0b00011000,
    0b00011000,
    0b00011000,
    0b00011000,
    0b00000000,
    0b00011000,
    0b00011000,
]

PATTERN_HEART = [
    0b00000000,
    0b01100110,
    0b11111111,
    0b11111111,
    0b11111111,
    0b01111110,
    0b00111100,
    0b00011000,
]

PATTERN_BLANK = [0x00] * 8


class DotMatrix:
    """8x8 dot matrix display state holder.

    Actual scanning is done by MultiplexThread which calls
    get_row_data() for each row during its refresh loop.
    """

    def __init__(self):
        self._pattern = PATTERN_BLANK[:]
        self._blink = False
        self._available = False

    def setup(self, sr_available: bool):
        """Mark available if the shift register chain has enough chips."""
        self._available = sr_available
        if sr_available:
            log.info("dot matrix initialized (via shift register chain)")
        else:
            log.warning("dot matrix not available — need 3 shift registers")

    @property
    def available(self) -> bool:
        return self._available

    def set_pattern(self, pattern: list[int]):
        """Set the 8-row pattern to display."""
        self._pattern = pattern[:8]

    def set_blink(self, blink: bool):
        """Enable/disable blink mode (used during alarm)."""
        self._blink = blink

    @property
    def blinking(self) -> bool:
        return self._blink

    def get_row_data(self, row: int) -> tuple[int, int]:
        """Get (row_select, col_data) for shift register chain.

        Returns two bytes to shift out:
          byte 0 → SR2 (row select, active LOW — one bit low)
          byte 1 → SR1 (column data, active HIGH)
        """
        # Row select: all high except the active row
        row_byte = ~(1 << row) & 0xFF
        col_byte = self._pattern[row] if row < len(self._pattern) else 0x00
        return row_byte, col_byte

    def cleanup(self):
        self._pattern = PATTERN_BLANK[:]
