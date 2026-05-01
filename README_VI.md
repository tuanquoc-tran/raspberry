# 🔧 RaspFlip - Raspberry Pi Flipper Zero Alternative

> Xây dựng thiết bị security đa năng từ Raspberry Pi để học về embedded systems, hardware hacking và penetration testing

[English](README.md) | **Tiếng Việt**

---

## 📖 Mục Lục

- [Giới Thiệu](#-giới-thiệu)
- [Tính Năng](#-tính-năng)
- [Hardware Cần Thiết](#-hardware-cần-thiết)
- [Cài Đặt Nhanh](#-cài-đặt-nhanh)
- [Sử Dụng](#-sử-dụng)
- [Tài Liệu](#-tài-liệu)
- [Lưu Ý Quan Trọng](#️-lưu-ý-quan-trọng)

---

## 🎯 Giới Thiệu

**RaspFlip** là dự án mã nguồn mở biến Raspberry Pi thành thiết bị đa năng tương tự Flipper Zero. Mục đích chính là **học tập và nghiên cứu** về:

- 🔌 **Embedded Systems**: Lập trình phần cứng, GPIO, SPI, I2C
- 📡 **RF Communications**: Sub-GHz radio, RFID, NFC, IR
- 🔐 **Security**: Penetration testing, protocol analysis
- 🖥️ **Portable Computing**: Thiết bị di động tự xây dựng

### Tại Sao RaspFlip?

- ✅ **Chi phí thấp**: Rẻ hơn Flipper Zero
- ✅ **Mạnh mẽ hơn**: CPU/RAM mạnh hơn
- ✅ **Mở rộng dễ**: Nhiều GPIO, USB ports
- ✅ **Mã nguồn mở**: Tự do tùy chỉnh
- ✅ **Học tập**: Hiểu sâu về hardware

---

## ⭐ Tính Năng

### 🎴 RFID/NFC
- Đọc và ghi thẻ RFID (125kHz, 13.56MHz)
- Đọc thẻ NFC
- Clone và emulate thẻ
- Phân tích protocols (MIFARE, NTAG, etc.)

### 📻 Sub-GHz Radio
- Capture tín hiệu RF (315/433/868/915 MHz)
- Replay attacks
- Phân tích remote controls
- Garage door openers

### 📡 Infrared
- Học tín hiệu IR từ remote
- Universal remote control
- Database mã IR phổ biến
- Protocol detection

### ⌨️ BadUSB
- Keystroke injection
- HID emulation
- DuckyScript payloads
- (Chỉ Pi Zero)

### 🔧 GPIO Tools
- GPIO manipulation
- I2C/SPI/UART testing
- Hardware debugging
- Protocol sniffing

### 📶 Wi-Fi & Bluetooth (Coming Soon)
- Wi-Fi scanning
- Network pentesting
- Bluetooth LE sniffing
- Wireless attacks

---

## 🛒 Hardware Cần Thiết

### Thiết Bị Chính

| Item | Giá (ước tính) | Ghi chú |
|------|----------------|---------|
| **Raspberry Pi 4** (2GB+) | ~$35-55 | Hoặc Pi Zero 2 W (~$15) |
| **microSD Card** 32GB | ~$10 | Class 10 trở lên |
| **Power Bank** 5V/3A | ~$15 | 10,000mAh+ |
| **Case** | ~$5-10 | In 3D hoặc acrylic |

### Module Phần Cứng

| Module | Giá | Chức năng |
|--------|-----|-----------|
| **RC522 RFID** | ~$2-5 | Đọc thẻ 13.56MHz |
| **PN532 NFC** | ~$8-12 | NFC đọc/ghi |
| **CC1101** | ~$3-6 | Sub-GHz radio |
| **IR LED + Receiver** | ~$1-3 | Infrared |
| **SSD1306 OLED** | ~$5-8 | Display 128x64 |
| **Buttons/Encoder** | ~$2-5 | Input controls |

**Tổng chi phí:** ~$50-100 (tùy module)

### Sơ Đồ Kết Nối

Xem chi tiết trong [docs/hardware-setup.md](docs/hardware-setup.md)

---

## 🚀 Cài Đặt Nhanh

### Bước 1: Chuẩn Bị SD Card

```bash
# 1. Flash Raspberry Pi OS (64-bit) lên microSD
# 2. Enable SSH trong Imager settings
# 3. Boot Raspberry Pi
```

### Bước 2: SSH và Update

```bash
# SSH vào Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y
```

### Bước 3: Clone và Setup

```bash
# Clone repository
git clone https://github.com/your-username/raspflip.git
cd raspflip

# Chạy setup script (mất 5-10 phút)
sudo chmod +x setup.sh
sudo ./setup.sh

# Reboot
sudo reboot
```

### Bước 4: Chạy Application

```bash
cd ~/raspflip
source raspflip-env/bin/activate
sudo $(which python3) main.py
```

**Xem chi tiết:** [docs/quick-start.md](docs/quick-start.md)

---

## 💻 Sử Dụng

### Main Menu

```
╔═══════════════════════════════════════╗
║         RaspFlip v0.1.0              ║
║   Raspberry Pi Security Tool         ║
╚═══════════════════════════════════════╝

┏━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Option ┃ Module      ┃ Description            ┃
┣━━━━━━━━╋━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━━━━━━┫
│ 1      │ RFID/NFC    │ Đọc/ghi thẻ           │
│ 2      │ Sub-GHz     │ RF signal tools       │
│ 3      │ Infrared    │ IR remote control     │
│ 4      │ BadUSB      │ Keystroke injection   │
│ 5      │ GPIO        │ Hardware testing      │
│ 6      │ Wi-Fi       │ Network pentesting    │
│ 7      │ Bluetooth   │ BT scanning           │
│ 8      │ iButton     │ Dallas key reader     │
│ 9      │ Settings    │ Configuration         │
│ 0      │ Exit        │ Thoát                 │
└────────┴─────────────┴────────────────────────┘
```

### Ví Dụ: Đọc Thẻ RFID

```bash
# 1. Chạy RaspFlip
sudo $(which python3) main.py

# 2. Chọn option "1" (RFID/NFC)
# 3. Chọn "Read card"
# 4. Đặt thẻ lên reader
# 5. Thông tin thẻ sẽ hiển thị
```

### Ví Dụ: Học Tín Hiệu IR

```bash
# 1. Chọn option "3" (Infrared)
# 2. Chọn "Learn signal"
# 3. Nhấn nút trên remote control
# 4. Signal được lưu tự động
# 5. Có thể replay sau
```

---

## 📚 Tài Liệu

### Hướng Dẫn Chi Tiết

- 📘 [Quick Start Guide](docs/quick-start.md) - Bắt đầu trong 15 phút
- 🔧 [Hardware Setup](docs/hardware-setup.md) - Kết nối phần cứng
- 💻 [Software Installation](docs/software-installation.md) - Cài đặt chi tiết
- 🔐 [Security Best Practices](docs/security.md) - Sử dụng an toàn

### Code Documentation

- 📁 `modules/rfid/` - RFID/NFC implementation
- 📁 `modules/subghz/` - Sub-GHz radio
- 📁 `modules/ir/` - Infrared
- 📁 `modules/badusb/` - BadUSB/HID
- 📁 `modules/gpio/` - GPIO utilities

### Tools & Scripts

- `scripts/check_hardware.py` - Kiểm tra hardware
- `scripts/setup_badusb.sh` - Setup BadUSB (Pi Zero)
- `payloads/` - Example payloads

---

## ⚠️ Lưu Ý Quan Trọng

### 🔴 Tuyên Bố Trách Nhiệm

**RaspFlip chỉ phục vụ mục đích GIÁO DỤC và NGHIÊN CỨU HỢP PHÁP.**

### ❌ KHÔNG Được Phép:

- ❌ Test trên thiết bị không được phép
- ❌ Truy cập trái phép hệ thống
- ❌ Đánh cắp dữ liệu
- ❌ Gây thiệt hại cho người khác
- ❌ Vi phạm pháp luật

### ✅ Được Phép:

- ✅ Test trên thiết bị của bạn
- ✅ Học tập và nghiên cứu
- ✅ Môi trường lab/isolated
- ✅ Có văn bản cho phép
- ✅ Ethical hacking

### 📜 Tuân Thủ Pháp Luật

- Luật an ninh mạng
- Luật tần số vô tuyến điện
- Luật bảo vệ dữ liệu cá nhân
- Quy định về thiết bị viễn thông

**Xem chi tiết:** [docs/security.md](docs/security.md)

---

## 🤝 Đóng Góp

Contributions được hoan nghênh! 

### Cách Đóng Góp:

1. Fork repository
2. Create branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add feature'`
4. Push: `git push origin feature/amazing`
5. Create Pull Request

**Xem:** [CONTRIBUTING.md](CONTRIBUTING.md)

### Areas Cần Help:

- 🎨 GUI development (PyQt/Tkinter)
- 📱 Mobile app companion
- 🔧 Hardware testing
- 📖 Documentation
- 🌐 Translations
- 🎯 Protocol implementations

---

## 🗺️ Roadmap

### Phase 1: Core Features ✅
- [x] Basic modules (RFID, IR, GPIO)
- [x] CLI interface
- [x] Documentation
- [x] Setup scripts

### Phase 2: Enhancement 🔄
- [ ] GUI interface
- [ ] Display support
- [ ] More protocols
- [ ] Better UX

### Phase 3: Advanced Features
- [ ] Wi-Fi pentesting
- [ ] Bluetooth tools
- [ ] ML signal analysis
- [ ] Mobile app

### Phase 4: Community
- [ ] Cloud integration
- [ ] Payload marketplace
- [ ] Tutorial videos
- [ ] Certification program

---

## 📞 Liên Hệ & Support

- 🐛 **Bug Reports:** [GitHub Issues](../../issues)
- 💬 **Discussions:** [GitHub Discussions](../../discussions)
- 📧 **Email:** project@raspflip.org
- 🔐 **Security:** security@raspflip.org

---

## 📄 License

MIT License - xem [LICENSE](LICENSE) file

**Lưu ý:** License bao gồm điều khoản về ethical use và educational purposes.

---

## 🙏 Credits

### Inspired By:
- [Flipper Zero](https://flipperzero.one/)
- Raspberry Pi Foundation
- Open source security community

### Built With:
- Python 3.9+
- RPi.GPIO
- Rich CLI library
- Love for learning ❤️

---

## ⭐ Star History

Nếu project hữu ích, đừng quên **Star** ⭐ repository!

---

## 🎓 Learning Resources

### Khóa Học Đề Xuất:
- Embedded Systems Programming
- RF Communications
- Security & Pentesting
- Python for Hardware

### Certifications:
- CEH (Certified Ethical Hacker)
- OSCP (Offensive Security)
- CompTIA Security+

### Books:
- "The Hardware Hacker" by Andrew Huang
- "Practical Reverse Engineering"
- "Penetration Testing" by Georgia Weidman

---

## 🚀 Quick Links

- [🏃 Quick Start](docs/quick-start.md)
- [🔧 Hardware Setup](docs/hardware-setup.md)
- [💻 Software Installation](docs/software-installation.md)
- [🔐 Security Guidelines](docs/security.md)
- [📖 Full Documentation](docs/)
- [🤝 Contributing](CONTRIBUTING.md)
- [📊 Project Overview](PROJECT_OVERVIEW.md)

---

<div align="center">

**Made with ❤️ for learning and ethical security research**

⚡ **RaspFlip** - *Your journey into hardware security starts here* ⚡

[Getting Started](docs/quick-start.md) • [Documentation](docs/) • [Community](../../discussions)

</div>

---

## 📸 Screenshots

*Coming soon - thêm screenshots khi đã build hardware*

---

**Happy Learning & Ethical Hacking!** 🎯🔧🚀
