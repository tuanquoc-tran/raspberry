"""
Hardware checker script
Verifies all hardware modules are properly connected
"""

import logging
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)

def check_spi():
    """Check SPI interface"""
    import os
    print("\n[*] Checking SPI...")
    
    spi_devices = ['/dev/spidev0.0', '/dev/spidev0.1']
    for device in spi_devices:
        if os.path.exists(device):
            print(f"  ✓ {device} found")
        else:
            print(f"  ✗ {device} not found")
            return False
    return True

def check_i2c():
    """Check I2C interface"""
    import os
    print("\n[*] Checking I2C...")
    
    if os.path.exists('/dev/i2c-1'):
        print("  ✓ /dev/i2c-1 found")
        
        try:
            import smbus2
            bus = smbus2.SMBus(1)
            
            devices = []
            for addr in range(0x03, 0x78):
                try:
                    bus.read_byte(addr)
                    devices.append(addr)
                except:
                    pass
            
            if devices:
                print(f"  ✓ Found {len(devices)} I2C device(s):")
                for addr in devices:
                    print(f"    - 0x{addr:02X}")
            else:
                print("  ! No I2C devices detected")
            
            return True
        except ImportError:
            print("  ✗ smbus2 not installed")
            return False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
    else:
        print("  ✗ /dev/i2c-1 not found")
        return False

def check_gpio():
    """Check GPIO access"""
    print("\n[*] Checking GPIO...")
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        print("  ✓ GPIO library working")
        GPIO.cleanup()
        return True
    except ImportError:
        print("  ✗ RPi.GPIO not installed")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def check_rfid():
    """Check RFID module"""
    print("\n[*] Checking RFID (RC522)...")
    
    try:
        from mfrc522 import SimpleMFRC522
        import RPi.GPIO as GPIO
        
        GPIO.setwarnings(False)
        reader = SimpleMFRC522()
        print("  ✓ RC522 module initialized")
        GPIO.cleanup()
        return True
    except ImportError:
        print("  ✗ mfrc522 library not installed")
        return False
    except Exception as e:
        print(f"  ! Warning: {e}")
        return False

def check_lirc():
    """Check LIRC for IR"""
    import os
    print("\n[*] Checking LIRC (Infrared)...")
    
    if os.path.exists('/dev/lirc0'):
        print("  ✓ /dev/lirc0 found")
        return True
    else:
        print("  ✗ /dev/lirc0 not found")
        print("    Install LIRC: sudo apt install lirc")
        return False

def check_bluetooth():
    """Check Bluetooth"""
    import subprocess
    print("\n[*] Checking Bluetooth...")
    
    try:
        result = subprocess.run(['hciconfig'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        if 'hci0' in result.stdout:
            print("  ✓ Bluetooth adapter found")
            return True
        else:
            print("  ✗ No Bluetooth adapter")
            return False
    except FileNotFoundError:
        print("  ✗ hciconfig not found")
        print("    Install: sudo apt install bluetooth bluez")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def check_python_packages():
    """Check required Python packages"""
    print("\n[*] Checking Python packages...")
    
    packages = [
        'RPi.GPIO',
        'spidev',
        'smbus2',
        'serial',
        'rich',
        'click'
    ]
    
    all_ok = True
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 50)
    print("  RaspFlip Hardware Checker")
    print("=" * 50)
    
    results = {
        'SPI': check_spi(),
        'I2C': check_i2c(),
        'GPIO': check_gpio(),
        'RFID': check_rfid(),
        'LIRC': check_lirc(),
        'Bluetooth': check_bluetooth(),
        'Python Packages': check_python_packages()
    }
    
    print("\n" + "=" * 50)
    print("  Summary")
    print("=" * 50)
    
    for name, status in results.items():
        status_str = "✓ OK" if status else "✗ FAIL"
        print(f"  {name:20s}: {status_str}")
    
    print("=" * 50)
    
    if all(results.values()):
        print("\n✓ All checks passed!")
        return 0
    else:
        print("\n⚠ Some checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
