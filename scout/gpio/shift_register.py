"""74HC595 shift register driver — bit-bang via lgpio.

Supports daisy-chaining: shift_out() accepts a list of bytes,
one per chip in the chain (first byte goes to the last chip
in the physical chain, last byte goes to the first chip).
"""

import logging

log = logging.getLogger("scout.gpio.shift_register")

# Shared 74HC595 chain pins (BCM)
PIN_DATA = 5    # SER  — serial data in
PIN_LATCH = 6   # RCLK — latch (storage clock)
PIN_CLOCK = 13  # SRCLK — shift clock


class ShiftRegister:
    """Bit-bang driver for a chain of 74HC595 shift registers."""

    def __init__(self, handle, lgpio):
        self._handle = handle
        self._gpio = lgpio
        self._available = False

    def setup(self):
        try:
            self._gpio.gpio_claim_output(self._handle, PIN_DATA, 0)
            self._gpio.gpio_claim_output(self._handle, PIN_LATCH, 0)
            self._gpio.gpio_claim_output(self._handle, PIN_CLOCK, 0)
            self._available = True
            log.info(
                "shift register chain initialized — data=%d latch=%d clock=%d",
                PIN_DATA, PIN_LATCH, PIN_CLOCK,
            )
        except Exception as e:
            log.warning("shift register not available: %s", e)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def shift_out(self, data: list[int]):
        """Shift out a list of bytes to the 74HC595 chain.

        Bytes are shifted MSB-first. The first byte in the list
        ends up in the chip furthest from the data pin.
        Latch is pulsed after all bits are shifted.
        """
        if not self._available:
            return
        gpio = self._gpio
        h = self._handle
        # Pull latch low before shifting
        gpio.gpio_write(h, PIN_LATCH, 0)
        for byte_val in data:
            for bit in range(7, -1, -1):
                gpio.gpio_write(h, PIN_DATA, (byte_val >> bit) & 1)
                gpio.gpio_write(h, PIN_CLOCK, 1)
                gpio.gpio_write(h, PIN_CLOCK, 0)
        # Pulse latch to transfer shift register → output register
        gpio.gpio_write(h, PIN_LATCH, 1)
        gpio.gpio_write(h, PIN_LATCH, 0)

    def clear(self, num_chips: int = 3):
        """Shift out all zeros to clear the chain."""
        self.shift_out([0x00] * num_chips)

    def cleanup(self):
        if not self._available:
            return
        self.clear()
