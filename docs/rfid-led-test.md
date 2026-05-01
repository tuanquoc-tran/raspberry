# Test RFID + LED

Script `scripts/rfid_led_test.py` dùng để xác nhận RC522 và GPIO hoạt động đúng:
**quét thẻ → bật LED 1 giây → tắt**.

## Linh Kiện Cần

- 1 × LED (màu tuỳ ý)
- 1 × điện trở 220Ω
- Dây jumper

## Wiring

```
Raspberry Pi 4
  pin 11 (GPIO 17) ●──[220Ω]──[LED+  LED-]──● pin 9 (GND)
```

```
GPIO 17 (pin 11) ──→ [220Ω] ──→ LED anode  (+)
                                 LED cathode (−) ──→ GND (pin 9)
```

> **Bắt buộc dùng điện trở 220Ω** để giới hạn dòng ~15mA, tránh cháy LED và GPIO.
> GPIO Raspberry Pi chịu tối đa 16mA mỗi pin.

### Tham chiếu chân GPIO

```
    3V3  (1) (2)  5V
  GPIO2  (3) (4)  5V
  GPIO3  (5) (6)  GND
  GPIO4  (7) (8)  GPIO14
    GND  (9) (10) GPIO15
 GPIO17 (11) (12) GPIO18   ← dùng pin 11 cho LED
```

## Chạy Script

```bash
cd /home/pi/Documents/raspberry
source .env/bin/activate
python scripts/rfid_led_test.py
```

## Output Mẫu

```
=== RFID + LED Test ===
LED: GPIO 17  |  Nhấn Ctrl+C để thoát

Sẵn sàng. Đặt thẻ lên reader...

[1] UID: E5:72:0B:53  |  MIFARE Classic 1K
    LED ON  ▶ 1.0s
    LED OFF ◀

[2] UID: E5:72:0B:53  |  MIFARE Classic 1K
    LED ON  ▶ 1.0s
    LED OFF ◀

Dừng. Đã quét 2 lần.
```

## Tuỳ Chỉnh

Sửa hai biến ở đầu file `scripts/rfid_led_test.py`:

| Biến | Mặc định | Mô tả |
|---|---|---|
| `LED_PIN` | `17` | Số GPIO (BCM) nối với LED |
| `LED_ON_TIME` | `1.0` | Thời gian LED sáng (giây) |

## Xử Lý Lỗi

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Failed to initialise RC522` | SPI chưa bật hoặc wiring sai | Chạy `sudo raspi-config` → Interface Options → SPI → Enable |
| LED không sáng | Wiring sai hoặc thiếu điện trở | Kiểm tra cực LED (anode/cathode) và điện trở |
| `RuntimeError: No access to /dev/mem` | Thiếu quyền GPIO | Chạy với `sudo` hoặc thêm user vào group `gpio` |

## Xem Thêm

- [RFID/NFC — MIFARE Classic 1K](rfid-mifare.md)
- [Hardware Setup Guide](hardware-setup.md)
