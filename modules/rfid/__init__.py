"""
RFID/NFC Module for RaspFlip
Supports RC522 (13.56MHz) and RDM6300 (125kHz) readers
"""

import json
import logging
import os
import time
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# MIFARE Classic constants
MIFARE_KEYA = 0x60
MIFARE_KEYB = 0x61
DEFAULT_KEY = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]
MIFARE_1K_SECTORS = 16
MIFARE_1K_BLOCKS = 64
BLOCKS_PER_SECTOR = 4

CARD_TYPES = {
    0x08: 'MIFARE Classic 1K',
    0x09: 'MIFARE Mini',
    0x18: 'MIFARE Classic 4K',
    0x88: 'MIFARE Classic 1K (Infineon)',
    0x28: 'JCOP30',
    0x20: 'MIFARE Plus / DESFire',
    0x98: 'MIFARE SmartMX 4K',
}

SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'rfid')


class RFIDReader:
    """Base class for RFID readers"""

    def __init__(self):
        self.initialized = False

    def initialize(self) -> bool:
        raise NotImplementedError

    def read_card(self) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def write_card(self, data: bytes) -> bool:
        raise NotImplementedError

    def cleanup(self):
        pass


class RC522Reader(RFIDReader):
    """
    RC522 RFID Reader (13.56MHz – MIFARE Classic).

    Provides high-level helpers on top of the raw MFRC522 driver:
      - read_uid()       – fast UID scan (no block read)
      - read_card()      – UID + text payload via SimpleMFRC522
      - write_card()     – write text payload via SimpleMFRC522
      - read_block()     – authenticate and read a single 16-byte block
      - write_block()    – authenticate and write a single 16-byte block
      - dump_card()      – read every block of a MIFARE Classic 1K card
      - save_card()      – persist a dump to JSON
      - load_card()      – restore a dump from JSON
      - write_dump()     – write a full dump back to a blank card
    """

    def __init__(self, bus: int = 0, device: int = 0):
        super().__init__()
        self.bus = bus
        self.device = device
        self._simple = None   # SimpleMFRC522 – for text read/write
        self._mfrc522 = None  # MFRC522       – for low-level block access

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        try:
            import RPi.GPIO as GPIO
            from mfrc522 import MFRC522, SimpleMFRC522

            GPIO.setwarnings(False)
            self._simple = SimpleMFRC522()
            self._mfrc522 = MFRC522()
            self.initialized = True
            logger.info("RC522 initialised successfully")
            return True
        except ImportError:
            logger.error("mfrc522 not installed – run: pip install mfrc522")
            return False
        except Exception as exc:
            logger.error(f"RC522 init failed: {exc}")
            return False

    def cleanup(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
        except Exception:
            pass
        self.initialized = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _uid_to_hex(self, uid: List[int]) -> str:
        return ':'.join(f'{b:02X}' for b in uid)

    def _uid_to_int(self, uid: List[int]) -> int:
        result = 0
        for b in uid:
            result = (result << 8) | b
        return result

    def _detect_card(self):
        """Return (card_type_byte, uid_list) or (None, None)."""
        from mfrc522 import MFRC522
        status, tag_type = self._mfrc522.MFRC522_Request(MFRC522.PICC_REQIDL)
        if status != MFRC522.MI_OK:
            return None, None
        status, uid = self._mfrc522.MFRC522_Anticoll()
        if status != MFRC522.MI_OK:
            return None, None
        return tag_type, uid

    def _select_card(self, uid: List[int]) -> bool:
        from mfrc522 import MFRC522
        size = self._mfrc522.MFRC522_SelectTag(uid)
        return size != 0

    def _auth(self, block: int, key: List[int], uid: List[int],
              key_type: int = MIFARE_KEYA) -> bool:
        from mfrc522 import MFRC522
        status = self._mfrc522.MFRC522_Auth(key_type, block, key, uid)
        return status == MFRC522.MI_OK

    def _stop_crypto(self):
        self._mfrc522.MFRC522_StopCrypto1()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_uid(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """
        Wait for a card and return its UID without reading any data blocks.
        Returns None on timeout.
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            tag_type, uid = self._detect_card()
            if uid is not None:
                self._mfrc522.MFRC522_StopCrypto1()
                card_name = CARD_TYPES.get(tag_type, f'Unknown (0x{tag_type:02X})'
                                           if tag_type is not None else 'Unknown')
                return {
                    'uid_hex': self._uid_to_hex(uid),
                    'uid_int': self._uid_to_int(uid),
                    'uid_bytes': uid,
                    'card_type': card_name,
                    'frequency': '13.56 MHz',
                }
            time.sleep(0.1)
        return None

    def read_card(self) -> Optional[Dict[str, Any]]:
        """
        Block until a MIFARE card is presented, then return UID + text payload.
        Uses SimpleMFRC522 so text spans blocks 8, 9, 10.
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return None
        try:
            logger.info("Waiting for card (read)…")
            uid_int, text = self._simple.read()
            uid_hex = f'{uid_int:X}'.zfill(8)
            return {
                'uid_hex': uid_hex,
                'uid_int': uid_int,
                'card_type': 'MIFARE Classic 1K',
                'data': text.strip(),
                'frequency': '13.56 MHz',
            }
        except Exception as exc:
            logger.error(f"read_card error: {exc}")
            return None

    def write_card(self, data: str) -> bool:
        """Write a text string to the card (blocks 8-10, max ~48 chars)."""
        if not self.initialized:
            logger.error("Reader not initialised")
            return False
        try:
            logger.info("Waiting for card (write)…")
            self._simple.write(data)
            logger.info("Text written successfully")
            return True
        except Exception as exc:
            logger.error(f"write_card error: {exc}")
            return False

    def read_block(self, block: int, key: Optional[List[int]] = None,
                   key_type: int = MIFARE_KEYA) -> Optional[bytes]:
        """
        Read a single 16-byte block from a MIFARE Classic 1K card.
        Handles card detection, selection, and authentication internally.
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return None
        if not 0 <= block < MIFARE_1K_BLOCKS:
            logger.error(f"Block {block} out of range (0-{MIFARE_1K_BLOCKS - 1})")
            return None

        key = key or DEFAULT_KEY
        try:
            tag_type, uid = self._detect_card()
            if uid is None:
                logger.error("No card detected")
                return None
            if not self._select_card(uid):
                logger.error("Card selection failed")
                return None
            if not self._auth(block, key, uid, key_type):
                logger.error(f"Authentication failed for block {block}")
                self._stop_crypto()
                return None

            from mfrc522 import MFRC522
            status, data_out = self._mfrc522.MFRC522_Read(block)
            self._stop_crypto()

            if status == MFRC522.MI_OK and data_out:
                return bytes(data_out[:16])
            logger.error(f"Read block {block} failed (status={status})")
            return None
        except Exception as exc:
            logger.error(f"read_block error: {exc}")
            self._stop_crypto()
            return None

    def write_block(self, block: int, data: bytes,
                    key: Optional[List[int]] = None,
                    key_type: int = MIFARE_KEYA) -> bool:
        """
        Write exactly 16 bytes to a block.
        Block 0 (manufacturer) and sector trailers (3, 7, 11, …) are
        protected by default and will raise a ValueError.
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return False
        if not 0 <= block < MIFARE_1K_BLOCKS:
            raise ValueError(f"Block {block} out of range")
        if block == 0:
            raise ValueError("Block 0 is read-only (manufacturer data)")
        if (block + 1) % BLOCKS_PER_SECTOR == 0:
            raise ValueError(f"Block {block} is a sector trailer – use write_sector_trailer()")
        if len(data) != 16:
            raise ValueError(f"Data must be exactly 16 bytes (got {len(data)})")

        key = key or DEFAULT_KEY
        try:
            tag_type, uid = self._detect_card()
            if uid is None:
                logger.error("No card detected")
                return False
            if not self._select_card(uid):
                logger.error("Card selection failed")
                return False
            if not self._auth(block, key, uid, key_type):
                logger.error(f"Authentication failed for block {block}")
                self._stop_crypto()
                return False

            from mfrc522 import MFRC522
            status = self._mfrc522.MFRC522_Write(block, list(data))
            self._stop_crypto()

            if status == MFRC522.MI_OK:
                logger.info(f"Block {block} written successfully")
                return True
            logger.error(f"Write block {block} failed (status={status})")
            return False
        except Exception as exc:
            logger.error(f"write_block error: {exc}")
            self._stop_crypto()
            return False

    def dump_card(self, key: Optional[List[int]] = None,
                  key_type: int = MIFARE_KEYA) -> Optional[Dict[str, Any]]:
        """
        Read all 64 blocks of a MIFARE Classic 1K card.

        Returns a dict with keys:
          uid_hex, uid_int, card_type, sectors
        where `sectors` is a list of 16 items, each a list of 4 blocks,
        each block being a list of 16 ints (or None on read failure).
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return None

        key = key or DEFAULT_KEY
        try:
            from mfrc522 import MFRC522

            tag_type, uid = self._detect_card()
            if uid is None:
                logger.error("No card detected")
                return None
            if not self._select_card(uid):
                logger.error("Card selection failed")
                return None

            uid_hex = self._uid_to_hex(uid)
            uid_int = self._uid_to_int(uid)
            card_name = CARD_TYPES.get(tag_type, f'Unknown (0x{tag_type:02X})'
                                       if tag_type is not None else 'Unknown')

            sectors: List[List[Optional[List[int]]]] = []
            for sector in range(MIFARE_1K_SECTORS):
                trailer_block = sector * BLOCKS_PER_SECTOR + 3
                auth_ok = self._auth(trailer_block, key, uid, key_type)
                sector_data: List[Optional[List[int]]] = []
                for blk_offset in range(BLOCKS_PER_SECTOR):
                    block = sector * BLOCKS_PER_SECTOR + blk_offset
                    if auth_ok:
                        status, blk_data = self._mfrc522.MFRC522_Read(block)
                        if status == MFRC522.MI_OK and blk_data:
                            sector_data.append(list(blk_data[:16]))
                        else:
                            sector_data.append(None)
                    else:
                        sector_data.append(None)
                sectors.append(sector_data)

            self._stop_crypto()
            logger.info(f"Dump complete – UID {uid_hex}")
            return {
                'uid_hex': uid_hex,
                'uid_int': uid_int,
                'card_type': card_name,
                'frequency': '13.56 MHz',
                'sectors': sectors,
            }
        except Exception as exc:
            logger.error(f"dump_card error: {exc}")
            self._stop_crypto()
            return None

    def save_card(self, dump: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Persist a card dump (from dump_card()) to a JSON file.
        Returns the path of the saved file.
        """
        os.makedirs(SAVE_DIR, exist_ok=True)
        if filename is None:
            uid = dump.get('uid_hex', 'unknown').replace(':', '')
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"mifare_{uid}_{timestamp}.json"
        path = os.path.join(SAVE_DIR, filename)
        with open(path, 'w') as fh:
            json.dump(dump, fh, indent=2)
        logger.info(f"Card saved to {path}")
        return path

    def load_card(self, filename: str) -> Optional[Dict[str, Any]]:
        """Load a card dump from a JSON file."""
        path = filename if os.path.isabs(filename) else os.path.join(SAVE_DIR, filename)
        try:
            with open(path) as fh:
                dump = json.load(fh)
            logger.info(f"Card loaded from {path}")
            return dump
        except FileNotFoundError:
            logger.error(f"File not found: {path}")
            return None
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in {path}: {exc}")
            return None

    def write_dump(self, dump: Dict[str, Any],
                   key: Optional[List[int]] = None,
                   key_type: int = MIFARE_KEYA) -> bool:
        """
        Write a full card dump back to a blank MIFARE Classic 1K card.
        Skips block 0 (read-only) and sector trailers.
        """
        if not self.initialized:
            logger.error("Reader not initialised")
            return False

        key = key or DEFAULT_KEY
        sectors = dump.get('sectors')
        if not sectors or len(sectors) != MIFARE_1K_SECTORS:
            logger.error("Invalid dump format")
            return False

        try:
            from mfrc522 import MFRC522

            tag_type, uid = self._detect_card()
            if uid is None:
                logger.error("No card detected")
                return False
            if not self._select_card(uid):
                logger.error("Card selection failed")
                return False

            errors = 0
            for sector_idx, sector_blocks in enumerate(sectors):
                trailer_block = sector_idx * BLOCKS_PER_SECTOR + 3
                if not self._auth(trailer_block, key, uid, key_type):
                    logger.warning(f"Auth failed for sector {sector_idx}, skipping")
                    errors += 1
                    continue
                for blk_offset, blk_data in enumerate(sector_blocks):
                    block = sector_idx * BLOCKS_PER_SECTOR + blk_offset
                    # Skip read-only block 0 and sector trailers
                    if block == 0 or (block + 1) % BLOCKS_PER_SECTOR == 0:
                        continue
                    if blk_data is None:
                        continue
                    status = self._mfrc522.MFRC522_Write(block, blk_data[:16])
                    if status != MFRC522.MI_OK:
                        logger.warning(f"Write failed on block {block}")
                        errors += 1

            self._stop_crypto()
            if errors:
                logger.warning(f"Write dump completed with {errors} error(s)")
            else:
                logger.info("Write dump completed successfully")
            return errors == 0
        except Exception as exc:
            logger.error(f"write_dump error: {exc}")
            self._stop_crypto()
            return False

    def list_saved_cards(self) -> List[str]:
        """Return filenames of all saved card dumps."""
        if not os.path.isdir(SAVE_DIR):
            return []
        return sorted(
            f for f in os.listdir(SAVE_DIR) if f.endswith('.json')
        )

class RDM6300Reader(RFIDReader):
    """
    RDM6300 125 kHz EM4100/HID reader via UART.
    Default UART: /dev/serial0 (GPIO 14/15), 9600 baud.

    The RDM6300 outputs a 14-byte frame:
      [STX 0x02] [10 ASCII hex digits = 5 bytes UID] [2 checksum hex digits] [ETX 0x03]
    """

    FRAME_LEN = 14
    STX = 0x02
    ETX = 0x03

    def __init__(self, port: str = '/dev/serial0', baudrate: int = 9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._serial = None

    def initialize(self) -> bool:
        try:
            import serial
            self._serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.initialized = True
            logger.info(f"RDM6300 initialised on {self.port}")
            return True
        except ImportError:
            logger.error("pyserial not installed – run: pip install pyserial")
            return False
        except Exception as exc:
            logger.error(f"RDM6300 init failed: {exc}")
            return False

    def _parse_frame(self, frame: bytes) -> Optional[Dict[str, Any]]:
        if len(frame) != self.FRAME_LEN:
            return None
        if frame[0] != self.STX or frame[-1] != self.ETX:
            return None
        try:
            payload = frame[1:11].decode('ascii')   # 10 hex chars
            checksum_str = frame[11:13].decode('ascii')
        except (UnicodeDecodeError, ValueError):
            return None

        # Verify XOR checksum over 4 bytes (8 hex chars after version nibble)
        raw_bytes = [int(payload[i:i+2], 16) for i in range(0, 10, 2)]
        expected_checksum = 0
        for b in raw_bytes[1:]:   # skip the version byte
            expected_checksum ^= b
        if expected_checksum != int(checksum_str, 16):
            logger.warning("RDM6300 checksum mismatch")
            return None

        uid_hex = payload[2:]   # skip version byte (2 hex chars)
        return {
            'uid_hex': uid_hex.upper(),
            'uid_int': int(uid_hex, 16),
            'card_type': 'EM4100',
            'frequency': '125 kHz',
        }

    def read_card(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        if not self.initialized:
            logger.error("Reader not initialised")
            return None

        deadline = time.time() + timeout
        buf = bytearray()
        try:
            while time.time() < deadline:
                raw = self._serial.read(self._serial.in_waiting or 1)
                buf.extend(raw)
                # Scan buffer for a complete frame
                while len(buf) >= self.FRAME_LEN:
                    start = buf.find(self.STX)
                    if start == -1:
                        buf.clear()
                        break
                    if start > 0:
                        del buf[:start]
                    if len(buf) < self.FRAME_LEN:
                        break
                    frame = bytes(buf[:self.FRAME_LEN])
                    del buf[:self.FRAME_LEN]
                    result = self._parse_frame(frame)
                    if result:
                        return result
        except Exception as exc:
            logger.error(f"RDM6300 read error: {exc}")
        return None

    def write_card(self, data: bytes) -> bool:
        logger.error("RDM6300 is read-only – writing is not supported")
        return False

    def cleanup(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self.initialized = False


class PN532Reader(RFIDReader):
    """PN532 NFC Reader (I2C)"""

    def __init__(self):
        super().__init__()
        self.pn532 = None

    def initialize(self) -> bool:
        try:
            import board
            import busio
            from adafruit_pn532.i2c import PN532_I2C

            i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(i2c, debug=False)
            ic, ver, rev, support = self.pn532.firmware_version
            logger.info(f"PN532 found – Firmware {ver}.{rev}")
            self.pn532.SAM_configuration()
            self.initialized = True
            return True
        except ImportError:
            logger.error("PN532 library not installed – run: pip install adafruit-circuitpython-pn532")
            return False
        except Exception as exc:
            logger.error(f"PN532 init failed: {exc}")
            return False

    def read_card(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        if not self.initialized:
            logger.error("Reader not initialised")
            return None
        try:
            logger.info("Waiting for NFC card…")
            uid = self.pn532.read_passive_target(timeout=timeout)
            if uid is None:
                return None
            return {
                'uid_hex': ':'.join(f'{b:02X}' for b in uid),
                'uid_int': int.from_bytes(uid, 'big'),
                'uid_bytes': list(uid),
                'card_type': 'NFC',
                'frequency': '13.56 MHz',
            }
        except Exception as exc:
            logger.error(f"PN532 read error: {exc}")
            return None

    def write_card(self, data: bytes) -> bool:
        logger.error("PN532 write not implemented")
        return False


def get_reader(reader_type: str = 'rc522') -> Optional[RFIDReader]:
    """Factory – return an uninitialised reader instance for the given type."""
    readers = {
        'rc522': RC522Reader,
        'rdm6300': RDM6300Reader,
        'pn532': PN532Reader,
    }
    reader_class = readers.get(reader_type.lower())
    if reader_class:
        return reader_class()
    logger.error(f"Unknown reader type: {reader_type}. Choose from: {list(readers)}")
    return None
