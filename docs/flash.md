# Flash / Chip Memory Module

> Raspberry Pi 4 có thể đọc, ghi, xoá và clone bộ nhớ từ nhiều loại chip khác nhau:
> SPI NOR Flash, STM32 (UART bootloader), AVR/Arduino (ISP), I2C EEPROM.

---

## Tổng Quan

```
modules/flash/__init__.py
├── class SPIFlashTool     — W25Qxx, MX25Lxx, S25FLxx  (via flashrom)
├── class STM32Tool        — STM32Fxxx, STM32Gxxx       (via stm32flash)
├── class AVRTool          — ATmega328P, ATmega2560 …   (via avrdude linuxspi)
├── class I2CEEPROMTool    — AT24Cxx, 24LCxx            (via smbus2)
├── get_tool(target)       — factory function
├── check_tools()          — kiểm tra tools đã cài
└── @dataclass FlashOperation — kết quả mỗi thao tác
```

### CLI — Main Menu → Option 10 → Flash/Chip

20 option: probe / read / write / erase / clone / fuses / I2C scan / check tools.

---

## Cài Tools

```bash
# System tools
sudo apt install flashrom stm32flash avrdude

# Python
pip install smbus2

# Driver RTL8812AU (nếu dùng SPI adapter USB, không cần cho built-in SPI)
sudo apt install dkms
```

Kiểm tra trong CLI: **Flash/Chip → Option 20 — Check installed tools**

---

## Kích Hoạt SPI và I2C

Thêm vào `/boot/config.txt` (hoặc `/boot/firmware/config.txt` trên Raspberry Pi OS Bookworm):

```ini
dtparam=spi=on
dtparam=i2c_arm=on
```

Reboot:

```bash
sudo reboot
# Sau reboot kiểm tra:
ls /dev/spidev0.*   # → /dev/spidev0.0  /dev/spidev0.1
ls /dev/i2c-*       # → /dev/i2c-1
```

Thêm user vào group (không cần sudo mỗi lần):

```bash
sudo usermod -aG spi,i2c,gpio $USER
# logout và login lại để có hiệu lực
```

---

## 1. SPI NOR Flash

### Giới thiệu

SPI NOR Flash là loại bộ nhớ phổ biến nhất trong thiết bị nhúng — router, camera IP, smart TV, IoT.
Dùng để lưu firmware, bootloader, filesystem (JFFS2, SquashFS).

**Ứng dụng pentest:**
- Đọc firmware từ thiết bị (khi không có UART shell)
- Bypass password bằng cách ghi lại firmware đã patch
- Clone thiết bị

### Chip phổ biến

| Chip | Size | Manufacturer | Thiết bị thường gặp |
|---|---|---|---|
| W25Q32 | 4 MB | Winbond | Router nhỏ, MCU dev board |
| W25Q64 | 8 MB | Winbond | Router tầm trung |
| W25Q128 | 16 MB | Winbond | Router cao cấp, camera IP |
| W25Q256 | 32 MB | Winbond | NAS, set-top box |
| MX25L3205D | 4 MB | Macronix | Router Tenda, TP-Link cũ |
| MX25L12805D | 16 MB | Macronix | Nhiều thiết bị IoT |
| S25FL128S | 16 MB | Spansion | Thiết bị công nghiệp |
| GD25Q64 | 8 MB | GigaDevice | Router giá rẻ |

### Pinout — Raspberry Pi 4 ↔ SPI Flash (SOIC-8)

```
Raspberry Pi 4                W25Q32/64/128 (SOIC-8)
──────────────────────        ────────────────────────────
3.3V  (Pin 17)         →      Pin 8 VCC
GND   (Pin 25)         →      Pin 4 GND
GPIO 8  / CE0 (Pin 24) →      Pin 1 CS#   (chip select, active LOW)
GPIO 11 / CLK (Pin 23) →      Pin 6 CLK
GPIO 10 / MOSI(Pin 19) →      Pin 5 DI    (Data In)
GPIO  9 / MISO(Pin 21) →      Pin 2 DO    (Data Out)
3.3V  (Pin 17)         →      Pin 3 WP#   (tie HIGH = write enabled)
3.3V  (Pin 17)         →      Pin 7 HOLD# (tie HIGH = không hold)
```

Sơ đồ SOIC-8 (nhìn từ trên, notch ở trái):

```
      ┌─────────────┐
  CS# │1           8│ VCC
   DO │2           7│ HOLD#
  WP# │3           6│ CLK
  GND │4           5│ DI
      └─────────────┘
```

> **In-circuit reading:** Nếu chip đang hàn trên board, thêm kẹp SOIC-8 clip.
> Đảm bảo **tắt nguồn thiết bị** khi kết nối — xung đột 3.3V có thể hỏng chip hoặc RPi.

### Sử dụng

```python
from modules.flash import SPIFlashTool

tool = SPIFlashTool()

# Detect chip
info = tool.probe()
print(f"{info.name}  {info.flash_size // 1024} KB")

# Read toàn bộ flash
op = tool.read("firmware.bin")

# Ghi firmware mới (erase + write + verify)
op = tool.write("patched_firmware.bin")

# Chỉ erase
op = tool.erase()

# Clone: đọc từ chip A → ghi vào chip B
op = tool.clone("backup.bin")
# Sau đó swap chip và:
op = tool.write("backup.bin")
```

### Lệnh flashrom thủ công

```bash
# Detect
sudo flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=4000

# Read
sudo flashrom -p linux_spi:dev=/dev/spidev0.0 -r firmware.bin

# Write + verify
sudo flashrom -p linux_spi:dev=/dev/spidev0.0 -w patched.bin

# Chỉ định chip nếu auto-detect fail
sudo flashrom -p linux_spi:dev=/dev/spidev0.0 -c W25Q64BV -r firmware.bin

# Erase
sudo flashrom -p linux_spi:dev=/dev/spidev0.0 -E
```

---

## 2. STM32

### Giới thiệu

STM32 là dòng vi điều khiển ARM Cortex-M của STMicroelectronics.
Tất cả STM32 đều có **built-in UART bootloader** ở ROM — không cần JTAG để nạp firmware lần đầu.

**Ứng dụng:**
- Nạp firmware cho STM32 dev board (Blue Pill, Nucleo, …)
- Đọc firmware từ thiết bị có STM32 (nếu read-out protection = Level 0)
- Clone firmware sang chip mới

### Read-Out Protection (RDP)

| Level | Đọc flash | Debugger | Ghi flash | Ghi lại |
|---|---|---|---|---|
| **0** (default) | ✅ | ✅ | ✅ | ✅ |
| **1** | ❌ | ❌ | ✅ (nếu boot từ flash) | ✅ nhưng erase hết |
| **2** | ❌ | ❌ | ❌ | ❌ permanent |

> Level 2 là **không thể phục hồi** — chip bị brick vĩnh viễn nếu tắt JTAG. Không set Level 2 trừ khi biết mình đang làm gì.

### Pinout — Raspberry Pi 4 ↔ STM32 (UART Bootloader)

```
Raspberry Pi 4                STM32
──────────────────────        ─────────────────────────────────────
GPIO 14 / TXD (Pin 8)  →      UART RX  (PA10 trên F103, PA3 trên F4 USART2)
GPIO 15 / RXD (Pin 10) ←      UART TX
GPIO 17       (Pin 11) →      BOOT0    (HIGH = enter bootloader)
GPIO 27       (Pin 13) →      NRST     (active LOW, reset pin)
3.3V          (Pin 17) →      VCC 3.3V
GND           (Pin 25) →      GND
```

> **STM32 Blue Pill** (F103C8T6): BOOT0 là jumper trên board — set jumper 1 (HIGH) để vào bootloader.  
> **Nucleo boards**: có ST-Link tích hợp — có thể dùng UART hoặc ST-Link.

### Bước Kết Nối

```
1. Tắt nguồn STM32
2. Set BOOT0 = HIGH (jumper hoặc kéo chân lên 3.3V)
3. Kết nối GPIO14/15 ↔ STM32 RX/TX (cross-over!)
4. Cấp nguồn STM32
5. Chạy stm32flash hoặc gọi STM32Tool.probe()
6. Sau khi nạp: set BOOT0 = LOW, reset để chạy firmware
```

> **Lưu ý điện áp:** STM32F103 chạy 3.3V I/O — tương thích trực tiếp với RPi 3.3V GPIO.
> STM32F4xx một số pin 5V-tolerant — xem datasheet.

### Sử dụng

```python
from modules.flash import STM32Tool

tool = STM32Tool(port="/dev/serial0", baud=115200)

# Detect (tự động pulse BOOT0 + NRST)
info = tool.probe()
print(f"{info.name}  {info.flash_size // 1024} KB")

# Read firmware
op = tool.read("stm32_firmware.bin")

# Write firmware (.bin hoặc .hex)
op = tool.write("new_firmware.bin", verify=True)

# Mass erase
op = tool.erase()
```

### Lệnh stm32flash thủ công

```bash
# Detect
stm32flash /dev/serial0

# Read 64KB từ địa chỉ flash (0x08000000)
stm32flash -r firmware.bin /dev/serial0

# Write + verify
stm32flash -w firmware.bin -v /dev/serial0

# Nạp và chạy ngay
stm32flash -w firmware.bin -v -g 0x08000000 /dev/serial0

# Mass erase
stm32flash -o /dev/serial0
```

### Kích Hoạt UART trên Raspberry Pi

```bash
# Tắt Bluetooth để lấy lại /dev/serial0 (ttyAMA0)
sudo systemctl disable hciuart
# Thêm vào /boot/config.txt:
# dtoverlay=disable-bt

# Hoặc dùng /dev/ttyS0 (mini UART — ít ổn định hơn)
```

---

## 3. AVR / Arduino

### Giới thiệu

AVR là kiến trúc 8-bit của Atmel (nay thuộc Microchip). Arduino dùng AVR (Uno/Nano = ATmega328P).
Raspberry Pi đóng vai trò **ISP programmer** qua SPI0 — giống USBasp hay AVRISP mkII.

**Ứng dụng:**
- Nạp firmware / bootloader cho Arduino
- Đọc lại firmware từ Arduino (nếu lock bit chưa set)
- Clone Arduino sang chip khác
- Set fuse bytes (clock source, brown-out detection, …)

### AVR MCU Phổ Biến

| MCU | Flash | EEPROM | SRAM | Board phổ biến |
|---|---|---|---|---|
| ATmega328P | 32 KB | 1024 B | 2 KB | Arduino Uno, Nano |
| ATmega2560 | 256 KB | 4096 B | 8 KB | Arduino Mega |
| ATmega32U4 | 32 KB | 1024 B | 2.5 KB | Arduino Leonardo, Micro |
| ATtiny85 | 8 KB | 512 B | 512 B | Digispark |
| ATtiny2313 | 2 KB | 128 B | 128 B | Standalone |

### Pinout — Raspberry Pi 4 ↔ AVR/Arduino (ISP/ICSP)

```
Raspberry Pi 4                Arduino ISP / ICSP Header
──────────────────────        ──────────────────────────
GPIO 10 / MOSI (Pin 19) →     MOSI  (ICSP Pin 4)
GPIO  9 / MISO (Pin 21) ←     MISO  (ICSP Pin 1)
GPIO 11 / SCK  (Pin 23) →     SCK   (ICSP Pin 3)
GPIO 25        (Pin 22) →     RESET (ICSP Pin 5)  active LOW
5V             (Pin  2) →     VCC   (ICSP Pin 2)  ⚠ Arduino cần 5V
GND            (Pin  6) →     GND   (ICSP Pin 6)
```

> **⚠ Điện áp:** Arduino Uno/Nano chạy 5V. RPi GPIO là 3.3V.  
> Kết nối trực tiếp có thể hoạt động nhưng không được khuyến nghị.  
> Giải pháp an toàn: dùng level shifter 3.3V↔5V, hoặc cấp nguồn Arduino ngoài và chỉ nối signal.

ICSP Header trên Arduino (nhìn từ trên, pin 1 có dấu chấm):

```
      ┌─────┐
MISO  │1   2│ VCC
SCK   │3   4│ MOSI
RESET │5   6│ GND
      └─────┘
```

### Fuse Bytes

Fuse bytes điều khiển cấu hình phần cứng của AVR — **không liên quan đến dữ liệu firmware**.

| Fuse | Ý nghĩa quan trọng |
|---|---|
| **LFUSE** | Clock source (internal RC, external crystal, …), clock divider |
| **HFUSE** | Bootloader size, EEPROM preserve khi erase, JTAG enable, SPI enable |
| **EFUSE** | Brown-out detection level |

> **⚠ Nguy hiểm:** Set sai fuse (ví dụ: disable SPI trên HFUSE) → **chip brick**, không thể nạp lại qua ISP.
> Recovery cần High-Voltage Parallel Programming (HVPP) — phức tạp hơn nhiều.

Giá trị mặc định ATmega328P:

```
LFUSE = 0x62  (internal RC 8MHz, /8 divider → 1MHz)
HFUSE = 0xD9  (bootloader 2KB, EEPROM preserve OFF, SPI ON)
EFUSE = 0xFF  (BOD disabled)

Arduino Uno bootloader fuses:
LFUSE = 0xFF  (external crystal 16MHz, full speed)
HFUSE = 0xDE  (bootloader 512 words = 1KB)
EFUSE = 0x05  (BOD 2.7V)
```

### Sử dụng

```python
from modules.flash import AVRTool

tool = AVRTool(mcu="atmega328p")

# Detect chip signature
info = tool.probe()
print(f"{info.name}  sig={info.extra['signature']}")

# Read flash → Intel HEX
op = tool.read_flash("sketch.hex")

# Write firmware
op = tool.write_flash("new_sketch.hex", verify=True)

# Read EEPROM
op = tool.read_eeprom("eeprom.hex")

# Ghi EEPROM
op = tool.write_eeprom("eeprom_new.hex")

# Đọc fuses
fuses = tool.read_fuses()
# {'lfuse': '0xff', 'hfuse': '0xde', 'efuse': '0x05'}
```

### Lệnh avrdude thủ công

```bash
# Detect
sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25

# Read flash
sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 \
    -U flash:r:firmware.hex:i

# Write flash
sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 \
    -U flash:w:firmware.hex:i

# Read fuses
sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 \
    -U lfuse:r:-:h -U hfuse:r:-:h -U efuse:r:-:h

# Write fuses (NGUY HIỂM — double check giá trị trước khi chạy)
sudo avrdude -p atmega328p -c linuxspi:dev=/dev/spidev0.0,reset=25 \
    -U lfuse:w:0xFF:m -U hfuse:w:0xDE:m -U efuse:w:0x05:m
```

---

## 4. I2C EEPROM

### Giới thiệu

I2C EEPROM (AT24Cxx) dùng để lưu dữ liệu cấu hình, calibration, serial number trong thiết bị nhúng.
Không có firmware — chỉ là bộ nhớ byte-addressable đơn giản, **không cần erase trước khi ghi**.

### Chip phổ biến

| Chip | Size | Page size | I2C address |
|---|---|---|---|
| AT24C01 | 128 B | 8 B | 0x50–0x57 |
| AT24C02 | 256 B | 8 B | 0x50–0x57 |
| AT24C32 | 4 KB | 32 B | 0x50–0x57 |
| AT24C256 | 32 KB | 64 B | 0x50–0x57 |
| AT24C512 | 64 KB | 128 B | 0x50–0x51 |

I2C address = `0b1010_A2_A1_A0` — 3 chân address bit trên chip:

```
A2 A1 A0  →  Address
 0  0  0  →  0x50 (default khi nối GND)
 0  0  1  →  0x51
 ...
 1  1  1  →  0x57
```

### Pinout — Raspberry Pi 4 ↔ I2C EEPROM (DIP-8 / SOIC-8)

```
Raspberry Pi 4                AT24Cxx (DIP-8)
──────────────────────        ─────────────────────
GPIO 2 / SDA (Pin 3)  ↔       Pin 5  SDA
GPIO 3 / SCL (Pin 5)  →       Pin 6  SCL
3.3V         (Pin 17) →       Pin 8  VCC
GND          (Pin 25) →       Pin 4  GND
GND          (Pin 25) →       Pin 1  A0 (address bit 0)
GND          (Pin 25) →       Pin 2  A1 (address bit 1)
GND          (Pin 25) →       Pin 3  A2 (address bit 2)
GND          (Pin 25) →       Pin 7  WP (write protect, LOW = enabled)
```

Sơ đồ DIP-8:

```
      ┌─────────────┐
   A0 │1           8│ VCC
   A1 │2           7│ WP
   A2 │3           6│ SCL
  GND │4           5│ SDA
      └─────────────┘
```

> Pull-up resistors: SDA và SCL cần 4.7kΩ lên 3.3V.  
> Raspberry Pi I2C1 đã có pull-up built-in (1.8kΩ) — thường đủ cho khoảng cách ngắn.

### Sử dụng

```python
from modules.flash import I2CEEPROMTool

tool = I2CEEPROMTool(bus=1, address=0x50, chip="AT24C256")

# Scan bus trước khi dùng
addrs = tool.scan_bus()
print([hex(a) for a in addrs])   # [0x50]

# Probe
info = tool.probe()

# Read toàn bộ
op = tool.read("eeprom_dump.bin")

# Write
op = tool.write("new_data.bin")

# Erase (fill 0xFF)
op = tool.erase()
```

### I2C scan thủ công

```bash
# Scan bus 1
i2cdetect -y 1

# Output — địa chỉ 0x50 xuất hiện nếu có EEPROM
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 50: 50 -- -- -- -- -- -- --

# Đọc 8 byte đầu từ 0x50
i2cdump -y 1 0x50 b | head -5
```

---

## 5. Clone Workflow

### SPI Flash Clone

```
[Board A] → tháo chip → kẹp SOIC clip
    ↓
RPi: flashrom -r chip_a.bin
    ↓
tháo kẹp, kẹp vào [Chip B] (blank)
    ↓
RPi: flashrom -w chip_a.bin -v
    ↓
hàn chip B vào [Board B]
```

### STM32 Clone

```
[STM32 A] — BOOT0=HIGH, RESET pulse
    ↓
RPi: stm32flash -r firmware.bin /dev/serial0
    ↓
Swap: tháo STM32 A, cắm STM32 B (blank, RDP=0)
    ↓
RPi: stm32flash -w firmware.bin -v /dev/serial0
    ↓
BOOT0=LOW, RESET → chạy firmware
```

### Arduino Clone

```
[Arduino A] — kết nối ISP
    ↓
RPi: avrdude -U flash:r:fw.hex:i
RPi: avrdude -U eeprom:r:ee.hex:i
RPi: avrdude -U lfuse:r:lf.hex:h  (ghi lại fuses)
    ↓
Swap: cắm ATmega328P mới (blank)
    ↓
RPi: avrdude -U flash:w:fw.hex:i
RPi: avrdude -U eeprom:w:ee.hex:i
RPi: avrdude -U lfuse:w:0xFF:m ...   (set fuses giống chip gốc)
```

---

## 6. Troubleshooting

| Triệu chứng | Nguyên nhân | Giải pháp |
|---|---|---|
| `flashrom: No EEPROM/flash device found` | SPI chưa enable, wiring sai, CS nối ngược | Kiểm tra `/boot/config.txt`, đo CS pin bằng multimeter |
| `flashrom: Chip is in odd write-protected state` | WP# nối GND thay vì 3.3V | Kéo WP# lên 3.3V |
| `stm32flash: Failed to init device` | BOOT0 không HIGH, UART cross-over sai | Kiểm tra TX→RX, RX←TX, đo BOOT0 = 3.3V |
| `avrdude: initialization failed, rc=-1` | SPI/GPIO conflict, RESET chưa đúng | Kiểm tra GPIO 25 = LOW khi reset, đảm bảo không có thiết bị khác dùng SPI |
| `OSError: [Errno 121] Remote I/O error` | EEPROM không phản hồi, địa chỉ sai | Dùng `i2cdetect -y 1`, kiểm tra A0/A1/A2 |
| `smbus2 not installed` | Python package thiếu | `pip install smbus2` |
| Đọc được nhưng toàn `0xFF` | Chip bị erase rồi, hoặc chưa có data | Bình thường cho chip trắng |
| Ghi OK nhưng verify fail | Nguồn 3.3V không đủ dòng | Dùng nguồn ngoài, không dùng RPi 3.3V pin cho chip lớn |

---

## 7. Bảo Mật

| Cơ chế | Chip | Bypass khả năng |
|---|---|---|
| WP# hardware write protect | SPI Flash | Kéo WP# lên HIGH — bypass dễ nếu có thể sờ vào board |
| RDP Level 1 | STM32 | Không đọc flash, nhưng có thể ghi lại (erase hết) |
| RDP Level 2 | STM32 | Không thể bypass — permanent |
| Lock bits | AVR | Không đọc flash nếu set, nhưng HVPP có thể reset |
| Hardware crypto (eFuse burned) | STM32H/L | Key lưu trong eFuse không thể đọc sau khi lock |

---

## 8. Python API Reference

```python
from modules.flash import get_tool, check_tools

# Tạo tool
spi   = get_tool("spi")
stm32 = get_tool("stm32", port="/dev/serial0", baud=115200)
avr   = get_tool("avr", mcu="atmega328p")
i2c   = get_tool("i2c", bus=1, address=0x50, chip="AT24C256")

# FlashOperation result
op = spi.read("dump.bin")
op.success   # bool
op.message   # str
op.file      # str | None
op.size      # int | None  (bytes)

# Kiểm tra tools
status = check_tools()
# {'flashrom': True, 'stm32flash': False, 'avrdude': True, 'smbus2': True}
```

---

## Xem Thêm

- [Hardware Setup Guide](hardware-setup.md)
- [Wi-Fi Pentest Guide](wifi-pentest.md)
- [flashrom Supported Hardware](https://www.flashrom.org/Supported_hardware)
- [stm32flash Documentation](https://sourceforge.net/p/stm32flash/wiki/Home/)
- [avrdude Manual](https://avrdude.nongnu.org/avrdude_toc.html)
- [ATmega328P Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-7810-Automotive-Microcontrollers-ATmega328P_Datasheet.pdf)
- [AT24C256 Datasheet](https://ww1.microchip.com/downloads/en/devicedoc/doc0670.pdf)
