# Quick Start Guide

## 🚀 Bắt Đầu Nhanh

Hướng dẫn này giúp bạn chạy RaspFlip trong 15 phút.

## Bước 1: Chuẩn Bị Phần Cứng (5 phút)

### Yêu Cầu Tối Thiểu:
- ✅ Raspberry Pi 4 (2GB RAM trở lên) hoặc Pi Zero 2 W
- ✅ microSD 32GB (đã flash Raspberry Pi OS)
- ✅ Nguồn điện 5V/3A
- ✅ Kết nối Internet (Wi-Fi hoặc Ethernet)

### Optional Hardware:
- RC522 RFID reader (cho module RFID)
- IR LED + VS1838B receiver (cho module IR)
- Buttons hoặc rotary encoder (cho input)

## Bước 2: Setup OS (5 phút)

### 2.1. Flash OS

1. Tải [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
2. Flash `Raspberry Pi OS (64-bit)` lên microSD
3. Trong Settings:
   - ✅ Enable SSH
   - ✅ Set username: `pi`, password: `raspberry` (hoặc của bạn)
   - ✅ Configure Wi-Fi
4. Boot Raspberry Pi

### 2.2. Kết Nối

```bash
# SSH vào Pi
ssh pi@raspberrypi.local

# Update system
sudo apt update && sudo apt upgrade -y
```

## Bước 3: Install RaspFlip (5 phút)

```bash
# Clone repository
git clone https://github.com/your-username/raspflip.git
cd raspflip

# Run setup script
sudo chmod +x setup.sh
sudo ./setup.sh

# Đợi 5-10 phút để cài đặt
```

### Manual Setup (nếu script fail):

```bash
# Install dependencies
sudo apt install -y python3 python3-pip python3-venv git i2c-tools

# Enable interfaces
sudo raspi-config
# -> Interface Options -> Enable: SPI, I2C, Serial

# Create virtual environment
python3 -m venv raspflip-env
source raspflip-env/bin/activate

# Install Python packages
pip install -r requirements.txt

# Reboot
sudo reboot
```

## Bước 4: First Run

```bash
# Navigate to project
cd ~/raspflip

# Activate virtual environment
source raspflip-env/bin/activate

# Run application
sudo $(which python3) main.py
```

Bạn sẽ thấy menu:

```
╔═══════════════════════════════════════╗
║         RaspFlip v0.1.0              ║
║   Raspberry Pi Security Tool         ║
║                                       ║
║   Educational & Research Use Only     ║
╚═══════════════════════════════════════╝

┏━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Option ┃ Module      ┃ Description                        ┃
┡━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1      │ RFID/NFC    │ Read, write, and emulate cards     │
│ 2      │ Sub-GHz     │ Capture and replay RF signals      │
│ 3      │ Infrared    │ Learn and replay IR signals        │
│ 4      │ BadUSB      │ Keystroke injection attacks        │
│ 5      │ GPIO        │ GPIO manipulation and testing      │
│ 6      │ Wi-Fi       │ Wi-Fi scanning and pentesting      │
│ 7      │ Bluetooth   │ Bluetooth scanning and analysis    │
│ 8      │ iButton     │ Read and clone iButton keys        │
│ 9      │ Settings    │ Configure hardware and software    │
│ 0      │ Exit        │ Exit RaspFlip                      │
└────────┴─────────────┴────────────────────────────────────┘
```

## Bước 5: Test Hardware

### Verify Hardware Setup:

```bash
# Check hardware status
python3 scripts/check_hardware.py
```

Output sẽ hiển thị:

```
==================================================
  RaspFlip Hardware Checker
==================================================

[*] Checking SPI...
  ✓ /dev/spidev0.0 found
  ✓ /dev/spidev0.1 found

[*] Checking I2C...
  ✓ /dev/i2c-1 found
  ✓ Found 2 I2C device(s):
    - 0x3C
    - 0x48

[*] Checking GPIO...
  ✓ GPIO library working

[*] Checking RFID (RC522)...
  ✓ RC522 module initialized

[*] Checking LIRC (Infrared)...
  ✗ /dev/lirc0 not found

...

==================================================
  Summary
==================================================
  SPI                 : ✓ OK
  I2C                 : ✓ OK
  GPIO                : ✓ OK
  RFID                : ✓ OK
  LIRC                : ✗ FAIL
  ...
==================================================
```

## 📖 Quick Tutorials

### Tutorial 1: Read RFID Card

1. Kết nối RC522 theo [hardware-setup.md](hardware-setup.md)
2. Chạy RaspFlip: `sudo $(which python3) main.py`
3. Chọn `1` (RFID/NFC)
4. Chọn `1` (Read card)
5. Đặt thẻ RFID lên reader
6. Kết quả sẽ hiển thị UID và data

### Tutorial 2: Learn IR Remote

1. Kết nối IR receiver theo [hardware-setup.md](hardware-setup.md)
2. Chạy RaspFlip
3. Chọn `3` (Infrared)
4. Chọn `1` (Learn signal)
5. Nhấn nút trên remote control
6. Signal được lưu tự động

### Tutorial 3: Test GPIO

1. Chạy RaspFlip
2. Chọn `5` (GPIO)
3. Chọn các option để test input/output pins

## 🔧 Troubleshooting

### Issue: "Permission denied"

```bash
# Add user to necessary groups
sudo usermod -a -G gpio,i2c,spi,dialout $USER

# Logout and login again
```

### Issue: "SPI not found"

```bash
# Enable SPI
sudo raspi-config nonint do_spi 0
sudo reboot
```

### Issue: "Module import error"

```bash
# Ensure virtual environment is activated
source raspflip-env/bin/activate

# Reinstall packages
pip install --upgrade -r requirements.txt
```

### Issue: "No hardware detected"

1. Check wiring connections
2. Verify pins in config
3. Run diagnostics: `python3 scripts/check_hardware.py`
4. Check power supply (should be 5V/3A)

## 📚 Next Steps

1. **Read Full Documentation:**
   - [Hardware Setup Guide](hardware-setup.md)
   - [Software Installation](software-installation.md)
   - [Security Best Practices](security.md)

2. **Connect More Hardware:**
   - Add RFID reader
   - Add IR transceiver
   - Add display and buttons

3. **Explore Modules:**
   - Try different RFID cards
   - Capture IR remote signals
   - Test GPIO pins

4. **Learn Security:**
   - Study RFID protocols
   - Understand RF signals
   - Practice ethical hacking

5. **Contribute:**
   - Report bugs
   - Add features
   - Improve documentation
   - Share your builds

## 💡 Pro Tips

1. **Always backup**: Git commit before major changes
2. **Test in VM**: Test dangerous payloads in virtual machines
3. **Use logs**: Check `logs/` for debugging
4. **Join community**: Get help from other users
5. **Stay legal**: Only test on your own devices

## 🆘 Get Help

- **Documentation:** `docs/` folder
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions
- **Discord:** [Join our server]

## ✅ Checklist

- [ ] OS installed and updated
- [ ] RaspFlip cloned and setup completed
- [ ] Virtual environment activated
- [ ] Hardware interfaces enabled (SPI, I2C)
- [ ] Hardware check passed
- [ ] First run successful
- [ ] Read documentation
- [ ] Understand ethical guidelines

## 🎉 You're Ready!

Chúc mừng! Bạn đã sẵn sàng sử dụng RaspFlip.

Remember: **Use responsibly and ethically!** 🛡️

---

**Happy Hacking!** 🚀
