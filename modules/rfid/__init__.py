"""
RFID/NFC Module for RaspFlip
Supports RC522 (13.56MHz) and RDM6300 (125kHz) readers
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class RFIDReader:
    """Base class for RFID readers"""
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize the RFID reader hardware"""
        raise NotImplementedError
    
    def read_card(self) -> Optional[Dict[str, Any]]:
        """Read a card and return its data"""
        raise NotImplementedError
    
    def write_card(self, data: bytes) -> bool:
        """Write data to a card"""
        raise NotImplementedError
    
    def cleanup(self):
        """Cleanup hardware resources"""
        pass

class RC522Reader(RFIDReader):
    """RC522 RFID Reader (13.56MHz - MIFARE)"""
    
    def __init__(self, bus=0, device=0):
        super().__init__()
        self.bus = bus
        self.device = device
        self.reader = None
    
    def initialize(self) -> bool:
        """Initialize RC522 reader"""
        try:
            # Import here to avoid errors if not installed
            from mfrc522 import SimpleMFRC522
            import RPi.GPIO as GPIO
            
            GPIO.setwarnings(False)
            self.reader = SimpleMFRC522()
            self.initialized = True
            logger.info("RC522 reader initialized successfully")
            return True
        except ImportError:
            logger.error("mfrc522 library not installed. Run: pip install mfrc522")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize RC522: {e}")
            return False
    
    def read_card(self) -> Optional[Dict[str, Any]]:
        """Read MIFARE card"""
        if not self.initialized:
            logger.error("Reader not initialized")
            return None
        
        try:
            logger.info("Waiting for card...")
            id, text = self.reader.read()
            
            return {
                'type': 'MIFARE',
                'uid': id,
                'data': text.strip(),
                'frequency': '13.56MHz'
            }
        except Exception as e:
            logger.error(f"Error reading card: {e}")
            return None
    
    def write_card(self, data: str) -> bool:
        """Write data to MIFARE card"""
        if not self.initialized:
            logger.error("Reader not initialized")
            return False
        
        try:
            logger.info("Waiting for card to write...")
            self.reader.write(data)
            logger.info("Data written successfully")
            return True
        except Exception as e:
            logger.error(f"Error writing card: {e}")
            return False
    
    def cleanup(self):
        """Cleanup GPIO"""
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except:
            pass

class PN532Reader(RFIDReader):
    """PN532 NFC Reader"""
    
    def __init__(self):
        super().__init__()
        self.pn532 = None
    
    def initialize(self) -> bool:
        """Initialize PN532 NFC reader"""
        try:
            import board
            import busio
            from adafruit_pn532.i2c import PN532_I2C
            
            i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(i2c, debug=False)
            
            # Get firmware version
            ic, ver, rev, support = self.pn532.firmware_version
            logger.info(f'PN532 found - Firmware: {ver}.{rev}')
            
            # Configure to read RFID tags
            self.pn532.SAM_configuration()
            self.initialized = True
            return True
        except ImportError:
            logger.error("PN532 library not installed. Run: pip install adafruit-circuitpython-pn532")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize PN532: {e}")
            return False
    
    def read_card(self) -> Optional[Dict[str, Any]]:
        """Read NFC card"""
        if not self.initialized:
            logger.error("Reader not initialized")
            return None
        
        try:
            logger.info("Waiting for NFC card...")
            uid = self.pn532.read_passive_target(timeout=5)
            
            if uid is None:
                return None
            
            return {
                'type': 'NFC',
                'uid': ''.join(['{:02x}'.format(i) for i in uid]),
                'uid_bytes': uid,
                'frequency': '13.56MHz'
            }
        except Exception as e:
            logger.error(f"Error reading card: {e}")
            return None

def get_reader(reader_type: str = 'rc522') -> Optional[RFIDReader]:
    """Factory function to get appropriate RFID reader"""
    readers = {
        'rc522': RC522Reader,
        'pn532': PN532Reader
    }
    
    reader_class = readers.get(reader_type.lower())
    if reader_class:
        return reader_class()
    else:
        logger.error(f"Unknown reader type: {reader_type}")
        return None
