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
        table.add_row("0", "Exit", "Exit RaspFlip")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
        
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
            console.print("[yellow]Wi-Fi module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "7":
            console.print("[yellow]Bluetooth module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "8":
            console.print("[yellow]iButton module - Coming soon![/yellow]")
            Prompt.ask("Press Enter to continue")
        elif choice == "9":
            settings_menu()

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
