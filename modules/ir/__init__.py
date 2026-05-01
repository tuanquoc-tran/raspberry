"""
Infrared Module for RaspFlip
Learn and replay IR signals for remote controls
"""

import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
import json

logger = logging.getLogger(__name__)

@dataclass
class IRSignal:
    """Represents an IR signal"""
    protocol: str
    data: List[int]  # Pulse/space timings in microseconds
    frequency: int = 38000  # Carrier frequency in Hz
    timestamp: datetime = None
    name: Optional[str] = None
    device_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for saving"""
        return {
            'protocol': self.protocol,
            'data': self.data,
            'frequency': self.frequency,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'name': self.name,
            'device_type': self.device_type
        }

class IRTransceiver:
    """IR Transmitter and Receiver"""
    
    # Common IR protocols
    PROTOCOLS = {
        'NEC': 'NEC (Japanese)',
        'RC5': 'Philips RC5',
        'RC6': 'Philips RC6',
        'SONY': 'Sony SIRC',
        'SAMSUNG': 'Samsung',
        'LG': 'LG',
        'RAW': 'Raw timing data'
    }
    
    def __init__(self, tx_pin: int = 18, rx_pin: int = 23):
        """
        Initialize IR transceiver
        
        Args:
            tx_pin: GPIO pin for IR LED transmitter
            rx_pin: GPIO pin for IR receiver (VS1838B)
        """
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.initialized = False
        self.gpio = None
    
    def initialize(self) -> bool:
        """Initialize GPIO for IR"""
        try:
            import RPi.GPIO as GPIO
            
            self.gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup TX pin
            GPIO.setup(self.tx_pin, GPIO.OUT)
            GPIO.output(self.tx_pin, GPIO.LOW)
            
            # Setup RX pin
            GPIO.setup(self.rx_pin, GPIO.IN)
            
            self.initialized = True
            logger.info("IR Transceiver initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize IR: {e}")
            return False
    
    def receive(self, timeout: float = 10.0) -> Optional[IRSignal]:
        """
        Receive and decode IR signal
        
        Args:
            timeout: Maximum time to wait for signal (seconds)
        
        Returns:
            IRSignal object or None
        """
        if not self.initialized:
            logger.error("IR not initialized")
            return None
        
        try:
            logger.info("Waiting for IR signal...")
            
            # Record pulse/space timings
            timings = self._record_timings(timeout)
            
            if not timings:
                logger.warning("No signal received")
                return None
            
            # Try to decode protocol
            protocol = self._detect_protocol(timings)
            
            return IRSignal(
                protocol=protocol,
                data=timings,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error receiving IR: {e}")
            return None
    
    def _record_timings(self, timeout: float) -> List[int]:
        """Record pulse/space timings from IR receiver"""
        import time
        
        timings = []
        start_time = time.time()
        
        # Wait for signal start
        while self.gpio.input(self.rx_pin) == self.gpio.HIGH:
            if time.time() - start_time > timeout:
                return []
            time.sleep(0.00001)
        
        # Record timings
        last_state = self.gpio.LOW
        last_time = time.time()
        
        while True:
            current_state = self.gpio.input(self.rx_pin)
            current_time = time.time()
            
            if current_state != last_state:
                duration = int((current_time - last_time) * 1000000)  # Convert to microseconds
                timings.append(duration)
                last_state = current_state
                last_time = current_time
            
            # Stop if no change for 50ms or timeout
            if current_time - last_time > 0.05 or current_time - start_time > timeout:
                break
        
        return timings
    
    def _detect_protocol(self, timings: List[int]) -> str:
        """Detect IR protocol from timings"""
        if not timings:
            return 'UNKNOWN'
        
        # Simple protocol detection based on leading pulse
        leading = timings[0] if timings else 0
        
        if 8000 < leading < 10000:  # ~9ms
            return 'NEC'
        elif 2000 < leading < 3000:  # ~2.4ms
            return 'SONY'
        elif 800 < leading < 1000:  # ~889µs
            return 'RC5'
        else:
            return 'RAW'
    
    def transmit(self, signal: IRSignal) -> bool:
        """
        Transmit IR signal
        
        Args:
            signal: IRSignal object to transmit
        
        Returns:
            True if successful
        """
        if not self.initialized:
            logger.error("IR not initialized")
            return False
        
        try:
            logger.info(f"Transmitting IR signal ({signal.protocol})...")
            
            # Generate carrier wave and modulate with data
            self._send_timings(signal.data, signal.frequency)
            
            logger.info("IR signal transmitted")
            return True
        except Exception as e:
            logger.error(f"Error transmitting IR: {e}")
            return False
    
    def _send_timings(self, timings: List[int], carrier_freq: int):
        """Send IR signal with carrier frequency modulation"""
        import time
        
        carrier_period = 1.0 / carrier_freq
        burst_time = carrier_period / 2
        
        for i, duration in enumerate(timings):
            duration_sec = duration / 1000000.0
            
            if i % 2 == 0:  # Pulse (ON)
                # Generate carrier
                end_time = time.time() + duration_sec
                while time.time() < end_time:
                    self.gpio.output(self.tx_pin, self.gpio.HIGH)
                    time.sleep(burst_time)
                    self.gpio.output(self.tx_pin, self.gpio.LOW)
                    time.sleep(burst_time)
            else:  # Space (OFF)
                self.gpio.output(self.tx_pin, self.gpio.LOW)
                time.sleep(duration_sec)
        
        self.gpio.output(self.tx_pin, self.gpio.LOW)
    
    def save_signal(self, signal: IRSignal, filepath: str) -> bool:
        """Save IR signal to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(signal.to_dict(), f, indent=2)
            logger.info(f"Signal saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return False
    
    def load_signal(self, filepath: str) -> Optional[IRSignal]:
        """Load IR signal from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            signal = IRSignal(
                protocol=data['protocol'],
                data=data['data'],
                frequency=data.get('frequency', 38000),
                timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else None,
                name=data.get('name'),
                device_type=data.get('device_type')
            )
            
            logger.info(f"Signal loaded from {filepath}")
            return signal
        except Exception as e:
            logger.error(f"Error loading signal: {e}")
            return None
    
    def cleanup(self):
        """Cleanup GPIO"""
        try:
            if self.gpio:
                self.gpio.cleanup([self.tx_pin, self.rx_pin])
        except:
            pass
