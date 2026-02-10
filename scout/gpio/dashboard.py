"""GPIO physical dashboard — LEDs, buzzer, button, DHT11, LCD1602."""

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
    def __init__(self, alerter=None, briefing_fn=None):
        self.alerter = alerter
        self.briefing_fn = briefing_fn
        self._gpio = None
        self._lcd = None
        self._available = False
        self._lcd_available = False
        self._dht_available = False
        self._last_temp = None
        self._last_humidity = None

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
        for _ in range(pulses):
            self.buzzer_on()
            await asyncio.sleep(0.2)
            self.buzzer_off()
            await asyncio.sleep(0.2)

    def read_button(self) -> bool:
        if not self._available:
            return False
        return self._gpio.gpio_read(self._handle, PIN_BUTTON) == 0

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

    def lcd_write(self, line1: str, line2: str = ""):
        if not self._lcd_available:
            return
        try:
            self._lcd.clear()
            self._lcd.write_string(line1[:16] + "\r\n" + line2[:16])
        except Exception as e:
            log.debug("LCD write error: %s", e)

    def update_lcd(self, gateway_ok: bool, uptime_str: str):
        temp, humidity = self.read_dht11()
        status = "GW: UP" if gateway_ok else "GW: DOWN"
        if temp is not None:
            line2 = f"{temp:.0f}C {humidity:.0f}% {uptime_str}"
        else:
            line2 = uptime_str
        self.lcd_write(status, line2)

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
                    if self.briefing_fn:
                        try:
                            await self.briefing_fn()
                        except Exception as e:
                            log.error("briefing failed: %s", e)
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.1)
                break
            except asyncio.TimeoutError:
                pass

    def cleanup(self):
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
