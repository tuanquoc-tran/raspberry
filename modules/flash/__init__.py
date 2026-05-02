"""
Flash / Chip Memory Module for RaspFlip
========================================
Supports reading, writing, erasing, and cloning flash memory from:
  1. SPI NOR Flash   (W25Qxx, MX25Lxx, S25FLxx …)  via flashrom + /dev/spidev0.0
  2. STM32           (F0/F1/F4/F7 …)                via UART bootloader + stm32flash
  3. AVR / Arduino   (Atmega328P, Atmega2560 …)      via ISP/ICSP + avrdude linuxspi
  4. I2C EEPROM      (AT24Cxx, 24LCxx …)             via smbus2

Raspberry Pi 4 pinout used by this module
==========================================
SPI NOR Flash  (SPI0):
  GPIO  8 / Pin 24  → CS  (CE0)
  GPIO 10 / Pin 19  → MOSI
  GPIO  9 / Pin 21  → MISO
  GPIO 11 / Pin 23  → CLK
  VCC  3.3 V        → VCC, WP (tie high), HOLD (tie high)

STM32 UART bootloader:
  GPIO 14 / Pin  8  → STM32 RX  (Pi TX)
  GPIO 15 / Pin 10  → STM32 TX  (Pi RX)
  GPIO 17 / Pin 11  → BOOT0     (HIGH = bootloader, LOW = normal)
  GPIO 27 / Pin 13  → NRST      (LOW = reset, HIGH = run)

AVR / Arduino ISP  (SPI0, shared with SPI flash — use separate CS):
  GPIO 10 / Pin 19  → MOSI
  GPIO  9 / Pin 21  → MISO
  GPIO 11 / Pin 23  → SCK
  GPIO 25 / Pin 22  → RESET (active LOW)

I2C EEPROM  (I2C1):
  GPIO  2 / Pin  3  → SDA
  GPIO  3 / Pin  5  → SCL
  A0/A1/A2          → GND (device address bits, default 0x50)
"""

import os
import re
import time
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPIO pins (BCM numbering)
# ---------------------------------------------------------------------------
PIN_STM32_BOOT0 = 17
PIN_STM32_NRST  = 27
PIN_AVR_RESET   = 25

# ---------------------------------------------------------------------------
# Supported chip lists (display only — flashrom/avrdude use their own DB)
# ---------------------------------------------------------------------------
SPI_FLASH_COMMON = [
    "W25Q32",  "W25Q64",  "W25Q128", "W25Q256",
    "MX25L3205D", "MX25L6405D", "MX25L12805D",
    "S25FL032P", "S25FL064P", "S25FL128S",
    "AT25DF321", "GD25Q64", "EN25Q64",
]

AVR_MCU_COMMON = {
    "atmega328p":  {"flash_kb": 32,  "eeprom_b": 1024, "board": "Arduino Uno/Nano"},
    "atmega2560":  {"flash_kb": 256, "eeprom_b": 4096, "board": "Arduino Mega"},
    "atmega32u4":  {"flash_kb": 32,  "eeprom_b": 1024, "board": "Arduino Leonardo/Micro"},
    "attiny85":    {"flash_kb": 8,   "eeprom_b": 512,  "board": "Digispark"},
    "attiny2313":  {"flash_kb": 2,   "eeprom_b": 128,  "board": "Standalone"},
}

STM32_COMMON = [
    "STM32F030", "STM32F103", "STM32F401",
    "STM32F407", "STM32F411", "STM32F446",
    "STM32G071", "STM32L432",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], sudo: bool = False, timeout: int = 60,
         env: Optional[Dict] = None) -> subprocess.CompletedProcess:
    if sudo:
        cmd = ["sudo"] + cmd
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, **(env or {})}
    )


def _tool_exists(name: str) -> bool:
    return subprocess.run(["which", name], capture_output=True).returncode == 0


def _gpio_set(pin: int, value: int) -> None:
    """Set a GPIO pin using RPi.GPIO (best-effort — module may not be available)."""
    try:
        import RPi.GPIO as GPIO
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, value)
    except Exception as e:
        logger.warning(f"GPIO set pin {pin}={value} failed: {e}")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ChipInfo:
    target:      str            # 'spi_flash' | 'stm32' | 'avr' | 'i2c_eeprom'
    name:        str            # chip name from tool output
    flash_size:  Optional[int]  # bytes
    page_size:   Optional[int]  # bytes
    extra:       Dict[str, Any] = field(default_factory=dict)


@dataclass
class FlashOperation:
    success:  bool
    message:  str
    file:     Optional[str] = None
    size:     Optional[int] = None  # bytes transferred


# ---------------------------------------------------------------------------
# SPI NOR Flash  (via flashrom)
# ---------------------------------------------------------------------------

class SPIFlashTool:
    """
    Read/write/erase SPI NOR flash chips using flashrom with the
    Raspberry Pi's hardware SPI (programmer: linux_spi:dev=/dev/spidev0.0).

    Requires:
      sudo apt install flashrom
      /boot/config.txt: dtparam=spi=on
    """

    PROGRAMMER = "linux_spi:dev=/dev/spidev0.0,spispeed=4000"

    def probe(self) -> Optional[ChipInfo]:
        """Auto-detect chip on SPI bus."""
        if not _tool_exists("flashrom"):
            logger.error("flashrom not installed. Run: sudo apt install flashrom")
            return None

        r = _run(["flashrom", "-p", self.PROGRAMMER], sudo=True)
        # flashrom prints chip name when found
        m = re.search(r'Found\s+\S+\s+flash chip\s+"([^"]+)"\s+\((\d+)\s+kB', r.stdout + r.stderr)
        if not m:
            logger.error(f"No SPI flash detected.\n{r.stderr.strip()}")
            return None

        name = m.group(1)
        size_kb = int(m.group(2))

        # Try to find page size
        page = 256  # typical default
        pm = re.search(r'page size\s*[=:]\s*(\d+)', r.stdout + r.stderr, re.I)
        if pm:
            page = int(pm.group(1))

        return ChipInfo(
            target="spi_flash",
            name=name,
            flash_size=size_kb * 1024,
            page_size=page,
        )

    def read(self, output_file: str, chip: Optional[str] = None) -> FlashOperation:
        """Read entire flash to file (binary image)."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        cmd = ["flashrom", "-p", self.PROGRAMMER, "-r", output_file]
        if chip:
            cmd += ["-c", chip]
        r = _run(cmd, sudo=True, timeout=120)
        ok = r.returncode == 0
        msg = "Read OK" if ok else r.stderr.strip() or r.stdout.strip()
        size = os.path.getsize(output_file) if ok and os.path.exists(output_file) else None
        return FlashOperation(success=ok, message=msg, file=output_file, size=size)

    def write(self, input_file: str, chip: Optional[str] = None,
              verify: bool = True) -> FlashOperation:
        """Write image file to flash (erase-then-write)."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        cmd = ["flashrom", "-p", self.PROGRAMMER, "-w", input_file]
        if chip:
            cmd += ["-c", chip]
        if not verify:
            cmd.append("--noverify")
        r = _run(cmd, sudo=True, timeout=300)
        ok = r.returncode == 0
        msg = "Write+Verify OK" if ok else r.stderr.strip() or r.stdout.strip()
        return FlashOperation(success=ok, message=msg, file=input_file,
                              size=os.path.getsize(input_file))

    def erase(self, chip: Optional[str] = None) -> FlashOperation:
        """Erase entire chip."""
        cmd = ["flashrom", "-p", self.PROGRAMMER, "-E"]
        if chip:
            cmd += ["-c", chip]
        r = _run(cmd, sudo=True, timeout=180)
        ok = r.returncode == 0
        msg = "Erase OK" if ok else r.stderr.strip()
        return FlashOperation(success=ok, message=msg)

    def verify(self, input_file: str, chip: Optional[str] = None) -> FlashOperation:
        """Verify flash content matches file."""
        cmd = ["flashrom", "-p", self.PROGRAMMER, "-v", input_file]
        if chip:
            cmd += ["-c", chip]
        r = _run(cmd, sudo=True, timeout=120)
        ok = r.returncode == 0
        msg = "Verify OK — flash matches file" if ok else r.stderr.strip()
        return FlashOperation(success=ok, message=msg, file=input_file)

    def clone(self, tmp_file: str, chip_src: Optional[str] = None,
              chip_dst: Optional[str] = None) -> FlashOperation:
        """
        Read from source chip, write to destination chip.
        Swap chips between read and write steps.
        """
        op = self.read(tmp_file, chip=chip_src)
        if not op.success:
            return FlashOperation(success=False, message=f"Clone READ failed: {op.message}")
        return FlashOperation(
            success=True,
            message=f"Clone image saved to {tmp_file} ({op.size} bytes). "
                    "Replace chip and call write() to program destination.",
            file=tmp_file,
            size=op.size,
        )


# ---------------------------------------------------------------------------
# STM32 via UART bootloader  (stm32flash)
# ---------------------------------------------------------------------------

class STM32Tool:
    """
    Program STM32 microcontrollers via the built-in UART bootloader.

    Physical connection (RPi4 ↔ STM32):
      GPIO14 (TX) → STM32 RX (e.g. PA10 on F103, PA3 on F4 USART2)
      GPIO15 (RX) → STM32 TX
      GPIO17      → BOOT0  (set HIGH to enter bootloader)
      GPIO27      → NRST   (active-LOW reset)

    BOOT0 must be HIGH and a reset pulse applied to enter bootloader.
    After programming set BOOT0 LOW and reset to run firmware.

    Requires: sudo apt install stm32flash
    """

    def __init__(self, port: str = "/dev/serial0", baud: int = 115200):
        self.port = port
        self.baud = baud

    def _enter_bootloader(self) -> None:
        """Pulse BOOT0 HIGH + NRST LOW→HIGH to enter bootloader mode."""
        _gpio_set(PIN_STM32_BOOT0, 1)   # BOOT0 HIGH
        time.sleep(0.05)
        _gpio_set(PIN_STM32_NRST, 0)    # RESET low
        time.sleep(0.1)
        _gpio_set(PIN_STM32_NRST, 1)    # RESET release
        time.sleep(0.2)                  # wait for bootloader ready

    def _exit_bootloader(self) -> None:
        """Set BOOT0 LOW + reset → run application."""
        _gpio_set(PIN_STM32_BOOT0, 0)
        time.sleep(0.05)
        _gpio_set(PIN_STM32_NRST, 0)
        time.sleep(0.1)
        _gpio_set(PIN_STM32_NRST, 1)
        time.sleep(0.1)

    def probe(self) -> Optional[ChipInfo]:
        """Detect STM32 chip via bootloader."""
        if not _tool_exists("stm32flash"):
            logger.error("stm32flash not installed. Run: sudo apt install stm32flash")
            return None
        self._enter_bootloader()
        r = _run(["stm32flash", self.port], sudo=False, timeout=10)
        if r.returncode != 0:
            logger.error(f"STM32 probe failed: {r.stderr.strip() or r.stdout.strip()}")
            return None

        name  = re.search(r'Device\s+ID\s*[=:]\s*(.+)', r.stdout)
        flash = re.search(r'RAM\s*[=:]\s*\S+\s*Flash\s*[=:]\s*(\d+)\s*KiB', r.stdout, re.I)
        return ChipInfo(
            target="stm32",
            name=name.group(1).strip() if name else "STM32 (unknown)",
            flash_size=int(flash.group(1)) * 1024 if flash else None,
            page_size=None,
            extra={"raw": r.stdout},
        )

    def read(self, output_file: str) -> FlashOperation:
        """Read entire flash memory to binary file."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        self._enter_bootloader()
        r = _run(["stm32flash", "-r", output_file, self.port], timeout=120)
        ok = r.returncode == 0
        size = os.path.getsize(output_file) if ok and os.path.exists(output_file) else None
        self._exit_bootloader()
        return FlashOperation(success=ok,
                              message="Read OK" if ok else r.stderr.strip(),
                              file=output_file, size=size)

    def write(self, input_file: str, verify: bool = True,
              start_addr: str = "0x08000000") -> FlashOperation:
        """Write firmware (.bin or .hex) to STM32 flash."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        self._enter_bootloader()
        cmd = ["stm32flash", "-w", input_file, "-S", start_addr]
        if verify:
            cmd.append("-v")
        cmd.append(self.port)
        r = _run(cmd, timeout=300)
        ok = r.returncode == 0
        msg = "Write OK" if ok else r.stderr.strip()
        self._exit_bootloader()
        return FlashOperation(success=ok, message=msg, file=input_file,
                              size=os.path.getsize(input_file))

    def erase(self) -> FlashOperation:
        """Mass-erase entire STM32 flash."""
        self._enter_bootloader()
        r = _run(["stm32flash", "-o", self.port], timeout=60)
        ok = r.returncode == 0
        self._exit_bootloader()
        return FlashOperation(success=ok,
                              message="Erase OK" if ok else r.stderr.strip())

    def clone(self, source_file: str, target_file: Optional[str] = None) -> FlashOperation:
        """Read firmware from one STM32 and optionally write to another."""
        op = self.read(source_file)
        if not op.success:
            return op
        msg = (f"Firmware saved ({op.size} bytes) → {source_file}. "
               "Swap chip and call write() to clone.")
        return FlashOperation(success=True, message=msg, file=source_file, size=op.size)


# ---------------------------------------------------------------------------
# AVR / Arduino via ISP  (avrdude + linuxspi)
# ---------------------------------------------------------------------------

class AVRTool:
    """
    Program AVR microcontrollers (Arduino Uno/Mega/Nano etc.) via SPI ISP.

    The Raspberry Pi acts as an ISP programmer using its hardware SPI0.
    avrdude programmer: linuxspi (uses /dev/spidev0.0 + GPIO for RESET)

    Physical connection:
      GPIO10 / MOSI → AVR MOSI (Arduino ICSP pin 4)
      GPIO 9 / MISO → AVR MISO (Arduino ICSP pin 1)
      GPIO11 / SCK  → AVR SCK  (Arduino ICSP pin 3)
      GPIO25        → AVR RESET (Arduino ICSP pin 5) active LOW
      3.3V or 5V    → VCC  (Arduino pin)  — check AVR voltage!

    Requires: sudo apt install avrdude
    """

    PROGRAMMER = f"linuxspi:dev=/dev/spidev0.0,reset={PIN_AVR_RESET}"

    def __init__(self, mcu: str = "atmega328p", baud: int = 400000):
        self.mcu  = mcu
        self.baud = baud

    def probe(self) -> Optional[ChipInfo]:
        """Read device signature to identify AVR chip."""
        if not _tool_exists("avrdude"):
            logger.error("avrdude not installed. Run: sudo apt install avrdude")
            return None
        r = _run(["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
                  "-b", str(self.baud), "-n"], sudo=True, timeout=15)
        ok = r.returncode == 0
        sig = re.search(r'Device signature\s*=\s*(0x\w+)', r.stderr + r.stdout)
        info = AVR_MCU_COMMON.get(self.mcu, {})
        if not ok and "initialization failed" in (r.stderr + r.stdout):
            return None
        return ChipInfo(
            target="avr",
            name=self.mcu.upper(),
            flash_size=info.get("flash_kb", 0) * 1024,
            page_size=128,
            extra={
                "signature": sig.group(1) if sig else "?",
                "eeprom_bytes": info.get("eeprom_b", 0),
                "board": info.get("board", ""),
            }
        )

    def read_flash(self, output_file: str) -> FlashOperation:
        """Read program flash to Intel HEX file."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        r = _run(["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
                  "-b", str(self.baud),
                  "-U", f"flash:r:{output_file}:i"],   # :i = Intel HEX
                 sudo=True, timeout=120)
        ok = r.returncode == 0
        size = os.path.getsize(output_file) if ok and os.path.exists(output_file) else None
        return FlashOperation(success=ok,
                              message="Flash read OK" if ok else r.stderr.strip(),
                              file=output_file, size=size)

    def write_flash(self, input_file: str, verify: bool = True) -> FlashOperation:
        """Write Intel HEX or binary firmware to program flash."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        fmt = "i" if input_file.endswith(".hex") else "r"
        cmd = ["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
               "-b", str(self.baud),
               "-U", f"flash:w:{input_file}:{fmt}"]
        if not verify:
            cmd.append("-V")
        r = _run(cmd, sudo=True, timeout=300)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="Flash write OK" if ok else r.stderr.strip(),
                              file=input_file,
                              size=os.path.getsize(input_file))

    def read_eeprom(self, output_file: str) -> FlashOperation:
        """Read EEPROM to Intel HEX file."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        r = _run(["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
                  "-b", str(self.baud),
                  "-U", f"eeprom:r:{output_file}:i"],
                 sudo=True, timeout=60)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="EEPROM read OK" if ok else r.stderr.strip(),
                              file=output_file)

    def write_eeprom(self, input_file: str) -> FlashOperation:
        """Write Intel HEX data to EEPROM."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        r = _run(["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
                  "-b", str(self.baud),
                  "-U", f"eeprom:w:{input_file}:i"],
                 sudo=True, timeout=120)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="EEPROM write OK" if ok else r.stderr.strip(),
                              file=input_file)

    def read_fuses(self) -> Dict[str, str]:
        """Read low, high, and extended fuse bytes."""
        fuses: Dict[str, str] = {}
        for fuse in ("lfuse", "hfuse", "efuse"):
            tmp = f"/tmp/{fuse}.hex"
            r = _run(["avrdude", "-p", self.mcu, "-c", self.PROGRAMMER,
                      "-b", str(self.baud),
                      "-U", f"{fuse}:r:{tmp}:h"],
                     sudo=True, timeout=15)
            if r.returncode == 0 and os.path.exists(tmp):
                with open(tmp) as f:
                    fuses[fuse] = f.read().strip()
        return fuses

    def clone_flash(self, tmp_file: str) -> FlashOperation:
        """Read flash from one AVR — swap chip — write to clone."""
        op = self.read_flash(tmp_file)
        if not op.success:
            return op
        return FlashOperation(
            success=True,
            message=f"Firmware saved ({op.size} bytes) → {tmp_file}. "
                    "Swap AVR chip and call write_flash() to clone.",
            file=tmp_file, size=op.size,
        )


# ---------------------------------------------------------------------------
# AVR / Arduino via USB Serial  (avrdude + arduino bootloader)
# ---------------------------------------------------------------------------

def _find_avr_usb_port() -> Optional[str]:
    """Auto-detect Arduino USB serial port (/dev/ttyACM* or /dev/ttyUSB*)."""
    import glob
    for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
        ports = sorted(glob.glob(pattern))
        if ports:
            return ports[0]
    return None


class AVRUSBTool:
    """
    Program AVR/Arduino via USB serial (Optiboot bootloader).

    Dùng kết nối USB thông thường — không cần dây SPI/ISP.
    Arduino UNO R3 phải có bootloader Optiboot còn nguyên.

    avrdude programmer: arduino  (stk500v1 protocol qua serial)

    Physical connection:
      Cắm cáp USB từ Arduino → Raspberry Pi
      Port xuất hiện: /dev/ttyACM0  (chip ATmega16U2)
                   hoặc /dev/ttyUSB0  (chip CH340 — bản clone)

    Giới hạn so với ISP:
      ✓ Read flash, Write flash, Read EEPROM, Write EEPROM
      ✗ Read/Write fuse bytes  (bootloader không hỗ trợ)
      ✗ Unlock/lock bits
      ✗ Chip erase toàn bộ (chỉ erase vùng app, không xoá bootloader)

    Requires: sudo apt install avrdude
    """

    def __init__(self, mcu: str = "atmega328p",
                 port: Optional[str] = None,
                 baud: int = 115200):
        self.mcu  = mcu
        self.port = port or _find_avr_usb_port() or "/dev/ttyACM0"
        self.baud = baud

    def _base_cmd(self) -> List[str]:
        return ["avrdude", "-p", self.mcu,
                "-c", "arduino",
                "-P", self.port,
                "-b", str(self.baud)]

    def probe(self) -> Optional[ChipInfo]:
        """Detect AVR chip via bootloader (reads device signature)."""
        if not _tool_exists("avrdude"):
            logger.error("avrdude not installed. Run: sudo apt install avrdude")
            return None
        r = _run(self._base_cmd() + ["-n"], sudo=False, timeout=10)
        ok = r.returncode == 0
        sig = re.search(r'Device signature\s*=\s*(0x\w+)', r.stderr + r.stdout)
        if not ok and "not in sync" in (r.stderr + r.stdout):
            logger.error("Arduino not responding — check port, baud, or reset Arduino")
            return None
        if not ok and "programmer is not responding" in (r.stderr + r.stdout):
            return None
        info = AVR_MCU_COMMON.get(self.mcu, {})
        return ChipInfo(
            target="avr_usb",
            name=self.mcu.upper(),
            flash_size=info.get("flash_kb", 0) * 1024,
            page_size=128,
            extra={
                "signature": sig.group(1) if sig else "?",
                "eeprom_bytes": info.get("eeprom_b", 0),
                "board": info.get("board", ""),
                "port": self.port,
                "baud": self.baud,
                "programmer": "arduino (USB bootloader)",
            }
        )

    def read_flash(self, output_file: str) -> FlashOperation:
        """Read program flash to Intel HEX file."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        r = _run(self._base_cmd() + ["-U", f"flash:r:{output_file}:i"],
                 sudo=False, timeout=120)
        ok = r.returncode == 0
        size = os.path.getsize(output_file) if ok and os.path.exists(output_file) else None
        return FlashOperation(success=ok,
                              message="Flash read OK" if ok else r.stderr.strip(),
                              file=output_file, size=size)

    def write_flash(self, input_file: str, verify: bool = True) -> FlashOperation:
        """Write Intel HEX firmware to flash via bootloader."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        fmt = "i" if input_file.endswith(".hex") else "r"
        cmd = self._base_cmd() + ["-U", f"flash:w:{input_file}:{fmt}"]
        if not verify:
            cmd.append("-V")
        r = _run(cmd, sudo=False, timeout=300)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="Flash write OK" if ok else r.stderr.strip(),
                              file=input_file,
                              size=os.path.getsize(input_file))

    def read_eeprom(self, output_file: str) -> FlashOperation:
        """Read EEPROM (1KB on UNO) to Intel HEX file."""
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        r = _run(self._base_cmd() + ["-U", f"eeprom:r:{output_file}:i"],
                 sudo=False, timeout=60)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="EEPROM read OK" if ok else r.stderr.strip(),
                              file=output_file)

    def write_eeprom(self, input_file: str) -> FlashOperation:
        """Write Intel HEX data to EEPROM."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        r = _run(self._base_cmd() + ["-U", f"eeprom:w:{input_file}:i"],
                 sudo=False, timeout=120)
        ok = r.returncode == 0
        return FlashOperation(success=ok,
                              message="EEPROM write OK" if ok else r.stderr.strip(),
                              file=input_file)

    def clone_flash(self, tmp_file: str, clone_eeprom: bool = False) -> FlashOperation:
        """
        Bước 1+2 của quy trình clone: đọc flash (và EEPROM) từ board nguồn.
        Sau đó user đổi board, gọi write_flash() để hoàn tất.
        """
        op = self.read_flash(tmp_file)
        if not op.success:
            return FlashOperation(success=False,
                                  message=f"Read flash thất bại: {op.message}")
        eeprom_file: Optional[str] = None
        if clone_eeprom:
            eeprom_file = tmp_file.replace(".hex", "_eeprom.hex")
            if not eeprom_file.endswith("_eeprom.hex"):
                eeprom_file = tmp_file + "_eeprom.hex"
            op_e = self.read_eeprom(eeprom_file)
            if not op_e.success:
                return FlashOperation(success=False,
                                      message=f"Read EEPROM thất bại: {op_e.message}")
        summary = (
            f"Flash đã lưu: {tmp_file} ({op.size} bytes)\n"
            + (f"EEPROM đã lưu: {eeprom_file}\n" if eeprom_file else "")
            + f"Cắm board đích, sau đó gọi write_flash('{tmp_file}') để hoàn tất clone."
        )
        return FlashOperation(success=True, message=summary,
                              file=tmp_file, size=op.size)

    def clone_write(self, tmp_file: str, clone_eeprom: bool = False) -> FlashOperation:
        """Bước 3+4: ghi flash (và EEPROM) lên board đích sau khi đã đọc xong."""
        op_w = self.write_flash(tmp_file)
        if not op_w.success:
            return FlashOperation(success=False,
                                  message=f"Write flash thất bại: {op_w.message}")
        if clone_eeprom:
            eeprom_file = tmp_file.replace(".hex", "_eeprom.hex")
            if not eeprom_file.endswith("_eeprom.hex"):
                eeprom_file = tmp_file + "_eeprom.hex"
            op_e = self.write_eeprom(eeprom_file)
            if not op_e.success:
                return FlashOperation(success=False,
                                      message=f"Write EEPROM thất bại: {op_e.message}")
        return FlashOperation(success=True,
                              message="Clone hoàn tất! Flash"
                              + (" + EEPROM" if clone_eeprom else "")
                              + " đã được sao chép.",
                              file=tmp_file, size=op_w.size)


# ---------------------------------------------------------------------------
# I2C EEPROM  (AT24Cxx via smbus2)
# ---------------------------------------------------------------------------

class I2CEEPROMTool:
    """
    Read/write I2C EEPROM chips (AT24C01 … AT24C512, 24LCxx …).

    Physical connection (RPi4 I2C1):
      GPIO2 / Pin 3  → SDA
      GPIO3 / Pin 5  → SCL
      A0/A1/A2 → GND → I2C address = 0x50 (default)
      VCC → 3.3V or 5V (check datasheet — RPi I2C is 3.3V)
      WP  → GND (write enabled)

    Requires: pip install smbus2
    """

    PAGE_SIZE = {
        "AT24C01":  8,   "AT24C02":  8,   "AT24C04":  16,
        "AT24C08":  16,  "AT24C16":  16,  "AT24C32":  32,
        "AT24C64":  32,  "AT24C128": 64,  "AT24C256": 64,
        "AT24C512": 128,
    }

    CHIP_SIZE = {
        "AT24C01":  128,    "AT24C02":  256,    "AT24C04":  512,
        "AT24C08":  1024,   "AT24C16":  2048,   "AT24C32":  4096,
        "AT24C64":  8192,   "AT24C128": 16384,  "AT24C256": 32768,
        "AT24C512": 65536,
    }

    def __init__(self, bus: int = 1, address: int = 0x50,
                 chip: str = "AT24C256"):
        self.bus     = bus
        self.address = address
        self.chip    = chip.upper()
        self.size    = self.CHIP_SIZE.get(self.chip, 32768)
        self.page    = self.PAGE_SIZE.get(self.chip, 64)

    def _get_smbus(self):
        try:
            from smbus2 import SMBus
            return SMBus(self.bus)
        except ImportError:
            raise RuntimeError("smbus2 not installed. Run: pip install smbus2")

    def probe(self) -> Optional[ChipInfo]:
        """Try to read address 0 to confirm EEPROM is present."""
        try:
            bus = self._get_smbus()
            with bus:
                bus.read_byte_data(self.address, 0)
            return ChipInfo(
                target="i2c_eeprom",
                name=self.chip,
                flash_size=self.size,
                page_size=self.page,
                extra={"i2c_address": hex(self.address), "bus": self.bus},
            )
        except OSError:
            logger.error(f"No I2C EEPROM at 0x{self.address:02X} on bus {self.bus}")
            return None

    def read(self, output_file: str,
             start: int = 0, length: Optional[int] = None) -> FlashOperation:
        """Read bytes from EEPROM to binary file."""
        length = length or (self.size - start)
        os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
        data = bytearray()
        try:
            bus = self._get_smbus()
            with bus:
                addr = start
                remaining = length
                while remaining > 0:
                    chunk = min(remaining, 32)
                    # 16-bit address for chips > 256 bytes
                    hi = (addr >> 8) & 0xFF
                    lo = addr & 0xFF
                    if self.size <= 256:
                        raw = bus.read_i2c_block_data(self.address, lo, chunk)
                    else:
                        bus.write_byte_data(self.address, hi, lo)
                        raw = bus.read_i2c_block_data(self.address, lo, chunk)
                    data.extend(raw[:chunk])
                    addr += chunk
                    remaining -= chunk
                    time.sleep(0.005)
            with open(output_file, "wb") as f:
                f.write(data)
            return FlashOperation(success=True, message="EEPROM read OK",
                                  file=output_file, size=len(data))
        except Exception as e:
            return FlashOperation(success=False, message=str(e))

    def write(self, input_file: str, start: int = 0) -> FlashOperation:
        """Write binary file to EEPROM (page-write mode)."""
        if not os.path.exists(input_file):
            return FlashOperation(success=False, message=f"File not found: {input_file}")
        with open(input_file, "rb") as f:
            data = f.read()
        if start + len(data) > self.size:
            return FlashOperation(success=False,
                message=f"Data too large: {len(data)} bytes starting at {start} "
                        f"exceeds chip size {self.size}")
        try:
            bus = self._get_smbus()
            with bus:
                offset = 0
                addr = start
                while offset < len(data):
                    # Align to page boundary
                    page_offset = addr % self.page
                    chunk = min(self.page - page_offset, len(data) - offset)
                    payload = list(data[offset:offset + chunk])
                    hi = (addr >> 8) & 0xFF
                    lo = addr & 0xFF
                    if self.size <= 256:
                        bus.write_i2c_block_data(self.address, lo, payload)
                    else:
                        bus.write_i2c_block_data(
                            self.address, hi, [lo] + payload
                        )
                    offset += chunk
                    addr   += chunk
                    time.sleep(0.01)  # AT24Cxx write cycle ~5ms, be safe
            return FlashOperation(success=True, message="EEPROM write OK",
                                  file=input_file, size=len(data))
        except Exception as e:
            return FlashOperation(success=False, message=str(e))

    def erase(self, fill: int = 0xFF) -> FlashOperation:
        """Fill entire EEPROM with fill byte (0xFF = erased state)."""
        import tempfile
        tmp = tempfile.mktemp(suffix=".bin")
        with open(tmp, "wb") as f:
            f.write(bytes([fill]) * self.size)
        op = self.write(tmp, start=0)
        os.unlink(tmp)
        return FlashOperation(success=op.success,
                              message="EEPROM erase OK" if op.success else op.message,
                              size=self.size)

    def scan_bus(self) -> List[int]:
        """Scan I2C bus and return list of responding addresses."""
        found = []
        try:
            bus = self._get_smbus()
            with bus:
                for addr in range(0x03, 0x78):
                    try:
                        bus.read_byte(addr)
                        found.append(addr)
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"I2C scan failed: {e}")
        return found


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def get_tool(target: str, **kwargs):
    """
    Factory for flash tools.

    target: 'spi'  | 'stm32' | 'avr' | 'i2c'
    kwargs: passed to the tool constructor
    """
    target = target.lower()
    if target == "spi":
        return SPIFlashTool()
    elif target == "stm32":
        return STM32Tool(**kwargs)
    elif target == "avr":
        return AVRTool(**kwargs)
    elif target in ("i2c", "eeprom", "i2c_eeprom"):
        return I2CEEPROMTool(**kwargs)
    else:
        raise ValueError(f"Unknown target: {target!r}. Use 'spi', 'stm32', 'avr', 'i2c'")


def check_tools() -> Dict[str, bool]:
    """Check which required system tools are installed."""
    return {
        "flashrom":   _tool_exists("flashrom"),
        "stm32flash": _tool_exists("stm32flash"),
        "avrdude":    _tool_exists("avrdude"),
        "smbus2":     _module_exists("smbus2"),
    }


def _module_exists(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Remote Flash Server  (HTTP, LAN only)
# ---------------------------------------------------------------------------

class RemoteFlashServer:
    """
    Lightweight HTTP server that accepts firmware uploads over the network
    and programs them into chips connected to this Raspberry Pi.

    Security model:
      - Shared-secret token in X-Auth-Token header (every request)
      - Intended for LAN use only — do NOT expose to the internet

    Endpoints:
      GET  /status   → JSON {"status":"ok","targets":[...]}
      POST /flash    → JSON body → program chip → JSON result

    POST /flash body (JSON):
      {
        "target":   "avr" | "stm32" | "spi",
        "mcu":      "atmega328p",          # AVR only
        "port":     "/dev/serial0",        # STM32 only
        "filename": "sketch.hex",          # for extension detection
        "file_b64": "<base64 content>",    # hex or bin file
        "verify":   true
      }

    Usage from laptop:
      python scripts/remote_flash.py --host raspberrypi.local \\
          --token <token> --target avr firmware.hex
    """

    DEFAULT_PORT = 7777

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_PORT,
                 token: Optional[str] = None):
        self.host  = host
        self.port  = port
        import secrets
        self.token = token or secrets.token_hex(16)
        self._server = None

    def start(self, blocking: bool = True) -> None:
        """Start the HTTP server. Blocks until stop() is called (if blocking=True)."""
        import json
        import base64
        import tempfile
        from http.server import HTTPServer, BaseHTTPRequestHandler

        server_token = self.token

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):  # suppress default stderr log
                logger.debug("[RemoteFlash] " + fmt % args)

            def _auth(self) -> bool:
                return self.headers.get("X-Auth-Token") == server_token

            def _send_json(self, code: int, data: dict) -> None:
                body = json.dumps(data).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                if not self._auth():
                    self._send_json(401, {"error": "unauthorized"})
                    return
                if self.path == "/status":
                    self._send_json(200, {
                        "status":  "ok",
                        "targets": ["avr", "stm32", "spi"],
                    })
                else:
                    self._send_json(404, {"error": "not found"})

            def do_POST(self):
                if not self._auth():
                    self._send_json(401, {"error": "unauthorized"})
                    return
                if self.path != "/flash":
                    self._send_json(404, {"error": "not found"})
                    return

                try:
                    length  = int(self.headers.get("Content-Length", 0))
                    if length > 32 * 1024 * 1024:  # 32 MB sanity limit
                        self._send_json(413, {"error": "payload too large"})
                        return
                    body     = json.loads(self.rfile.read(length))
                    target   = str(body.get("target", "avr")).lower()
                    filename = os.path.basename(str(body.get("filename", "firmware.bin")))
                    file_b64 = str(body.get("file_b64", ""))
                    mcu      = str(body.get("mcu", "atmega328p"))
                    port     = str(body.get("port", "/dev/serial0"))
                    verify   = bool(body.get("verify", True))

                    # Validate target
                    if target not in ("avr", "stm32", "spi"):
                        self._send_json(400, {"error": f"unknown target: {target}"})
                        return

                    # Decode firmware
                    data = base64.b64decode(file_b64)
                    ext  = os.path.splitext(filename)[1].lower() or ".bin"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
                        f.write(data)
                        tmp_path = f.name

                    try:
                        if target == "avr":
                            op = AVRTool(mcu=mcu).write_flash(tmp_path, verify=verify)
                        elif target == "stm32":
                            op = STM32Tool(port=port).write(tmp_path, verify=verify)
                        elif target == "spi":
                            op = SPIFlashTool().write(tmp_path, verify=verify)
                        else:
                            op = FlashOperation(success=False, message="unreachable")
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass

                    self._send_json(200 if op.success else 500, {
                        "success": op.success,
                        "message": op.message,
                        "size":    op.size,
                    })

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    self._send_json(400, {"error": f"bad request: {e}"})
                except Exception as e:
                    logger.error(f"RemoteFlash error: {e}")
                    self._send_json(500, {"success": False, "message": str(e)})

        from http.server import HTTPServer
        self._server = HTTPServer((self.host, self.port), _Handler)
        logger.info(f"RemoteFlashServer listening on {self.host}:{self.port}")
        if blocking:
            self._server.serve_forever()

    def stop(self) -> None:
        """Shut down the HTTP server."""
        if self._server:
            self._server.shutdown()
            self._server = None
