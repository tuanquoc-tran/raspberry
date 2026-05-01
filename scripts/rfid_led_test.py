"""
RFID + LED Test
Quét thẻ → bật LED 1 giây → tắt
Dùng để xác nhận RC522 và GPIO đều hoạt động.

Wiring:
  LED anode  → GPIO 17 (pin 11) qua điện trở 220Ω
  LED cathode → GND (pin 9)

Chạy:
  cd /home/pi/Documents/raspberry
  source .env/bin/activate
  python scripts/rfid_led_test.py
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import RPi.GPIO as GPIO
from modules.rfid import get_reader

LED_PIN = 17      # BCM numbering — đổi nếu dùng pin khác
LED_ON_TIME = 1.0 # giây

def setup_led(pin: int):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

def led_on(pin: int):
    GPIO.output(pin, GPIO.HIGH)

def led_off(pin: int):
    GPIO.output(pin, GPIO.LOW)

def main():
    print("=== RFID + LED Test ===")
    print(f"LED: GPIO {LED_PIN}  |  Nhấn Ctrl+C để thoát\n")

    setup_led(LED_PIN)

    reader = get_reader('rc522')
    if not reader.initialize():
        print("[LỖI] Không khởi tạo được RC522. Kiểm tra lại wiring và thư viện.")
        GPIO.cleanup()
        sys.exit(1)

    print("Sẵn sàng. Đặt thẻ lên reader...\n")

    scan_count = 0
    try:
        while True:
            result = reader.read_uid(timeout=10)
            if result:
                scan_count += 1
                uid = result['uid_hex']
                card_type = result['card_type']
                print(f"[{scan_count}] UID: {uid}  |  {card_type}")

                # Bật LED
                led_on(LED_PIN)
                print(f"    LED ON  ▶ {LED_ON_TIME}s")
                time.sleep(LED_ON_TIME)

                # Tắt LED
                led_off(LED_PIN)
                print(f"    LED OFF ◀\n")

                # Chờ thẻ rời khỏi reader trước lần quét tiếp
                time.sleep(0.5)
            else:
                print("  (timeout — không có thẻ, thử lại...)")

    except KeyboardInterrupt:
        print(f"\nDừng. Đã quét {scan_count} lần.")
    finally:
        led_off(LED_PIN)
        reader.cleanup()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
