"""
CLI User Interface for RaspFlip
"""

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

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
    while True:
        console.clear()
        
        table = Table(title="RFID/NFC Module", show_header=True, header_style="bold cyan")
        table.add_column("Option", style="cyan", width=8)
        table.add_column("Action", style="white")
        
        table.add_row("1", "Read RFID/NFC card")
        table.add_row("2", "Write to card")
        table.add_row("3", "Emulate card")
        table.add_row("4", "Saved cards")
        table.add_row("0", "Back to main menu")
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask("Select option", choices=["0", "1", "2", "3", "4"])
        
        if choice == "0":
            break
        else:
            console.print("[yellow]Function not yet implemented[/yellow]")
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
