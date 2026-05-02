"""
Servo / PCA9685 module — pure Python, no external dependencies.

Uses the Linux I2C file interface (/dev/i2c-N) via fcntl.ioctl directly,
so smbus2 / Adafruit libraries are NOT required.

PCA9685 overview
----------------
- 16-channel 12-bit PWM driver (I2C, default address 0x40)
- Internal clock: 25 MHz
- Prescaler:  prescale = round(25_000_000 / (4096 * freq_hz)) - 1
- Servo PWM:  50 Hz, pulse 500–2500 µs  →  0°–180°

Usage
-----
    from modules.servo import PCA9685, detect_pca9685

    addrs = detect_pca9685()          # scan bus 1 for PCA9685 chips
    with PCA9685() as pca:
        pca.set_pwm_freq(50)
        pca.set_servo_angle(0, 90)    # channel 0, 90 degrees
"""

from __future__ import annotations

import fcntl
import time
import os
import struct
from dataclasses import dataclass, field
from typing import List, Optional

# ── Linux I2C ioctl constant ────────────────────────────────────────────────
_I2C_SLAVE = 0x0703

# ── PCA9685 register map ─────────────────────────────────────────────────────
_MODE1        = 0x00
_MODE2        = 0x01
_PRESCALE     = 0xFE
_LED0_ON_L    = 0x06   # 4 bytes per channel: ON_L, ON_H, OFF_L, OFF_H
_ALL_LED_OFF_H = 0xFD  # bit 4 = full-off for all channels

# MODE1 bits
_RESTART   = 0x80
_SLEEP     = 0x10
_ALLCALL   = 0x01
_AI        = 0x20      # auto-increment

# Internal oscillator frequency
_OSC_CLOCK = 25_000_000

# ── Common PCA9685 I2C addresses (A5..A0 pins) ───────────────────────────────
KNOWN_ADDRESSES: List[int] = [0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
                               0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F,
                               0x70]   # 0x70 = ALLCALL broadcast address


# ── Detection result ─────────────────────────────────────────────────────────
@dataclass
class DetectedChip:
    address:     int
    bus:         int
    mode1_reg:   int   # raw MODE1 register value (useful for sanity check)
    description: str


# ── Low-level I2C bus wrapper ─────────────────────────────────────────────────
class _I2CBus:
    """Minimal raw I2C file interface; not thread-safe."""

    def __init__(self, bus: int, addr: int):
        self._path = f"/dev/i2c-{bus}"
        self._addr = addr
        self._fd: Optional[object] = None

    def open(self) -> None:
        self._fd = open(self._path, "rb+", buffering=0)
        fcntl.ioctl(self._fd, _I2C_SLAVE, self._addr)

    def close(self) -> None:
        if self._fd:
            self._fd.close()
            self._fd = None

    def write_byte(self, reg: int, value: int) -> None:
        self._fd.write(bytes([reg & 0xFF, value & 0xFF]))

    def write_block(self, reg: int, data: bytes) -> None:
        self._fd.write(bytes([reg & 0xFF]) + data)

    def read_byte(self, reg: int) -> int:
        self._fd.write(bytes([reg & 0xFF]))
        return self._fd.read(1)[0]

    def __enter__(self) -> "_I2CBus":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()


# ── PCA9685 driver ─────────────────────────────────────────────────────────
class PCA9685:
    """
    PCA9685 16-channel 12-bit PWM driver.

    Parameters
    ----------
    bus  : I2C bus number (default 1 → /dev/i2c-1)
    addr : I2C address   (default 0x40)
    """

    CHANNEL_COUNT = 16

    def __init__(self, bus: int = 1, addr: int = 0x40):
        self._bus  = _I2CBus(bus, addr)
        self._freq = 50.0  # Hz (set after open)

    # ── context manager ─────────────────────────────────────────────────────
    def __enter__(self) -> "PCA9685":
        self._bus.open()
        self.reset()
        return self

    def __exit__(self, *_) -> None:
        self._bus.close()

    # ── basic control ────────────────────────────────────────────────────────
    def reset(self) -> None:
        """Software reset — wake chip, enable auto-increment."""
        self._bus.write_byte(_MODE1, _ALLCALL | _AI)
        time.sleep(0.005)

    def set_pwm_freq(self, freq_hz: float = 50.0) -> None:
        """
        Set PWM frequency (24–1526 Hz; 50 Hz for standard servos).

        Must put chip to sleep to write PRESCALE.
        """
        freq_hz = max(24.0, min(1526.0, freq_hz))
        prescale = round(_OSC_CLOCK / (4096.0 * freq_hz)) - 1
        prescale = max(3, min(255, prescale))

        old_mode = self._bus.read_byte(_MODE1)
        sleep_mode = (old_mode & ~_RESTART) | _SLEEP

        self._bus.write_byte(_MODE1, sleep_mode)
        self._bus.write_byte(_PRESCALE, prescale)
        self._bus.write_byte(_MODE1, old_mode)
        time.sleep(0.005)
        # Set RESTART + AI
        self._bus.write_byte(_MODE1, old_mode | _RESTART | _AI)

        self._freq = freq_hz

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        """
        Set raw PWM on/off ticks (0-4095) for a channel.

        on  : tick count when output goes HIGH
        off : tick count when output goes LOW
        """
        if not 0 <= channel < self.CHANNEL_COUNT:
            raise ValueError(f"Channel must be 0–{self.CHANNEL_COUNT - 1}")
        base = _LED0_ON_L + 4 * channel
        self._bus.write_block(base, struct.pack("<HH", on & 0x0FFF, off & 0x0FFF))

    def set_servo_angle(
        self,
        channel: int,
        angle: float,
        min_pulse_us: int = 500,
        max_pulse_us: int = 2500,
    ) -> None:
        """
        Move servo on *channel* to *angle* (0–180°).

        min_pulse_us / max_pulse_us define the pulse range in microseconds.
        Most hobby servos use 500–2500 µs; some use 1000–2000 µs.
        """
        angle = max(0.0, min(180.0, float(angle)))
        pulse_us = min_pulse_us + (max_pulse_us - min_pulse_us) * angle / 180.0
        ticks = int(pulse_us * 4096.0 * self._freq / 1_000_000.0)
        ticks = max(0, min(4095, ticks))
        self.set_pwm(channel, 0, ticks)

    def channel_off(self, channel: int) -> None:
        """Cut power to a single channel (full-off bit)."""
        base = _LED0_ON_L + 4 * channel
        self._bus.write_block(base, b"\x00\x00\x00\x10")  # OFF_H bit4=full-off

    def all_off(self) -> None:
        """Cut PWM on all 16 channels."""
        self._bus.write_byte(_ALL_LED_OFF_H, 0x10)

    def sweep(
        self,
        channel: int,
        angle_start: float = 0.0,
        angle_end: float = 180.0,
        steps: int = 36,
        delay_s: float = 0.03,
        callback=None,
        min_pulse_us: int = 500,
        max_pulse_us: int = 2500,
    ) -> None:
        """
        Sweep servo from angle_start → angle_end → angle_start.

        callback(angle) is called at each step if provided (for UI progress).
        """
        angles = [angle_start + (angle_end - angle_start) * i / steps
                  for i in range(steps + 1)]
        for direction in (angles, list(reversed(angles))):
            for a in direction:
                self.set_servo_angle(channel, a,
                                     min_pulse_us=min_pulse_us,
                                     max_pulse_us=max_pulse_us)
                if callback:
                    callback(a)
                time.sleep(delay_s)

    # ── properties ───────────────────────────────────────────────────────────
    @property
    def freq(self) -> float:
        return self._freq


# ── Detection helper ─────────────────────────────────────────────────────────
def detect_pca9685(bus: int = 1) -> List[DetectedChip]:
    """
    Probe known PCA9685 addresses on *bus* and return those that respond.

    Does NOT require the device to be powered with servos attached;
    just needs a valid I2C response.
    """
    results: List[DetectedChip] = []
    dev_path = f"/dev/i2c-{bus}"
    if not os.path.exists(dev_path):
        return results

    for addr in KNOWN_ADDRESSES:
        try:
            with _I2CBus(bus, addr) as b:
                mode1 = b.read_byte(_MODE1)
                # PCA9685 MODE1 power-on default has bit 4 (SLEEP) set = 0x10
                # We consider any readable response on these addresses as a hit.
                desc = "PCA9685 (sleep)" if (mode1 & _SLEEP) else "PCA9685 (active)"
                results.append(DetectedChip(
                    address=addr,
                    bus=bus,
                    mode1_reg=mode1,
                    description=desc,
                ))
        except OSError:
            pass  # no device at this address

    return results


def get_pca9685(bus: int = 1, addr: int = 0x40) -> PCA9685:
    """Convenience factory — returns an initialised (but not yet opened) PCA9685."""
    return PCA9685(bus=bus, addr=addr)
