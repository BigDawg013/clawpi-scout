"""Background multiplexing thread for 7-segment + dot matrix displays.

A single daemon thread cycles through:
  - 4 digits of the 7-segment display
  - 8 rows of the 8x8 dot matrix
at a combined refresh rate fast enough to avoid visible flicker (~800Hz+).

Shared state is read via threading.Lock for thread safety.
"""

import logging
import threading
import time

log = logging.getLogger("scout.gpio.multiplex")


class MultiplexThread:
    """Daemon thread that refreshes multiplexed displays."""

    def __init__(self, shift_register, seven_seg=None, dot_matrix=None):
        self._sr = shift_register
        self._7seg = seven_seg
        self._matrix = dot_matrix
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        # Blink state for matrix
        self._blink_on = True
        self._blink_counter = 0
        # Colon blink for 7-seg
        self._colon_counter = 0

    def start(self):
        if self._thread is not None:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("multiplex thread started")

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None
            log.info("multiplex thread stopped")

    def _loop(self):
        """Main refresh loop — interleaves 7-seg digits and matrix rows."""
        cycle = 0
        while self._running:
            try:
                self._refresh_cycle(cycle)
                cycle = (cycle + 1) % 12  # 4 digits + 8 rows = 12 slots
                # ~1000Hz total → each digit/row at ~83Hz (enough to avoid flicker)
                time.sleep(0.001)
            except Exception as e:
                log.debug("multiplex error: %s", e)
                time.sleep(0.01)

    def _refresh_cycle(self, cycle: int):
        # Update blink counters (roughly every 500ms at 1kHz)
        self._blink_counter += 1
        if self._blink_counter >= 500:
            self._blink_counter = 0
            self._blink_on = not self._blink_on
        self._colon_counter += 1
        if self._colon_counter >= 500:
            self._colon_counter = 0
            if self._7seg and self._7seg.available:
                with self._lock:
                    self._7seg.set_colon(not self._7seg._colon)

        if cycle < 4:
            # 7-segment digit
            self._render_7seg_digit(cycle)
        else:
            # Dot matrix row
            self._render_matrix_row(cycle - 4)

    def _render_7seg_digit(self, digit_index: int):
        if not self._7seg or not self._7seg.available:
            return
        if not self._sr or not self._sr.available:
            return

        with self._lock:
            seg_data = self._7seg.get_digit_data(digit_index)

        # Shift out: only 1 byte for the 7-seg SR (first in chain)
        # If matrix SRs exist, send zeros for them
        if self._matrix and self._matrix.available:
            # 3 chips: [matrix_row, matrix_col, 7seg_segments]
            # Turn off matrix during 7-seg slot
            self._sr.shift_out([0xFF, 0x00, seg_data])
        else:
            # 1 chip: just 7-seg
            self._sr.shift_out([seg_data])

        self._7seg.select_digit(digit_index)

    def _render_matrix_row(self, row: int):
        if not self._matrix or not self._matrix.available:
            return
        if not self._sr or not self._sr.available:
            return

        with self._lock:
            row_byte, col_byte = self._matrix.get_row_data(row)

        # Handle blink
        if self._matrix.blinking and not self._blink_on:
            col_byte = 0x00

        # Turn off 7-seg digits during matrix slot
        if self._7seg and self._7seg.available:
            self._7seg.all_off()

        # 3 chips: [matrix_row, matrix_col, 7seg_segments]
        # Zero out 7-seg during matrix refresh
        self._sr.shift_out([row_byte, col_byte, 0x00])

    @property
    def lock(self) -> threading.Lock:
        """Expose lock for external state updates."""
        return self._lock
