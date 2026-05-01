# RaspFlip - Raspberry Pi Flipper Zero Alternative

Một dự án mã nguồn mở để biến Raspberry Pi thành thiết bị đa năng tương tự Flipper Zero, phục vụ mục đích học tập về embedded systems, security và penetration testing.

## 🎯 Mục Tiêu Dự Án

- Học về embedded systems và hardware hacking
- Hiểu về các giao thức bảo mật (RFID, NFC, Sub-GHz, IR)
- Thực hành penetration testing một cách có đạo đức
- Xây dựng thiết bị portable cho security research

## ⚠️ Tuyên Bố Trách Nhiệm

Dự án này chỉ phục vụ mục đích **GIÁO DỤC VÀ NGHIÊN CỨU HỢP PHÁP**. Người dùng chịu trách nhiệm tuân thủ luật pháp địa phương khi sử dụng các công cụ này.

## 🚀 Tính Năng Chính

### 1. **RFID/NFC** 
- Đọc và ghi thẻ RFID (125kHz, 13.56MHz)
- Đọc và mô phỏng thẻ NFC
- Phân tích và clone thẻ

### 2. **Sub-GHz Radio**
- Capture và replay tín hiệu RF (433MHz, 315MHz, 868MHz, 915MHz)
- Phân tích remote control, garage door, sensor
- Signal analysis và decoding

### 3. **Infrared (IR)**
- Học và replay tín hiệu IR
- Universal remote control
- Database các mã IR phổ biến

### 4. **GPIO & Hardware Interface**
- GPIO manipulation
- I2C, SPI, UART communication
- Hardware debugging

### 5. **BadUSB**
- Keystroke injection attacks
- Payload automation
- HID device emulation

### 6. **Wi-Fi & Bluetooth**
- Wi-Fi scanning và penetration testing
- Bluetooth LE sniffing
- Wireless attack tools

### 7. **iButton**
- Đọc và clone iButton/Dallas keys
- Access control research

## 📦 Hardware Yêu Cầu

### Thiết Bị Chính:
- **Raspberry Pi 4** (khuyến nghị) hoặc Pi Zero 2 W
- Thẻ microSD tối thiểu 32GB (Class 10)
- Pin di động 5V/3A (power bank)
- Case in 3D hoặc case acrylic

### Module Bổ Sung:
- **RFID Reader**: RC522 (13.56MHz) hoặc RDM6300 (125kHz)
- **NFC Module**: PN532
- **Sub-GHz Module**:   hoặc nRF24L01+
- **IR Transceiver**: VS1838B receiver + IR LED
- **Display**: SSD1306 OLED (128x64) hoặc 2.8" TFT
- **Input**: Rotary encoder hoặc tactile buttons
- **USB-A Port**: Cho BadUSB attacks

## 🛠️ Cài Đặt

### 1. Chuẩn Bị OS
```bash
# Flash Raspberry Pi OS Lite lên thẻ SD
# Hoặc sử dụng script setup tự động
```

### 2. Clone Repository
```bash
git clone https://github.com/your-repo/raspflip.git
cd raspflip
```

### 3. Chạy Setup Script
```bash
sudo chmod +x setup.sh
sudo ./setup.sh
```

### 4. Cấu Hình Hardware
```bash
# Enable SPI, I2C, UART
sudo raspi-config
```

## 📂 Cấu Trúc Dự Án

```
raspflip/
├── docs/              # Tài liệu chi tiết
├── hardware/          # Schematics, PCB designs, 3D models
├── modules/           # Code cho từng module chức năng
│   ├── rfid/         # RFID/NFC module
│   ├── subghz/       # Sub-GHz radio module
│   ├── ir/           # Infrared module
│   ├── badusb/       # BadUSB module
│   ├── gpio/         # GPIO utilities
│   ├── wifi/         # Wi-Fi tools
│   └── bluetooth/    # Bluetooth tools
├── ui/               # User interface (CLI/GUI)
├── scripts/          # Utility scripts
├── payloads/         # BadUSB payloads
├── databases/        # IR codes, RFID dumps, etc.
└── tests/            # Unit tests

```

## 🎓 Tài Liệu Học Tập

- [Hardware Setup Guide](docs/hardware-setup.md)
- [Software Installation](docs/software-installation.md)
- [Module Tutorials](docs/tutorials/)
- [Security Best Practices](docs/security.md)

## 🤝 Đóng Góp

Mọi đóng góp đều được hoan nghênh! Vui lòng đọc [CONTRIBUTING.md](CONTRIBUTING.md) để biết thêm chi tiết.

## 📄 License

MIT License - xem [LICENSE](LICENSE) để biết chi tiết.

## 🔗 Tài Nguyên Tham Khảo

- [Flipper Zero Official](https://flipperzero.one/)
- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [HackRF & SDR Resources](https://greatscottgadgets.com/hackrf/)

## ⭐ Roadmap

- [ ] Phase 1: Setup cơ bản và RFID/NFC
- [ ] Phase 2: Sub-GHz và IR
- [ ] Phase 3: BadUSB và GPIO tools
- [ ] Phase 4: Wi-Fi/Bluetooth pentesting
- [ ] Phase 5: GUI interface
- [ ] Phase 6: Mobile app companion

---

**Made with ❤️ for learning and ethical security research**
