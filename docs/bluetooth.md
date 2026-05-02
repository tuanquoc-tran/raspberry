# Bluetooth — Scanning & Analysis

> **Hardware:** BCM43455 (Raspberry Pi 4 built-in)  
> **Interface:** `hci0` · **Address:** `2C:CF:67:78:DC:DC`  
> **Standard:** Bluetooth 5.0 · **Transport:** UART (via Broadcom BCM combo chip)  
> **Modes:** BR/EDR (Classic) + LE (BLE) — simultaneous

---

## Table of Contents

1. [Hardware Architecture](#1-hardware-architecture)
2. [Bluetooth Protocol Stack](#2-bluetooth-protocol-stack)
3. [Classic BT vs BLE — Architecture Differences](#3-classic-bt-vs-ble--architecture-differences)
4. [BLE Advertising Deep Dive](#4-ble-advertising-deep-dive)
5. [GATT Architecture (BLE)](#5-gatt-architecture-ble)
6. [SDP — Service Discovery (Classic BT)](#6-sdp--service-discovery-classic-bt)
7. [Security & Pairing](#7-security--pairing)
8. [Privacy — Random MAC Addresses](#8-privacy--random-mac-addresses)
9. [System Tools Reference](#9-system-tools-reference)
10. [Python API Reference](#10-python-api-reference)
11. [CLI Usage Guide](#11-cli-usage-guide)
12. [OUI Vendor Identification](#12-oui-vendor-identification)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Hardware Architecture

### BCM43455 Combo Chip

The Raspberry Pi 4 uses a **Cypress (formerly Broadcom) BCM43455** — a
single-chip Wi-Fi + Bluetooth combo solution.

```
┌──────────────────────────────────────────────────────────┐
│                      BCM43455                            │
│                                                          │
│   ┌────────────┐    ┌────────────────┐    ┌───────────┐  │
│   │  Wi-Fi     │    │   Bluetooth    │    │   RF      │  │
│   │  802.11ac  │    │   5.0 BR/EDR   │    │  Front    │  │
│   │  2.4/5 GHz │    │   + BLE        │    │  End      │  │
│   └──────┬─────┘    └───────┬────────┘    └─────┬─────┘  │
│          │ SDIO             │ UART               │        │
└──────────┼──────────────────┼────────────────────┼────────┘
           │                  │                    │
      SoC SDIO           /dev/ttyAMA0         Antenna
      (Wi-Fi driver)     (BT HCI UART)        (shared 2.4 GHz)
```

**Key hardware facts:**

| Property | Value |
|---|---|
| Chip | Cypress BCM43455 |
| BT Standard | Bluetooth 5.0 (HCI Version 9) |
| Transport | HCI over UART (`/dev/ttyAMA0`) |
| BD Address | `2C:CF:67:78:DC:DC` (OUI: Raspberry Pi Foundation) |
| Classic BT | BR/EDR ✓ |
| BLE | LE ✓ |
| Dual-mode | Simultaneous BR/EDR + LE ✓ |
| Secure Connections | ✓ (BT 4.1+ feature) |
| Advertising Sets | Hardware-limited (BCM43455: 1 simultaneous LE advertiser) |
| BT Roles | Central + Peripheral (simultaneous) |

**RF sharing — important note:**  
The BCM43455 shares its 2.4 GHz RF front-end between Wi-Fi (2.4 GHz band)
and Bluetooth. When both are active:

- BT and 2.4 GHz Wi-Fi use **coexistence arbitration** (Wi-Fi coex signalling
  on the chip's internal bus) to time-share the antenna.
- **5 GHz Wi-Fi is completely unaffected** — separate RF path.
- Heavy continuous BLE scanning can marginally reduce 2.4 GHz Wi-Fi
  throughput in dense RF environments (typically < 10% degradation).

---

## 2. Bluetooth Protocol Stack

Bluetooth uses a layered architecture. The BCM43455 implements all
layers below HCI in firmware; BlueZ implements layers above HCI in Linux.

```
Application (Python, bluetoothctl, etc.)
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│  BlueZ (user-space)                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Profiles │  │   GATT   │  │   SDP    │  │  A2DP  │  │
│  │ (GAP/etc)│  │(BLE svc) │  │(Classic) │  │(Audio) │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
│       │             │             │             │        │
│  ┌────▼─────────────▼─────────────▼─────────────▼────┐  │
│  │               L2CAP (multiplexing)                 │  │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────────┐  │  │
│  │   │  RFCOMM  │   │  ATT     │   │  AVDTP/AVCTP │  │  │
│  │   │(serial)  │   │(GATT tpt)│   │(audio/remote)│  │  │
│  │   └──────────┘   └──────────┘   └──────────────┘  │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────┘
                     │ HCI (Host Controller Interface)
           ──────────▼──────────
           │   BCM43455 (UART) │  ← firmware: LMP, BB, RF
           ────────────────────
```

### Layer Summary

| Layer | Role | Protocol |
|---|---|---|
| **RF / Baseband** | Physical radio, bit timing, frequency hopping | — |
| **LMP / LLCP** | Link management, pairing, power control | LMP (Classic) / LLCP (BLE) |
| **HCI** | Host↔Controller interface (commands, events, ACL data) | HCI over UART |
| **L2CAP** | Logical Link Control, channel multiplexing, MTU negotiation | L2CAP |
| **RFCOMM** | Serial port emulation over L2CAP | SPP, Handsfree |
| **ATT** | Attribute Protocol — carries GATT read/write | BLE only |
| **SDP** | Service Discovery Protocol — enumerate BR/EDR services | Classic only |
| **GATT** | Generic Attribute Profile — structured service database | BLE primary |
| **GAP** | Generic Access Profile — advertising, scanning, connection | Both |

---

## 3. Classic BT vs BLE — Architecture Differences

Understanding the fundamental architectural split is essential for
correctly interpreting scan results.

### Classic BT (BR/EDR)

```
Master ←──────────────────────────────── Slave
        Frequency Hopping (1600 hops/s)
        79 channels × 1 MHz (2402–2480 MHz)
        Piconet topology (1 master, up to 7 active slaves)
```

- **Discovery:** Device must be set DISCOVERABLE. Master sends `HCI_Inquiry`,
  slave responds with `FHS` (Frequency Hopping Synchronization) packet.
- **Connection:** Page procedure → ACL link → L2CAP channels
- **Latency:** ~100 ms inquiry → first response typical
- **Data rate:** 1–3 Mbps (Classic), up to 24 Mbps (HS via 802.11 MAC bridge)
- **Range:** Typically 10–100 m (class 1/2)
- **Topology:** Piconet (star). Multiple piconets = Scatternet.

### BLE (Bluetooth Low Energy)

```
Advertiser ─────────────────────────────► Scanner
            3 advertising channels:
            37 (2402 MHz), 38 (2426 MHz), 39 (2480 MHz)
            Advertising interval: 20 ms – 10.24 s
```

- **Discovery:** Advertiser continuously broadcasts on ch 37/38/39.
  Scanner is always listening — no need to make device discoverable.
- **Connection:** Optional — many IoT devices are connectionless (beacon mode)
- **Latency:** Sub-millisecond for advertising detection
- **Data rate:** 125 kbps – 2 Mbps (BT 5.0 adds 125k/500k long-range PHYs)
- **Range:** 10–400 m (standard / long-range LE Coded PHY)
- **Power:** Designed for µA sleep, brief radio bursts (coin cell years)

### Side-by-side comparison

| | Classic BT | BLE |
|---|---|---|
| Frequency | 2.4 GHz, 79×1 MHz channels | 2.4 GHz, 40×2 MHz channels |
| Modulation | GFSK / π/4-DQPSK / 8DPSK | GFSK |
| Discovery | Inquiry (device must be discoverable) | Advertising (always on) |
| Service discovery | SDP over L2CAP | GATT over ATT |
| Pairing security | SSP (BT 2.1+) or legacy PIN | LE Legacy / Secure Conn |
| Power | ~50–100 mW active | < 1 mW active burst |
| Throughput | 1–24 Mbps | 0.125–2 Mbps |
| Typical use | Audio, file transfer, HID | Sensors, beacons, wearables |

---

## 4. BLE Advertising Deep Dive

### Channel Map

```
2402 MHz  2426 MHz  2480 MHz
   │          │          │
  ch37       ch38       ch39   ← Primary advertising channels
   │          │          │
   └──────────┴──────────┘
   37 data channels (ch0–ch36) ← Used for connections + secondary adv
```

### Advertising PDU Types

| PDU Type | Connectable | Scannable | Description |
|---|---|---|---|
| `ADV_IND` | Yes | Yes | Standard connectable undirected advertising |
| `ADV_DIRECT_IND` | Yes | No | Connectable directed (specific scanner address) |
| `ADV_NONCONN_IND` | No | No | Non-connectable, non-scannable (beacon) |
| `ADV_SCAN_IND` | No | Yes | Non-connectable, scannable (responds to SCAN_REQ) |
| `SCAN_RSP` | — | — | Response to SCAN_REQ, carries extra data |

Most IoT sensors use `ADV_NONCONN_IND` (beacon mode) — they never accept
connections, just broadcast sensor readings continuously.

### Advertising Payload Structure

```
┌─────────────────────────────────────────────────────────┐
│  Advertising Data (AD) — max 31 bytes per PDU           │
│  (BT 5.0 Extended Advertising: up to 255 bytes)         │
│                                                         │
│  ┌──────┬──────┬──────────────────┐                     │
│  │Length│ Type │     Data         │  ← AD Structure 1   │
│  └──────┴──────┴──────────────────┘                     │
│  ┌──────┬──────┬──────────────────┐                     │
│  │Length│ Type │     Data         │  ← AD Structure 2   │
│  └──────┴──────┴──────────────────┘                     │
│  ...                                                    │
└─────────────────────────────────────────────────────────┘
```

Common AD Type codes (Bluetooth SIG assigned):

| AD Type | Name | Example |
|---|---|---|
| `0x01` | Flags | `0x06` = LE General Discoverable + BR/EDR Not Supported |
| `0x02` | 16-bit UUIDs (incomplete) | Service hint list |
| `0x03` | 16-bit UUIDs (complete) | Full service list |
| `0x07` | 128-bit UUIDs (complete) | Proprietary service |
| `0x08` | Shortened Local Name | First 8 chars of name |
| `0x09` | Complete Local Name | Full device name |
| `0xFF` | Manufacturer Specific | Company ID + custom payload |

### Advertising Flags Byte (`AD Type 0x01`)

```
Bit 7  Bit 6  Bit 5  Bit 4  Bit 3  Bit 2  Bit 1  Bit 0
  0      0      0    LE+BDR LE+BDR BR/EDR LE Gen  LE Lim
                     Host   Ctrl   Not    Disc    Disc
                     Cap    Cap    Sup    Mode    Mode

Typical values:
  0x02 = Bit 1 only: LE General Discoverable, BR/EDR supported (dual-mode)
  0x06 = Bits 1+2:   LE General Discoverable, BR/EDR NOT supported (BLE-only)
  0x1A = Bits 1+3+4: LE General Discoverable, dual-mode capable
```

---

## 5. GATT Architecture (BLE)

GATT (Generic Attribute Profile) is the service layer for BLE. It defines
a hierarchical database of **Attributes** stored on the peripheral (server).

```
GATT Server (peripheral, e.g. heart rate monitor)
│
├── Service: Heart Rate (UUID 0x180D)
│   ├── Characteristic: Heart Rate Measurement (UUID 0x2A37)
│   │   ├── Properties: NOTIFY
│   │   └── Descriptor: Client Characteristic Config (UUID 0x2902)
│   └── Characteristic: Body Sensor Location (UUID 0x2A38)
│       └── Properties: READ
│
├── Service: Device Information (UUID 0x180A)
│   ├── Characteristic: Manufacturer Name (UUID 0x2A29)
│   ├── Characteristic: Model Number (UUID 0x2A24)
│   └── Characteristic: Firmware Revision (UUID 0x2A26)
│
└── Service: Battery (UUID 0x180F)
    └── Characteristic: Battery Level (UUID 0x2A19)
        └── Properties: READ, NOTIFY
```

### Characteristic Properties

| Property | Meaning |
|---|---|
| `READ` | Central can read the current value |
| `WRITE` | Central can write a new value (with acknowledgement) |
| `WRITE WITHOUT RESPONSE` | Central can write (fire-and-forget, no ACK) |
| `NOTIFY` | Peripheral sends updates automatically (no ACK) |
| `INDICATE` | Peripheral sends updates, central must ACK |
| `BROADCAST` | Value is included in advertising data |

### UUID Format

Bluetooth SIG defines 16-bit UUIDs for standard services/characteristics:

```
16-bit UUID: 0x180D
128-bit expansion: 0000180D-0000-1000-8000-00805F9B34FB
                   ^^^^^^^^ ← 16-bit UUID embedded here
```

Proprietary services use random 128-bit UUIDs (e.g., Nordic UART Service,
Apple ANCS, custom IoT applications).

---

## 6. SDP — Service Discovery (Classic BT)

SDP (Service Discovery Protocol) is the Classic BT equivalent of GATT.
It runs over L2CAP PSM 0x0001 and provides a simple key-value database
of service records.

### SDP Workflow

```
Client (us)                    Server (remote device)
    │                               │
    │── ServiceSearch ─────────────►│  "Do you have RFCOMM services?"
    │◄─ ServiceSearchResponse ───── │  "Yes, handles 0x0001, 0x0003"
    │                               │
    │── ServiceAttribute ──────────►│  "Give me attrs for handle 0x0001"
    │◄─ ServiceAttributeResponse ── │  "Name: Serial Port, RFCOMM ch: 3"
```

### Common SDP Attributes

| Attribute ID | Name |
|---|---|
| `0x0000` | Service Record Handle |
| `0x0001` | Service Class ID List |
| `0x0002` | Service Record State |
| `0x0003` | Service ID |
| `0x0004` | Protocol Descriptor List |
| `0x0005` | Browse Group List |
| `0x0009` | Bluetooth Profile Descriptor List |
| `0x0100` | Service Name |
| `0x0101` | Service Description |
| `0x0102` | Provider Name |

### SDP vs GATT Comparison

| | SDP (Classic BT) | GATT (BLE) |
|---|---|---|
| Transport | L2CAP PSM 0x0001 | ATT (dedicated LE channel) |
| Connection required | Yes (ACL link) | Yes (for enumeration) |
| Real-time data | No | Yes (Notify/Indicate) |
| Hierarchy | Flat service list | Service → Char → Descriptor |
| Dynamic attributes | No | Yes (CCCD writable) |
| Tool | `sdptool browse` | `bleak`, `gatttool` |

---

## 7. Security & Pairing

### Classic BT — Secure Simple Pairing (SSP)

Introduced in BT 2.1+EDR, SSP replaces the insecure PIN-based pairing.
It uses **Elliptic Curve Diffie-Hellman (ECDH)** for key exchange.

#### SSP Association Models

| Model | When Used | Description |
|---|---|---|
| **Just Works** | Neither device has display/input | No user confirmation. Vulnerable to MITM. Used for headphones, etc. |
| **Numeric Comparison** | Both devices have display | Both show 6-digit number, user confirms match. MITM-protected. |
| **Passkey Entry** | One device has input, other has display | One shows 6-digit number, user types it on other. MITM-protected. |
| **Out of Band (OOB)** | NFC or other channel available | Key material transferred via NFC. Strongest security. |

### BLE — LE Pairing

BLE has two pairing generations:

#### LE Legacy Pairing (BT 4.0–4.1)

```
Phase 1: Feature exchange (IO capabilities, OOB, bonding flags)
Phase 2: Short-Term Key (STK) generation
         TK (Temporary Key) → STK via s1() function
Phase 3: LTK, CSRK, IRK distribution over encrypted link
```

Weakness: STK generation uses a **128-bit random number (SKdm, SKds)**
shared in plaintext. A passive eavesdropper who captures the pairing
can recover the STK and decrypt the session. **Not forward-secret.**

#### LE Secure Connections (BT 4.2+, BCM43455 ✓)

```
Phase 1: Feature exchange
Phase 2: ECDH key exchange (P-256 curve)
         Public keys exchanged → DHKey computed independently
         No key material on air → eavesdropping useless
Phase 3: LTK derived from DHKey via HMAC-SHA256
         (same LTK on both sides without transmitting it)
```

**Forward-secret, MITM-resistant** (with Numeric Comparison or OOB).

### Key Types

| Key | Size | Purpose |
|---|---|---|
| **LTK** (Long-Term Key) | 128 bits | Re-encryption on reconnect (BLE) |
| **IRK** (Identity Resolving Key) | 128 bits | Resolve private random addresses |
| **CSRK** (Connection Signature Resolving Key) | 128 bits | Data signing without encryption |
| **Link Key** | 128 bits | Classic BT equivalent of LTK |

Keys are stored by BlueZ in `/var/lib/bluetooth/<controller_addr>/<device_addr>/`.

---

## 8. Privacy — Random MAC Addresses

Modern mobile OS (iOS 14+, Android 10+) and many BLE sensors use
**random MAC addresses** to prevent long-term tracking.

### Address Types

```
BD Address: XX:XX:XX:XX:XX:XX
            ││
            │└── bit 0: always 1 for LE (advisory)
            └─── bit 1: address type indicator

Public address    : bit7:bit6 = 0b  (manufacturer OUI in top 24 bits)
Static random     : bit7:bit6 = 11  (random, fixed per boot)
Private resolvable: bit7:bit6 = 01  (changes every ~15 min, resolvable with IRK)
Private non-res.  : bit7:bit6 = 00  (changes every ~15 min, unresolvable)
```

### Private Resolvable Addresses (RPA)

Used by iOS and Android in BLE advertising.

```
RPA = prand[22 bits] || ah(IRK, prand)[24 bits]

Where:
  prand  = 22 random bits (changes per interval, ~15 min)
  ah()   = AES-128 based hash
  IRK    = Identity Resolving Key (shared after pairing)

Resolution: given IRK, compute ah(IRK, prand) and compare to
            lower 24 bits of address.
```

**Implication for scanning:**
- The same iPhone may appear as a different address every 15 minutes.
- Without the IRK (only available after pairing + key exchange),
  you cannot correlate multiple observations to the same device.
- OUI lookup is meaningless for random addresses (first byte bit pattern
  overrides the OUI registry).

Our scanner detects random addresses by testing `addr_byte[0] & 0x02`.

---

## 9. System Tools Reference

All scanning operations use Linux system tools — no extra Python packages
required for basic BR/EDR + BLE scanning.

### Available Tools

| Tool | Package | Purpose |
|---|---|---|
| `hcitool` | `bluez` | HCI-level commands: scan, lescan, info, rssi, name |
| `btmgmt` | `bluez` | Management API: dual scan, capabilities, settings |
| `sdptool` | `bluez` | SDP service enumeration for Classic BT |
| `bluetoothctl` | `bluez` | Interactive BT management (paired devices, power, name) |
| `rfkill` | kernel | RF kill switch control (unblock BT on boot) |
| `hciconfig` | `bluez` | HCI interface configuration |

### Quick Reference

```bash
# Enable controller
sudo rfkill unblock bluetooth
sudo hciconfig hci0 up

# Show controller status
hciconfig -a
bluetoothctl show

# Dual-mode scan (BR/EDR + BLE), 10 seconds
sudo timeout 10 btmgmt find --adv; btmgmt stop-find

# BLE passive scan, 10 seconds
sudo timeout 10 hcitool lescan --passive

# Classic BT inquiry (12.8 s)
hcitool scan --length 10 --flush

# Device info (Classic BT, must be connectable)
hcitool info AA:BB:CC:DD:EE:FF

# Get RSSI (must be connected)
hcitool rssi AA:BB:CC:DD:EE:FF

# Remote name request
hcitool name AA:BB:CC:DD:EE:FF

# Browse SDP services
sdptool browse --l2cap AA:BB:CC:DD:EE:FF

# List paired devices
bluetoothctl paired-devices

# Remove pairing
bluetoothctl remove AA:BB:CC:DD:EE:FF

# Enable discoverable for 180 s
bluetoothctl discoverable-timeout 180
bluetoothctl discoverable on

# Set local name
bluetoothctl system-alias "RaspFlip"

# BlueZ daemon status
systemctl status bluetooth

# HCI log (raw HCI frames)
sudo hcidump -i hci0
```

### Controller State After Boot

```bash
$ rfkill list bluetooth
1: hci0: Bluetooth
    Soft blocked: yes    ← soft-blocked by default
    Hard blocked: no

$ sudo rfkill unblock bluetooth && sudo hciconfig hci0 up
$ hciconfig
hci0:  Type: Primary  Bus: UART
       BD Address: 2C:CF:67:78:DC:DC  ACL MTU: 1021:8  SCO MTU: 64:1
       UP RUNNING
       ...
```

### btmgmt — Management API vs hcitool Comparison

`hcitool` uses raw HCI commands (kernel BT socket, `AF_BLUETOOTH`).
`btmgmt` uses the **Management API** introduced in Linux 3.4, which
routes through BlueZ rather than bypassing it. For modern kernels
(RPi 4 running kernel 5.x+), `btmgmt` is preferred for scan control
because it integrates with BlueZ's coexistence management.

| Operation | hcitool | btmgmt |
|---|---|---|
| Dual scan (BR/EDR+BLE) | Separate commands | `find` (type 7) |
| BLE passive scan | `lescan --passive` | `find --adv` |
| Power control | `hciconfig up/down` | `power on/off` |
| Controller info | `hciconfig -a` | `info` |
| Feature flags | Not directly | `info` → current settings |

---

## 10. Python API Reference

```python
from modules.bluetooth import BluetoothManager, get_manager

mgr = BluetoothManager(iface='hci0')
# Or: mgr = get_manager()
```

### Controller Management

```python
# Power up (safe to call multiple times)
mgr.controller_up()   # → bool

# Power down
mgr.controller_down()

# Full status
info = mgr.get_controller_info()
# Returns ControllerInfo dataclass:
print(info.bt_version)        # '5.0'
print(info.br_edr, info.le)   # True, True
print(info.secure_conn)       # True
print(info.discoverable)      # False
```

### Scanning

```python
# Dual-mode scan (recommended)
devices = mgr.scan(duration=10, mode='all')

# BLE only
devices = mgr.scan(duration=10, mode='ble')

# Classic BT only
devices = mgr.scan(duration=15, mode='classic')

# Each device is a BTDevice dataclass:
for d in devices:
    print(d.addr)           # 'DE:CD:2F:E8:6C:C5'
    print(d.name)           # 'L8050 Series'
    print(d.rssi)           # -72 (dBm)
    print(d.device_type)    # 'BLE' | 'Classic' | 'Dual' | 'Unknown'
    print(d.addr_type)      # 'public' | 'random'
    print(d.manufacturer)   # 'Samsung' (OUI lookup)
    print(d.signal_quality) # 'Fair'
    print(d.is_ble_only)    # True if flags & 0x04
    print(d.flags_decoded)  # ['LE General Discoverable', 'BR/EDR Not Supported']
```

### Device Inspection

```python
# Device info (Classic BT — must be connectable)
info = mgr.get_device_info('AA:BB:CC:DD:EE:FF')
# Returns dict: {'addr', 'success', 'device_name', 'lmp_version', ...}

# SDP services (Classic BT)
services = mgr.get_services('AA:BB:CC:DD:EE:FF')
for s in services:
    print(s.name)       # 'Serial Port'
    print(s.protocol)   # 'RFCOMM'
    print(s.channel)    # 3
    print(s.uuid_name)  # 'Serial Port (SPP)'

# GATT services (BLE, requires: pip install bleak)
try:
    services = mgr.get_ble_services('DE:CD:2F:E8:6C:C5', timeout=15)
    for s in services:
        print(s.name, s.uuid)
except RuntimeError as e:
    print(e)   # "bleak not installed — run: pip install bleak"

# RSSI (connected devices only)
rssi = mgr.get_rssi('AA:BB:CC:DD:EE:FF')  # → int | None

# Remote name (Classic BT)
name = mgr.get_name('AA:BB:CC:DD:EE:FF')  # → str | None
```

### Paired Devices

```python
# List all paired devices
paired = mgr.get_paired_devices()
for d in paired:
    print(d['addr'], d['name'], d['manufacturer'])

# Remove pairing
ok = mgr.remove_pairing('AA:BB:CC:DD:EE:FF')  # → bool
```

### Local Controller Settings

```python
# Enable discoverable for 180 s
mgr.set_discoverable(True, timeout_sec=180)

# Disable discoverable
mgr.set_discoverable(False)

# Set device name (visible to other devices)
mgr.set_name("RaspFlip")
```

### Utility Functions

```python
from modules.bluetooth import oui_lookup, uuid_name, adv_flags_decode

# OUI vendor lookup
print(oui_lookup('2C:CF:67:78:DC:DC'))   # 'Raspberry Pi'
print(oui_lookup('18:EF:3A:5A:EF:17'))   # 'Samsung'

# UUID resolution
print(uuid_name('0x180D'))               # 'Heart Rate'
print(uuid_name('00001101-0000-1000-8000-00805f9b34fb'))  # 'Serial Port (SPP)'

# Advertising flags decode
flags = adv_flags_decode(0x06)
# ['LE General Discoverable', 'BR/EDR Not Supported (BLE-only device)']
```

### Capabilities Check

```python
caps = mgr.check_capabilities()
# {
#   'tools': {
#       'hcitool': True, 'btmgmt': True,
#       'sdptool': True, 'bluetoothctl': True
#   },
#   'optional': {'bleak': False},
#   'controller': {
#       'hci': 'hci0', 'addr': '2C:CF:67:78:DC:DC',
#       'bt_version': '5.0', 'br_edr': True, 'le': True,
#       'secure_conn': True, 'adv_instances': 0, 'roles': [...]
#   }
# }
```

---

## 11. CLI Usage Guide

Launch RaspFlip and navigate to the Bluetooth menu:

```
RaspFlip Main Menu
  7. Bluetooth
     ├── 1  Controller info
     ├── 2  Scan all (BR/EDR + BLE)   — 15 s
     ├── 3  Scan BLE only             — 10 s
     ├── 4  Scan Classic BT only      — 15 s
     ├── 5  Device details (by address)
     ├── 6  Browse SDP services (Classic BT)
     ├── 7  GATT services — BLE (requires bleak)
     ├── 8  List paired devices
     ├── 9  Set discoverable ON  (180 s)
     ├── 10 Set discoverable OFF
     ├── 11 Set local device name
     ├── 12 Check capabilities & tools
     └── 0  Back
```

### Typical workflow — enumerate a Classic BT device

1. **Option 2** — Scan all → note the target's BD address
2. **Option 5** — Enter address → read LMP version, device class
3. **Option 6** — Enter address → list RFCOMM services and channels
4. Use `rfcomm connect hci0 AA:BB:CC:DD:EE:FF 3` to connect (external)

### Typical workflow — analyse a BLE device

1. **Option 3** — BLE scan → note address and advertising name
2. **Option 7** — Enter address → list GATT services (bleak required)
   - Use `pip install bleak` first if not installed
3. Use `gatttool` or `bluetoothctl` for characteristic read/write

---

## 12. OUI Vendor Identification

**OUI** (Organizationally Unique Identifier) is the first 24 bits (3 octets)
of a **public** MAC address, assigned by the IEEE to equipment manufacturers.

```
BD Address: 18:EF:3A : 5A:EF:17
            ────────   ────────
              OUI        NIC specific
            (Samsung)   (device serial)
```

Built-in OUI database covers: Raspberry Pi, Apple, Samsung, Espressif
(ESP32), Texas Instruments, Nordic Semiconductor, Xiaomi, Toshiba, Intel,
Broadcom, Sony, Garmin, Fitbit, AVM, and others.

**OUI lookup limitations:**

- **Random addresses** (`addr_type='random'`): The first byte's upper bits
  are repurposed for the random address type indicator. The OUI has no
  meaning. `oui_lookup()` returns `""` for these.

- **Virtualized addresses**: VMs and some test hardware use locally-
  administered addresses (bit 1 of first byte = 1), which override OUI.

- **Database completeness**: The built-in DB covers common IoT/consumer
  hardware. For comprehensive lookup, query the IEEE registry:
  `https://regauth.standards.ieee.org/standards-ra-web/pub/view.html#registries`

---

## 13. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `hciconfig: No such device` | Controller not up or rfkill blocked | `sudo rfkill unblock bluetooth && sudo hciconfig hci0 up` |
| Soft blocked: yes | rfkill default state on boot | `sudo rfkill unblock bluetooth` |
| `btmgmt find` returns nothing | Controller may be down | Ensure `controller_up()` succeeded |
| `hcitool lescan: Can't set scan parameters` | Need root or capability | Run with `sudo` |
| No classic devices in scan | They must be DISCOVERABLE | Pair from device side first, or enable discoverable on target |
| `sdptool browse` → "Failed to connect to SDP server" | BLE-only device | Use GATT (`get_ble_services`) instead |
| `get_ble_services` → RuntimeError | bleak not installed | `pip install bleak` |
| Random addresses changing | iOS/Android privacy feature | Normal — cannot be prevented without pairing |
| Wi-Fi degraded during BLE scan | 2.4 GHz RF coexistence | Use 5 GHz Wi-Fi or reduce scan frequency |
| `bluetoothctl show` → Controller not available | BlueZ daemon not running | `sudo systemctl start bluetooth` |
| Scan finds fewer devices than expected | Short scan duration | Increase to 20–30 s; advertising intervals vary per device |
| `hcitool rssi` returns error | Device not connected | RSSI only works on active ACL connections |
| Device appears with wrong name | Advertising name vs SDP name differ | Use `get_name(addr)` for authoritative name via HCI |

### Checking BlueZ Daemon

```bash
sudo systemctl status bluetooth
sudo systemctl restart bluetooth

# Enable on boot
sudo systemctl enable bluetooth
```

### Complete Reset if Stuck

```bash
sudo systemctl stop bluetooth
sudo hciconfig hci0 down
sudo rfkill block bluetooth
sleep 1
sudo rfkill unblock bluetooth
sudo hciconfig hci0 up
sudo systemctl start bluetooth
```

### Installing Optional Dependencies

```bash
# GATT/BLE service enumeration
pip install bleak

# Advanced packet analysis (optional)
sudo apt install -y wireshark
sudo adduser $USER wireshark
# then: sudo hcidump -i hci0 -w /tmp/bt.pcap
# open in Wireshark: File → Open → /tmp/bt.pcap
```

---

## See Also

- [docs/wifi.md](wifi.md) — Wi-Fi scanning (same BCM43455 chip)
- [docs/rfid-mifare.md](rfid-mifare.md) — RFID/NFC protocols
- [Bluetooth Core Specification 5.0](https://www.bluetooth.com/specifications/specs/core-specification-5-0/)
- [BlueZ Documentation](http://www.bluez.org/)
- `man hcitool` · `man sdptool` · `man btmgmt` · `man bluetoothctl`
