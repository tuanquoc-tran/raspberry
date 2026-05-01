"""
BadUSB Module for RaspFlip
Keyboard and HID emulation for penetration testing
"""

import logging
import time
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class BadUSB:
    """
    BadUSB - HID Keyboard emulation
    
    Uses Raspberry Pi Zero as USB Gadget (requires OTG support)
    """
    
    HID_DEVICE = '/dev/hidg0'
    GADGET_PATH = '/sys/kernel/config/usb_gadget/raspflip'
    
    # USB HID Keycodes
    KEYCODES = {
        'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08,
        'f': 0x09, 'g': 0x0a, 'h': 0x0b, 'i': 0x0c, 'j': 0x0d,
        'k': 0x0e, 'l': 0x0f, 'm': 0x10, 'n': 0x11, 'o': 0x12,
        'p': 0x13, 'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17,
        'u': 0x18, 'v': 0x19, 'w': 0x1a, 'x': 0x1b, 'y': 0x1c, 'z': 0x1d,
        '1': 0x1e, '2': 0x1f, '3': 0x20, '4': 0x21, '5': 0x22,
        '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
        'ENTER': 0x28, 'ESC': 0x29, 'BACKSPACE': 0x2a, 'TAB': 0x2b,
        'SPACE': 0x2c, '-': 0x2d, '=': 0x2e, '[': 0x2f, ']': 0x30,
        '\\': 0x31, ';': 0x33, "'": 0x34, '`': 0x35, ',': 0x36,
        '.': 0x37, '/': 0x38, 'CAPSLOCK': 0x39,
        'F1': 0x3a, 'F2': 0x3b, 'F3': 0x3c, 'F4': 0x3d, 'F5': 0x3e,
        'F6': 0x3f, 'F7': 0x40, 'F8': 0x41, 'F9': 0x42, 'F10': 0x43,
        'F11': 0x44, 'F12': 0x45,
        'DELETE': 0x4c, 'HOME': 0x4a, 'END': 0x4d,
        'PAGEUP': 0x4b, 'PAGEDOWN': 0x4e,
        'RIGHT': 0x4f, 'LEFT': 0x50, 'DOWN': 0x51, 'UP': 0x52,
        'GUI': 0x08, 'WINDOWS': 0x08, 'COMMAND': 0x08,
    }
    
    # Modifier keys (bitmask)
    MOD_CTRL_LEFT = 0x01
    MOD_SHIFT_LEFT = 0x02
    MOD_ALT_LEFT = 0x04
    MOD_GUI_LEFT = 0x08
    MOD_CTRL_RIGHT = 0x10
    MOD_SHIFT_RIGHT = 0x20
    MOD_ALT_RIGHT = 0x40
    MOD_GUI_RIGHT = 0x80
    
    def __init__(self):
        self.initialized = False
        self.hid_file = None
    
    def initialize(self) -> bool:
        """Initialize USB Gadget for HID"""
        try:
            # Check if running on Pi Zero with OTG support
            if not Path('/sys/kernel/config/usb_gadget').exists():
                logger.error("USB Gadget not supported on this device")
                logger.info("BadUSB requires Raspberry Pi Zero W/2W with OTG support")
                return False
            
            # Setup USB gadget if not already configured
            if not Path(self.GADGET_PATH).exists():
                logger.info("Setting up USB gadget...")
                # This requires root and proper setup script
                # See docs/badusb-setup.md for details
                pass
            
            # Open HID device
            if Path(self.HID_DEVICE).exists():
                self.hid_file = open(self.HID_DEVICE, 'wb')
                self.initialized = True
                logger.info("BadUSB initialized successfully")
                return True
            else:
                logger.error(f"HID device not found: {self.HID_DEVICE}")
                logger.info("Run setup script: sudo bash scripts/setup_badusb.sh")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize BadUSB: {e}")
            return False
    
    def _send_report(self, modifiers: int, keycode: int):
        """Send HID keyboard report"""
        if not self.initialized or not self.hid_file:
            return
        
        # HID report: [modifier, reserved, key1, key2, key3, key4, key5, key6]
        report = bytes([modifiers, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.hid_file.write(report)
        self.hid_file.flush()
    
    def _release_keys(self):
        """Release all keys"""
        if not self.initialized or not self.hid_file:
            return
        
        report = bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self.hid_file.write(report)
        self.hid_file.flush()
    
    def press_key(self, key: str, modifiers: int = 0x00, delay: float = 0.05):
        """
        Press and release a key
        
        Args:
            key: Key name (e.g., 'a', 'ENTER', 'F1')
            modifiers: Modifier bitmask (CTRL, SHIFT, ALT, GUI)
            delay: Delay between press and release (seconds)
        """
        if not self.initialized:
            logger.error("BadUSB not initialized")
            return
        
        keycode = self.KEYCODES.get(key.upper(), 0x00)
        if keycode == 0x00 and key.upper() not in self.KEYCODES:
            logger.warning(f"Unknown key: {key}")
            return
        
        self._send_report(modifiers, keycode)
        time.sleep(delay)
        self._release_keys()
        time.sleep(delay)
    
    def type_string(self, text: str, delay: float = 0.05):
        """
        Type a string of text
        
        Args:
            text: Text to type
            delay: Delay between keystrokes (seconds)
        """
        if not self.initialized:
            logger.error("BadUSB not initialized")
            return
        
        for char in text:
            if char.isupper():
                # Use shift modifier for uppercase
                keycode = self.KEYCODES.get(char.lower(), 0x00)
                self._send_report(self.MOD_SHIFT_LEFT, keycode)
            else:
                keycode = self.KEYCODES.get(char, 0x00)
                self._send_report(0x00, keycode)
            
            time.sleep(delay)
            self._release_keys()
            time.sleep(delay)
    
    def execute_payload(self, payload_path: str):
        """
        Execute a DuckyScript payload
        
        Args:
            payload_path: Path to payload file
        """
        if not self.initialized:
            logger.error("BadUSB not initialized")
            return
        
        try:
            with open(payload_path, 'r') as f:
                lines = f.readlines()
            
            logger.info(f"Executing payload: {payload_path}")
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                self._execute_command(line)
                
        except Exception as e:
            logger.error(f"Error executing payload: {e}")
    
    def _execute_command(self, command: str):
        """Execute a DuckyScript command"""
        parts = command.split(' ', 1)
        cmd = parts[0].upper()
        args = parts[1] if len(parts) > 1 else ''
        
        if cmd == 'DELAY':
            time.sleep(int(args) / 1000.0)
        elif cmd == 'STRING':
            self.type_string(args)
        elif cmd == 'ENTER':
            self.press_key('ENTER')
        elif cmd == 'GUI' or cmd == 'WINDOWS':
            if args:
                # GUI + key combination
                keycode = self.KEYCODES.get(args.upper(), 0x00)
                self._send_report(self.MOD_GUI_LEFT, keycode)
                time.sleep(0.05)
                self._release_keys()
            else:
                self.press_key('GUI')
        elif cmd == 'CTRL':
            keys = args.split()
            if len(keys) == 1:
                keycode = self.KEYCODES.get(keys[0].upper(), 0x00)
                self._send_report(self.MOD_CTRL_LEFT, keycode)
                time.sleep(0.05)
                self._release_keys()
        elif cmd == 'ALT':
            keys = args.split()
            if len(keys) == 1:
                keycode = self.KEYCODES.get(keys[0].upper(), 0x00)
                self._send_report(self.MOD_ALT_LEFT, keycode)
                time.sleep(0.05)
                self._release_keys()
        else:
            # Try as direct key press
            self.press_key(cmd)
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.hid_file:
                self._release_keys()
                self.hid_file.close()
        except:
            pass

# Example payloads
EXAMPLE_PAYLOADS = {
    'hello_world': """
REM Simple Hello World payload
DELAY 1000
GUI r
DELAY 500
STRING notepad
ENTER
DELAY 1000
STRING Hello from RaspFlip!
ENTER
STRING This is a BadUSB demonstration.
""",
    
    'info_gather': """
REM System Information Gathering (Windows)
DELAY 1000
GUI r
DELAY 500
STRING cmd
ENTER
DELAY 1000
STRING systeminfo > %TEMP%\\sysinfo.txt
ENTER
STRING ipconfig /all >> %TEMP%\\sysinfo.txt
ENTER
STRING exit
ENTER
"""
}
