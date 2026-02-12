#!/usr/bin/env python3
"""Demo script — cycles through all 3 new displays to verify wiring.

Run directly on the Pi:
    sudo python3 scripts/demo_displays.py

Tests each display independently, then runs them all together.
Press Ctrl+C at any time to stop and clean up.
"""

import sys
import time

def main():
    try:
        import lgpio
    except ImportError:
        print("ERROR: lgpio not available — run this on the Pi")
        sys.exit(1)

    h = lgpio.gpiochip_open(0)
    print("GPIO chip opened\n")

    # ── Phase 1: Bar Graph ─────────────────────────
    print("═" * 50)
    print("PHASE 1: LED Bar Graph")
    print("═" * 50)
    print("You should see bars fill up 0→10, then drain 10→0\n")

    from scout.gpio.bar_graph import BarGraph

    bar = BarGraph(h, lgpio)
    bar.setup()

    if bar._available:
        for level in range(11):
            bar.set_level(level)
            print(f"  bar level: {level:2d}  {'█' * level}{'░' * (10 - level)}")
            time.sleep(0.3)
        time.sleep(0.5)
        for level in range(10, -1, -1):
            bar.set_level(level)
            print(f"  bar level: {level:2d}  {'█' * level}{'░' * (10 - level)}")
            time.sleep(0.2)
        print("  ✓ bar graph test complete\n")
    else:
        print("  ✗ bar graph not available — check wiring\n")

    # ── Phase 2: 7-Segment via Shift Register ──────
    print("═" * 50)
    print("PHASE 2: 4-Digit 7-Segment Display")
    print("═" * 50)
    print("You should see 00:00 → 12:34 → 23:59 → counting up\n")

    from scout.gpio.shift_register import ShiftRegister
    from scout.gpio.seven_segment import SevenSegment
    from scout.gpio.multiplex_thread import MultiplexThread

    sr = ShiftRegister(h, lgpio)
    sr.setup()

    seg = SevenSegment(h, lgpio)
    seg.setup()

    if sr.available and seg.available:
        # Start multiplex (no matrix yet)
        mux = MultiplexThread(sr, seven_seg=seg, dot_matrix=None)
        mux.start()

        test_times = [(0, 0), (12, 34), (23, 59)]
        for hours, minutes in test_times:
            with mux.lock:
                seg.set_time(hours, minutes)
            print(f"  showing {hours:02d}:{minutes:02d}")
            time.sleep(2)

        print("  counting up from 00:00...")
        for t in range(10):
            with mux.lock:
                seg.set_time(0, t)
            time.sleep(0.5)

        mux.stop()
        seg.cleanup()
        sr.clear(num_chips=1)
        print("  ✓ 7-segment test complete\n")
    else:
        print(f"  ✗ shift register available: {sr.available}")
        print(f"  ✗ 7-segment available: {seg.available}")
        print("  check wiring\n")

    # ── Phase 3: Dot Matrix via Shift Registers ────
    print("═" * 50)
    print("PHASE 3: 8x8 Dot Matrix Display")
    print("═" * 50)
    print("You should see: smiley → X → check → heart → exclaim → blink\n")

    from scout.gpio.dot_matrix import (
        DotMatrix,
        PATTERN_SMILEY,
        PATTERN_X,
        PATTERN_CHECK,
        PATTERN_HEART,
        PATTERN_EXCLAIM,
        PATTERN_BLANK,
    )

    # Re-init SR for full 3-chip chain
    sr2 = ShiftRegister(h, lgpio)
    sr2.setup()
    seg2 = SevenSegment(h, lgpio)
    seg2.setup()

    matrix = DotMatrix()
    matrix.setup(sr_available=sr2.available)

    if sr2.available and matrix.available:
        mux2 = MultiplexThread(sr2, seven_seg=seg2, dot_matrix=matrix)
        mux2.start()

        patterns = [
            ("smiley :)", PATTERN_SMILEY),
            ("X (down)", PATTERN_X),
            ("checkmark", PATTERN_CHECK),
            ("heart", PATTERN_HEART),
            ("exclamation", PATTERN_EXCLAIM),
        ]

        for name, pat in patterns:
            with mux2.lock:
                matrix.set_pattern(pat)
            print(f"  showing: {name}")
            time.sleep(2)

        # Blink test
        print("  blinking X pattern...")
        with mux2.lock:
            matrix.set_pattern(PATTERN_X)
            matrix.set_blink(True)
        time.sleep(3)
        with mux2.lock:
            matrix.set_blink(False)

        mux2.stop()
        matrix.cleanup()
        seg2.cleanup()
        sr2.clear(num_chips=3)
        print("  ✓ dot matrix test complete\n")
    else:
        print(f"  ✗ shift register available: {sr2.available}")
        print(f"  ✗ matrix available: {matrix.available}")
        print("  need 3x 74HC595 — check wiring\n")

    # ── Phase 4: All Together ──────────────────────
    print("═" * 50)
    print("PHASE 4: All Displays Running Together")
    print("═" * 50)
    print("Bar graph filling, 7-seg counting, matrix cycling")
    print("Press Ctrl+C to stop\n")

    sr3 = ShiftRegister(h, lgpio)
    sr3.setup()
    seg3 = SevenSegment(h, lgpio)
    seg3.setup()
    matrix3 = DotMatrix()
    matrix3.setup(sr_available=sr3.available)
    bar3 = BarGraph(h, lgpio)
    bar3.setup()

    mux3 = MultiplexThread(sr3, seven_seg=seg3, dot_matrix=matrix3)
    mux3.start()

    all_patterns = [PATTERN_SMILEY, PATTERN_HEART, PATTERN_CHECK, PATTERN_X, PATTERN_EXCLAIM]
    try:
        seconds = 0
        while True:
            hours = (seconds // 3600) % 100
            minutes = (seconds % 3600) // 60

            with mux3.lock:
                seg3.set_time(hours, minutes)
                matrix3.set_pattern(all_patterns[(seconds // 3) % len(all_patterns)])

            bar_level = (seconds % 20)
            if bar_level > 10:
                bar_level = 20 - bar_level
            bar3.set_level(bar_level)

            status = f"  {hours:02d}:{minutes:02d}  bar={bar_level:2d}  {'█' * bar_level}{'░' * (10 - bar_level)}"
            print(f"\r{status}", end="", flush=True)

            time.sleep(1)
            seconds += 60  # skip ahead 1 min per second for a faster demo
    except KeyboardInterrupt:
        print("\n\n  stopping...")

    mux3.stop()
    bar3.cleanup()
    seg3.cleanup()
    matrix3.cleanup()
    sr3.clear(num_chips=3)

    lgpio.gpiochip_close(h)
    print("  ✓ all cleaned up — GPIO released")
    print("\n🎉 Demo complete!")


if __name__ == "__main__":
    main()
