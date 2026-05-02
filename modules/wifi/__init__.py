"""
Wi-Fi Module for RaspFlip
Requires root (sudo) for scan and interface management.

Chip: BCM43455 (Raspberry Pi 4 built-in)
Supported modes: managed, AP, IBSS, P2P
NOT supported: monitor mode, packet injection

Tools used (must be installed):
  iw, iwlist, ip, rfkill, wpa_supplicant, wpa_cli
"""

import re
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Network:
    """Represents a scanned Wi-Fi network (BSS)."""
    bssid: str
    ssid: str
    channel: int
    frequency_ghz: float
    band: str                       # '2.4GHz' | '5GHz'
    signal_dbm: int
    quality: str                    # e.g. '54/70'
    quality_pct: int                # 0-100
    encryption: str                 # 'Open' | 'WEP' | 'WPA' | 'WPA2' | 'WPA2/WPA3' | 'WPA3'
    cipher: str                     # e.g. 'CCMP' | 'TKIP/CCMP'
    auth: str                       # e.g. 'PSK' | 'SAE' | 'Enterprise'
    last_beacon_ms: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterfaceInfo:
    """State of a wireless interface."""
    iface: str
    mac: str
    mode: str                       # managed | monitor | AP | ...
    state: str                      # UP | DOWN
    ssid: Optional[str]
    bssid: Optional[str]
    channel: Optional[int]
    frequency_mhz: Optional[int]
    txpower_dbm: Optional[float]
    bitrate_mbps: Optional[float]
    signal_dbm: Optional[int]
    ip: Optional[str]
    rfkill_soft: bool
    rfkill_hard: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], sudo: bool = False, timeout: int = 15) -> subprocess.CompletedProcess:
    if sudo:
        cmd = ['sudo'] + cmd
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _parse_iwlist_scan(raw: str) -> List[Network]:
    """Parse `iwlist <iface> scan` output into Network objects."""
    networks: List[Network] = []
    # Split on Cell boundaries
    cells = re.split(r'Cell \d+ -', raw)
    for cell in cells[1:]:   # skip preamble
        try:
            bssid = _re(r'Address:\s*([\dA-Fa-f:]{17})', cell) or ''
            ssid = _re(r'ESSID:"([^"]*)"', cell) or '<hidden>'
            channel = int(_re(r'Channel:(\d+)', cell) or 0)
            freq_str = _re(r'Frequency:([\d.]+)', cell) or '0'
            freq = float(freq_str)
            band = '2.4GHz' if freq < 3 else '5GHz'
            signal = int(_re(r'Signal level=(-?\d+)', cell) or -100)
            quality_raw = _re(r'Quality=(\d+/\d+)', cell) or '0/70'
            q_num, q_den = (int(x) for x in quality_raw.split('/'))
            quality_pct = int(q_num / q_den * 100)
            last_beacon = _re(r'Last beacon:\s*(\d+)ms', cell)

            # Encryption
            enc_on = 'Encryption key:on' in cell
            has_wpa2 = 'IEEE 802.11i/WPA2' in cell
            has_wpa3 = 'WPA3' in cell or 'SAE' in cell
            has_wpa  = 'IE: WPA Version 1' in cell

            if not enc_on:
                encryption = 'Open'
            elif has_wpa3 and has_wpa2:
                encryption = 'WPA2/WPA3'
            elif has_wpa3:
                encryption = 'WPA3'
            elif has_wpa2:
                encryption = 'WPA2'
            elif has_wpa:
                encryption = 'WPA'
            else:
                encryption = 'WEP'

            # Ciphers
            ciphers = re.findall(r'Pairwise Ciphers.*?:\s*(.*)', cell)
            cipher = '/'.join(dict.fromkeys(
                c.strip() for raw_c in ciphers for c in raw_c.split()
            )) if ciphers else ('N/A' if not enc_on else '?')

            # Auth
            auth_matches = re.findall(r'Authentication Suites.*?:\s*(.*)', cell)
            auth_tokens = ' '.join(auth_matches).strip()
            if 'SAE' in auth_tokens:
                auth = 'SAE'
            elif 'PSK' in auth_tokens:
                auth = 'PSK'
            elif 'EAP' in auth_tokens or 'MGT' in auth_tokens:
                auth = 'Enterprise'
            else:
                auth = 'N/A'

            networks.append(Network(
                bssid=bssid.upper(),
                ssid=ssid,
                channel=channel,
                frequency_ghz=freq,
                band=band,
                signal_dbm=signal,
                quality=quality_raw,
                quality_pct=quality_pct,
                encryption=encryption,
                cipher=cipher,
                auth=auth,
                last_beacon_ms=int(last_beacon) if last_beacon else None,
            ))
        except Exception as exc:
            logger.debug(f"Parse error on cell: {exc}")
    return networks


def _re(pattern: str, text: str) -> Optional[str]:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def _rfkill_status(iface: str) -> tuple[bool, bool]:
    """Return (soft_blocked, hard_blocked) for the wifi rfkill entry."""
    try:
        r = _run(['rfkill', 'list', 'wifi'])
        soft = bool(re.search(r'Soft blocked:\s*yes', r.stdout))
        hard = bool(re.search(r'Hard blocked:\s*yes', r.stdout))
        return soft, hard
    except Exception:
        return False, False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class WiFiManager:
    """
    High-level Wi-Fi manager.

    All operations that interact with the kernel (scan, up/down,
    rfkill) require root privileges — call from sudo or add the
    invoking user to the `netdev` group and configure sudoers.
    """

    def __init__(self, iface: str = 'wlan0'):
        self.iface = iface

    # ------------------------------------------------------------------
    # Interface control
    # ------------------------------------------------------------------

    def interface_up(self) -> bool:
        """Bring the wireless interface up (unblocks rfkill if needed)."""
        soft, hard = _rfkill_status(self.iface)
        if hard:
            logger.error("Hardware RF-kill switch is ON — cannot unblock via software")
            return False
        if soft:
            r = _run(['rfkill', 'unblock', 'wifi'], sudo=True)
            if r.returncode != 0:
                logger.error(f"rfkill unblock failed: {r.stderr.strip()}")
                return False
            time.sleep(0.3)
        r = _run(['ip', 'link', 'set', self.iface, 'up'], sudo=True)
        if r.returncode != 0:
            logger.error(f"ip link set up failed: {r.stderr.strip()}")
            return False
        logger.info(f"{self.iface} is UP")
        return True

    def interface_down(self) -> bool:
        """Take the wireless interface down."""
        r = _run(['ip', 'link', 'set', self.iface, 'down'], sudo=True)
        if r.returncode != 0:
            logger.error(f"ip link set down failed: {r.stderr.strip()}")
            return False
        logger.info(f"{self.iface} is DOWN")
        return True

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self, ensure_up: bool = True) -> Optional[List[Network]]:
        """
        Perform an active scan and return list of discovered networks,
        sorted by signal strength (strongest first).

        Requires root.  If the interface is down and `ensure_up=True`,
        it will be brought up automatically.
        """
        if ensure_up:
            info = self.get_interface_info()
            if info and info.state == 'DOWN':
                if not self.interface_up():
                    return None

        r = _run(['iwlist', self.iface, 'scan'], sudo=True, timeout=20)
        if r.returncode != 0 or 'Scan completed' not in r.stdout:
            err = r.stderr.strip() or r.stdout.strip()
            logger.error(f"Scan failed: {err}")
            return None

        networks = _parse_iwlist_scan(r.stdout)
        networks.sort(key=lambda n: n.signal_dbm, reverse=True)
        logger.info(f"Found {len(networks)} network(s)")
        return networks

    # ------------------------------------------------------------------
    # Interface info
    # ------------------------------------------------------------------

    def get_interface_info(self) -> Optional[InterfaceInfo]:
        """Return current state of the wireless interface."""
        try:
            iw_r  = _run(['iw', 'dev', self.iface, 'info'])
            iwc_r = _run(['iwconfig', self.iface])
            ip_r  = _run(['ip', 'addr', 'show', self.iface])
            soft, hard = _rfkill_status(self.iface)

            iw  = iw_r.stdout
            iwc = iwc_r.stdout

            mac   = _re(r'addr\s+([\da-f:]{17})', iw) or \
                    _re(r'HWaddr\s+([\dA-Fa-f:]{17})', iwc) or ''
            mode  = _re(r'type\s+(\w+)', iw) or \
                    _re(r'Mode:(\S+)', iwc) or 'unknown'
            ssid  = _re(r'ssid\s+(.+)', iw) or \
                    _re(r'ESSID:"([^"]*)"', iwc)
            bssid = _re(r'Access Point:\s*([\dA-Fa-f:]{17})', iwc)
            ch    = _re(r'channel\s+(\d+)', iw)
            freq  = _re(r'channel\s+\d+\s+\((\d+)\s+MHz\)', iw)
            txpwr = _re(r'txpower\s+([\d.]+)', iw)
            bitrate = _re(r'Bit Rate=([\d.]+)', iwc)
            signal  = _re(r'Signal level=(-?\d+)', iwc)
            ip_addr = _re(r'inet\s+([\d.]+/\d+)', ip_r.stdout)

            # Interface state from ip link
            state = 'UP' if 'state UP' in ip_r.stdout or \
                    re.search(r'<[^>]*UP[^>]*>', ip_r.stdout) else 'DOWN'

            return InterfaceInfo(
                iface=self.iface,
                mac=mac.upper(),
                mode=mode,
                state=state,
                ssid=ssid if ssid and ssid != '""' else None,
                bssid=bssid.upper() if bssid else None,
                channel=int(ch) if ch else None,
                frequency_mhz=int(freq) if freq else None,
                txpower_dbm=float(txpwr) if txpwr else None,
                bitrate_mbps=float(bitrate) if bitrate else None,
                signal_dbm=int(signal) if signal else None,
                ip=ip_addr,
                rfkill_soft=soft,
                rfkill_hard=hard,
            )
        except Exception as exc:
            logger.error(f"get_interface_info error: {exc}")
            return None

    # ------------------------------------------------------------------
    # Network details
    # ------------------------------------------------------------------

    def get_network_info(self) -> Dict[str, Any]:
        """
        Return current network configuration:
        IP, netmask, gateway, DNS servers, hostname.
        """
        info: Dict[str, Any] = {}

        # IP / netmask
        r = _run(['ip', 'addr', 'show', self.iface])
        info['ip_cidr']  = _re(r'inet\s+([\d.]+/\d+)', r.stdout)
        info['ip6_cidr'] = _re(r'inet6\s+([^\s]+)', r.stdout)

        # Gateway
        r2 = _run(['ip', 'route', 'show', 'default'])
        info['gateway'] = _re(r'default via ([\d.]+)', r2.stdout)

        # DNS (systemd-resolved)
        r3 = _run(['resolvectl', 'status', self.iface])
        if r3.returncode == 0:
            dns = re.findall(r'DNS Servers:\s*([\d. ]+)', r3.stdout)
            info['dns'] = dns[0].strip().split() if dns else []
        else:
            # Fallback: parse /etc/resolv.conf
            try:
                with open('/etc/resolv.conf') as f:
                    info['dns'] = re.findall(r'^nameserver\s+([\d.]+)', f.read(), re.M)
            except OSError:
                info['dns'] = []

        # Hostname
        r4 = _run(['hostname'])
        info['hostname'] = r4.stdout.strip()

        return info

    # ------------------------------------------------------------------
    # Connection management (wpa_supplicant)
    # ------------------------------------------------------------------

    def get_connection_status(self) -> Dict[str, Any]:
        """Return current wpa_supplicant association status."""
        r = _run(['wpa_cli', '-i', self.iface, 'status'])
        if r.returncode != 0:
            return {'error': r.stderr.strip() or 'wpa_cli not available'}
        status: Dict[str, Any] = {}
        for line in r.stdout.splitlines():
            if '=' in line:
                k, _, v = line.partition('=')
                status[k.strip()] = v.strip()
        return status

    def list_saved_networks(self) -> List[Dict[str, str]]:
        """List networks saved in wpa_supplicant."""
        r = _run(['wpa_cli', '-i', self.iface, 'list_networks'])
        if r.returncode != 0:
            return []
        lines = r.stdout.strip().splitlines()[1:]  # skip header
        nets = []
        for line in lines:
            parts = re.split(r'\t+', line)
            if len(parts) >= 3:
                nets.append({
                    'id':    parts[0],
                    'ssid':  parts[1],
                    'bssid': parts[2],
                    'flags': parts[3] if len(parts) > 3 else '',
                })
        return nets

    def connect(self, ssid: str, password: Optional[str] = None) -> bool:
        """
        Connect to a WPA2-PSK or Open network via wpa_cli.
        Returns True if association started (check status() for completion).
        """
        cli = ['wpa_cli', '-i', self.iface]

        # Add new network
        r = _run(cli + ['add_network'])
        if r.returncode != 0:
            logger.error("wpa_cli add_network failed")
            return False
        net_id = r.stdout.strip()

        # Set SSID (quoted)
        _run(cli + ['set_network', net_id, 'ssid', f'"{ssid}"'])

        if password:
            _run(cli + ['set_network', net_id, 'psk', f'"{password}"'])
        else:
            _run(cli + ['set_network', net_id, 'key_mgmt', 'NONE'])

        _run(cli + ['enable_network', net_id])
        _run(cli + ['select_network', net_id])
        _run(cli + ['save_config'])

        logger.info(f"Connecting to '{ssid}'… (check status)")
        return True

    def disconnect(self) -> bool:
        """Disconnect from current AP."""
        r = _run(['wpa_cli', '-i', self.iface, 'disconnect'])
        return r.returncode == 0

    # ------------------------------------------------------------------
    # Saved passwords
    # ------------------------------------------------------------------

    def read_saved_passwords(self) -> List[Dict[str, str]]:
        """
        Read saved Wi-Fi credentials from wpa_supplicant.conf.

        Tries common config paths in order.
        Requires root to read the file.

        Returns list of dicts with keys:
          ssid, psk (password or '<none>' for open), key_mgmt, priority
        """
        candidates = [
            f'/etc/wpa_supplicant/wpa_supplicant-{self.iface}.conf',
            '/etc/wpa_supplicant/wpa_supplicant.conf',
        ]

        content = None
        used_path = None
        for path in candidates:
            r = _run(['cat', path], sudo=True)
            if r.returncode == 0 and 'network={' in r.stdout:
                content = r.stdout
                used_path = path
                break

        if not content:
            logger.warning("wpa_supplicant.conf not found or no saved networks")
            return []

        logger.info(f"Reading credentials from {used_path}")
        networks = []

        # Extract each network={...} block
        for block in re.findall(r'network=\{([^}]+)\}', content, re.S):
            entry: Dict[str, str] = {}

            ssid_m = re.search(r'ssid="([^"]*)"', block)
            psk_m  = re.search(r'psk="([^"]*)"', block)     # plaintext password
            hash_m = re.search(r'^\s*psk=([0-9a-fA-F]{64})\s*$', block, re.M)  # hashed
            km_m   = re.search(r'key_mgmt=(\S+)', block)
            pri_m  = re.search(r'priority=(\d+)', block)

            entry['ssid']     = ssid_m.group(1) if ssid_m else '<hidden>'
            entry['key_mgmt'] = km_m.group(1) if km_m else 'WPA-PSK'
            entry['priority'] = pri_m.group(1) if pri_m else '0'

            if psk_m:
                entry['psk'] = psk_m.group(1)          # plaintext stored
            elif hash_m:
                entry['psk'] = f'<hashed:{hash_m.group(1)[:16]}…>'  # wpa_passphrase output
            elif 'NONE' in entry['key_mgmt']:
                entry['psk'] = '<none — open network>'
            else:
                entry['psk'] = '<not stored>'

            networks.append(entry)

        return networks

    # ------------------------------------------------------------------
    # Capabilities
    # ------------------------------------------------------------------

    def get_capabilities(self) -> Dict[str, Any]:
        """Return hardware capabilities of the wireless phy."""
        r = _run(['iw', 'list'])
        raw = r.stdout

        modes = re.findall(r'\* (\S+)\n', re.search(
            r'Supported interface modes:(.*?)(?=\n\t\t[^\s*]|\Z)', raw, re.S
        ).group(1) if re.search(r'Supported interface modes:', raw) else '')

        bands: Dict[str, List[int]] = {}
        for band_m in re.finditer(r'Band (\d+):(.*?)(?=Band \d+:|$)', raw, re.S):
            band_num = band_m.group(1)
            channels = re.findall(r'\* (\d+) MHz \[(\d+)\]', band_m.group(2))
            ghz = '2.4GHz' if band_num == '1' else '5GHz'
            bands[ghz] = [int(ch) for _, ch in channels]

        ciphers = re.findall(r'\* (\w+) \(00-0f-ac:\d+\)', raw)

        return {
            'phy':     'phy0',
            'driver':  _get_driver(),
            'modes':   modes,
            'bands':   bands,
            'ciphers': list(dict.fromkeys(ciphers)),
            'monitor': 'monitor' in [m.lower() for m in modes],
        }

    # ------------------------------------------------------------------
    # Signal monitor
    # ------------------------------------------------------------------

    def monitor_signal(self, interval: float = 1.0, count: int = 10) -> List[Dict[str, Any]]:
        """
        Poll signal/bitrate every `interval` seconds, `count` times.
        Returns list of readings [{time, signal_dbm, bitrate_mbps, quality_pct}].
        """
        readings: List[Dict[str, Any]] = []
        for _ in range(count):
            r = _run(['iwconfig', self.iface])
            t = time.time()
            sig   = _re(r'Signal level=(-?\d+)', r.stdout)
            rate  = _re(r'Bit Rate=([\d.]+)', r.stdout)
            qual  = _re(r'Link Quality=(\d+)/(\d+)', r.stdout)
            q_pct = int(int(qual.split('/')[0]) / int(qual.split('/')[1]) * 100) \
                    if qual else None
            readings.append({
                'time':        t,
                'signal_dbm':  int(sig) if sig else None,
                'bitrate_mbps': float(rate) if rate else None,
                'quality_pct': q_pct,
            })
            if _ < count - 1:
                time.sleep(interval)
        return readings

    # ------------------------------------------------------------------
    # Channel analysis
    # ------------------------------------------------------------------

    def channel_analysis(self) -> Dict[int, List[str]]:
        """
        Scan and group BSSIDs by channel.
        Useful to identify congested channels.
        """
        networks = self.scan()
        if not networks:
            return {}
        result: Dict[int, List[str]] = {}
        for n in networks:
            result.setdefault(n.channel, []).append(n.ssid)
        return dict(sorted(result.items()))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_driver() -> str:
    try:
        r = subprocess.run(
            ['readlink', '-f', '/sys/class/net/wlan0/device/driver'],
            capture_output=True, text=True
        )
        return os.path.basename(r.stdout.strip()) if r.returncode == 0 else 'unknown'
    except Exception:
        return 'unknown'


def signal_to_quality(dbm: int) -> str:
    """Convert dBm to human-readable quality label."""
    if dbm >= -50:  return 'Excellent'
    if dbm >= -60:  return 'Good'
    if dbm >= -70:  return 'Fair'
    if dbm >= -80:  return 'Weak'
    return 'Very Weak'


def encryption_risk(enc: str) -> str:
    """Return security risk level for an encryption type."""
    risks = {
        'Open':      'CRITICAL — no encryption',
        'WEP':       'HIGH — WEP cracked in minutes',
        'WPA':       'MEDIUM — TKIP vulnerable to MITM',
        'WPA2':      'LOW — secure with strong password',
        'WPA2/WPA3': 'LOW — transition mode',
        'WPA3':      'VERY LOW — SAE resistant to offline attacks',
    }
    return risks.get(enc, 'Unknown')
