# Hardware Setup Guide

## 📋 Tổng Quan

Hướng dẫn này sẽ giúp bạn kết nối các module phần cứng với Raspberry Pi để xây dựng thiết bị RaspFlip.

## 🔌 Sơ Đồ GPIO Raspberry Pi 4

```
    3V3  (1) (2)  5V
  GPIO2  (3) (4)  5V
  GPIO3  (5) (6)  GND
  GPIO4  (7) (8)  GPIO14
    GND  (9) (10) GPIO15
 GPIO17 (11) (12) GPIO18
 GPIO27 (13) (14) GND
 GPIO22 (15) (16) GPIO23
    3V3 (17) (18) GPIO24
 GPIO10 (19) (20) GND
  GPIO9 (21) (22) GPIO25
 GPIO11 (23) (24) GPIO8
    GND (25) (26) GPIO7
  GPIO0 (27) (28) GPIO1
  GPIO5 (29) (30) GND
  GPIO6 (31) (32) GPIO12
 GPIO13 (33) (34) GND
 GPIO19 (35) (36) GPIO16
 GPIO26 (37) (38) GPIO20
    GND (39) (40) GPIO21
```

## 1. RFID/NFC Module

### RC522 (MFRC522) - 13.56MHz

**Kết nối SPI:**
```
RC522    →  Raspberry Pi
SDA      →  GPIO8  (Pin 24 - CE0)
SCK      →  GPIO11 (Pin 23 - SCLK)
MOSI     →  GPIO10 (Pin 19 - MOSI)
MISO     →  GPIO9  (Pin 21 - MISO)
IRQ      →  (Không kết nối)
GND      →  GND    (Pin 6)
RST      →  GPIO25 (Pin 22)
3.3V     →  3.3V   (Pin 1)
```

**Cấu hình:**
```bash
# Enable SPI
sudo raspi-config
# Interface Options → SPI → Enable

# Test
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1
```

### PN532 - NFC Module

**Kết nối I2C:**
```
PN532    →  Raspberry Pi
VCC      →  3.3V   (Pin 1)
GND      →  GND    (Pin 6)
SDA      →  GPIO2  (Pin 3 - SDA)
SCL      →  GPIO3  (Pin 5 - SCL)
```

**Cấu hình:**
```bash
# Enable I2C
sudo raspi-config
# Interface Options → I2C → Enable

# Test
i2cdetect -y 1
# Should show device at 0x24
```

## 2. Sub-GHz Radio Module

### CC1101 Transceiver

**Kết nối SPI:**
```
CC1101   →  Raspberry Pi
VCC      →  3.3V   (Pin 17)
GND      →  GND    (Pin 20)
MISO     →  GPIO9  (Pin 21)
MOSI     →  GPIO10 (Pin 19)
SCK      →  GPIO11 (Pin 23)
CSN      →  GPIO8  (Pin 24)
GDO0     →  GPIO24 (Pin 18)
GDO2     →  GPIO25 (Pin 22)
```

**Lưu ý:**
- CC1101 hoạt động ở 3.3V
- Cần anten phù hợp với tần số sử dụng (433MHz, 315MHz, 868MHz, 915MHz)
- Kiểm tra luật pháp địa phương về tần số radio

## 3. Infrared Module

### IR Receiver (VS1838B)

**Kết nối:**
```
VS1838B  →  Raspberry Pi
OUT      →  GPIO23 (Pin 16)
GND      →  GND    (Pin 14)
VCC      →  3.3V   (Pin 17)
```

### IR Transmitter (LED)

**Kết nối:**
```
IR LED   →  Raspberry Pi
Cathode  →  GND qua transistor
Anode    →  GPIO18 (Pin 12) qua transistor + resistor
```

**Sơ đồ mạch phát IR:**
```
GPIO18 → 330Ω → Base (2N2222 NPN)
                Collector → IR LED (Anode) → 100Ω → 3.3V
                Emitter → GND
IR LED Cathode → GND
```

**Cấu hình LIRC:**
```bash
# Install LIRC
sudo apt-get install lirc

# Edit /etc/lirc/lirc_options.conf
driver = default
device = /dev/lirc0

# Edit /boot/config.txt
dtoverlay=gpio-ir,gpio_pin=23
dtoverlay=gpio-ir-tx,gpio_pin=18
```

## 4. Display Options

### SSD1306 OLED (128x64) - I2C

**Kết nối:**
```
SSD1306  →  Raspberry Pi
VCC      →  3.3V   (Pin 1)
GND      →  GND    (Pin 9)
SCL      →  GPIO3  (Pin 5)
SDA      →  GPIO2  (Pin 3)
```

### 2.8" TFT Display - SPI

**Kết nối:**
```
TFT      →  Raspberry Pi
VCC      →  5V     (Pin 2)
GND      →  GND    (Pin 6)
CS       →  GPIO8  (Pin 24)
RESET    →  GPIO25 (Pin 22)
DC/RS    →  GPIO24 (Pin 18)
MOSI     →  GPIO10 (Pin 19)
SCK      →  GPIO11 (Pin 23)
LED      →  3.3V   (Pin 1)
MISO     →  GPIO9  (Pin 21)
```

## 5. Input Controls

### Rotary Encoder

**Kết nối:**
```
Encoder  →  Raspberry Pi
CLK      →  GPIO17 (Pin 11)
DT       →  GPIO27 (Pin 13)
SW       →  GPIO22 (Pin 15)
+        →  3.3V   (Pin 17)
GND      →  GND    (Pin 14)
```

### Tactile Buttons

**Kết nối (với pull-up resistor):**
```
Button 1 →  GPIO5  (Pin 29) + 10kΩ to 3.3V
Button 2 →  GPIO6  (Pin 31) + 10kΩ to 3.3V
Button 3 →  GPIO13 (Pin 33) + 10kΩ to 3.3V
Button 4 →  GPIO19 (Pin 35) + 10kΩ to 3.3V
All GND  →  GND
```

## 6. BadUSB Setup (Chỉ Raspberry Pi Zero)

Raspberry Pi Zero có thể hoạt động như USB Gadget.

**Cấu hình:**

1. Enable USB OTG:
```bash
# Edit /boot/config.txt
dtoverlay=dwc2

# Edit /etc/modules
dwc2
libcomposite
```

2. Create HID gadget:
```bash
sudo bash scripts/setup_badusb.sh
```

## 7. Power Supply

**Yêu cầu nguồn:**
- Raspberry Pi 4: 5V/3A (khuyến nghị)
- Raspberry Pi Zero: 5V/2A

**Pin di động:**
- Dung lượng: 10,000mAh trở lên
- Output: 5V/2.4A hoặc cao hơn
- Tính năng passthrough charging (tùy chọn)

## 8. Case và Thiết Kế

### Case In 3D

File STL có sẵn tại: `hardware/case/`

**Tính năng:**
- Khe cho tất cả module
- Vị trí cho display
- Lỗ cho buttons/encoder
- Khe tản nhiệt
- Lỗ cho anten (Sub-GHz)

### Lắp Ráp

1. Mount Raspberry Pi vào case
2. Kết nối các module theo sơ đồ
3. Cố định display
4. Lắp buttons/encoder
5. Kết nối anten
6. Test từng module trước khi đóng case

## 9. Testing Checklist

- [ ] Raspberry Pi boot bình thường
- [ ] SPI devices visible: `ls /dev/spi*`
- [ ] I2C devices detected: `i2cdetect -y 1`
- [ ] GPIO accessible: `gpio readall`
- [ ] RFID module đọc thẻ
- [ ] Display hiển thị
- [ ] Buttons/encoder hoạt động
- [ ] IR receiver nhận tín hiệu
- [ ] IR transmitter phát tín hiệu

## ⚠️ Cảnh Báo An Toàn

1. **Nguồn điện:** Luôn tắt nguồn trước khi kết nối hardware
2. **Voltage:** Kiểm tra kỹ 3.3V vs 5V
3. **Static:** Sử dụng wrist strap chống tĩnh điện
4. **Polarity:** Kiểm tra cực tính (+/-) trước khi cấp nguồn
5. **Short circuit:** Tránh chạm ngắn mạch các chân GPIO

## 📚 Tài Liệu Tham Khảo

- [Raspberry Pi Pinout](https://pinout.xyz/)
- [RC522 Datasheet](https://www.nxp.com/docs/en/data-sheet/MFRC522.pdf)
- [CC1101 Datasheet](https://www.ti.com/lit/ds/symlink/cc1101.pdf)
- [VS1838B Datasheet](https://www.vishay.com/docs/82459/tsop48.pdf)

---

## 🤖 PCA9685 — 16-Channel PWM Servo Driver

### Wiring to Raspberry Pi 4

| PCA9685 Pin | Raspberry Pi 4 | Physical Pin |
|-------------|---------------|--------------|
| **VCC**     | 3.3 V         | Pin 1        |
| **GND**     | GND           | Pin 6        |
| **SDA**     | GPIO 2 (SDA1) | Pin 3        |
| **SCL**     | GPIO 3 (SCL1) | Pin 5        |
| **V+**      | 5 V *(servo power — see note)* | Pin 2 or 4 |

> **V+** powers the servos, not the PCA9685 chip itself.  
> For more than 2–3 servos, or servos larger than micro-size, use a dedicated 5 V–6 V power supply on V+/GND rather than drawing from the Pi's 5 V rail.

### Enable I2C on the Pi

```bash
sudo raspi-config
# → Interface Options → I2C → Enable → Reboot
```

Or add to `/boot/config.txt` and reboot:
```
dtparam=i2c_arm=on
```

Load the module without rebooting:
```bash
sudo modprobe i2c-dev
```

### Verify Connection

```bash
# List available I2C buses
ls /dev/i2c*

# Scan for devices (requires i2c-tools)
sudo apt install i2c-tools
i2cdetect -y 1
```

PCA9685 default address is **0x40** — you should see `40` in the scan grid.

### I2C Address Selection (multiple PCA9685 boards)

Each chip has six address pins A0–A5 (solder bridge pads):

| Bridged pins | I2C Address |
|-------------|-------------|
| None        | 0x40        |
| A0          | 0x41        |
| A1          | 0x42        |
| A0 + A1     | 0x43        |
| A2          | 0x44        |
| …           | up to 0x4F  |

Up to 62 boards can share one I2C bus.

### Servo Channel Pinout

Each of the 16 channels (0–15) has three pins:

```
PWM  →  Signal wire  (orange / yellow)
V+   →  VCC servo   (red)
GND  →  GND servo   (brown / black)
```

### Software (RaspFlip)

1. Main menu → **option 12 (Servo)**
2. **Option 1** — Detect: scans I2C bus and auto-saves the address
3. **Option 7** — Configure: change bus, address, PWM frequency, pulse range

Default pulse range: **500–2500 µs** (0°–180°).  
For servos using a narrower range (e.g. 1000–2000 µs), update via option 7.
