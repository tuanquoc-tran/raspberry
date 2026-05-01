"""
GPIO Module for RaspFlip
General Purpose Input/Output manipulation and testing
"""

import logging
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)

class PinMode(Enum):
    """GPIO Pin modes"""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    PWM = "PWM"

class PullMode(Enum):
    """Pull up/down resistor modes"""
    OFF = "OFF"
    UP = "UP"
    DOWN = "DOWN"

class GPIOController:
    """GPIO Controller for Raspberry Pi"""
    
    def __init__(self):
        self.initialized = False
        self.gpio = None
        self.pin_modes = {}
    
    def initialize(self) -> bool:
        """Initialize GPIO"""
        try:
            import RPi.GPIO as GPIO
            
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            self.initialized = True
            logger.info("GPIO initialized successfully")
            return True
        except ImportError:
            logger.error("RPi.GPIO not installed. Run: pip install RPi.GPIO")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize GPIO: {e}")
            return False
    
    def setup_pin(self, pin: int, mode: PinMode, pull: PullMode = PullMode.OFF) -> bool:
        """
        Setup GPIO pin
        
        Args:
            pin: GPIO pin number (BCM numbering)
            mode: Pin mode (INPUT, OUTPUT, PWM)
            pull: Pull resistor mode
        
        Returns:
            True if successful
        """
        if not self.initialized:
            logger.error("GPIO not initialized")
            return False
        
        try:
            if mode == PinMode.INPUT:
                pull_mode = {
                    PullMode.OFF: self.gpio.PUD_OFF,
                    PullMode.UP: self.gpio.PUD_UP,
                    PullMode.DOWN: self.gpio.PUD_DOWN
                }[pull]
                self.gpio.setup(pin, self.gpio.IN, pull_up_down=pull_mode)
            elif mode == PinMode.OUTPUT:
                self.gpio.setup(pin, self.gpio.OUT)
            
            self.pin_modes[pin] = mode
            logger.info(f"Pin {pin} configured as {mode.value}")
            return True
        except Exception as e:
            logger.error(f"Error setting up pin {pin}: {e}")
            return False
    
    def digital_write(self, pin: int, value: bool) -> bool:
        """Write digital value to pin"""
        if not self.initialized:
            return False
        
        try:
            self.gpio.output(pin, self.gpio.HIGH if value else self.gpio.LOW)
            return True
        except Exception as e:
            logger.error(f"Error writing to pin {pin}: {e}")
            return False
    
    def digital_read(self, pin: int) -> Optional[bool]:
        """Read digital value from pin"""
        if not self.initialized:
            return None
        
        try:
            return self.gpio.input(pin) == self.gpio.HIGH
        except Exception as e:
            logger.error(f"Error reading pin {pin}: {e}")
            return None
    
    def pulse_width_modulation(self, pin: int, frequency: float, duty_cycle: float):
        """
        Start PWM on pin
        
        Args:
            pin: GPIO pin number
            frequency: PWM frequency in Hz
            duty_cycle: Duty cycle (0-100)
        """
        if not self.initialized:
            return None
        
        try:
            pwm = self.gpio.PWM(pin, frequency)
            pwm.start(duty_cycle)
            return pwm
        except Exception as e:
            logger.error(f"Error starting PWM on pin {pin}: {e}")
            return None
    
    def read_all_pins(self) -> Dict[int, bool]:
        """Read state of all configured pins"""
        states = {}
        for pin in self.pin_modes.keys():
            if self.pin_modes[pin] == PinMode.INPUT:
                states[pin] = self.digital_read(pin)
        return states
    
    def cleanup(self):
        """Cleanup GPIO"""
        try:
            if self.gpio:
                self.gpio.cleanup()
        except:
            pass

class I2CScanner:
    """I2C Bus Scanner"""
    
    def __init__(self, bus: int = 1):
        self.bus = bus
        self.smbus = None
    
    def scan(self) -> List[int]:
        """Scan I2C bus for devices"""
        try:
            import smbus2
            
            self.smbus = smbus2.SMBus(self.bus)
            devices = []
            
            logger.info(f"Scanning I2C bus {self.bus}...")
            
            for address in range(0x03, 0x78):
                try:
                    self.smbus.read_byte(address)
                    devices.append(address)
                    logger.info(f"Found device at 0x{address:02X}")
                except:
                    pass
            
            return devices
        except ImportError:
            logger.error("smbus2 not installed. Run: pip install smbus2")
            return []
        except Exception as e:
            logger.error(f"Error scanning I2C: {e}")
            return []

class SPITester:
    """SPI Bus Tester"""
    
    def __init__(self, bus: int = 0, device: int = 0):
        self.bus = bus
        self.device = device
        self.spi = None
    
    def initialize(self) -> bool:
        """Initialize SPI"""
        try:
            import spidev
            
            self.spi = spidev.SpiDev()
            self.spi.open(self.bus, self.device)
            self.spi.max_speed_hz = 1000000
            
            logger.info(f"SPI bus {self.bus}, device {self.device} initialized")
            return True
        except ImportError:
            logger.error("spidev not installed. Run: pip install spidev")
            return False
        except Exception as e:
            logger.error(f"Error initializing SPI: {e}")
            return False
    
    def transfer(self, data: List[int]) -> Optional[List[int]]:
        """Transfer data over SPI"""
        if not self.spi:
            return None
        
        try:
            return self.spi.xfer2(data)
        except Exception as e:
            logger.error(f"Error in SPI transfer: {e}")
            return None
    
    def cleanup(self):
        """Close SPI connection"""
        try:
            if self.spi:
                self.spi.close()
        except:
            pass

class UARTTester:
    """UART Serial Tester"""
    
    def __init__(self, port: str = '/dev/serial0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
    
    def initialize(self) -> bool:
        """Initialize UART"""
        try:
            import serial
            
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            
            logger.info(f"UART {self.port} initialized at {self.baudrate} baud")
            return True
        except ImportError:
            logger.error("pyserial not installed. Run: pip install pyserial")
            return False
        except Exception as e:
            logger.error(f"Error initializing UART: {e}")
            return False
    
    def write(self, data: bytes) -> bool:
        """Write data to UART"""
        if not self.serial:
            return False
        
        try:
            self.serial.write(data)
            return True
        except Exception as e:
            logger.error(f"Error writing to UART: {e}")
            return False
    
    def read(self, size: int = 1) -> Optional[bytes]:
        """Read data from UART"""
        if not self.serial:
            return None
        
        try:
            return self.serial.read(size)
        except Exception as e:
            logger.error(f"Error reading from UART: {e}")
            return None
    
    def cleanup(self):
        """Close UART connection"""
        try:
            if self.serial:
                self.serial.close()
        except:
            pass
