"""GPIO physical dashboard — LEDs, buzzer, button, DHT11, LCD1602,
LED bar graph, 4-digit 7-segment, 8x8 dot matrix."""

import asyncio
import logging
import time

log = logging.getLogger("scout.gpio")

# Pin assignments (BCM numbering)
PIN_LED_GREEN = 17
PIN_LED_RED = 27
PIN_LED_YELLOW = 22
PIN_BUZZER = 23
PIN_BUTTON = 24
PIN_DHT11 = 4

# LCD I2C address (run `i2cdetect -y 1` to verify)
LCD_I2C_ADDR = 0x27


class Dashboard:
    def __init__(self, alerter=None, briefing_fn=None, config=None):
        self.alerter = alerter
        self.briefing_fn = briefing_fn
        self._config = config or {}
        self._gpio = None
        self._lcd = None
        self._available = False
        self._lcd_available = False
        self._dht_available = False
        self._last_temp = None
        self._last_humidity = None
        self._last_gateway_ok = True
        self._last_uptime = ""

        # Health score for bar graph (0-10)
        self._health_score = 0

        # Sub-drivers
        self._bar_graph = None
        self._shift_register = None
        self._seven_seg = None
        self._dot_matrix = None
        self._multiplex = None

    def setup(self):
        try:
            import lgpio
            self._gpio = lgpio
            h = lgpio.gpiochip_open(0)
            self._handle = h

            # LEDs as output
            lgpio.gpio_claim_output(h, PIN_LED_GREEN, 0)
            lgpio.gpio_claim_output(h, PIN_LED_RED, 0)
            lgpio.gpio_claim_output(h, PIN_LED_YELLOW, 0)
            lgpio.gpio_claim_output(h, PIN_BUZZER, 0)

            # Button as input with pull-up
            lgpio.gpio_claim_input(h, PIN_BUTTON, lgpio.SET_PULL_UP)

            self._available = True
            log.info("GPIO initialized — LEDs, buzzer, button ready")
        except Exception as e:
            log.warning("GPIO not available: %s", e)
            self._available = False

        # LCD setup
        try:
            from RPLCD.i2c import CharLCD
            self._lcd = CharLCD(
                i2c_expander="PCF8574",
                address=LCD_I2C_ADDR,
                port=1,
                cols=16,
                rows=2,
            )
            self._lcd.clear()
            self._lcd.write_string("clawpi-scout\r\nStarting...")
            self._lcd_available = True
            log.info("LCD1602 initialized at 0x%02x", LCD_I2C_ADDR)
        except Exception as e:
            log.warning("LCD not available: %s", e)
            self._lcd_available = False

        # DHT11 setup
        try:
            import adafruit_dht
            import board
            self._dht = adafruit_dht.DHT11(board.D4)
            self._dht_available = True
            log.info("DHT11 initialized on GPIO4")
        except Exception as e:
            log.warning("DHT11 not available: %s", e)
            self._dht_available = False

        # --- New display sub-drivers ---
        gpio_cfg = self._config.get("gpio", {})

        # LED Bar Graph
        if gpio_cfg.get("bar_graph", True) and self._available:
            self._setup_bar_graph()

        # Shift register chain (shared by 7-segment + matrix)
        if gpio_cfg.get("seven_segment", True) or gpio_cfg.get("dot_matrix", True):
            if self._available:
                self._setup_shift_register()

        # 4-Digit 7-Segment
        if gpio_cfg.get("seven_segment", True) and self._available:
            self._setup_seven_segment()

        # 8x8 Dot Matrix
        if gpio_cfg.get("dot_matrix", True) and self._available:
            self._setup_dot_matrix()

        # Start multiplex thread if any multiplexed display is active
        if self._seven_seg or self._dot_matrix:
            self._setup_multiplex()

    def _setup_bar_graph(self):
        try:
            from scout.gpio.bar_graph import BarGraph
            self._bar_graph = BarGraph(self._handle, self._gpio)
            self._bar_graph.setup()
        except Exception as e:
            log.warning("bar graph setup failed: %s", e)
            self._bar_graph = None

    def _setup_shift_register(self):
        try:
            from scout.gpio.shift_register import ShiftRegister
            self._shift_register = ShiftRegister(self._handle, self._gpio)
            self._shift_register.setup()
        except Exception as e:
            log.warning("shift register setup failed: %s", e)
            self._shift_register = None

    def _setup_seven_segment(self):
        if not self._shift_register or not self._shift_register.available:
            log.warning("7-segment skipped — shift register not available")
            return
        try:
            from scout.gpio.seven_segment import SevenSegment
            self._seven_seg = SevenSegment(self._handle, self._gpio)
            self._seven_seg.setup()
            if not self._seven_seg.available:
                self._seven_seg = None
        except Exception as e:
            log.warning("7-segment setup failed: %s", e)
            self._seven_seg = None

    def _setup_dot_matrix(self):
        if not self._shift_register or not self._shift_register.available:
            log.warning("dot matrix skipped — shift register not available")
            return
        try:
            from scout.gpio.dot_matrix import DotMatrix
            self._dot_matrix = DotMatrix()
            # Matrix needs 3 SR chips (1 for 7-seg + 2 for matrix)
            self._dot_matrix.setup(sr_available=True)
        except Exception as e:
            log.warning("dot matrix setup failed: %s", e)
            self._dot_matrix = None

    def _setup_multiplex(self):
        try:
            from scout.gpio.multiplex_thread import MultiplexThread
            self._multiplex = MultiplexThread(
                self._shift_register,
                seven_seg=self._seven_seg,
                dot_matrix=self._dot_matrix,
            )
            self._multiplex.start()
        except Exception as e:
            log.warning("multiplex thread setup failed: %s", e)
            self._multiplex = None

    # --- LED controls ---

    def led_checking(self):
        if not self._available:
            return
        lgpio = self._gpio
        lgpio.gpio_write(self._handle, PIN_LED_GREEN, 0)
        lgpio.gpio_write(self._handle, PIN_LED_RED, 0)
        lgpio.gpio_write(self._handle, PIN_LED_YELLOW, 1)

    def led_ok(self):
        if not self._available:
            return
        lgpio = self._gpio
        lgpio.gpio_write(self._handle, PIN_LED_GREEN, 1)
        lgpio.gpio_write(self._handle, PIN_LED_RED, 0)
        lgpio.gpio_write(self._handle, PIN_LED_YELLOW, 0)

    def led_fail(self):
        if not self._available:
            return
        lgpio = self._gpio
        lgpio.gpio_write(self._handle, PIN_LED_GREEN, 0)
        lgpio.gpio_write(self._handle, PIN_LED_RED, 1)
        lgpio.gpio_write(self._handle, PIN_LED_YELLOW, 0)

    # --- Buzzer ---

    def buzzer_on(self):
        if not self._available:
            return
        self._gpio.gpio_write(self._handle, PIN_BUZZER, 1)

    def buzzer_off(self):
        if not self._available:
            return
        self._gpio.gpio_write(self._handle, PIN_BUZZER, 0)

    async def alarm(self, pulses: int = 3):
        """Short buzzer pulses for alerts."""
        self.lcd_write("!! GW DOWN !!", "KABOOOOM!!!")
        # Matrix blink during alarm
        if self._dot_matrix and self._multiplex:
            with self._multiplex.lock:
                self._dot_matrix.set_blink(True)
        for _ in range(pulses):
            self.buzzer_on()
            await asyncio.sleep(0.2)
            self.buzzer_off()
            await asyncio.sleep(0.2)
        if self._dot_matrix and self._multiplex:
            with self._multiplex.lock:
                self._dot_matrix.set_blink(False)

    # --- Button ---

    def read_button(self) -> bool:
        if not self._available:
            return False
        return self._gpio.gpio_read(self._handle, PIN_BUTTON) == 0

    # --- DHT11 ---

    def read_dht11(self) -> tuple[float | None, float | None]:
        if not self._dht_available:
            return self._last_temp, self._last_humidity
        try:
            temp = self._dht.temperature
            humidity = self._dht.humidity
            if temp is not None:
                self._last_temp = temp
            if humidity is not None:
                self._last_humidity = humidity
        except Exception:
            pass
        return self._last_temp, self._last_humidity

    # --- LCD ---

    def lcd_write(self, line1: str, line2: str = ""):
        if not self._lcd_available:
            return
        try:
            self._lcd.clear()
            self._lcd.write_string(line1[:16] + "\r\n" + line2[:16])
        except Exception as e:
            log.debug("LCD write error: %s", e)

    def update_lcd(self, gateway_ok: bool, uptime_str: str):
        self._last_gateway_ok = gateway_ok
        self._last_uptime = uptime_str
        self._refresh_lcd()

    _UP_MESSAGES = [
        "Claw Vibin'",
        "All Good Fam",
        "Claw Online",
        "Scout On Duty",
        "Systems Nominal",
        "We Cookin'",
        "Claw Runnin'",
        "Big Dawg Mode",
    ]
    _DOWN_MESSAGES = [
        "Claw is DEAD!",
        "MAYDAY MAYDAY!",
        "Houston Problem",
        "Not Good Fam",
    ]
    _msg_index = 0

    def _refresh_lcd(self):
        import random
        temp, humidity = self.read_dht11()
        if self._last_gateway_ok:
            status = self._UP_MESSAGES[self._msg_index % len(self._UP_MESSAGES)]
            self._msg_index += 1
        else:
            status = random.choice(self._DOWN_MESSAGES)
        if temp is not None:
            line2 = f"{temp:.0f}C {humidity:.0f}% {self._last_uptime}"
        else:
            line2 = self._last_uptime
        self.lcd_write(status, line2)

    # --- Health score + new displays ---

    def on_health_check(self, ok: bool, consecutive_ok: int, uptime_seconds: int):
        """Called by HealthMonitor after each check to update all displays."""
        # Update health score for bar graph
        if ok:
            self._health_score = min(10, self._health_score + 1)
        else:
            self._health_score = max(0, self._health_score - 2)

        # Bar graph
        if self._bar_graph:
            self._bar_graph.set_level(self._health_score)

        # 7-segment uptime (HH:MM)
        if self._seven_seg and self._multiplex:
            hours = (uptime_seconds // 3600) % 100  # wrap at 99h
            minutes = (uptime_seconds % 3600) // 60
            with self._multiplex.lock:
                self._seven_seg.set_time(hours, minutes)

        # Dot matrix pattern
        if self._dot_matrix and self._multiplex:
            from scout.gpio.dot_matrix import PATTERN_SMILEY, PATTERN_X
            with self._multiplex.lock:
                self._dot_matrix.set_pattern(
                    PATTERN_SMILEY if ok else PATTERN_X
                )

    # --- Button watcher ---

    async def watch_button(self, stop: asyncio.Event):
        """Poll button and trigger briefing on press."""
        if not self._available:
            log.info("button watcher skipped — GPIO not available")
            await stop.wait()
            return

        log.info("button watcher started on GPIO%d", PIN_BUTTON)
        last_press = 0
        while not stop.is_set():
            if self.read_button():
                now = time.time()
                if now - last_press > 2:  # debounce 2s
                    last_press = now
                    log.info("button pressed — sending briefing")
                    self.lcd_write("Sending...", "Briefing >>")
                    if self.briefing_fn:
                        try:
                            await self.briefing_fn()
                            self.lcd_write("Briefing sent!", "Check Telegram")
                            await asyncio.sleep(2)
                        except Exception as e:
                            log.error("briefing failed: %s", e)
                            self.lcd_write("Briefing", "FAILED :(")
                            await asyncio.sleep(2)
                    self._refresh_lcd()
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.1)
                break
            except asyncio.TimeoutError:
                pass

    # --- Cleanup ---

    def cleanup(self):
        # Stop multiplex thread first
        if self._multiplex:
            try:
                self._multiplex.stop()
            except Exception:
                pass

        # Clean up new displays
        if self._bar_graph:
            try:
                self._bar_graph.cleanup()
            except Exception:
                pass
        if self._seven_seg:
            try:
                self._seven_seg.cleanup()
            except Exception:
                pass
        if self._dot_matrix:
            try:
                self._dot_matrix.cleanup()
            except Exception:
                pass
        if self._shift_register:
            try:
                self._shift_register.cleanup()
            except Exception:
                pass

        # Original cleanup
        if self._available:
            try:
                lgpio = self._gpio
                lgpio.gpio_write(self._handle, PIN_LED_GREEN, 0)
                lgpio.gpio_write(self._handle, PIN_LED_RED, 0)
                lgpio.gpio_write(self._handle, PIN_LED_YELLOW, 0)
                lgpio.gpio_write(self._handle, PIN_BUZZER, 0)
                lgpio.gpiochip_close(self._handle)
            except Exception:
                pass
        if self._lcd_available:
            try:
                self._lcd.clear()
                self._lcd.close(clear=True)
            except Exception:
                pass
        if self._dht_available:
            try:
                self._dht.exit()
            except Exception:
                pass
        log.info("GPIO cleaned up")
