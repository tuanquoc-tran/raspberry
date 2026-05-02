"""
Bluetooth Module for RaspFlip
================================
Hardware  : BCM43455 (Raspberry Pi 4 built-in, shared with Wi-Fi)
Controller: hci0
Transport : UART (/dev/ttyAMA0 via Broadcom combo chip)
Standard  : Bluetooth 5.0 — BR/EDR (Classic) + LE (BLE)
Roles     : central, peripheral (simultaneous)

Capabilities
============
✓ Classic BT inquiry (BR/EDR)          — hcitool scan
✓ BLE passive + active scan            — hcitool lescan / btmgmt find
✓ Dual-mode scan (BR/EDR + BLE)        — btmgmt find
✓ SDP service enumeration (Classic)    — sdptool browse
✓ Device info / RSSI                   — hcitool info / rssi
✓ Paired device list                   — bluetoothctl paired-devices
✓ Discoverable mode control            — bluetoothctl
✗ Packet capture / injection           — not supported by BCM43455 driver
✗ GATT attribute enumeration           — needs 'bleak' (pip install bleak)

Architecture
============
This module uses system tools exclusively (no pybluez, no external libs
required for basic operation). bleak is an optional dependency that
unlocks full GATT service/characteristic enumeration for BLE devices.

    BluetoothManager
    ├── controller_up()        rfkill unblock + hciconfig hci0 up
    ├── controller_down()      hciconfig hci0 down
    ├── get_controller_info()  bluetoothctl show + btmgmt info
    ├── scan()                 btmgmt find / hcitool lescan / hcitool scan
    ├── get_device_info()      hcitool info  (Classic BT only)
    ├── get_services()         sdptool browse  (Classic BT only)
    ├── get_ble_services()     bleak GATT read  (BLE, optional)
    ├── get_rssi()             hcitool rssi  (connected devices)
    ├── get_name()             hcitool name  (Classic BT)
    ├── get_paired_devices()   bluetoothctl paired-devices
    ├── set_discoverable()     bluetoothctl
    ├── set_name()             bluetoothctl system-alias
    └── check_capabilities()  tools + controller feature flags

Important Notes
===============
- BCM43455 shares the 2.4 GHz RF front-end with Wi-Fi.
  Heavy BLE scanning can slightly degrade Wi-Fi throughput on 2.4 GHz.
  5 GHz Wi-Fi is NOT affected (separate RF chain).

- By default the controller is soft-blocked by rfkill on boot.
  Call controller_up() to enable it. This is non-destructive.

- Random MAC addresses (addr_type='random') are used by iOS, Android
  and many IoT devices as a privacy measure. OUI lookup will not work
  for random addresses.

- Classic BT devices must be in DISCOVERABLE mode to appear in inquiry
  scan. BLE devices are always advertising (if powered) without pairing.

- sdptool may print "Failed to connect to SDP server on ..." for BLE-only
  devices — this is expected, BLE uses GATT not SDP.
"""

import os
import re
import time
import logging
import threading
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bluetooth specification version from HCI version code
_HCI_VERSION: Dict[int, str] = {
    0: "1.0b", 1: "1.1", 2: "1.2", 3: "2.0+EDR",
    4: "2.1+EDR", 5: "3.0+HS", 6: "4.0", 7: "4.1",
    8: "4.2", 9: "5.0", 10: "5.1", 11: "5.2", 12: "5.3",
}

# BLE Advertising flags (AD Type 0x01) bit meanings
_ADV_FLAG_BITS: Dict[int, str] = {
    0: "LE Limited Discoverable",
    1: "LE General Discoverable",
    2: "BR/EDR Not Supported (BLE-only device)",
    3: "Dual-mode: LE+BR/EDR Controller",
    4: "Dual-mode: LE+BR/EDR Host",
}

# Compact OUI → vendor name (common embedded, IoT, consumer electronics)
_OUI_DB: Dict[str, str] = {
    # Raspberry Pi Foundation
    "2C:CF:67": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    "D8:3A:DD": "Raspberry Pi",
    # Apple
    "F0:18:98": "Apple",
    "AC:DE:48": "Apple",
    "A4:C3:F0": "Apple",
    "00:1C:B3": "Apple",
    "3C:07:54": "Apple",
    "34:36:3B": "Apple",
    # Samsung
    "18:EF:3A": "Samsung",
    "8C:71:F8": "Samsung",
    "E4:FA:FD": "Samsung",
    "CC:07:AB": "Samsung",
    # Espressif (ESP32, ESP8266)
    "E4:B0:63": "Espressif",
    "A4:CF:12": "Espressif",
    "24:6F:28": "Espressif",
    "30:C6:F7": "Espressif",
    "3C:71:BF": "Espressif",
    "10:06:1C": "Espressif",
    "FC:F5:C4": "Espressif",
    # Nordic Semiconductor
    "E7:AC:89": "Nordic Semi (random-like)",
    "EF:C1:64": "Nordic Semi (random-like)",
    # Texas Instruments (BLE SoCs)
    "00:17:E9": "Texas Instruments",
    "00:12:4B": "Texas Instruments",
    "04:EE:03": "Texas Instruments",
    # Xiaomi / Mi
    "C8:90:A8": "Xiaomi",
    "E4:F0:42": "Xiaomi",
    "28:6C:07": "Xiaomi",
    # Toshiba
    "C0:84:FF": "Toshiba",
    # Intel
    "00:1A:7D": "Intel",
    "8C:8D:28": "Intel",
    "A4:C3:F0": "Intel",
    # Broadcom (RPi Wi-Fi / BT chip itself)
    "00:0A:F7": "Broadcom",
    # Sony
    "00:1D:BA": "Sony",
    "00:13:A9": "Sony",
    "AC:7B:A1": "Sony",
    # Garmin
    "FC:A8:9A": "Garmin",
    # Fitbit
    "C4:4F:33": "Fitbit",
    # AVM (Fritz!Box)
    "00:1B:DC": "AVM (Fritz!)",
    "24:65:11": "AVM (Fritz!)",
    # Virtualization
    "08:00:27": "VirtualBox",
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
}

# Common SDP / GATT service UUIDs → human name (16-bit Bluetooth SIG UUIDs)
_UUID_NAMES: Dict[str, str] = {
    # GATT / Generic services
    "00001800": "Generic Access Profile",
    "00001801": "Generic Attribute Profile",
    "00001802": "Immediate Alert",
    "00001803": "Link Loss",
    "00001804": "TX Power",
    "00001805": "Current Time",
    "00001806": "Reference Time Update",
    "00001808": "Glucose",
    "00001809": "Health Thermometer",
    "0000180a": "Device Information",
    "0000180d": "Heart Rate",
    "0000180e": "Phone Alert Status",
    "0000180f": "Battery Service",
    "00001810": "Blood Pressure",
    "00001811": "Alert Notification",
    "00001812": "HID over GATT",
    "00001813": "Scan Parameters",
    "00001816": "Cycling Speed and Cadence",
    "00001818": "Cycling Power",
    "00001819": "Location and Navigation",
    "0000181a": "Environmental Sensing",
    "0000181c": "User Data",
    "0000181d": "Weight Scale",
    "0000181e": "Bond Management",
    "0000181f": "Continuous Glucose Monitoring",
    "00001820": "Internet Protocol Support",
    "00001821": "Indoor Positioning",
    # Classic BT profiles (SDP)
    "00001101": "Serial Port (SPP)",
    "00001103": "Dialup Networking",
    "00001104": "IrMC Sync",
    "00001105": "OBEX Object Push",
    "00001106": "OBEX File Transfer",
    "00001108": "Headset",
    "00001109": "Cordless Telephony",
    "0000110a": "Audio Source (A2DP)",
    "0000110b": "Audio Sink (A2DP)",
    "0000110c": "A/V Remote Control Target",
    "0000110d": "Advanced Audio Distribution (A2DP)",
    "0000110e": "A/V Remote Control (AVRCP)",
    "0000110f": "Video Conferencing",
    "00001110": "Intercom",
    "00001111": "Fax",
    "00001112": "Headset Audio Gateway",
    "00001115": "PANU",
    "00001116": "NAP",
    "00001117": "GN",
    "00001118": "Direct Printing",
    "0000111e": "Handsfree",
    "0000111f": "Handsfree Audio Gateway",
    "00001122": "WAP Client",
    "00001124": "Human Interface Device (HID)",
    "00001126": "HCRP Print",
    "00001127": "HCRP Scan",
    "0000112d": "SIM Access (SAP)",
    "0000112e": "Phonebook Access (PBAP) Client",
    "0000112f": "Phonebook Access (PBAP) Server",
    "00001130": "Headset HS",
    "00001132": "Message Access (MAP) Server",
    "00001133": "Message Notification Server",
    "00001134": "Message Access Profile",
    "0000113a": "3D Synchronisation Profile",
    "00001200": "PnP Information",
    "00001201": "Generic Networking",
    "00001202": "Generic File Transfer",
    "00001203": "Generic Audio",
    "00001204": "Generic Telephony",
    "00001205": "UPnP",
    "00001303": "Video Source",
    "00001304": "Video Sink",
    # Apple Proprietary
    "7905f431": "Apple Notification Center Service (ANCS)",
    "89d3502b": "Apple Media Service (AMS)",
    "03b80e5a": "Apple MIDI (Bluetooth MIDI)",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BTDevice:
    """Represents a discovered Bluetooth device."""
    addr: str               # BD address (XX:XX:XX:XX:XX:XX uppercase)
    name: str               # Device name (empty string = unknown)
    rssi: Optional[int]     # Signal strength in dBm (None if not reported)
    device_type: str        # 'Classic' | 'BLE' | 'Dual' | 'Unknown'
    addr_type: str          # 'public' | 'random' | 'unknown'
    manufacturer: str       # OUI vendor name (empty for random addresses)
    services: List[str]     # Service names from advertising/EIR data
    flags: Optional[int]    # BLE advertising flags byte (None for Classic)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def signal_quality(self) -> str:
        """Qualitative signal strength description."""
        if self.rssi is None:
            return "Unknown"
        if self.rssi >= -50:
            return "Excellent"
        if self.rssi >= -65:
            return "Good"
        if self.rssi >= -75:
            return "Fair"
        if self.rssi >= -85:
            return "Weak"
        return "Very Weak"

    @property
    def flags_decoded(self) -> List[str]:
        """Human-readable list of set advertising flag bits."""
        if self.flags is None:
            return []
        return [desc for bit, desc in _ADV_FLAG_BITS.items()
                if self.flags & (1 << bit)]

    @property
    def is_ble_only(self) -> bool:
        """True if device advertises itself as BLE-only (BR/EDR not supported)."""
        return bool(self.flags and (self.flags & 0x04))


@dataclass
class ControllerInfo:
    """State and capabilities of the local Bluetooth controller."""
    hci: str                    # Interface name, e.g. 'hci0'
    addr: str                   # BD address (public)
    name: str                   # Local device name
    hci_version: int            # Raw HCI version code (9 = BT 5.0)
    bt_version: str             # Human-readable BT version, e.g. '5.0'
    manufacturer_id: int        # HCI manufacturer company ID
    powered: bool               # Controller is up and powered
    discoverable: bool          # Accepting inquiry from remote devices
    pairable: bool              # Accepting pairing requests
    roles: List[str]            # ['central', 'peripheral']
    br_edr: bool                # Classic BT (BR/EDR) supported
    le: bool                    # BLE (LE) supported
    secure_conn: bool           # Secure Connections (BT 4.1+) enabled
    advertising_instances: int  # Max simultaneous BLE advertising sets


@dataclass
class ServiceRecord:
    """An SDP service record (Classic BT) or GATT service (BLE)."""
    handle: str             # SDP record handle (hex) or GATT service handle
    name: str               # Human-readable service name
    description: str        # Service description (optional)
    uuid: str               # Primary UUID (8-char hex, lowercase)
    uuid_name: str          # Resolved UUID name
    protocol: str           # 'RFCOMM' | 'L2CAP' | 'AVDTP' | 'GATT' | ''
    channel: Optional[int]  # RFCOMM channel, L2CAP PSM, or GATT handle


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], sudo: bool = False, timeout: int = 30,
         input_data: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a command synchronously and return CompletedProcess."""
    if sudo:
        cmd = ["sudo"] + cmd
    return subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=timeout, input=input_data,
    )


def _run_timed(cmd: List[str], duration: float,
               sudo: bool = False) -> Tuple[str, str]:
    """
    Run a command for `duration` seconds then terminate it.
    Returns (stdout, stderr) as strings.

    Used for indefinitely-running scan commands like 'hcitool lescan'
    and 'btmgmt find'.
    """
    if sudo:
        cmd = ["sudo"] + cmd

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    def _read_stdout():
        for line in proc.stdout:
            stdout_lines.append(line)

    def _read_stderr():
        for line in proc.stderr:
            stderr_lines.append(line)

    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_out.start()
    t_err.start()

    time.sleep(duration)
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    return "".join(stdout_lines), "".join(stderr_lines)


def _oui_lookup(addr: str) -> str:
    """Return vendor name from MAC OUI prefix (first 3 octets)."""
    prefix = addr.upper()[:8]
    return _OUI_DB.get(prefix, "")


def _resolve_uuid(uuid_str: str) -> str:
    """Return human-readable service name for a UUID."""
    # Normalise: strip dashes, 0x prefix, lowercase
    clean = uuid_str.lower().replace("-", "").replace("0x", "").strip()
    # Try 8-char prefix (covers full 128-bit UUIDs using 16-bit base)
    return _UUID_NAMES.get(clean[:8] if len(clean) >= 8 else clean, "")


def _bt_version(hci_ver: int) -> str:
    """Convert HCI version code to BT spec version string."""
    return _HCI_VERSION.get(hci_ver, f"Unknown (v{hci_ver})")


def _tool_exists(name: str) -> bool:
    return subprocess.run(["which", name], capture_output=True).returncode == 0


def _module_exists(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# BluetoothManager
# ---------------------------------------------------------------------------

class BluetoothManager:
    """
    Bluetooth scanning and analysis manager for Raspberry Pi 4.

    Hardware backend: BCM43455 (hci0, Bluetooth 5.0, BR/EDR + BLE)

    All operations use Linux system tools (hcitool, btmgmt, sdptool,
    bluetoothctl) via subprocess — no external Python packages required
    for basic scanning. Install 'bleak' for GATT enumeration:
        pip install bleak

    Typical workflow::

        mgr = BluetoothManager()
        mgr.controller_up()

        # Dual-mode scan (BR/EDR + BLE) for 10 seconds
        devices = mgr.scan(duration=10, mode='all')
        for d in devices:
            print(d.addr, d.name, d.rssi, 'dBm')

        # Browse SDP services on a Classic BT device
        services = mgr.get_services("AA:BB:CC:DD:EE:FF")
    """

    def __init__(self, iface: str = "hci0"):
        self.iface = iface

    # ── Controller power management ────────────────────────────────────────

    def controller_up(self) -> bool:
        """
        Unblock rfkill and power up the HCI controller.

        The BCM43455 is soft-blocked on fresh boot. This call is
        safe to repeat — it's idempotent.
        """
        _run(["rfkill", "unblock", "bluetooth"], sudo=True)
        r = _run(["hciconfig", self.iface, "up"], sudo=True)
        if r.returncode != 0:
            logger.error(f"hciconfig {self.iface} up failed: {r.stderr.strip()}")
            return False
        time.sleep(0.3)
        return True

    def controller_down(self) -> None:
        """Power down the HCI controller."""
        _run(["hciconfig", self.iface, "down"], sudo=True)

    # ── Controller information ─────────────────────────────────────────────

    def get_controller_info(self) -> Optional[ControllerInfo]:
        """
        Read full controller state.

        Combines output from:
          - bluetoothctl show   → power state, name, roles, advertising
          - btmgmt info         → feature flags (br/edr, le, secure-conn)
          - hciconfig -a        → HCI version, manufacturer
        """
        r_ctl = _run(["bluetoothctl", "show"])
        if r_ctl.returncode != 0:
            logger.error("bluetoothctl show failed")
            return None

        out = r_ctl.stdout

        def _field(key: str) -> str:
            m = re.search(rf"^\s*{re.escape(key)}:\s*(.+)$", out, re.M)
            return m.group(1).strip() if m else ""

        addr        = _field("Address").split()[0] if _field("Address") else ""
        name        = _field("Name")
        powered     = _field("Powered").lower() == "yes"
        discoverable = _field("Discoverable").lower() == "yes"
        pairable    = _field("Pairable").lower() == "yes"
        roles       = re.findall(r"^\s*Roles:\s*(\S+)", out, re.M)

        adv_m = re.search(r"SupportedInstances:\s*0x(\w+)", out)
        adv_instances = int(adv_m.group(1), 16) if adv_m else 0

        # btmgmt info — feature flags
        r_btm    = _run(["btmgmt", "info"])
        curr_m   = re.search(r"current settings:\s*(.+)", r_btm.stdout)
        settings = curr_m.group(1).split() if curr_m else []
        br_edr      = "br/edr"      in settings
        le          = "le"          in settings
        secure_conn = "secure-conn" in settings

        # hciconfig -a — HCI version number
        r_hci = _run(["hciconfig", "-a", self.iface])
        # "HCI Version: 5.0 (0x9)  Revision: 0x17e  LMP Version: ..."
        ver_m = re.search(r"HCI Version:\s*[\d.]+\s*\(0x([0-9a-fA-F]+)\)",
                          r_hci.stdout)
        hci_ver = int(ver_m.group(1), 16) if ver_m else 9

        return ControllerInfo(
            hci=self.iface,
            addr=addr,
            name=name,
            hci_version=hci_ver,
            bt_version=_bt_version(hci_ver),
            manufacturer_id=305,          # Broadcom/Cypress (BCM43455)
            powered=powered,
            discoverable=discoverable,
            pairable=pairable,
            roles=roles,
            br_edr=br_edr,
            le=le,
            secure_conn=secure_conn,
            advertising_instances=adv_instances,
        )

    # ── Scanning ───────────────────────────────────────────────────────────

    def scan(self, duration: float = 10.0,
             mode: str = "all") -> List[BTDevice]:
        """
        Scan for nearby Bluetooth devices.

        Parameters
        ----------
        duration : float
            How long to scan in seconds. Longer = more devices found.
            Recommended: 10–30 s for typical environment.

        mode : str
            'all'     — BR/EDR + BLE via btmgmt find  (default, recommended)
            'ble'     — BLE only via hcitool lescan --passive
            'classic' — BR/EDR only via hcitool scan

        Returns
        -------
        List[BTDevice] sorted by RSSI descending (strongest signal first).

        Notes
        -----
        - Classic BT devices must be in DISCOVERABLE mode to respond.
        - BLE devices advertise continuously and are always visible.
        - Random addresses (iOS, Android privacy) change periodically —
          the same physical device may appear under different addresses.
        - Requires controller to be UP. Call controller_up() first.
        """
        if mode == "classic":
            return self._scan_classic(duration)
        elif mode == "ble":
            return self._scan_ble(duration)
        else:
            return self._scan_all(duration)

    def _scan_all(self, duration: float) -> List[BTDevice]:
        """
        btmgmt find — dual-mode (BR/EDR + BLE) scan.

        btmgmt type=7 means both BR/EDR and LE inquiry/scanning simultaneously.
        Output line format:
          hci0 Device Found: AA:BB:CC:DD:EE:FF type LE Random rssi -72 \
              flags 0x0002 name FooBar
        """
        stdout, _stderr = _run_timed(
            ["btmgmt", "find", "--adv"], duration=duration, sudo=False
        )
        # Ensure scan is stopped (belt-and-suspenders)
        _run(["btmgmt", "stop-find"])
        return self._parse_btmgmt_find(stdout)

    def _scan_ble(self, duration: float) -> List[BTDevice]:
        """
        hcitool lescan --passive — BLE only.

        Passive scan: no SCAN_REQ sent, only SCAN_IND/ADV_IND received.
        Less intrusive, cannot retrieve scan response data (complete name).
        Use active scan (remove --passive) for more name resolution.
        """
        stdout, _stderr = _run_timed(
            ["hcitool", "lescan", "--passive", "--duplicates"],
            duration=duration, sudo=True,
        )
        return self._parse_lescan(stdout)

    def _scan_classic(self, duration: float) -> List[BTDevice]:
        """
        hcitool scan — Classic BT (BR/EDR) inquiry.

        Sends HCI_Inquiry command. Remote devices must respond.
        Duration is encoded as N*1.28 seconds (BT spec).
        """
        length = max(1, min(48, int(duration / 1.28)))   # 48 ≈ 61 s max
        r = _run(
            ["hcitool", "scan", "--length", str(length), "--flush"],
            sudo=False, timeout=int(duration) + 15,
        )
        return self._parse_hciscan(r.stdout)

    # ── Output parsers ─────────────────────────────────────────────────────

    def _parse_btmgmt_find(self, raw: str) -> List[BTDevice]:
        """
        Parse btmgmt find output.

        btmgmt emits one line per advertising event, so the same device
        appears many times. We deduplicate by address, keeping the best
        RSSI and the first non-empty name we find.
        """
        devices: Dict[str, BTDevice] = {}

        # Pattern covers all variants:
        #   type LE Random | LE Public | BR/EDR | BR/EDR/LE
        pattern = re.compile(
            r"Device Found:\s+([0-9A-Fa-f:]{17})"
            r"\s+type\s+([\w/]+(?:\s+\w+)?)"
            r"\s+rssi\s+(-?\d+)"
            r"(?:\s+flags\s+(\S+))?"
            r"(?:.*?\bname\s+(.+?))?$",
            re.I | re.M,
        )

        for m in pattern.finditer(raw):
            addr      = m.group(1).upper()
            type_raw  = m.group(2).strip().upper()
            rssi      = int(m.group(3))
            flags_hex = m.group(4)
            name      = (m.group(5) or "").strip()

            if "BR/EDR" in type_raw and "LE" not in type_raw:
                dev_type  = "Classic"
                addr_type = "public"
            elif "LE" in type_raw and "BR/EDR" not in type_raw:
                dev_type  = "BLE"
                addr_type = "random" if "RANDOM" in type_raw else "public"
            elif "BR/EDR" in type_raw and "LE" in type_raw:
                dev_type  = "Dual"
                addr_type = "public"
            else:
                dev_type  = "Unknown"
                addr_type = "public"

            flags = int(flags_hex, 16) if flags_hex else None

            if addr in devices:
                existing = devices[addr]
                if name and not existing.name:
                    existing.name = name
                if rssi > (existing.rssi or -999):
                    existing.rssi = rssi
                if dev_type in ("Dual", "Classic") and existing.device_type == "BLE":
                    existing.device_type = dev_type
            else:
                devices[addr] = BTDevice(
                    addr=addr,
                    name=name,
                    rssi=rssi,
                    device_type=dev_type,
                    addr_type=addr_type,
                    manufacturer=_oui_lookup(addr),
                    services=[],
                    flags=flags,
                )

        return sorted(
            devices.values(),
            key=lambda d: d.rssi if d.rssi is not None else -999,
            reverse=True,
        )

    def _parse_lescan(self, raw: str) -> List[BTDevice]:
        """
        Parse hcitool lescan output.

        Output lines:
            LE Scan ...
            AA:BB:CC:DD:EE:FF (unknown)
            AA:BB:CC:DD:EE:FF Device Name
        """
        devices: Dict[str, BTDevice] = {}
        for line in raw.splitlines():
            m = re.match(r"([0-9A-Fa-f:]{17})\s*(.*)", line.strip())
            if not m:
                continue
            addr = m.group(1).upper()
            name = m.group(2).strip()
            if name in ("(unknown)", ""):
                name = ""
            # Heuristic: addresses with 2nd LSB of first byte set are random
            first_byte = int(addr.split(":")[0], 16)
            addr_type = "random" if (first_byte & 0x02) else "public"

            if addr not in devices:
                devices[addr] = BTDevice(
                    addr=addr, name=name, rssi=None,
                    device_type="BLE", addr_type=addr_type,
                    manufacturer=_oui_lookup(addr) if addr_type == "public" else "",
                    services=[], flags=None,
                )
            elif name and not devices[addr].name:
                devices[addr].name = name

        return list(devices.values())

    def _parse_hciscan(self, raw: str) -> List[BTDevice]:
        """
        Parse hcitool scan output.

        Output lines:
            Scanning ...
                AA:BB:CC:DD:EE:FF    Device Name
        """
        devices = []
        for line in raw.splitlines():
            m = re.match(r"\s+([0-9A-Fa-f:]{17})\s+(.+)", line)
            if not m:
                continue
            addr = m.group(1).upper()
            name = m.group(2).strip()
            devices.append(BTDevice(
                addr=addr, name=name, rssi=None,
                device_type="Classic", addr_type="public",
                manufacturer=_oui_lookup(addr),
                services=[], flags=None,
            ))
        return devices

    # ── Device inspection ──────────────────────────────────────────────────

    def get_device_info(self, addr: str) -> Dict[str, Any]:
        """
        Read device information via hcitool info (Classic BT only).

        Sends HCI_Remote_Name_Request and reads remote device features.
        The device must be in range and connectable.

        Returns dict with keys: device_name, version, manufacturer,
        clock_offset, device_class, lmp_version, features, ...
        """
        r = _run(["hcitool", "info", addr], sudo=False, timeout=15)
        result: Dict[str, Any] = {
            "addr":       addr,
            "success":    r.returncode == 0,
            "raw_output": r.stdout,
        }
        for line in r.stdout.splitlines():
            line = line.strip()
            if ":" in line:
                k, _, v = line.partition(":")
                result[k.strip().lower().replace(" ", "_")] = v.strip()
        return result

    def get_services(self, addr: str) -> List[ServiceRecord]:
        """
        Enumerate SDP service records on a Classic BT device.

        Uses sdptool browse which performs an SDP ServiceSearch +
        AttributeRequest sequence over L2CAP. The device must be
        connectable (not necessarily paired).

        BLE devices use GATT instead of SDP — for those, use
        get_ble_services() (requires bleak).

        Returns list of ServiceRecord sorted by name.
        """
        r = _run(["sdptool", "browse", "--l2cap", addr], timeout=25)
        if r.returncode != 0:
            # Retry without --l2cap for some older implementations
            r = _run(["sdptool", "browse", addr], timeout=25)

        services: List[ServiceRecord] = []
        current: Dict[str, str] = {}

        def _flush():
            if current.get("name"):
                uuid = current.get("uuid", "")
                services.append(ServiceRecord(
                    handle=current.get("handle", ""),
                    name=current.get("name", "Unknown"),
                    description=current.get("description", ""),
                    uuid=uuid,
                    uuid_name=_resolve_uuid(uuid),
                    protocol=current.get("protocol", ""),
                    channel=(int(current["channel"])
                             if "channel" in current
                             and current["channel"].isdigit()
                             else None),
                ))

        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("Service Name:"):
                _flush()
                current = {"name": line.split(":", 1)[1].strip()}
            elif line.startswith("Service RecHandle:"):
                current["handle"] = line.split(":", 1)[1].strip()
            elif line.startswith("Service Description:"):
                current["description"] = line.split(":", 1)[1].strip()
            elif '"' in line and "(0x" in line:
                m = re.search(r'"([^"]+)"\s*\(0x([0-9a-fA-F]+)\)', line)
                if m and "uuid" not in current:
                    current["uuid"] = m.group(2).lower().zfill(8)
            elif "RFCOMM" in line and "protocol" not in current:
                current["protocol"] = "RFCOMM"
            elif "AVDTP" in line:
                current["protocol"] = "AVDTP"
            elif line.startswith("Channel:"):
                current["channel"] = line.split(":", 1)[1].strip()
            elif line.startswith("PSM:"):
                current["channel"] = line.split(":", 1)[1].strip()
        _flush()

        return sorted(services, key=lambda s: s.name)

    def get_ble_services(self, addr: str,
                         timeout: float = 15.0) -> List[ServiceRecord]:
        """
        Enumerate GATT services on a BLE device.

        Requires: pip install bleak
        Uses asyncio internally via bleak.BleakClient.

        Unlike SDP (Classic BT), BLE service discovery uses GATT which
        operates over ATT protocol. The structure is:
          Service (UUID) → Characteristics → Descriptors

        Returns list of top-level GATT services.
        """
        if not _module_exists("bleak"):
            raise RuntimeError(
                "bleak not installed — run: pip install bleak\n"
                "bleak is required for GATT/BLE service enumeration."
            )

        import asyncio
        from bleak import BleakClient

        services: List[ServiceRecord] = []

        async def _read():
            async with BleakClient(addr, timeout=timeout) as client:
                for svc in client.services:
                    uuid_clean = str(svc.uuid).lower().replace("-", "")
                    services.append(ServiceRecord(
                        handle=hex(svc.handle),
                        name=svc.description or _resolve_uuid(uuid_clean) or "Unknown",
                        description="",
                        uuid=uuid_clean[:8],
                        uuid_name=_resolve_uuid(uuid_clean),
                        protocol="GATT",
                        channel=svc.handle,
                    ))

        asyncio.run(_read())
        return sorted(services, key=lambda s: s.name)

    def get_rssi(self, addr: str) -> Optional[int]:
        """
        Read RSSI of a currently-connected device (dBm).

        Only works if the device is connected (ACL link established).
        Returns None if not connected or command fails.
        """
        r = _run(["hcitool", "rssi", addr], sudo=False, timeout=5)
        m = re.search(r"RSSI return value:\s*(-?\d+)", r.stdout)
        return int(m.group(1)) if m else None

    def get_name(self, addr: str) -> Optional[str]:
        """
        Resolve device name via HCI Remote Name Request.

        Connects briefly to the remote Classic BT device to read its
        device name. Slower than inquiry scan names but more accurate.
        """
        r = _run(["hcitool", "name", addr], sudo=False, timeout=15)
        name = r.stdout.strip()
        return name if name and name != addr else None

    # ── Paired device management ───────────────────────────────────────────

    def get_paired_devices(self) -> List[Dict[str, str]]:
        """
        Return list of devices paired with this controller.

        Pairing creates long-term keys (LTK for BLE, link key for Classic)
        stored in BlueZ's device database (/var/lib/bluetooth/).
        """
        r = _run(["bluetoothctl", "paired-devices"])
        devices = []
        for line in r.stdout.splitlines():
            m = re.match(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
            if m:
                addr = m.group(1).upper()
                devices.append({
                    "addr":         addr,
                    "name":         m.group(2).strip(),
                    "manufacturer": _oui_lookup(addr),
                })
        return devices

    def remove_pairing(self, addr: str) -> bool:
        """Remove a paired device from the BlueZ database."""
        r = _run(
            ["bluetoothctl"],
            input_data=f"remove {addr}\n",
            timeout=5,
        )
        return "Device has been removed" in r.stdout or r.returncode == 0

    # ── Local controller settings ──────────────────────────────────────────

    def set_discoverable(self, on: bool, timeout_sec: int = 180) -> bool:
        """
        Enable or disable discoverable mode.

        When discoverable, this controller responds to Classic BT inquiry
        scans from other devices. Timeout (seconds) applies when on=True.
        0 = infinite (not recommended for security).
        """
        if on:
            cmds = f"discoverable-timeout {timeout_sec}\ndiscoverable on\n"
        else:
            cmds = "discoverable off\n"
        r = _run(["bluetoothctl"], input_data=cmds, timeout=5)
        return r.returncode == 0

    def set_name(self, name: str) -> bool:
        """Set the local Bluetooth device name (broadcast in advertising)."""
        r = _run(["bluetoothctl"], input_data=f"system-alias {name}\n", timeout=5)
        return r.returncode == 0

    # ── Capabilities ───────────────────────────────────────────────────────

    def check_capabilities(self) -> Dict[str, Any]:
        """
        Return a capability summary dict covering:
          - Installed system tools
          - Optional Python packages
          - Controller hardware features
        """
        tools = {
            "hcitool":      _tool_exists("hcitool"),
            "btmgmt":       _tool_exists("btmgmt"),
            "sdptool":      _tool_exists("sdptool"),
            "bluetoothctl": _tool_exists("bluetoothctl"),
        }
        optional = {
            "bleak":  _module_exists("bleak"),
        }
        info = self.get_controller_info()
        return {
            "tools":    tools,
            "optional": optional,
            "controller": {
                "hci":              self.iface,
                "addr":             info.addr        if info else "?",
                "name":             info.name        if info else "?",
                "bt_version":       info.bt_version  if info else "?",
                "br_edr":           info.br_edr      if info else False,
                "le":               info.le          if info else False,
                "secure_conn":      info.secure_conn if info else False,
                "adv_instances":    info.advertising_instances if info else 0,
                "roles":            info.roles       if info else [],
            },
        }


# ---------------------------------------------------------------------------
# Public helpers / factory
# ---------------------------------------------------------------------------

def get_manager(iface: str = "hci0") -> BluetoothManager:
    """Create and return a BluetoothManager instance."""
    return BluetoothManager(iface=iface)


def oui_lookup(addr: str) -> str:
    """Look up vendor name by MAC OUI prefix."""
    return _oui_lookup(addr)


def uuid_name(uuid: str) -> str:
    """Return human-readable name for a Bluetooth service UUID."""
    return _resolve_uuid(uuid)


def adv_flags_decode(flags: int) -> List[str]:
    """Return list of human-readable BLE advertising flag descriptions."""
    return [desc for bit, desc in _ADV_FLAG_BITS.items()
            if flags & (1 << bit)]
