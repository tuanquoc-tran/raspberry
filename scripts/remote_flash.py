#!/usr/bin/env python3
"""
RaspFlip Remote Flash Client
==============================
Upload a firmware file from your laptop/PC to a Raspberry Pi running
RaspFlip's RemoteFlashServer, which then programs the chip directly.

Requires only Python 3 stdlib — no extra packages needed.

Usage examples:
  # Flash AVR / Arduino Uno
  python scripts/remote_flash.py \\
      --host raspberrypi.local --token <token> \\
      --target avr --mcu atmega328p \\
      firmware.hex

  # Flash STM32
  python scripts/remote_flash.py \\
      --host 192.168.1.100 --token <token> \\
      --target stm32 firmware.bin

  # Flash SPI NOR chip
  python scripts/remote_flash.py \\
      --host 192.168.1.100 --token <token> \\
      --target spi router_firmware.bin

  # Check server status only
  python scripts/remote_flash.py \\
      --host raspberrypi.local --token <token> --status
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def _request(url: str, token: str, data: bytes | None = None,
             timeout: int = 10) -> dict:
    """Send GET/POST and return parsed JSON. Raises on HTTP error."""
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json",
    }
    if data is not None:
        headers["Content-Length"] = str(len(data))
    req = urllib.request.Request(url, data=data, headers=headers,
                                  method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RaspFlip Remote Flash Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("file",
                        nargs="?",
                        help="Firmware file (.hex or .bin)")
    parser.add_argument("--host", "-H",
                        required=True,
                        help="RPi hostname or IP address")
    parser.add_argument("--port", "-p",
                        type=int, default=7777,
                        help="Server port (default: 7777)")
    parser.add_argument("--token", "-t",
                        required=True,
                        help="Authentication token")
    parser.add_argument("--target",
                        default="avr",
                        choices=["avr", "stm32", "spi"],
                        help="Target chip type (default: avr)")
    parser.add_argument("--mcu",
                        default="atmega328p",
                        help="AVR MCU type (default: atmega328p)")
    parser.add_argument("--serial-port",
                        default="/dev/serial0",
                        dest="serial_port",
                        help="Serial port on RPi for STM32 (default: /dev/serial0)")
    parser.add_argument("--no-verify",
                        action="store_true",
                        help="Skip verify after write")
    parser.add_argument("--status",
                        action="store_true",
                        help="Check server status and exit")

    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    # ---- Check server status ----
    print(f"[*] Connecting to {base_url} …")
    try:
        status = _request(f"{base_url}/status", args.token, timeout=5)
    except Exception as e:
        print(f"[-] Cannot reach server: {e}", file=sys.stderr)
        return 1

    print(f"[+] Server OK — supported targets: {', '.join(status.get('targets', []))}")

    if args.status:
        return 0

    # ---- Validate inputs ----
    if not args.file:
        parser.error("firmware file required (unless --status)")

    if not os.path.isfile(args.file):
        print(f"[-] File not found: {args.file}", file=sys.stderr)
        return 1

    file_size = os.path.getsize(args.file)
    if file_size > 32 * 1024 * 1024:
        print("[-] File too large (>32 MB)", file=sys.stderr)
        return 1

    # ---- Upload ----
    with open(args.file, "rb") as f:
        raw = f.read()

    print(f"[*] Uploading {os.path.basename(args.file)} ({file_size:,} bytes) "
          f"→ {args.target.upper()} …")

    payload = json.dumps({
        "target":   args.target,
        "mcu":      args.mcu,
        "port":     args.serial_port,
        "filename": os.path.basename(args.file),
        "file_b64": base64.b64encode(raw).decode(),
        "verify":   not args.no_verify,
    }).encode()

    try:
        result = _request(f"{base_url}/flash", args.token,
                          data=payload, timeout=180)
    except Exception as e:
        print(f"[-] Flash request failed: {e}", file=sys.stderr)
        return 1

    if result.get("success"):
        size_info = ""
        if result.get("size"):
            size_info = f" ({result['size']:,} bytes)"
        print(f"[✓] {result['message']}{size_info}")
        return 0
    else:
        print(f"[✗] Flash failed: {result.get('message', 'unknown error')}",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
