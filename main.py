"""
RaspFlip - Raspberry Pi Flipper Zero Alternative
Main application entry point
"""

import sys
import os
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / 'modules'))

from ui.cli import main_menu

def banner():
    """Display application banner"""
    print("""
    ╔═══════════════════════════════════════╗
    ║         RaspFlip v0.1.0              ║
    ║   Raspberry Pi Security Tool         ║
    ║                                       ║
    ║   Educational & Research Use Only     ║
    ╚═══════════════════════════════════════╝
    """)

def check_permissions():
    """Check if running with necessary permissions"""
    if os.geteuid() != 0:
        print("⚠️  Warning: Some features require root privileges")
        print("   Run with: sudo python3 main.py")
        print()

def main():
    """Main application entry point"""
    banner()
    check_permissions()
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting RaspFlip...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
