"""
Hardware Monitor Module for RaspFlip
======================================
Collects hardware information from Raspberry Pi:
  - CPU model, cores, frequency, usage, temperature
  - RAM & Swap usage
  - Storage partitions, SD card info
  - Network interfaces, gateway, DNS
  - USB devices with board identification (Arduino, STM32, Pico …)
  - I2C bus scan with device recognition
  - SPI / GPIO / UART / 1-Wire interface status

No external libraries required — uses /proc, /sys, sysfs and system tools
(vcgencmd, i2cdetect, lsusb, ip, gpiodetect).

Usage
=====
    from modules.hardware import get_monitor

    mon = get_monitor()
    ov  = mon.get_overview()     # SystemOverview
    th  = mon.get_thermal()      # ThermalInfo
    cpu = mon.get_cpu()          # CPUInfo
    mem = mon.get_memory()       # MemoryInfo
    dis = mon.get_storage()      # List[DiskEntry]
    net = mon.get_network()      # NetworkInfo
    usb = mon.get_usb()          # USBInfo
    i2c = mon.scan_i2c()         # List[I2CDevice]
    ifc = mon.get_interfaces()   # InterfaceInfo
"""

import os
import re
import glob
import shutil
import platform
import subprocess
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# VID:PID database — USB board identification
# ---------------------------------------------------------------------------
BOARD_MAP: Dict[str, str] = {
    "2341:0043": "Arduino Uno R3 (ATmega16U2)",
    "2341:0001": "Arduino Uno (DFU)",
    "2341:0010": "Arduino Mega 2560",
    "2341:0036": "Arduino Leonardo",
    "2341:003d": "Arduino Micro",
    "2341:0042": "Arduino Mega 2560 R3",
    "1a86:7523": "CH340 (Arduino clone / USB-Serial)",
    "1a86:5523": "CH341 USB-Serial",
    "0403:6001": "FT232RL (FTDI USB-Serial)",
    "0403:6015": "FT231XS (FTDI USB-Serial)",
    "0403:6010": "FT2232 (FTDI dual USB-Serial)",
    "10c4:ea60": "CP2102 (Silicon Labs USB-Serial)",
    "10c4:ea70": "CP2105 (Silicon Labs dual USB-Serial)",
    "16c0:0483": "Teensy USB Device",
    "239a:800b": "Adafruit Feather M0",
    "239a:8022": "Adafruit Circuit Playground Express",
    "0d28:0204": "BBC micro:bit",
    "2e8a:0005": "Raspberry Pi Pico (MicroPython)",
    "2e8a:0003": "Raspberry Pi Pico (RP2040 Boot ROM)",
    "2e8a:000a": "Raspberry Pi Pico W",
    "0483:df11": "STM32 DFU Bootloader",
    "0483:3748": "STLink/V2",
    "0483:374b": "STLink/V2-1",
    "0483:374e": "STLink/V3",
    "04b4:f13b": "Cypress FX2LP (logic analyzer)",
    "0925:3881": "LPC Link2 (NXP debugger)",
    "1366:0101": "J-Link (SEGGER debugger)",
    "0a5c:21e8": "BCM43455 Bluetooth (RPi4 built-in)",
}

# ---------------------------------------------------------------------------
# I2C device address database
# ---------------------------------------------------------------------------
I2C_KNOWN: Dict[int, str] = {
    0x20: "PCF8574 GPIO expander",
    0x21: "PCF8574 GPIO expander",
    0x27: "PCF8574 GPIO expander / LCD I2C backpack",
    0x3C: "SSD1306 OLED 128x64",
    0x3D: "SSD1306 OLED 128x32",
    0x40: "INA219 power monitor / PCA9685 PWM driver",
    0x41: "INA219 (addr A0=1)",
    0x44: "SHT30/SHT31 humidity+temp",
    0x45: "SHT30/SHT31 (addr A=1)",
    0x48: "ADS1115 ADC / PCF8591 ADC / LM75 temp",
    0x4A: "ADS1015 ADC",
    0x50: "AT24C EEPROM",
    0x51: "AT24C EEPROM",
    0x52: "AT24C EEPROM",
    0x57: "AT24C EEPROM / DS2482 1-Wire bridge",
    0x5A: "MLX90614 IR temperature",
    0x60: "SI5351 clock generator / MPL3115A2 pressure",
    0x68: "DS3231/DS1307 RTC / MPU-6050 IMU",
    0x69: "MPU-6050 IMU (AD0=HIGH) / ITG-3200 gyro",
    0x70: "TCA9548A I2C multiplexer",
    0x76: "BMP280/BME280/BME680 pressure+temp",
    0x77: "BMP180/BMP280 pressure+temp (SDO=HIGH)",
}


# ---------------------------------------------------------------------------
# Low-level helpers (private)
# ---------------------------------------------------------------------------

def _read_file(path: str, default: str = "") -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return default


def _run(cmd: str, default: str = "", timeout: int = 5) -> str:
    try:
        return subprocess.check_output(
            cmd, shell=True, stderr=subprocess.DEVNULL,
            text=True, timeout=timeout
        ).strip()
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SystemOverview:
    model:        str
    hostname:     str
    kernel:       str
    arch:         str
    uptime:       str
    load:         str
    cpu_temp_c:   float
    ram_total_mb: int
    ram_used_mb:  int
    disk_used_gb: int
    disk_total_gb: int


@dataclass
class ThermalReading:
    label:   str
    temp_c:  float
    source:  str   # "cpu" | "gpu" | "hwmon" | "vcgencmd"


@dataclass
class ThermalInfo:
    readings:        List[ThermalReading]
    throttle_raw:    str   # e.g. "throttled=0x0"
    throttle_active: bool
    throttle_events: bool


@dataclass
class CPUFreq:
    core:    int
    cur_mhz: int
    min_mhz: int
    max_mhz: int


@dataclass
class CPUInfo:
    hardware:    str   # from /proc/cpuinfo "Hardware"
    model_name:  str   # from /proc/cpuinfo "Model name" (if x86) or "Model"
    revision:    str
    cores:       int
    governor:    str
    usage_pct:   float
    freqs:       List[CPUFreq]


@dataclass
class MemoryInfo:
    total_mb:     int
    used_mb:      int
    free_mb:      int
    available_mb: int
    cached_mb:    int
    buffers_mb:   int
    swap_total_mb: int
    swap_used_mb:  int


@dataclass
class DiskEntry:
    mount:   str
    device:  str
    fstype:  str
    total:   str
    used:    str
    free:    str
    pct:     int


@dataclass
class StorageInfo:
    disks:     List[DiskEntry]
    sd_model:  Optional[str]
    sd_size:   Optional[str]


@dataclass
class NetInterface:
    name:     str
    state:    str
    addresses: str


@dataclass
class NetworkInfo:
    interfaces: List[NetInterface]
    gateway:    str
    dns:        str


@dataclass
class USBDevice:
    bus_dev:     str
    vidpid:      str
    description: str
    board:       str   # empty string if not in BOARD_MAP


@dataclass
class USBInfo:
    devices:          List[USBDevice]
    serial_ports:     List[str]
    recognized_boards: List[str]


@dataclass
class I2CDevice:
    address:     int
    description: str


@dataclass
class InterfaceInfo:
    spi_devs:    List[str]
    spi0_driver: str
    i2c_devs:    List[str]
    uart_devs:   List[str]
    gpio_chips:  str
    gpio_lines:  str
    w1_sensors:  List[str]
    dtoverlay:   str


# ---------------------------------------------------------------------------
# HardwareMonitor
# ---------------------------------------------------------------------------

class HardwareMonitor:
    """
    Collects hardware information from Raspberry Pi.
    All methods are safe — no exceptions raised; defaults returned on error.
    """

    # --- helpers ---

    def _uptime(self) -> str:
        raw = _read_file("/proc/uptime", "0")
        try:
            secs  = float(raw.split()[0])
            delta = timedelta(seconds=int(secs))
            d, h, m = delta.days, delta.seconds // 3600, (delta.seconds % 3600) // 60
            return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
        except Exception:
            return "N/A"

    def _load(self) -> str:
        raw = _read_file("/proc/loadavg", "")
        parts = raw.split()
        if len(parts) >= 3:
            return f"{parts[0]}  {parts[1]}  {parts[2]}  (1m / 5m / 15m)"
        return "N/A"

    def _cpu_temp(self) -> float:
        raw = _read_file("/sys/class/thermal/thermal_zone0/temp", "0")
        try:
            return int(raw) / 1000.0
        except ValueError:
            return 0.0

    def _meminfo(self) -> Dict[str, int]:
        result: Dict[str, int] = {}
        for line in _read_file("/proc/meminfo", "").splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    result[parts[0].rstrip(":")] = int(parts[1])
                except ValueError:
                    pass
        return result

    def _cpu_usage(self) -> float:
        """Two-sample /proc/stat measurement (~200 ms)."""
        def _stat():
            line = _read_file("/proc/stat", "").splitlines()
            if not line:
                return 0, 1
            vals = list(map(int, line[0].split()[1:]))
            return vals[3], sum(vals)   # idle, total
        i1, t1 = _stat()
        time.sleep(0.2)
        i2, t2 = _stat()
        dt = t2 - t1
        return (1.0 - (i2 - i1) / dt) * 100 if dt else 0.0

    # --- public API ---

    def get_overview(self) -> SystemOverview:
        model    = _read_file("/proc/device-tree/model") or platform.node()
        hostname = _run("hostname", platform.node())
        kernel   = platform.release()
        arch     = platform.machine()
        uptime   = self._uptime()
        load     = self._load()
        cpu_temp = self._cpu_temp()

        mem      = self._meminfo()
        total_mb = mem.get("MemTotal",     0) // 1024
        avail_mb = mem.get("MemAvailable", 0) // 1024
        used_mb  = total_mb - avail_mb

        disk     = shutil.disk_usage("/")
        return SystemOverview(
            model=model, hostname=hostname,
            kernel=kernel, arch=arch,
            uptime=uptime, load=load,
            cpu_temp_c=cpu_temp,
            ram_total_mb=total_mb, ram_used_mb=used_mb,
            disk_used_gb=disk.used  // (1024**3),
            disk_total_gb=disk.total // (1024**3),
        )

    def get_thermal(self) -> ThermalInfo:
        readings: List[ThermalReading] = []

        cpu_c = self._cpu_temp()
        readings.append(ThermalReading("CPU (thermal_zone0)", cpu_c, "cpu"))

        gpu_str = _run("vcgencmd measure_temp 2>/dev/null | sed 's/temp=//'", "")
        if gpu_str:
            try:
                gpu_c = float(gpu_str.replace("'C", "").strip())
                readings.append(ThermalReading("GPU (vcgencmd)", gpu_c, "gpu"))
            except ValueError:
                readings.append(ThermalReading("GPU (vcgencmd)", 0.0, "vcgencmd"))

        for inp_path in sorted(glob.glob("/sys/class/hwmon/hwmon*/temp*_input")):
            label_path = inp_path.replace("_input", "_label")
            label = _read_file(label_path, os.path.basename(inp_path))
            raw   = _read_file(inp_path, "0")
            try:
                readings.append(ThermalReading(
                    f"hwmon — {label}", int(raw) / 1000.0, "hwmon"
                ))
            except ValueError:
                pass

        throttle_raw = _run("vcgencmd get_throttled 2>/dev/null", "throttled=0x0")
        match = re.search(r"0x([0-9a-fA-F]+)", throttle_raw)
        flags = int(match.group(1), 16) if match else 0
        return ThermalInfo(
            readings=readings,
            throttle_raw=throttle_raw,
            throttle_active=bool(flags & 0xF),    # bits 0-3: currently active
            throttle_events=bool(flags & 0xF0000), # bits 16-19: ever occurred
        )

    def get_cpu(self) -> CPUInfo:
        cpuinfo = _read_file("/proc/cpuinfo", "")
        hardware   = ""
        model_name = ""
        revision   = ""
        for line in cpuinfo.splitlines():
            k, _, v = line.partition(":")
            k = k.strip().lower()
            v = v.strip()
            if k == "hardware":
                hardware = v
            elif k in ("model name", "model"):
                if not model_name:
                    model_name = v
            elif k == "revision":
                revision = v

        cores    = os.cpu_count() or 1
        governor = _read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", "N/A")

        freqs: List[CPUFreq] = []
        for i in range(cores):
            try:
                cur  = int(_read_file(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq",  "0")) // 1000
                minf = int(_read_file(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_min_freq",  "0")) // 1000
                maxf = int(_read_file(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq",  "0")) // 1000
            except ValueError:
                cur = minf = maxf = 0
            freqs.append(CPUFreq(core=i, cur_mhz=cur, min_mhz=minf, max_mhz=maxf))

        usage = self._cpu_usage()
        return CPUInfo(
            hardware=hardware, model_name=model_name, revision=revision,
            cores=cores, governor=governor,
            usage_pct=round(usage, 1), freqs=freqs,
        )

    def get_memory(self) -> MemoryInfo:
        m        = self._meminfo()
        total_mb = m.get("MemTotal",      0) // 1024
        free_mb  = m.get("MemFree",       0) // 1024
        avail_mb = m.get("MemAvailable",  0) // 1024
        cached   = m.get("Cached",        0) // 1024
        buffers  = m.get("Buffers",       0) // 1024
        swap_tot = m.get("SwapTotal",     0) // 1024
        swap_fr  = m.get("SwapFree",      0) // 1024
        return MemoryInfo(
            total_mb=total_mb,
            used_mb=total_mb - avail_mb,
            free_mb=free_mb,
            available_mb=avail_mb,
            cached_mb=cached,
            buffers_mb=buffers,
            swap_total_mb=swap_tot,
            swap_used_mb=swap_tot - swap_fr,
        )

    def get_storage(self) -> StorageInfo:
        df_out = _run(
            "df -h --output=target,source,fstype,size,used,avail,pcent "
            "-x tmpfs -x devtmpfs -x overlay 2>/dev/null", ""
        )
        disks: List[DiskEntry] = []
        for line in df_out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 7:
                try:
                    pct = int(parts[6].rstrip("%"))
                except ValueError:
                    pct = 0
                disks.append(DiskEntry(
                    mount=parts[0], device=parts[1], fstype=parts[2],
                    total=parts[3], used=parts[4], free=parts[5], pct=pct,
                ))

        sd_model = _read_file("/sys/block/mmcblk0/device/name") or None
        sd_size  = _run("lsblk -dno SIZE /dev/mmcblk0 2>/dev/null") or None
        return StorageInfo(disks=disks, sd_model=sd_model, sd_size=sd_size)

    def get_network(self) -> NetworkInfo:
        ip_out = _run("ip -br addr show 2>/dev/null", "")
        ifaces: List[NetInterface] = []
        for line in ip_out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                ifaces.append(NetInterface(
                    name=parts[0],
                    state=parts[1],
                    addresses="  ".join(parts[2:]) if len(parts) > 2 else "",
                ))

        gw  = _run("ip route show default 2>/dev/null | awk '{print $3; exit}'", "N/A")
        dns = _run(
            "grep '^nameserver' /etc/resolv.conf 2>/dev/null "
            "| awk '{print $2}' | tr '\\n' ' '", "N/A"
        )
        return NetworkInfo(interfaces=ifaces, gateway=gw.strip() or "N/A",
                           dns=dns.strip() or "N/A")

    def get_usb(self) -> USBInfo:
        lsusb_out    = _run("lsusb 2>/dev/null", "")
        serial_raw   = _run("ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null", "")
        serial_ports = [p for p in serial_raw.split() if p.startswith("/dev/")]

        devices: List[USBDevice] = []
        recognized: List[str]    = []
        for line in lsusb_out.splitlines():
            m_vp = re.search(r"ID\s+([0-9a-fA-F]{4}:[0-9a-fA-F]{4})\s+(.*)", line)
            m_bd = re.search(r"Bus (\d+) Device (\d+)", line)
            if not m_vp:
                continue
            vidpid = m_vp.group(1).lower()
            desc   = m_vp.group(2).strip()
            busdev = f"{m_bd.group(1)}/{m_bd.group(2)}" if m_bd else "—"
            board  = BOARD_MAP.get(vidpid, "")
            if board:
                recognized.append(board)
            devices.append(USBDevice(bus_dev=busdev, vidpid=vidpid,
                                     description=desc, board=board))

        return USBInfo(devices=devices, serial_ports=serial_ports,
                       recognized_boards=recognized)

    def scan_i2c(self, bus: int = 1) -> List[I2CDevice]:
        """Scan I2C bus and identify known devices."""
        output = _run(f"i2cdetect -y {bus} 2>/dev/null", "")
        found: List[I2CDevice] = []
        for addr_hex in re.findall(r"\b([0-9a-f]{2})\b", output):
            try:
                addr = int(addr_hex, 16)
                if 0x03 <= addr <= 0x77:
                    found.append(I2CDevice(
                        address=addr,
                        description=I2C_KNOWN.get(addr, "Unknown device"),
                    ))
            except ValueError:
                pass
        # deduplicate preserving order
        seen: set = set()
        result: List[I2CDevice] = []
        for d in found:
            if d.address not in seen:
                seen.add(d.address)
                result.append(d)
        return sorted(result, key=lambda x: x.address)

    def get_interfaces(self) -> InterfaceInfo:
        spi_devs  = sorted(glob.glob("/dev/spidev*"))
        spi0_drv  = _read_file("/sys/bus/spi/devices/spi0.0/modalias", "N/A")
        i2c_devs  = sorted(glob.glob("/dev/i2c-*"))
        uart_devs = sorted(glob.glob("/dev/ttyAMA*") + glob.glob("/dev/ttyS*"))

        gpio_chips = _run("gpiodetect 2>/dev/null | head -3", "N/A")
        gpio_lines = _run("gpioinfo 2>/dev/null | grep -c '\"'", "")
        gpio_lines_str = (gpio_lines + " total") if gpio_lines.isdigit() else "N/A"

        w1_paths  = glob.glob("/sys/bus/w1/devices/28-*")
        w1_names  = [p.split("/")[-1] for p in w1_paths]

        dtoverlay = _run(
            "grep -v '^#' /boot/config.txt 2>/dev/null "
            "| grep -E 'dtoverlay|dtparam|enable' | head -10", "N/A"
        )
        return InterfaceInfo(
            spi_devs=spi_devs, spi0_driver=spi0_drv,
            i2c_devs=i2c_devs, uart_devs=uart_devs,
            gpio_chips=gpio_chips, gpio_lines=gpio_lines_str,
            w1_sensors=w1_names, dtoverlay=dtoverlay,
        )


# ---------------------------------------------------------------------------
# Public factory
# ---------------------------------------------------------------------------

def get_monitor() -> HardwareMonitor:
    """Return a HardwareMonitor instance."""
    return HardwareMonitor()
