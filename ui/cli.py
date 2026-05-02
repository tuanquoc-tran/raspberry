"""
CLI User Interface for RaspFlip
"""

import os

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()

def main_menu():
    """Display main menu and handle user input"""
    
    while True:
        console.clear()
        
        # Create menu table
        table = Table(title="RaspFlip Main Menu", show_header=True, header_style="bold magenta")
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Module", style="green")
        table.add_column("Description", style="white")
        
        table.add_row("1", "RFID/NFC", "Read, write, and emulate RFID/NFC cards")
        table.add_row("2", "Sub-GHz", "Capture and replay RF signals")
        table.add_row("3", "Infrared", "Learn and replay IR signals")
        table.add_row("4", "BadUSB", "Keystroke injection attacks")
        table.add_row("5", "GPIO", "GPIO manipulation and testing")
        table.add_row("6", "Wi-Fi", "Wi-Fi scanning and pentesting")
        table.add_row("7", "Bluetooth", "Bluetooth scanning and analysis")
        table.add_row("8", "iButton", "Read and clone iButton keys")
        table.add_row("9", "Settings", "Configure hardware and software")
        table.add_row("10", "Flash/Chip", "Read, write, clone SPI/STM32/AVR/I2C chips")
        table.add_row("11", "Hardware",   "System info, temperature, CPU, connected devices")
        table.add_row("12", "Servo",      "PCA9685 16-ch PWM driver — servo test & control")
        table.add_row("0", "Exit", "Exit RaspFlip")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0","1","2","3","4","5","6","7","8","9","10","11","12"])
        
        if choice == "0":
            break
        elif choice == "1":

            rfid_menu()
        elif choice == "2":
            console.print("[yellow]Sub-GHz module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "3":
            console.print("[yellow]IR module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "4":
            console.print("[yellow]BadUSB module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "5":
            console.print("[yellow]GPIO module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "6":
            wifi_menu()
        elif choice == "7":
            bluetooth_menu()
        elif choice == "8":
            console.print("[yellow]iButton module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "9":
            settings_menu()
        elif choice == "10":
            flash_menu()
        elif choice == "11":
            hardware_menu()
        elif choice == "12":
            servo_menu()

def rfid_menu():
    """RFID/NFC module menu"""
    from modules.rfid import get_reader, MIFARE_KEYA

    # Initialise RC522 once for the whole session
    reader = get_reader('rc522')
    if not reader.initialize():
        console.print("[red]Failed to initialise RC522. Check wiring and libraries.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    while True:
        console.clear()

        table = Table(title="RFID/NFC Module (RC522)", show_header=True, header_style="bold cyan")
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Action", style="white")

        table.add_row("1", "Read card (UID only)")
        table.add_row("2", "Read card (UID + text payload)")
        table.add_row("3", "Write text to card")
        table.add_row("4", "Dump card (all sectors)")
        table.add_row("5", "Save last dump to file")
        table.add_row("6", "Load & write dump to card (clone)")
        table.add_row("7", "List saved cards")
        table.add_row("0", "Back to main menu")

        console.print(table)
        console.print()

        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7"])

        if choice == "0":
            reader.cleanup()
            break

        elif choice == "1":
            _rfid_read_uid(reader)

        elif choice == "2":
            _rfid_read_card(reader)

        elif choice == "3":
            _rfid_write_card(reader)

        elif choice == "4":
            _rfid_dump_card(reader)

        elif choice == "5":
            _rfid_save_dump(reader)

        elif choice == "6":
            _rfid_clone_card(reader)

        elif choice == "7":
            _rfid_list_saved(reader)


# -----------------------------------------------------------------------
# RFID helpers
# -----------------------------------------------------------------------

_last_dump = None   # module-level cache for the most recent dump


def _rfid_read_uid(reader):
    console.print("[cyan]Place card on reader… (10 s timeout)[/cyan]")
    result = reader.read_uid(timeout=10)
    if result:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green")
        t.add_column("Value")
        t.add_row("UID (hex)", result['uid_hex'])
        t.add_row("UID (dec)", str(result['uid_int']))
        t.add_row("Card type", result['card_type'])
        t.add_row("Frequency", result['frequency'])
        console.print(Panel(t, title="Card detected", border_style="green"))
    else:
        console.print("[red]No card detected within timeout.[/red]")
    Prompt.ask("Press Enter to continue")


def _rfid_read_card(reader):
    console.print("[cyan]Place card on reader… (blocking)[/cyan]")
    result = reader.read_card()
    if result:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green")
        t.add_column("Value")
        t.add_row("UID (hex)", result['uid_hex'])
        t.add_row("UID (dec)", str(result['uid_int']))
        t.add_row("Card type", result['card_type'])
        t.add_row("Payload",   result.get('data', '(empty)'))
        console.print(Panel(t, title="Card read", border_style="green"))
    else:
        console.print("[red]Read failed.[/red]")
    Prompt.ask("Press Enter to continue")


def _rfid_write_card(reader):
    text = Prompt.ask("Enter text to write (max ~48 chars)")
    if len(text) > 48:
        console.print("[yellow]Text truncated to 48 characters.[/yellow]")
        text = text[:48]
    console.print("[cyan]Place card on reader… (blocking)[/cyan]")
    ok = reader.write_card(text)
    if ok:
        console.print("[green]Text written successfully.[/green]")
    else:
        console.print("[red]Write failed.[/red]")
    Prompt.ask("Press Enter to continue")


def _rfid_dump_card(reader):
    global _last_dump
    console.print("[cyan]Place card on reader… reading all sectors[/cyan]")
    dump = reader.dump_card()
    if not dump:
        console.print("[red]Dump failed.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    _last_dump = dump
    console.print(f"\n[green]UID: {dump['uid_hex']}  Type: {dump['card_type']}[/green]\n")

    for s_idx, sector in enumerate(dump['sectors']):
        t = Table(title=f"Sector {s_idx}", show_header=True, header_style="bold magenta")
        t.add_column("Block", style="cyan", width=6)
        t.add_column("Data (hex)", style="white")
        t.add_column("ASCII", style="dim")
        for b_offset, blk in enumerate(sector):
            block_num = s_idx * 4 + b_offset
            label = f"{block_num}"
            if b_offset == 3:
                label += " [trailer]"
            if blk is None:
                t.add_row(label, "[red]read error[/red]", "")
            else:
                hex_str = ' '.join(f'{x:02X}' for x in blk)
                ascii_str = ''.join(chr(x) if 32 <= x < 127 else '.' for x in blk)
                t.add_row(label, hex_str, ascii_str)
        console.print(t)

    console.print("[dim]Dump cached – use option 5 to save.[/dim]")
    Prompt.ask("Press Enter to continue")


def _rfid_save_dump(reader):
    global _last_dump
    if _last_dump is None:
        console.print("[yellow]No dump in memory. Run option 4 first.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return
    path = reader.save_card(_last_dump)
    console.print(f"[green]Saved to {path}[/green]")
    Prompt.ask("Press Enter to continue")


def _rfid_clone_card(reader):
    files = reader.list_saved_cards()
    if not files:
        console.print("[yellow]No saved cards found.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return

    t = Table(title="Saved cards", show_header=True, header_style="bold cyan")
    t.add_column("#", style="cyan", width=4)
    t.add_column("Filename", style="white")
    for i, f in enumerate(files, 1):
        t.add_row(str(i), f)
    console.print(t)

    choice = Prompt.ask("Enter number to select file (0 to cancel)")
    if choice == "0":
        return
    try:
        idx = int(choice) - 1
        filename = files[idx]
    except (ValueError, IndexError):
        console.print("[red]Invalid selection.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    dump = reader.load_card(filename)
    if not dump:
        console.print("[red]Failed to load dump.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    console.print(f"[cyan]Loaded: UID {dump.get('uid_hex')}  Type: {dump.get('card_type')}[/cyan]")
    console.print("[bold yellow]Place blank card on reader to write…[/bold yellow]")
    ok = reader.write_dump(dump)
    if ok:
        console.print("[green]Card cloned successfully.[/green]")
    else:
        console.print("[red]Clone completed with errors – check log.[/red]")
    Prompt.ask("Press Enter to continue")


def _rfid_list_saved(reader):
    files = reader.list_saved_cards()
    if not files:
        console.print("[yellow]No saved cards found.[/yellow]")
    else:
        t = Table(title="Saved RFID cards", show_header=True, header_style="bold cyan")
        t.add_column("#", style="cyan", width=4)
        t.add_column("Filename", style="white")
        for i, f in enumerate(files, 1):
            t.add_row(str(i), f)
        console.print(t)
    Prompt.ask("Press Enter to continue")



def settings_menu():
    """Settings and configuration menu"""
    while True:
        console.clear()
        
        table = Table(title="Settings", show_header=True, header_style="bold green")
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Setting", style="white")
        
        table.add_row("1", "Hardware configuration")
        table.add_row("2", "System information")
        table.add_row("3", "Update software")
        table.add_row("0", "Back to main menu")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3"])
        
        if choice == "0":
            break
        else:
            console.print("[yellow]Function not yet implemented[/yellow]")
            Prompt.ask("Press Enter to continue")


# ---------------------------------------------------------------------------
# Hardware Monitor menu
# ---------------------------------------------------------------------------

def hardware_menu():
    """Hardware monitor — CPU, RAM, temperature, connected devices."""
    while True:
        console.clear()
        t = Table(title="Hardware Monitor", show_header=True, header_style="bold magenta")
        t.add_column("Option", style="cyan", width=8)
        t.add_column("Info", style="white")
        t.add_row("1",  "System overview (CPU, RAM, Storage, Uptime)")
        t.add_row("2",  "Temperature (CPU, GPU, sensors, throttle)")
        t.add_row("3",  "CPU details (model, cores, frequency, usage)")
        t.add_row("4",  "RAM & Swap")
        t.add_row("5",  "Storage & disks")
        t.add_row("6",  "Network interfaces")
        t.add_row("7",  "USB devices (connected boards)")
        t.add_row("8",  "I2C devices (bus scan)")
        t.add_row("9",  "SPI / GPIO / UART interfaces")
        t.add_row("10", "All information (all in one)")
        t.add_row("0",  "Back")
        console.print(t)

        choice = Prompt.ask("Select option", choices=[str(i) for i in range(11)])
        if choice == "0":
            break
        elif choice == "1":
            _hw_overview()
        elif choice == "2":
            _hw_temperature()
        elif choice == "3":
            _hw_cpu()
        elif choice == "4":
            _hw_memory()
        elif choice == "5":
            _hw_storage()
        elif choice == "6":
            _hw_network()
        elif choice == "7":
            _hw_usb_devices()
        elif choice == "8":
            _hw_i2c_scan()
        elif choice == "9":
            _hw_spi_gpio()
        elif choice == "10":
            _hw_all()


# -----------------------------------------------------------------------
# Hardware display helpers  (data from modules.hardware)
# -----------------------------------------------------------------------

def _hw_overview():
    from modules.hardware import get_monitor
    d = get_monitor().get_overview()
    tc = "red" if d.cpu_temp_c >= 80 else "yellow" if d.cpu_temp_c >= 70 else "green"
    ram_pct  = d.ram_used_mb / d.ram_total_mb * 100 if d.ram_total_mb else 0
    disk_pct = d.disk_used_gb / d.disk_total_gb * 100 if d.disk_total_gb else 0

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("K", style="bold cyan", width=22)
    t.add_column("V", style="white")
    t.add_row("Model",        d.model)
    t.add_row("Hostname",     d.hostname)
    t.add_row("Kernel",       d.kernel)
    t.add_row("Architecture", d.arch)
    t.add_row("Uptime",       d.uptime)
    t.add_row("Load average", d.load)
    t.add_row("CPU Temp",     f"[{tc}]{d.cpu_temp_c:.1f} °C[/{tc}]")
    t.add_row("RAM",          f"{d.ram_used_mb} / {d.ram_total_mb} MB  ({ram_pct:.0f}% used)")
    t.add_row("Storage (/)",  f"{d.disk_used_gb} / {d.disk_total_gb} GB  ({disk_pct:.0f}% used)")
    console.print(Panel(t, title="System Overview", border_style="magenta"))
    Prompt.ask("Press Enter to continue")


def _hw_temperature():
    from modules.hardware import get_monitor
    th = get_monitor().get_thermal()

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("Sensor", style="bold cyan", width=26)
    t.add_column("Value",  style="white")

    border = "green"
    for r in th.readings:
        c = "red" if r.temp_c >= 80 else "yellow" if r.temp_c >= 70 else "green"
        if c != "green":
            border = c
        t.add_row(r.label, f"[{c}]{r.temp_c:.1f} °C[/{c}]")

    t.add_row("Throttle", th.throttle_raw)
    if th.throttle_active:
        t.add_row("", "[red]⚠ CPU is currently throttled![/red]")
    elif th.throttle_events:
        t.add_row("", "[yellow]⚠ Throttling has occurred since boot (now recovered)[/yellow]")

    console.print(Panel(t, title="Temperature Sensors", border_style=border))
    console.print(
        "[dim]  < 70 °C — Normal  |  70–80 °C — Warm  |  > 80 °C — Hot (throttle risk)[/dim]"
    )
    Prompt.ask("Press Enter to continue")


def _hw_cpu():
    from modules.hardware import get_monitor
    cpu = get_monitor().get_cpu()

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("K", style="bold cyan", width=22)
    t.add_column("V", style="white")
    if cpu.hardware:
        t.add_row("Hardware",   cpu.hardware)
    if cpu.model_name:
        t.add_row("Model",      cpu.model_name)
    if cpu.revision:
        t.add_row("Revision",   cpu.revision)
    t.add_row("Cores",          str(cpu.cores))
    t.add_row("Governor",       cpu.governor)
    usage_col = "red" if cpu.usage_pct > 90 else "yellow" if cpu.usage_pct > 70 else "green"
    t.add_row("CPU usage",      f"[{usage_col}]{cpu.usage_pct:.1f} %[/{usage_col}]")
    for f in cpu.freqs:
        t.add_row(f"cpu{f.core}",
                  f"cur {f.cur_mhz} MHz  /  min {f.min_mhz} MHz  /  max {f.max_mhz} MHz")
    console.print(Panel(t, title="CPU Details", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _hw_memory():
    from modules.hardware import get_monitor
    m = get_monitor().get_memory()

    ram_pct  = m.used_mb  / m.total_mb  * 100 if m.total_mb  else 0
    swap_pct = m.swap_used_mb / m.swap_total_mb * 100 if m.swap_total_mb else 0
    rc = "red" if ram_pct  > 85 else "yellow" if ram_pct  > 70 else "green"
    sc = "red" if swap_pct > 50 else "yellow" if swap_pct > 20 else "green"

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("K", style="bold cyan", width=22)
    t.add_column("V", style="white")
    t.add_row("Total RAM",   f"{m.total_mb} MB")
    t.add_row("Used",        f"[{rc}]{m.used_mb} MB  ({ram_pct:.0f}%)[/{rc}]")
    t.add_row("Available",   f"{m.available_mb} MB")
    t.add_row("Free",        f"{m.free_mb} MB")
    t.add_row("Buffers",     f"{m.buffers_mb} MB")
    t.add_row("Cached",      f"{m.cached_mb} MB")
    t.add_row("Swap total",  f"{m.swap_total_mb} MB")
    t.add_row("Swap used",   f"[{sc}]{m.swap_used_mb} MB  ({swap_pct:.0f}%)[/{sc}]")
    console.print(Panel(t, title="RAM & Swap", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _hw_storage():
    from modules.hardware import get_monitor
    st = get_monitor().get_storage()

    t = Table(show_header=True, header_style="bold cyan", padding=(0, 1))
    t.add_column("Mount",  style="white", width=20)
    t.add_column("Device", style="dim",   width=16)
    t.add_column("FS",     style="dim",   width=8)
    t.add_column("Total",  style="white", width=8)
    t.add_column("Used",   style="white", width=8)
    t.add_column("Free",   style="white", width=8)
    t.add_column("Usage",  style="white", width=7)
    for d in st.disks:
        col = "red" if d.pct > 85 else "yellow" if d.pct > 70 else "green"
        t.add_row(d.mount, d.device, d.fstype,
                  d.total, d.used, d.free, f"[{col}]{d.pct}%[/{col}]")
    console.print(Panel(t, title="Storage Partitions", border_style="cyan"))
    if st.sd_model:
        console.print(f"  [dim]SD Card: [white]{st.sd_model}[/white]  {st.sd_size or ''}[/dim]")
    Prompt.ask("Press Enter to continue")


def _hw_network():
    from modules.hardware import get_monitor
    net = get_monitor().get_network()

    t = Table(show_header=True, header_style="bold cyan", padding=(0, 1))
    t.add_column("Interface",  style="white", width=16)
    t.add_column("State",      style="white", width=8)
    t.add_column("IP Address", style="white")
    for ifc in net.interfaces:
        sc = "green" if "UP" in ifc.state else "red"
        t.add_row(ifc.name, f"[{sc}]{ifc.state}[/{sc}]", ifc.addresses or "—")
    console.print(Panel(t, title="Network Interfaces", border_style="cyan"))
    console.print(f"  [dim]Gateway: [white]{net.gateway}[/white]    DNS: [white]{net.dns}[/white][/dim]")
    Prompt.ask("Press Enter to continue")


def _hw_usb_devices():
    from modules.hardware import get_monitor
    usb = get_monitor().get_usb()

    t = Table(show_header=True, header_style="bold cyan", padding=(0, 1))
    t.add_column("Bus/Dev",     style="dim",    width=10)
    t.add_column("VID:PID",     style="yellow", width=12)
    t.add_column("Description", style="white")
    t.add_column("Board?",      style="green")
    for dev in usb.devices:
        t.add_row(dev.bus_dev, dev.vidpid, dev.description, dev.board)
    console.print(Panel(t, title="USB Devices (lsusb)", border_style="cyan"))

    if usb.serial_ports:
        console.print(f"  [dim]Serial ports: [white]{',  '.join(usb.serial_ports)}[/white][/dim]")
    else:
        console.print("  [dim]Serial ports: none found (/dev/ttyACM* / /dev/ttyUSB*)[/dim]")

    if usb.recognized_boards:
        console.print("  [bold green]Recognized boards: " + ",  ".join(usb.recognized_boards) + "[/bold green]")
    else:
        console.print("  [dim]No known boards detected (check VID:PID above).[/dim]")
    Prompt.ask("Press Enter to continue")


def _hw_i2c_scan():
    from modules.hardware import get_monitor
    console.print("[cyan]Scanning I2C bus 1 (GPIO2/GPIO3)…[/cyan]")
    devices = get_monitor().scan_i2c(bus=1)

    if not devices:
        console.print(Panel(
            "[dim]No I2C devices found.[/dim]\n"
            "Check: SDA=GPIO2(pin3), SCL=GPIO3(pin5), 3.3V, pull-up 4.7kΩ",
            title="I2C Scan", border_style="yellow",
        ))
    else:
        t = Table(show_header=True, header_style="bold cyan", padding=(0, 1))
        t.add_column("Address",  style="yellow", width=14)
        t.add_column("Device",   style="white")
        for dev in devices:
            t.add_row(f"0x{dev.address:02X}  ({dev.address})", dev.description)
        console.print(Panel(t, title=f"I2C Scan — {len(devices)} device(s) found",
                            border_style="green"))
    Prompt.ask("Press Enter to continue")


def _hw_spi_gpio():
    from modules.hardware import get_monitor
    ifc = get_monitor().get_interfaces()

    t = Table(show_header=False, box=None, padding=(0, 1))
    t.add_column("K", style="bold cyan", width=26)
    t.add_column("V", style="white")
    t.add_row("SPI devices",
              ", ".join(ifc.spi_devs) if ifc.spi_devs
              else "[red]None[/red] — enable in raspi-config")
    t.add_row("SPI0 driver",   ifc.spi0_driver)
    t.add_row("I2C devices",
              ", ".join(ifc.i2c_devs) if ifc.i2c_devs
              else "[red]None[/red] — enable in raspi-config")
    t.add_row("UART devices",  ", ".join(ifc.uart_devs) if ifc.uart_devs else "N/A")
    t.add_row("GPIO chips",    ifc.gpio_chips)
    t.add_row("GPIO lines",    ifc.gpio_lines)
    if ifc.w1_sensors:
        t.add_row("1-Wire (DS18B20)",
                  f"{len(ifc.w1_sensors)} sensor(s): " + ", ".join(ifc.w1_sensors))
    else:
        t.add_row("1-Wire", "None found")
    t.add_row("dtoverlay active", ifc.dtoverlay if ifc.dtoverlay else "N/A")
    console.print(Panel(t, title="SPI / I2C / GPIO / UART Interfaces", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _hw_all():
    for label, fn in [
        ("System Overview", _hw_overview),
        ("Temperature",     _hw_temperature),
        ("CPU",             _hw_cpu),
        ("Memory",          _hw_memory),
        ("Storage",         _hw_storage),
        ("Network",         _hw_network),
        ("USB Devices",     _hw_usb_devices),
        ("I2C Scan",        _hw_i2c_scan),
        ("SPI/GPIO/UART",   _hw_spi_gpio),
    ]:
        console.rule(f"[bold cyan]{label}")
        fn()


# ---------------------------------------------------------------------------
# Wi-Fi menu
# ---------------------------------------------------------------------------

def wifi_menu():
    """Wi-Fi module menu"""
    from modules.wifi import WiFiManager, signal_to_quality, encryption_risk

    mgr = WiFiManager('wlan0')

    while True:
        console.clear()
        t = Table(title="Wi-Fi Module", show_header=True, header_style="bold cyan")
        t.add_column("Option", style="cyan", width=8)
        t.add_column("Action", style="white")
        t.add_row("1", "Interface info")
        t.add_row("2", "Scan networks")
        t.add_row("3", "Channel analysis")
        t.add_row("4", "Network / IP info")
        t.add_row("5", "Connection status (wpa_supplicant)")
        t.add_row("6", "Saved networks")
        t.add_row("7", "Connect to network")
        t.add_row("8", "Signal monitor (live)")
        t.add_row("9", "Hardware capabilities")
        t.add_row("10", "Show saved passwords")
        t.add_row("0", "Back")
        console.print(t)
        console.print()

        choice = Prompt.ask("Select option",
                            choices=["0","1","2","3","4","5","6","7","8","9","10"])
        if choice == "0":
            break
        elif choice == "1":
            _wifi_iface_info(mgr)
        elif choice == "2":
            _wifi_scan(mgr, signal_to_quality, encryption_risk)
        elif choice == "3":
            _wifi_channel_analysis(mgr)
        elif choice == "4":
            _wifi_network_info(mgr)
        elif choice == "5":
            _wifi_conn_status(mgr)
        elif choice == "6":
            _wifi_saved_networks(mgr)
        elif choice == "7":
            _wifi_connect(mgr)
        elif choice == "8":
            _wifi_signal_monitor(mgr, signal_to_quality)
        elif choice == "9":
            _wifi_capabilities(mgr)
        elif choice == "10":
            _wifi_saved_passwords(mgr)


# -----------------------------------------------------------------------
# Wi-Fi helpers
# -----------------------------------------------------------------------

def _wifi_iface_info(mgr):
    info = mgr.get_interface_info()
    if not info:
        console.print("[red]Could not read interface info.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold green")
    t.add_column("Value")
    t.add_row("Interface",  info.iface)
    t.add_row("MAC",        info.mac)
    t.add_row("State",      f"[green]{info.state}[/green]" if info.state == 'UP'
                             else f"[red]{info.state}[/red]")
    t.add_row("Mode",       info.mode)
    t.add_row("SSID",       info.ssid or '—')
    t.add_row("BSSID",      info.bssid or '—')
    t.add_row("Channel",    str(info.channel) if info.channel else '—')
    t.add_row("Frequency",  f"{info.frequency_mhz} MHz" if info.frequency_mhz else '—')
    t.add_row("TX Power",   f"{info.txpower_dbm} dBm" if info.txpower_dbm else '—')
    t.add_row("Bit Rate",   f"{info.bitrate_mbps} Mb/s" if info.bitrate_mbps else '—')
    t.add_row("Signal",     f"{info.signal_dbm} dBm" if info.signal_dbm else '—')
    t.add_row("IP",         info.ip or '—')
    t.add_row("RF-kill soft", "[red]YES[/red]" if info.rfkill_soft else "no")
    t.add_row("RF-kill hard", "[red]YES[/red]" if info.rfkill_hard else "no")
    console.print(Panel(t, title="Interface Info", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _wifi_scan(mgr, signal_to_quality, encryption_risk):
    console.print("[cyan]Scanning… (requires sudo)[/cyan]")
    networks = mgr.scan()
    if networks is None:
        console.print("[red]Scan failed. Try running with sudo.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    if not networks:
        console.print("[yellow]No networks found.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return

    t = Table(title=f"Networks ({len(networks)} found)",
              show_header=True, header_style="bold cyan")
    t.add_column("#",    style="dim",   width=4)
    t.add_column("SSID", style="white", min_width=16)
    t.add_column("BSSID",style="dim",   width=19)
    t.add_column("Ch",   style="cyan",  width=4)
    t.add_column("Band", style="blue",  width=8)
    t.add_column("dBm",  style="white", width=6)
    t.add_column("Qual", style="white", width=6)
    t.add_column("Enc",  style="white", width=10)
    t.add_column("Risk", style="white", min_width=12)

    for i, n in enumerate(networks, 1):
        q = signal_to_quality(n.signal_dbm)
        colour = {'Excellent':'green','Good':'green','Fair':'yellow',
                  'Weak':'red','Very Weak':'red'}.get(q, 'white')
        enc_colour = {'Open':'red','WEP':'red','WPA':'yellow'}.get(n.encryption, 'green')
        risk = encryption_risk(n.encryption).split(' — ')[0]
        risk_colour = {'CRITICAL':'red','HIGH':'red','MEDIUM':'yellow',
                       'LOW':'green','VERY LOW':'green'}.get(risk, 'white')
        t.add_row(
            str(i),
            n.ssid,
            n.bssid,
            str(n.channel),
            n.band,
            f"[{colour}]{n.signal_dbm}[/{colour}]",
            f"[{colour}]{n.quality_pct}%[/{colour}]",
            f"[{enc_colour}]{n.encryption}[/{enc_colour}]",
            f"[{risk_colour}]{risk}[/{risk_colour}]",
        )
    console.print(t)

    # Detail view
    detail = Prompt.ask("Enter # for details (Enter to skip)", default="")
    if detail.isdigit() and 1 <= int(detail) <= len(networks):
        n = networks[int(detail) - 1]
        d = Table(show_header=False, box=None)
        d.add_column("Key", style="bold green")
        d.add_column("Value")
        d.add_row("SSID",       n.ssid)
        d.add_row("BSSID",      n.bssid)
        d.add_row("Channel",    str(n.channel))
        d.add_row("Frequency",  f"{n.frequency_ghz} GHz ({n.band})")
        d.add_row("Signal",     f"{n.signal_dbm} dBm — {signal_to_quality(n.signal_dbm)}")
        d.add_row("Quality",    f"{n.quality} ({n.quality_pct}%)")
        d.add_row("Encryption", n.encryption)
        d.add_row("Cipher",     n.cipher)
        d.add_row("Auth",       n.auth)
        d.add_row("Security",   encryption_risk(n.encryption))
        d.add_row("Last beacon", f"{n.last_beacon_ms} ms ago"
                  if n.last_beacon_ms is not None else '—')
        console.print(Panel(d, title=f"Detail — {n.ssid}", border_style="green"))

    Prompt.ask("Press Enter to continue")


def _wifi_channel_analysis(mgr):
    console.print("[cyan]Scanning for channel analysis…[/cyan]")
    ch_map = mgr.channel_analysis()
    if not ch_map:
        console.print("[red]Scan failed or no networks found.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(title="Channel Usage", show_header=True, header_style="bold cyan")
    t.add_column("Channel", style="cyan", width=9)
    t.add_column("APs",     style="white", width=5)
    t.add_column("SSIDs",   style="dim")
    for ch, ssids in ch_map.items():
        count = len(ssids)
        colour = 'red' if count >= 4 else 'yellow' if count >= 2 else 'green'
        t.add_row(str(ch), f"[{colour}]{count}[/{colour}]", ', '.join(ssids))
    console.print(t)
    console.print("[dim]Least congested channels are best for your AP.[/dim]")
    Prompt.ask("Press Enter to continue")


def _wifi_network_info(mgr):
    info = mgr.get_network_info()
    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold green")
    t.add_column("Value")
    t.add_row("Hostname",    info.get('hostname') or '—')
    t.add_row("IP (IPv4)",   info.get('ip_cidr') or '—')
    t.add_row("IP (IPv6)",   info.get('ip6_cidr') or '—')
    t.add_row("Gateway",     info.get('gateway') or '—')
    t.add_row("DNS servers", ', '.join(info.get('dns', [])) or '—')
    console.print(Panel(t, title="Network / IP Info", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _wifi_conn_status(mgr):
    status = mgr.get_connection_status()
    if 'error' in status:
        console.print(f"[red]{status['error']}[/red]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold green")
    t.add_column("Value")
    for k, v in status.items():
        t.add_row(k, v)
    console.print(Panel(t, title="wpa_supplicant Status", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _wifi_saved_networks(mgr):
    nets = mgr.list_saved_networks()
    if not nets:
        console.print("[yellow]No saved networks (or wpa_cli not available).[/yellow]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(title="Saved Networks", show_header=True, header_style="bold cyan")
    t.add_column("ID",    style="cyan",  width=4)
    t.add_column("SSID",  style="white")
    t.add_column("BSSID", style="dim")
    t.add_column("Flags", style="yellow")
    for n in nets:
        t.add_row(n['id'], n['ssid'], n['bssid'], n['flags'])
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _wifi_connect(mgr):
    ssid = Prompt.ask("SSID")
    enc  = Prompt.ask("Encryption", choices=["WPA2","WPA","WEP","Open"], default="WPA2")
    if enc in ("WPA2", "WPA"):
        password = Prompt.ask("Password", password=True)
    else:
        password = None
    console.print(f"[cyan]Connecting to '{ssid}'…[/cyan]")
    ok = mgr.connect(ssid, password)
    if ok:
        console.print("[green]Connection request sent. Check status (option 5) in a few seconds.[/green]")
    else:
        console.print("[red]Connection request failed.[/red]")
    Prompt.ask("Press Enter to continue")


def _wifi_signal_monitor(mgr, signal_to_quality):
    try:
        count = int(Prompt.ask("Number of readings", default="10"))
        interval = float(Prompt.ask("Interval (seconds)", default="1.0"))
    except ValueError:
        count, interval = 10, 1.0

    console.print(f"[cyan]Monitoring signal ({count}× every {interval}s)…[/cyan]")
    readings = mgr.monitor_signal(interval=interval, count=count)

    t = Table(title="Signal Monitor", show_header=True, header_style="bold cyan")
    t.add_column("#",       style="dim",   width=4)
    t.add_column("dBm",     style="white", width=8)
    t.add_column("Quality", style="white", width=8)
    t.add_column("Mbps",    style="white", width=8)
    t.add_column("Rating",  style="white")
    for i, r in enumerate(readings, 1):
        sig = r['signal_dbm']
        q   = signal_to_quality(sig) if sig else '—'
        colour = {'Excellent':'green','Good':'green','Fair':'yellow',
                  'Weak':'red','Very Weak':'red'}.get(q, 'white')
        t.add_row(
            str(i),
            f"[{colour}]{sig}[/{colour}]" if sig else '—',
            f"{r['quality_pct']}%" if r['quality_pct'] else '—',
            str(r['bitrate_mbps']) if r['bitrate_mbps'] else '—',
            f"[{colour}]{q}[/{colour}]",
        )
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _wifi_capabilities(mgr):
    caps = mgr.get_capabilities()
    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold green")
    t.add_column("Value")
    t.add_row("Driver",       caps.get('driver', '—'))
    t.add_row("Monitor mode", "[red]NOT supported[/red]" if not caps.get('monitor')
              else "[green]Supported[/green]")
    t.add_row("Modes",        ', '.join(caps.get('modes', [])))
    t.add_row("Ciphers",      ', '.join(caps.get('ciphers', [])))
    for band, channels in caps.get('bands', {}).items():
        t.add_row(f"Channels {band}", ', '.join(str(c) for c in channels[:20]) +
                  ('…' if len(channels) > 20 else ''))
    console.print(Panel(t, title="Hardware Capabilities", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


def _wifi_saved_passwords(mgr):
    console.print("[yellow]Reading wpa_supplicant.conf (requires sudo)…[/yellow]")
    networks = mgr.read_saved_passwords()
    if not networks:
        console.print("[red]No saved networks found, or permission denied.[/red]")
        console.print("[dim]Make sure you run with sudo or add yourself to the netdev group.[/dim]")
        Prompt.ask("Press Enter to continue")
        return

    t = Table(title=f"Saved Passwords ({len(networks)} network(s))",
              show_header=True, header_style="bold cyan")
    t.add_column("SSID",       style="white",  min_width=20)
    t.add_column("Password",   style="yellow", min_width=24)
    t.add_column("Auth",       style="cyan",   min_width=12)
    t.add_column("Priority",   style="dim",    min_width=8)

    for n in networks:
        psk = n['psk']
        if psk.startswith('<none'):
            psk_display = "[dim]— open —[/dim]"
        elif psk.startswith('<hashed'):
            psk_display = f"[dim]{psk}[/dim]"
        elif psk.startswith('<not'):
            psk_display = "[dim]not stored[/dim]"
        else:
            psk_display = f"[bold green]{psk}[/bold green]"

        t.add_row(n['ssid'], psk_display, n['key_mgmt'], n['priority'])

    console.print(t)
    console.print("[dim]Source: /etc/wpa_supplicant/wpa_supplicant.conf[/dim]")
    Prompt.ask("Press Enter to continue")


# ---------------------------------------------------------------------------
# Flash / Chip Memory menu
# ---------------------------------------------------------------------------

def flash_menu():
    """Flash/Chip memory read-write-clone menu."""
    from modules.flash import get_tool, check_tools, SPI_FLASH_COMMON, AVR_MCU_COMMON, STM32_COMMON

    while True:
        console.clear()
        t = Table(title="Flash / Chip Memory", show_header=True, header_style="bold yellow")
        t.add_column("Option", style="cyan", width=8)
        t.add_column("Target", style="yellow", width=14)
        t.add_column("Action", style="white")
        t.add_row("1",  "SPI Flash",  "Probe chip")
        t.add_row("2",  "SPI Flash",  "Read → file")
        t.add_row("3",  "SPI Flash",  "Write file → chip")
        t.add_row("4",  "SPI Flash",  "Erase chip")
        t.add_row("5",  "SPI Flash",  "Clone (read → swap → write)")
        t.add_row("6",  "STM32",      "Probe chip info")
        t.add_row("7",  "STM32",      "Read flash → file")
        t.add_row("8",  "STM32",      "Write file → flash")
        t.add_row("9",  "STM32",      "Mass erase")
        t.add_row("10", "AVR/Arduino","Probe chip signature")
        t.add_row("11", "AVR/Arduino","Read flash → HEX")
        t.add_row("12", "AVR/Arduino","Write HEX → flash")
        t.add_row("13", "AVR/Arduino","Read EEPROM")
        t.add_row("14", "AVR/Arduino","Write EEPROM")
        t.add_row("15", "AVR/Arduino","Read fuses")
        t.add_row("16", "I2C EEPROM", "Scan I2C bus")
        t.add_row("17", "I2C EEPROM", "Read → file")
        t.add_row("18", "I2C EEPROM", "Write file → EEPROM")
        t.add_row("19", "I2C EEPROM", "Erase (fill 0xFF)")
        t.add_row("20", "System",     "Check installed tools")
        t.add_row("21", "Remote",     "Start Remote Flash Server (LAN)")
        t.add_row("───", "───",        "── USB / Serial ──────────────────────")
        t.add_row("22", "AVR USB",    "Probe Arduino qua USB (auto-detect port)")
        t.add_row("23", "AVR USB",    "Read flash → HEX  (qua USB)")
        t.add_row("24", "AVR USB",    "Write HEX → flash (qua USB)")
        t.add_row("25", "AVR USB",    "Read EEPROM       (qua USB)")
        t.add_row("26", "AVR USB",    "Write EEPROM      (qua USB)")
        t.add_row("27", "AVR USB",    "Clone Arduino → Arduino (qua USB)")
        t.add_row("───", "───",        "── Lock Bits ─────────────────────────")
        t.add_row("28", "AVR ISP",    "Kiểm tra Lock Bits (qua ISP)")
        t.add_row("29", "AVR USB",    "Kiểm tra Lock Bits (qua USB)")
        t.add_row("0",  "—",          "Back")
        console.print(t)

        choices = [str(i) for i in range(30)]
        choice = Prompt.ask("Select option", choices=choices)

        if choice == "0":
            break
        elif choice == "1":
            _flash_spi_probe()
        elif choice == "2":
            _flash_spi_read()
        elif choice == "3":
            _flash_spi_write()
        elif choice == "4":
            _flash_spi_erase()
        elif choice == "5":
            _flash_spi_clone()
        elif choice == "6":
            _flash_stm32_probe()
        elif choice == "7":
            _flash_stm32_read()
        elif choice == "8":
            _flash_stm32_write()
        elif choice == "9":
            _flash_stm32_erase()
        elif choice == "10":
            _flash_avr_probe()
        elif choice == "11":
            _flash_avr_read_flash()
        elif choice == "12":
            _flash_avr_write_flash()
        elif choice == "13":
            _flash_avr_read_eeprom()
        elif choice == "14":
            _flash_avr_write_eeprom()
        elif choice == "15":
            _flash_avr_fuses()
        elif choice == "16":
            _flash_i2c_scan()
        elif choice == "17":
            _flash_i2c_read()
        elif choice == "18":
            _flash_i2c_write()
        elif choice == "19":
            _flash_i2c_erase()
        elif choice == "20":
            _flash_check_tools()
        elif choice == "21":
            _flash_remote_server()
        elif choice == "22":
            _flash_avr_usb_probe()
        elif choice == "23":
            _flash_avr_usb_read_flash()
        elif choice == "24":
            _flash_avr_usb_write_flash()
        elif choice == "25":
            _flash_avr_usb_read_eeprom()
        elif choice == "26":
            _flash_avr_usb_write_eeprom()
        elif choice == "27":
            _flash_avr_usb_clone()
        elif choice == "28":
            _flash_avr_check_lock_bits()
        elif choice == "29":
            _flash_avr_usb_check_lock_bits()


# -----------------------------------------------------------------------
# Flash helpers — SPI NOR
# -----------------------------------------------------------------------

def _flash_spi_probe():
    from modules.flash import SPIFlashTool
    console.print("[cyan]Probing SPI flash on /dev/spidev0.0…[/cyan]")
    info = SPIFlashTool().probe()
    if not info:
        console.print("[red]No SPI flash detected. Check wiring and SPI enabled.[/red]")
    else:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green"); t.add_column("Value")
        t.add_row("Chip",       info.name)
        t.add_row("Flash size", f"{info.flash_size // 1024} KB  ({info.flash_size} bytes)")
        t.add_row("Page size",  f"{info.page_size} bytes")
        console.print(Panel(t, title="SPI Flash Detected", border_style="green"))
    Prompt.ask("Press Enter to continue")


def _flash_spi_read():
    from modules.flash import SPIFlashTool
    out = Prompt.ask("Output file", default="data/flash/spi_dump.bin")
    chip = Prompt.ask("Chip name (blank = auto-detect)", default="")
    console.print("[cyan]Reading SPI flash…[/cyan]")
    op = SPIFlashTool().read(out, chip=chip or None)
    _show_op(op)


def _flash_spi_write():
    from modules.flash import SPIFlashTool
    src = Prompt.ask("Firmware file path")
    chip = Prompt.ask("Chip name (blank = auto-detect)", default="")
    console.print("[yellow]This will ERASE and OVERWRITE the chip![/yellow]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    console.print("[cyan]Writing SPI flash…[/cyan]")
    op = SPIFlashTool().write(src, chip=chip or None)
    _show_op(op)


def _flash_spi_erase():
    from modules.flash import SPIFlashTool
    chip = Prompt.ask("Chip name (blank = auto-detect)", default="")
    console.print("[red]This will ERASE the entire chip![/red]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    op = SPIFlashTool().erase(chip=chip or None)
    _show_op(op)


def _flash_spi_clone():
    from modules.flash import SPIFlashTool
    tmp = Prompt.ask("Save image to", default="data/flash/spi_clone.bin")
    console.print("[cyan]Step 1: Reading source chip…[/cyan]")
    tool = SPIFlashTool()
    op = tool.read(tmp)
    _show_op(op)
    if op.success:
        console.print("[yellow]Remove source chip and insert destination chip, then press Enter.[/yellow]")
        Prompt.ask("")
        console.print("[cyan]Step 2: Writing to destination chip…[/cyan]")
        op2 = tool.write(tmp)
        _show_op(op2)


# -----------------------------------------------------------------------
# Flash helpers — STM32
# -----------------------------------------------------------------------

def _stm32_tool():
    from modules.flash import STM32Tool
    port = Prompt.ask("UART port", default="/dev/serial0")
    baud = int(Prompt.ask("Baud rate", default="115200"))
    return STM32Tool(port=port, baud=baud)


def _flash_stm32_probe():
    tool = _stm32_tool()
    console.print("[cyan]Entering bootloader mode and probing STM32…[/cyan]")
    info = tool.probe()
    if not info:
        console.print("[red]STM32 not detected. Check BOOT0/NRST wiring and UART connection.[/red]")
    else:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green"); t.add_column("Value")
        t.add_row("Device",     info.name)
        t.add_row("Flash size", f"{info.flash_size // 1024} KB" if info.flash_size else "?")
        console.print(Panel(t, title="STM32 Detected", border_style="green"))
    Prompt.ask("Press Enter to continue")


def _flash_stm32_read():
    tool = _stm32_tool()
    out = Prompt.ask("Output file", default="data/flash/stm32_dump.bin")
    console.print("[cyan]Reading STM32 flash…[/cyan]")
    _show_op(tool.read(out))


def _flash_stm32_write():
    tool = _stm32_tool()
    src = Prompt.ask("Firmware file (.bin or .hex)")
    console.print("[yellow]This will overwrite STM32 flash![/yellow]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    console.print("[cyan]Writing STM32 flash…[/cyan]")
    _show_op(tool.write(src))


def _flash_stm32_erase():
    tool = _stm32_tool()
    console.print("[red]This will MASS ERASE the STM32![/red]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    _show_op(tool.erase())


# -----------------------------------------------------------------------
# Flash helpers — AVR / Arduino
# -----------------------------------------------------------------------

def _avr_tool():
    from modules.flash import AVRTool, AVR_MCU_COMMON
    console.print("[dim]Common MCUs: " + ", ".join(AVR_MCU_COMMON.keys()) + "[/dim]")
    mcu = Prompt.ask("MCU", default="atmega328p")
    return AVRTool(mcu=mcu)


def _flash_avr_probe():
    tool = _avr_tool()
    console.print("[cyan]Probing AVR via ISP…[/cyan]")
    info = tool.probe()
    if not info:
        console.print("[red]AVR not detected. Check ISP wiring and RESET pin (GPIO 25).[/red]")
    else:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green"); t.add_column("Value")
        t.add_row("MCU",        info.name)
        t.add_row("Flash",      f"{info.flash_size // 1024} KB")
        t.add_row("EEPROM",     f"{info.extra.get('eeprom_bytes', '?')} bytes")
        t.add_row("Signature",  info.extra.get("signature", "?"))
        t.add_row("Board",      info.extra.get("board", "?"))
        console.print(Panel(t, title="AVR Detected", border_style="green"))
    Prompt.ask("Press Enter to continue")


def _flash_avr_read_flash():
    tool = _avr_tool()
    out = Prompt.ask("Output HEX file", default="data/flash/avr_flash.hex")
    console.print("[cyan]Reading AVR flash via ISP…[/cyan]")
    _show_op(tool.read_flash(out))


def _flash_avr_write_flash():
    tool = _avr_tool()
    src = Prompt.ask("Firmware .hex file")
    console.print("[yellow]This will overwrite the AVR flash![/yellow]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    console.print("[cyan]Writing AVR flash…[/cyan]")
    _show_op(tool.write_flash(src))


def _flash_avr_read_eeprom():
    tool = _avr_tool()
    out = Prompt.ask("Output HEX file", default="data/flash/avr_eeprom.hex")
    console.print("[cyan]Reading AVR EEPROM…[/cyan]")
    _show_op(tool.read_eeprom(out))


def _flash_avr_write_eeprom():
    tool = _avr_tool()
    src = Prompt.ask("EEPROM .hex file")
    _show_op(tool.write_eeprom(src))


def _flash_avr_fuses():
    tool = _avr_tool()
    console.print("[cyan]Reading fuse bytes…[/cyan]")
    fuses = tool.read_fuses()
    if not fuses:
        console.print("[red]Could not read fuses.[/red]")
    else:
        t = Table(show_header=False, box=None)
        t.add_column("Fuse", style="bold green"); t.add_column("Value")
        for k, v in fuses.items():
            t.add_row(k, v)
        console.print(Panel(t, title="AVR Fuse Bytes", border_style="cyan"))
    Prompt.ask("Press Enter to continue")


# -----------------------------------------------------------------------
# Flash helpers — AVR via USB Serial
# -----------------------------------------------------------------------

def _avr_usb_tool():
    """Tạo AVRUSBTool — auto-detect port hoặc để user nhập."""
    import glob
    from modules.flash import AVRUSBTool, AVR_MCU_COMMON

    # Auto-detect port
    ports = sorted(glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    if ports:
        console.print(f"[dim]Ports tìm thấy: {', '.join(ports)}[/dim]")
        default_port = ports[0]
    else:
        console.print("[yellow]Không tìm thấy port USB. Kiểm tra cáp và driver.[/yellow]")
        default_port = "/dev/ttyACM0"

    port = Prompt.ask("Serial port", default=default_port)
    console.print(f"[dim]Common MCUs: {', '.join(AVR_MCU_COMMON.keys())}[/dim]")
    mcu  = Prompt.ask("MCU", default="atmega328p")
    baud = int(Prompt.ask("Baud rate", default="115200"))
    return AVRUSBTool(mcu=mcu, port=port, baud=baud)


def _flash_avr_usb_probe():
    from modules.flash import AVRUSBTool
    tool = _avr_usb_tool()
    console.print(f"[cyan]Probing {tool.mcu} trên {tool.port}…[/cyan]")
    info = tool.probe()
    if not info:
        console.print("[red]Không detect được AVR.[/red]")
        console.print("[dim]Tips: Reset Arduino, kiểm tra đúng port/baud, sketch không block serial.[/dim]")
    else:
        t = Table(show_header=False, box=None)
        t.add_column("Key", style="bold green"); t.add_column("Value")
        t.add_row("MCU",        info.name)
        t.add_row("Flash",      f"{info.flash_size // 1024} KB")
        t.add_row("EEPROM",     f"{info.extra.get('eeprom_bytes', '?')} bytes")
        t.add_row("Signature",  info.extra.get("signature", "?"))
        t.add_row("Board",      info.extra.get("board", "?"))
        t.add_row("Port",       info.extra.get("port", "?"))
        t.add_row("Programmer", info.extra.get("programmer", "?"))
        console.print(Panel(t, title="Arduino Detected (USB)", border_style="green"))
    Prompt.ask("Press Enter to continue")


def _flash_avr_usb_read_flash():
    tool = _avr_usb_tool()
    out  = Prompt.ask("Output HEX file", default="data/flash/avr_usb_flash.hex")
    console.print(f"[cyan]Đọc flash từ {tool.port}…[/cyan]")
    _show_op(tool.read_flash(out))


def _flash_avr_usb_write_flash():
    tool = _avr_usb_tool()
    src  = Prompt.ask("Firmware .hex file")
    console.print("[yellow]Sẽ ghi đè flash Arduino![/yellow]")
    if Prompt.ask("Tiếp tục?", choices=["y", "n"]) != "y":
        return
    console.print(f"[cyan]Ghi flash lên {tool.port}…[/cyan]")
    _show_op(tool.write_flash(src))


def _flash_avr_usb_read_eeprom():
    tool = _avr_usb_tool()
    out  = Prompt.ask("Output HEX file", default="data/flash/avr_usb_eeprom.hex")
    console.print(f"[cyan]Đọc EEPROM từ {tool.port}…[/cyan]")
    _show_op(tool.read_eeprom(out))


def _flash_avr_usb_write_eeprom():
    tool = _avr_usb_tool()
    src  = Prompt.ask("EEPROM .hex file")
    _show_op(tool.write_eeprom(src))


def _flash_avr_usb_clone():
    console.print(Panel(
        "[bold]Clone Arduino → Arduino qua USB[/bold]\n"
        "  Bước 1: Kết nối board NGUỒN → đọc flash (+ EEPROM tùy chọn)\n"
        "  Bước 2: Rút board nguồn, cắm board ĐÍCH vào cùng cổng USB\n"
        "  Bước 3: Ghi flash (+ EEPROM) lên board đích\n\n"
        "[yellow]⚠  Bootloader trên board đích phải còn nguyên.[/yellow]\n"
        "[dim]Fuse bytes KHÔNG clone được qua USB — dùng ISP nếu cần.[/dim]",
        title="AVR USB Clone", border_style="cyan",
    ))

    clone_eeprom = Prompt.ask("Clone cả EEPROM?", choices=["y", "n"], default="n") == "y"
    tmp = Prompt.ask("File tạm lưu flash", default="data/flash/avr_clone.hex")

    # Bước 1 — đọc board nguồn
    console.print("\n[bold cyan]Bước 1 — Kết nối board NGUỒN rồi nhấn Enter…[/bold cyan]")
    Prompt.ask("")
    tool = _avr_usb_tool()
    console.print(f"[cyan]Đọc flash từ {tool.port}…[/cyan]")
    op = tool.clone_flash(tmp, clone_eeprom=clone_eeprom)
    if not op.success:
        console.print(f"[red]✗ {op.message}[/red]")
        Prompt.ask("Press Enter to continue")
        return
    console.print(f"[green]✓ Đọc xong — {op.size:,} bytes → {tmp}[/green]")
    if clone_eeprom:
        console.print(f"[green]✓ EEPROM → {tmp.replace('.hex','_eeprom.hex')}[/green]")

    # Bước 2 — đổi board
    console.print("\n[bold yellow]Bước 2 — Rút board NGUỒN, cắm board ĐÍCH vào cùng cổng USB.[/bold yellow]")
    Prompt.ask("Nhấn Enter khi đã cắm board đích…")

    # Bước 3 — ghi board đích
    console.print(f"[cyan]Bước 3 — Ghi flash lên {tool.port}…[/cyan]")
    op_w = tool.clone_write(tmp, clone_eeprom=clone_eeprom)
    if not op_w.success:
        console.print(f"[red]✗ {op_w.message}[/red]")
        Prompt.ask("Press Enter to continue")
        return

    console.print(Panel(
        f"[bold green]Clone hoàn tất![/bold green]\n"
        f"Flash{'  +  EEPROM' if clone_eeprom else ''} đã được sao chép.\n"
        f"Backup: [white]{tmp}[/white]",
        border_style="green",
    ))
    Prompt.ask("Press Enter to continue")


# -----------------------------------------------------------------------
# Flash helpers — Lock Bits
# -----------------------------------------------------------------------

def _show_lock_bits_result(result: dict):
    """Hiển thị kết quả đọc lock bits với màu sắc theo mức độ."""
    if not result.get("success"):
        console.print(f"[red]✗ Lỗi: {result.get('error', 'Không xác định')}[/red]")
        return

    readable = result["readable"]
    color    = "green" if readable else "red"
    icon     = "✓" if readable else "✗"

    t = Table(show_header=False, box=None)
    t.add_column("Key", style="bold cyan", width=18)
    t.add_column("Value")
    t.add_row("Lock byte",  f"[white]{result['raw']}[/white] (0b{result['value']:08b})")
    t.add_row("Chế độ",    f"[{color}]{result['mode']}[/{color}]")
    t.add_row("Flash readable", f"[{color}]{icon} {'Có' if readable else 'Không'}[/{color}]")
    t.add_row("Mô tả",     result["description"].split("\n")[0])
    if not readable and "\n" in result["description"]:
        t.add_row("", "[dim]" + result["description"].split("\n", 1)[1] + "[/dim]")

    border = "green" if readable else "red"
    console.print(Panel(t, title="Lock Bits Status", border_style=border))


def _flash_avr_check_lock_bits():
    """Đọc lock bits qua ISP (AVRTool) — luôn hoạt động dù flash đã bị lock."""
    from modules.flash import AVRTool
    tool = _avr_tool()
    console.print("[cyan]Đọc lock byte qua ISP…[/cyan]")
    result = tool.read_lock_bits()
    _show_lock_bits_result(result)
    if result.get("success") and not result["readable"]:
        console.print(
            "[yellow]Flash bị lock Mode 3. Để mở khóa:[/yellow]\n"
            "  [white]• Chip Erase (mất toàn bộ data):[/white]\n"
            "    sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 -e\n"
            "  [white]• HVPP (12V vào RESET, giữ data — cần mạch riêng)[/white]"
        )
    Prompt.ask("Press Enter to continue")


def _flash_avr_usb_check_lock_bits():
    """Đọc lock bits qua USB bootloader (Optiboot). Fallback hướng dẫn dùng ISP nếu thất bại."""
    tool = _avr_usb_tool()
    console.print("[cyan]Đọc lock byte qua USB bootloader…[/cyan]")
    result = tool.read_lock_bits()
    _show_lock_bits_result(result)
    if not result.get("success"):
        console.print(
            "[yellow]Bootloader không hỗ trợ đọc lock byte.\n"
            "Dùng tùy chọn 28 (ISP) để đọc lock bits chính xác.[/yellow]"
        )
    elif result.get("success") and not result["readable"]:
        console.print(
            "[yellow]Flash bị lock Mode 3. Để mở khóa cần dùng ISP:[/yellow]\n"
            "  sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 -e"
        )
    Prompt.ask("Press Enter to continue")


# -----------------------------------------------------------------------
# Flash helpers — I2C EEPROM
# -----------------------------------------------------------------------

def _i2c_tool():
    from modules.flash import I2CEEPROMTool
    chips = list(I2CEEPROMTool.CHIP_SIZE.keys())
    console.print("[dim]Common chips: " + ", ".join(chips[:8]) + "…[/dim]")
    chip = Prompt.ask("Chip model", default="AT24C256")
    addr = int(Prompt.ask("I2C address (hex)", default="0x50"), 16)
    return I2CEEPROMTool(bus=1, address=addr, chip=chip)


def _flash_i2c_scan():
    from modules.flash import I2CEEPROMTool
    console.print("[cyan]Scanning I2C bus 1…[/cyan]")
    found = I2CEEPROMTool(bus=1, address=0x50).scan_bus()
    if not found:
        console.print("[red]No I2C devices found.[/red]")
    else:
        t = Table(title="I2C Devices Found", show_header=True, header_style="bold cyan")
        t.add_column("Address (hex)")
        t.add_column("Address (dec)")
        for addr in found:
            t.add_row(f"0x{addr:02X}", str(addr))
        console.print(t)
    Prompt.ask("Press Enter to continue")


def _flash_i2c_read():
    tool = _i2c_tool()
    out = Prompt.ask("Output file", default="data/flash/eeprom_dump.bin")
    console.print("[cyan]Reading I2C EEPROM…[/cyan]")
    _show_op(tool.read(out))


def _flash_i2c_write():
    tool = _i2c_tool()
    src = Prompt.ask("Input binary file")
    _show_op(tool.write(src))


def _flash_i2c_erase():
    tool = _i2c_tool()
    console.print("[yellow]This will fill the entire EEPROM with 0xFF.[/yellow]")
    if Prompt.ask("Continue?", choices=["y", "n"]) != "y":
        return
    console.print("[cyan]Erasing EEPROM…[/cyan]")
    _show_op(tool.erase())


def _flash_remote_server():
    """Start RemoteFlashServer on LAN so laptops can push firmware over HTTP."""
    import threading
    import socket
    from modules.flash import RemoteFlashServer

    console.print(Panel(
        "[bold yellow]Remote Flash Server[/bold yellow]\n"
        "Cho phép upload và nạp firmware từ laptop/PC qua mạng LAN.\n"
        "Server chạy HTTP — [red]chỉ dùng trên mạng LAN tin cậy.[/red]",
        border_style="yellow",
    ))

    port_str = Prompt.ask("Port", default="7777")
    token_in = Prompt.ask("Auth token (Enter để tự generate)", default="")

    try:
        port = int(port_str)
    except ValueError:
        console.print("[red]Port không hợp lệ.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    server = RemoteFlashServer(port=port, token=token_in or None)

    # Detect LAN IP for display
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "raspberrypi.local"

    console.print(f"\n[green]Token :[/green] [bold cyan]{server.token}[/bold cyan]")
    console.print(f"[green]URL   :[/green] http://{lan_ip}:{port}/flash")
    console.print("\n[dim]Từ laptop:[/dim]")
    console.print(
        f"[white]  python scripts/remote_flash.py "
        f"--host {lan_ip} --token {server.token} "
        f"--target avr firmware.hex[/white]"
    )
    console.print("\n[yellow]Nhấn Ctrl+C để dừng server.[/yellow]\n")

    t = threading.Thread(target=lambda: server.start(blocking=True), daemon=True)
    t.start()
    try:
        while t.is_alive():
            import time
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.stop()
    console.print("\n[yellow]Server stopped.[/yellow]")
    Prompt.ask("Press Enter to continue")


def _flash_check_tools():
    from modules.flash import check_tools
    status = check_tools()
    t = Table(title="Required Tools", show_header=True, header_style="bold cyan")
    t.add_column("Tool",    style="white")
    t.add_column("Status",  style="white")
    t.add_column("Install", style="dim")
    install_cmds = {
        "flashrom":   "sudo apt install flashrom",
        "stm32flash": "sudo apt install stm32flash",
        "avrdude":    "sudo apt install avrdude",
        "smbus2":     "pip install smbus2",
    }
    for tool, ok in status.items():
        label = "[green]✓ installed[/green]" if ok else "[red]✗ missing[/red]"
        t.add_row(tool, label, install_cmds.get(tool, ""))
    console.print(t)
    Prompt.ask("Press Enter to continue")


# -----------------------------------------------------------------------
# Shared helper
# -----------------------------------------------------------------------

def _show_op(op):
    """Display a FlashOperation result."""
    if op.success:
        msg = f"[green]✓ {op.message}[/green]"
        if op.file:
            msg += f"\n  File: [cyan]{op.file}[/cyan]"
        if op.size is not None:
            msg += f"\n  Size: [white]{op.size:,} bytes ({op.size // 1024} KB)[/white]"
    else:
        msg = f"[red]✗ {op.message}[/red]"
    console.print(msg)
    Prompt.ask("Press Enter to continue")


# =============================================================================
# Bluetooth Menu
# =============================================================================

def bluetooth_menu():
    """Bluetooth scanning and analysis menu."""
    from modules.bluetooth import BluetoothManager

    mgr = BluetoothManager()

    # Ensure controller is up on first entry
    if not mgr.controller_up():
        console.print("[red]Failed to power up Bluetooth controller.[/red]")
        console.print("[dim]Try: sudo rfkill unblock bluetooth[/dim]")
        Prompt.ask("Press Enter to continue")
        return

    while True:
        console.clear()
        t = Table(title="Bluetooth", show_header=True, header_style="bold blue")
        t.add_column("Option", style="cyan", width=8)
        t.add_column("Action", style="white")
        t.add_row("1",  "Controller info")
        t.add_row("2",  "Scan all (BR/EDR + BLE)  — 15 s")
        t.add_row("3",  "Scan BLE only            — 10 s")
        t.add_row("4",  "Scan Classic BT only     — 15 s")
        t.add_row("5",  "Device details (by address)")
        t.add_row("6",  "Browse SDP services (Classic BT)")
        t.add_row("7",  "GATT services — BLE (requires bleak)")
        t.add_row("8",  "List paired devices")
        t.add_row("9",  "Set discoverable ON  (180 s)")
        t.add_row("10", "Set discoverable OFF")
        t.add_row("11", "Set local device name")
        t.add_row("12", "Check capabilities & tools")
        t.add_row("0",  "Back")
        console.print(t)

        choice = Prompt.ask("Select option",
                            choices=[str(i) for i in range(13)])

        if choice == "0":
            break
        elif choice == "1":
            _bt_controller_info(mgr)
        elif choice == "2":
            _bt_scan(mgr, mode="all", duration=15)
        elif choice == "3":
            _bt_scan(mgr, mode="ble", duration=10)
        elif choice == "4":
            _bt_scan(mgr, mode="classic", duration=15)
        elif choice == "5":
            _bt_device_info(mgr)
        elif choice == "6":
            _bt_sdp_services(mgr)
        elif choice == "7":
            _bt_gatt_services(mgr)
        elif choice == "8":
            _bt_paired_devices(mgr)
        elif choice == "9":
            _bt_set_discoverable(mgr, True)
        elif choice == "10":
            _bt_set_discoverable(mgr, False)
        elif choice == "11":
            _bt_set_name(mgr)
        elif choice == "12":
            _bt_capabilities(mgr)


# ── Bluetooth helpers ────────────────────────────────────────────────────────

def _bt_controller_info(mgr):
    from modules.bluetooth import ControllerInfo
    console.print("[cyan]Reading controller info…[/cyan]")
    info = mgr.get_controller_info()
    if not info:
        console.print("[red]Failed to read controller info.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    t = Table(title=f"Controller — {info.hci}",
              show_header=False, box=None)
    t.add_column("Field", style="bold green", width=22)
    t.add_column("Value", style="white")
    t.add_row("BD Address",       info.addr)
    t.add_row("Name",             info.name)
    t.add_row("BT Version",       info.bt_version)
    t.add_row("Manufacturer ID",  str(info.manufacturer_id))
    t.add_row("Powered",          "[green]YES[/green]" if info.powered else "[red]NO[/red]")
    t.add_row("Discoverable",     "[green]YES[/green]" if info.discoverable else "NO")
    t.add_row("Pairable",         "YES" if info.pairable else "NO")
    t.add_row("BR/EDR (Classic)", "[green]YES[/green]" if info.br_edr else "NO")
    t.add_row("BLE (LE)",         "[green]YES[/green]" if info.le else "NO")
    t.add_row("Secure Conn",      "YES" if info.secure_conn else "NO")
    t.add_row("Roles",            ", ".join(info.roles) if info.roles else "-")
    t.add_row("ADV Instances",    str(info.advertising_instances))
    console.print(Panel(t, border_style="blue"))
    Prompt.ask("Press Enter to continue")


def _bt_scan(mgr, mode: str, duration: float):
    mode_label = {"all": "BR/EDR + BLE", "ble": "BLE only", "classic": "Classic BT"}
    console.print(
        f"[cyan]Scanning [{mode_label.get(mode, mode)}] for {duration:.0f} s…[/cyan] "
        f"[dim](Ctrl+C to stop early)[/dim]"
    )
    try:
        devices = mgr.scan(duration=duration, mode=mode)
    except KeyboardInterrupt:
        console.print("[yellow]Scan interrupted.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return

    if not devices:
        console.print("[yellow]No devices found.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return

    t = Table(
        title=f"Found {len(devices)} device(s)",
        show_header=True, header_style="bold blue",
    )
    t.add_column("#",      style="dim",    width=4)
    t.add_column("Address",               width=19)
    t.add_column("Name",                  width=24)
    t.add_column("Type",    style="cyan",  width=9)
    t.add_column("RSSI",    style="yellow",width=8)
    t.add_column("Signal",               width=12)
    t.add_column("Vendor",  style="dim",  width=18)

    for i, d in enumerate(devices, 1):
        rssi_str = f"{d.rssi} dBm" if d.rssi is not None else "-"
        name_disp = d.name[:22] + "…" if len(d.name) > 23 else d.name
        vendor = d.manufacturer[:16] + "…" if len(d.manufacturer) > 17 else d.manufacturer
        t.add_row(
            str(i), d.addr, name_disp or "[dim](unknown)[/dim]",
            d.device_type, rssi_str, d.signal_quality, vendor,
        )
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _bt_device_info(mgr):
    addr = Prompt.ask("BD Address (XX:XX:XX:XX:XX:XX)").strip().upper()
    if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", addr):
        console.print("[red]Invalid address format.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    console.print(f"[cyan]Querying {addr}…[/cyan]")
    info = mgr.get_device_info(addr)
    if not info.get("success"):
        console.print("[red]Failed. Device may not be connectable / in range.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(show_header=False, box=None)
    t.add_column("Key",   style="bold green", width=24)
    t.add_column("Value", style="white")
    skip = {"addr", "success", "raw_output"}
    for k, v in info.items():
        if k not in skip and v:
            t.add_row(k.replace("_", " ").title(), str(v))
    console.print(Panel(t, title=f"Device Info — {addr}", border_style="blue"))
    Prompt.ask("Press Enter to continue")


def _bt_sdp_services(mgr):
    import re
    addr = Prompt.ask("BD Address (Classic BT device)").strip().upper()
    if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", addr):
        console.print("[red]Invalid address.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    console.print(f"[cyan]Browsing SDP services on {addr}…[/cyan]")
    try:
        services = mgr.get_services(addr)
    except Exception as e:
        console.print(f"[red]SDP browse failed: {e}[/red]")
        Prompt.ask("Press Enter to continue")
        return
    if not services:
        console.print("[yellow]No SDP services found (device may be BLE-only).[/yellow]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(title=f"SDP Services — {addr}",
              show_header=True, header_style="bold blue")
    t.add_column("Service",   width=28)
    t.add_column("UUID",      style="dim", width=12)
    t.add_column("Protocol",  style="cyan", width=10)
    t.add_column("CH/PSM",    style="yellow", width=8)
    t.add_column("Description", style="dim")
    for s in services:
        ch_str = str(s.channel) if s.channel is not None else "-"
        desc = s.uuid_name or s.description or "-"
        t.add_row(s.name[:26], s.uuid[:10], s.protocol[:8], ch_str, desc[:30])
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _bt_gatt_services(mgr):
    import re
    addr = Prompt.ask("BD Address (BLE device)").strip().upper()
    if not re.match(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", addr):
        console.print("[red]Invalid address.[/red]")
        Prompt.ask("Press Enter to continue")
        return
    console.print(f"[cyan]Reading GATT services on {addr}…[/cyan]")
    try:
        services = mgr.get_ble_services(addr, timeout=15)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        Prompt.ask("Press Enter to continue")
        return
    except Exception as e:
        console.print(f"[red]GATT read failed: {e}[/red]")
        Prompt.ask("Press Enter to continue")
        return
    if not services:
        console.print("[yellow]No GATT services found.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(title=f"GATT Services — {addr}",
              show_header=True, header_style="bold blue")
    t.add_column("Service",  width=32)
    t.add_column("UUID",     style="dim", width=12)
    t.add_column("Handle",   style="yellow", width=8)
    for s in services:
        t.add_row(s.name[:30], s.uuid[:10], str(s.channel or "-"))
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _bt_paired_devices(mgr):
    devices = mgr.get_paired_devices()
    if not devices:
        console.print("[yellow]No paired devices.[/yellow]")
        Prompt.ask("Press Enter to continue")
        return
    t = Table(title="Paired Devices",
              show_header=True, header_style="bold blue")
    t.add_column("Address",  width=19)
    t.add_column("Name",     width=28)
    t.add_column("Vendor",   style="dim")
    for d in devices:
        t.add_row(d["addr"], d["name"], d["manufacturer"])
    console.print(t)
    Prompt.ask("Press Enter to continue")


def _bt_set_discoverable(mgr, on: bool):
    ok = mgr.set_discoverable(on)
    state = "[green]ON (180 s)[/green]" if on else "[yellow]OFF[/yellow]"
    msg = f"Discoverable set to {state}" if ok else "[red]Failed to set discoverable mode.[/red]"
    console.print(msg)
    Prompt.ask("Press Enter to continue")


def _bt_set_name(mgr):
    name = Prompt.ask("New device name")
    if not name.strip():
        return
    ok = mgr.set_name(name.strip())
    console.print("[green]Name set.[/green]" if ok else "[red]Failed.[/red]")
    Prompt.ask("Press Enter to continue")


def _bt_capabilities(mgr):
    caps = mgr.check_capabilities()

    t_tools = Table(title="System Tools",
                    show_header=True, header_style="bold cyan")
    t_tools.add_column("Tool");  t_tools.add_column("Status")
    for tool, ok in caps["tools"].items():
        t_tools.add_row(tool, "[green]✓[/green]" if ok else "[red]✗ missing[/red]")
    for tool, ok in caps["optional"].items():
        label = "[green]✓ installed[/green]" if ok else "[yellow]✗ optional (pip install bleak)[/yellow]"
        t_tools.add_row(f"{tool} (optional)", label)
    console.print(t_tools)

    ctl = caps["controller"]
    t_ctl = Table(title="Controller",
                  show_header=False, box=None)
    t_ctl.add_column("Key",   style="bold green", width=18)
    t_ctl.add_column("Value", style="white")
    t_ctl.add_row("HCI",         ctl["hci"])
    t_ctl.add_row("Address",     ctl["addr"])
    t_ctl.add_row("Name",        ctl["name"])
    t_ctl.add_row("BT Version",  ctl["bt_version"])
    t_ctl.add_row("BR/EDR",      "YES" if ctl["br_edr"] else "NO")
    t_ctl.add_row("BLE",         "YES" if ctl["le"] else "NO")
    t_ctl.add_row("Secure Conn", "YES" if ctl["secure_conn"] else "NO")
    t_ctl.add_row("ADV Sets",    str(ctl["adv_instances"]))
    console.print(Panel(t_ctl, border_style="blue"))
    Prompt.ask("Press Enter to continue")


# ═══════════════════════════════════════════════════════════════════════════════
# Servo / PCA9685 Menu
# ═══════════════════════════════════════════════════════════════════════════════

def servo_menu():
    """PCA9685 16-channel PWM servo driver — test & control."""
    from modules.servo import PCA9685, detect_pca9685

    # ── persistent state for this session ──────────────────────────────────
    state = {
        "bus":         1,
        "addr":        0x40,
        "freq":        50.0,
        "min_pulse":   500,
        "max_pulse":   2500,
    }

    while True:
        console.clear()
        t = Table(title="Servo / PCA9685", show_header=True, header_style="bold magenta")
        t.add_column("Option", style="cyan", width=8)
        t.add_column("Action", style="white")
        t.add_row("1",  "Detect PCA9685 on I2C bus")
        t.add_row("2",  "Set servo angle  (single channel)")
        t.add_row("3",  "Sweep test       (0 → 180 → 0°)")
        t.add_row("4",  "Center all channels  (90°)")
        t.add_row("5",  "Release all channels (PWM off)")
        t.add_row("6",  "Multi-channel set    (several channels at once)")
        t.add_row("7",  "Configure  (bus, address, frequency, pulse range)")
        t.add_row("0",  "Back")
        console.print(t)
        console.print(
            f"[dim]  Bus: i2c-{state['bus']}  Addr: 0x{state['addr']:02X}  "
            f"Freq: {state['freq']:.0f} Hz  "
            f"Pulse: {state['min_pulse']}–{state['max_pulse']} µs[/dim]"
        )

        choice = Prompt.ask("Select option", choices=[str(i) for i in range(8)])
        if choice == "0":
            break
        elif choice == "1":
            _servo_detect(state)
        elif choice == "2":
            _servo_set_angle(state)
        elif choice == "3":
            _servo_sweep(state)
        elif choice == "4":
            _servo_center_all(state)
        elif choice == "5":
            _servo_all_off(state)
        elif choice == "6":
            _servo_multi_set(state)
        elif choice == "7":
            _servo_configure(state)


# ── Servo helpers ─────────────────────────────────────────────────────────────

def _servo_detect(state: dict) -> None:
    from modules.servo import detect_pca9685
    console.print()
    with console.status(f"[cyan]Scanning I2C bus {state['bus']} for PCA9685…[/cyan]"):
        chips = detect_pca9685(state["bus"])

    if not chips:
        console.print(Panel(
            "[yellow]No PCA9685 found.[/yellow]\n"
            "[dim]Check wiring: SDA=GPIO2(pin3)  SCL=GPIO3(pin5)  VCC=3.3 V or 5 V\n"
            "Enable I2C:  sudo raspi-config  → Interface Options → I2C[/dim]",
            title="Detect PCA9685", border_style="yellow",
        ))
    else:
        t = Table(show_header=True, header_style="bold cyan")
        t.add_column("Address",     style="yellow", width=12)
        t.add_column("Mode1 reg",   style="dim",    width=12)
        t.add_column("Status",      style="white")
        for c in chips:
            t.add_row(f"0x{c.address:02X}", f"0x{c.mode1_reg:02X}", c.description)
        console.print(Panel(t, title=f"PCA9685 found — {len(chips)} chip(s)",
                            border_style="green"))
        if len(chips) == 1:
            state["addr"] = chips[0].address
            console.print(f"[dim]Address 0x{state['addr']:02X} saved as active.[/dim]")

    Prompt.ask("Press Enter to continue")


def _servo_set_angle(state: dict) -> None:
    from modules.servo import PCA9685
    console.print()
    ch_str  = Prompt.ask("Channel (0–15)", default="0")
    ang_str = Prompt.ask("Angle   (0–180)", default="90")
    try:
        ch  = int(ch_str)
        ang = float(ang_str)
        if not 0 <= ch <= 15:
            raise ValueError("Channel out of range")
    except ValueError as e:
        console.print(f"[red]Invalid input: {e}[/red]")
        Prompt.ask("Press Enter to continue")
        return

    try:
        with PCA9685(state["bus"], state["addr"]) as pca:
            pca.set_pwm_freq(state["freq"])
            pca.set_servo_angle(ch, ang,
                                min_pulse_us=state["min_pulse"],
                                max_pulse_us=state["max_pulse"])
        console.print(f"[green]Channel {ch} → {ang:.1f}°[/green]")
    except OSError as e:
        _servo_error(e)

    Prompt.ask("Press Enter to continue")


def _servo_sweep(state: dict) -> None:
    from modules.servo import PCA9685
    console.print()
    ch_str = Prompt.ask("Channel (0–15)", default="0")
    try:
        ch = int(ch_str)
        if not 0 <= ch <= 15:
            raise ValueError
    except ValueError:
        console.print("[red]Invalid channel.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    console.print(f"[cyan]Sweeping channel {ch}: 0° → 180° → 0°  (Ctrl-C to stop)[/cyan]")
    try:
        with PCA9685(state["bus"], state["addr"]) as pca:
            pca.set_pwm_freq(state["freq"])

            def _tick(angle: float) -> None:
                bar = int(angle / 5)
                console.print(
                    f"\r  {angle:5.1f}°  [{'█' * bar}{' ' * (36 - bar)}]",
                    end="", highlight=False,
                )

            pca.sweep(ch, 0, 180,
                      steps=60, delay_s=0.025,
                      callback=_tick,
                      min_pulse_us=state["min_pulse"],
                      max_pulse_us=state["max_pulse"])
        console.print("\n[green]Sweep complete.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Sweep interrupted.[/yellow]")
    except OSError as e:
        _servo_error(e)

    Prompt.ask("Press Enter to continue")


def _servo_center_all(state: dict) -> None:
    from modules.servo import PCA9685
    console.print()
    try:
        with PCA9685(state["bus"], state["addr"]) as pca:
            pca.set_pwm_freq(state["freq"])
            for ch in range(16):
                pca.set_servo_angle(ch, 90,
                                    min_pulse_us=state["min_pulse"],
                                    max_pulse_us=state["max_pulse"])
        console.print("[green]All 16 channels centered at 90°.[/green]")
    except OSError as e:
        _servo_error(e)
    Prompt.ask("Press Enter to continue")


def _servo_all_off(state: dict) -> None:
    from modules.servo import PCA9685
    console.print()
    try:
        with PCA9685(state["bus"], state["addr"]) as pca:
            pca.all_off()
        console.print("[green]All channels OFF — servos released.[/green]")
    except OSError as e:
        _servo_error(e)
    Prompt.ask("Press Enter to continue")


def _servo_multi_set(state: dict) -> None:
    from modules.servo import PCA9685
    console.print()
    console.print("[dim]Enter channel:angle pairs, e.g.  0:90  1:45  3:135[/dim]")
    raw = Prompt.ask("Channels")
    pairs: list[tuple[int, float]] = []
    for token in raw.split():
        if ":" not in token:
            continue
        left, right = token.split(":", 1)
        try:
            ch  = int(left)
            ang = float(right)
            if 0 <= ch <= 15 and 0 <= ang <= 180:
                pairs.append((ch, ang))
        except ValueError:
            pass

    if not pairs:
        console.print("[red]No valid pairs parsed.[/red]")
        Prompt.ask("Press Enter to continue")
        return

    try:
        with PCA9685(state["bus"], state["addr"]) as pca:
            pca.set_pwm_freq(state["freq"])
            for ch, ang in pairs:
                pca.set_servo_angle(ch, ang,
                                    min_pulse_us=state["min_pulse"],
                                    max_pulse_us=state["max_pulse"])
                console.print(f"  Channel {ch:2d} → {ang:.1f}°")
        console.print(f"[green]{len(pairs)} channel(s) updated.[/green]")
    except OSError as e:
        _servo_error(e)

    Prompt.ask("Press Enter to continue")


def _servo_configure(state: dict) -> None:
    console.print()
    console.print("[bold cyan]Configure PCA9685 connection[/bold cyan]")

    bus_s = Prompt.ask("I2C bus number", default=str(state["bus"]))
    addr_s = Prompt.ask("I2C address (hex, e.g. 40)", default=f"{state['addr']:02X}")
    freq_s = Prompt.ask("PWM frequency Hz (50 for standard servos)", default=str(int(state["freq"])))
    min_s  = Prompt.ask("Min pulse µs (0°)",   default=str(state["min_pulse"]))
    max_s  = Prompt.ask("Max pulse µs (180°)", default=str(state["max_pulse"]))

    try:
        state["bus"]       = int(bus_s)
        state["addr"]      = int(addr_s, 16)
        state["freq"]      = float(freq_s)
        state["min_pulse"] = int(min_s)
        state["max_pulse"] = int(max_s)
        console.print("[green]Settings updated.[/green]")
    except ValueError as e:
        console.print(f"[red]Invalid value: {e}[/red]")

    Prompt.ask("Press Enter to continue")


def _servo_error(exc: OSError) -> None:
    msg = str(exc)
    if "No such file" in msg:
        hint = "I2C device not found — is /dev/i2c-1 present? Run: sudo raspi-config → I2C"
    elif "Permission denied" in msg:
        hint = "Permission denied — run as root or add user to 'i2c' group: sudo usermod -aG i2c $USER"
    elif "No such device" in msg or "errno 6" in msg.lower() or "[errno 6]" in msg.lower():
        hint = "Device not responding — check wiring (SDA/SCL/VCC/GND) and I2C address"
    elif "Remote I/O error" in msg:
        hint = "NACK from device — wrong address? Run option 1 (Detect) first"
    else:
        hint = "Check wiring and I2C configuration"
    console.print(Panel(
        f"[red]{exc}[/red]\n[dim]{hint}[/dim]",
        title="I2C Error", border_style="red",
    ))

