# Wiring Guide — GPIO Physical Dashboard

Components from the Freenove Ultimate Starter Kit (FNK0020) or equivalent.

## Parts needed

| Component | Qty | From kit |
|-----------|-----|----------|
| Green LED | 1 | Yes |
| Red LED | 1 | Yes |
| Yellow LED | 1 | Yes |
| 220 ohm resistor | 3 | Yes |
| Active buzzer | 1 | Yes |
| Push button | 1 | Yes |
| DHT11 temp/humidity sensor | 1 | Yes |
| LCD1602 with I2C backpack | 1 | Yes |
| Breadboard | 1 | Yes |
| Jumper wires (M-F, M-M) | ~15 | Yes |

## Pin assignments (BCM numbering)

| Component | GPIO | Physical pin | Direction |
|-----------|------|-------------|-----------|
| Green LED | 17 | 11 | Output |
| Red LED | 27 | 13 | Output |
| Yellow LED | 22 | 15 | Output |
| Active buzzer | 23 | 16 | Output |
| Push button | 24 | 18 | Input (pull-up) |
| DHT11 data | 4 | 7 | Input |
| LCD1602 SDA | 2 | 3 | I2C |
| LCD1602 SCL | 3 | 5 | I2C |

## Wiring

### LEDs (green, red, yellow)

Each LED needs a 220 ohm resistor in series.

```
GPIO pin ──→ 220Ω resistor ──→ LED anode (+, longer leg)
                                 LED cathode (-, shorter leg) ──→ GND
```

- GPIO 17 (pin 11) → resistor → green LED → GND
- GPIO 27 (pin 13) → resistor → red LED → GND
- GPIO 22 (pin 15) → resistor → yellow LED → GND

### Active buzzer

```
GPIO 23 (pin 16) ──→ Buzzer + (marked with +)
                      Buzzer - ──→ GND (pin 14)
```

### Push button

No external resistor needed — uses the Pi's internal pull-up.

```
GPIO 24 (pin 18) ──→ one leg of button
                      other leg ──→ GND (pin 20)
```

### DHT11 temperature/humidity sensor

```
DHT11 VCC  ──→ 3.3V (pin 17)
DHT11 DATA ──→ GPIO 4 (pin 7)
DHT11 GND  ──→ GND (pin 9)
```

If your DHT11 module has 4 pins, the 3rd pin is unused.

### LCD1602 (I2C)

Make sure I2C is enabled: `sudo raspi-config nonint do_i2c 0`

```
LCD GND ──→ GND (pin 6)
LCD VCC ──→ 5V (pin 2)
LCD SDA ──→ SDA / GPIO 2 (pin 3)
LCD SCL ──→ SCL / GPIO 3 (pin 5)
```

Verify the LCD is detected:

```bash
i2cdetect -y 1
```

You should see `27` (or `3f`) in the grid. If your address differs, update `LCD_I2C_ADDR` in `scout/gpio/dashboard.py`.

## Breadboard layout

```
                    Raspberry Pi GPIO Header
                    ┌──────────────────────┐
                    │ (1)3V3      5V(2)  ──┤── LCD VCC
                    │ (3)SDA ─────────────┤── LCD SDA
                    │ (5)SCL ─────────────┤── LCD SCL
                    │ (6)GND ─────────────┤── LCD GND
                    │ (7)GP4 ─────────────┤── DHT11 DATA
                    │ (9)GND ─────────────┤── DHT11 GND
                    │(11)GP17 ────────────┤── 220Ω → GREEN LED → GND
                    │(13)GP27 ────────────┤── 220Ω → RED LED → GND
                    │(14)GND ─────────────┤── BUZZER -
                    │(15)GP22 ────────────┤── 220Ω → YELLOW LED → GND
                    │(16)GP23 ────────────┤── BUZZER +
                    │(17)3V3 ─────────────┤── DHT11 VCC
                    │(18)GP24 ────────────┤── BUTTON → GND (pin 20)
                    │(20)GND ─────────────┤── BUTTON GND
                    └──────────────────────┘
```

## What each component does

| Component | Behavior |
|-----------|----------|
| Green LED | Solid = gateway is UP |
| Red LED | Solid = gateway is DOWN |
| Yellow LED | Brief flash = health check in progress |
| Buzzer | 3 short pulses when gateway goes down |
| Button | Press = send Telegram briefing immediately |
| DHT11 | Room temp/humidity shown on LCD and in briefings |
| LCD1602 | Line 1: gateway status, Line 2: temp + uptime |
