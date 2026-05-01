# Software Installation Guide

## 🚀 Hướng Dẫn Cài Đặt Phần Mềm

### Yêu Cầu Hệ Thống

- **Raspberry Pi:** Pi 4 Model B (khuyến nghị) hoặc Pi Zero 2 W
- **OS:** Raspberry Pi OS (64-bit khuyến nghị)
- **microSD:** Tối thiểu 32GB Class 10
- **RAM:** Tối thiểu 2GB (Pi 4)
- **Kết nối:** Internet để tải packages

## Bước 1: Chuẩn Bị OS

### 1.1. Flash Raspberry Pi OS

**Sử dụng Raspberry Pi Imager:**

1. Tải [Raspberry Pi Imager](https://www.raspberrypi.org/software/)
2. Chọn OS: `Raspberry Pi OS (64-bit)` hoặc `Raspberry Pi OS Lite`
3. Chọn storage: Thẻ microSD của bạn
4. Settings (gear icon):
   - Enable SSH
   - Set username/password
   - Configure Wi-Fi (nếu cần)
   - Set locale
5. Write

### 1.2. First Boot

```bash
# SSH vào Raspberry Pi
ssh pi@raspberrypi.local
# hoặc
ssh pi@<IP_ADDRESS>

# Update system
sudo apt update
sudo apt upgrade -y

# Reboot
sudo reboot
```

## Bước 2: Enable Hardware Interfaces

```bash
# Mở raspi-config
sudo raspi-config

# Enable các interface sau:
# Interface Options →
#   - SPI: Enable
#   - I2C: Enable
#   - Serial Port: Enable (login shell: No, serial hardware: Yes)
#   - 1-Wire: Enable (nếu dùng iButton)

# Performance Options →
#   - GPU Memory: 128MB (nếu dùng display)

# Finish và reboot
sudo reboot
```

## Bước 3: Clone Repository

```bash
# Cài đặt git (nếu chưa có)
sudo apt install -y git

# Clone project
cd ~
git clone https://github.com/your-username/raspflip.git
cd raspflip
```

## Bước 4: Run Setup Script

```bash
# Make script executable
chmod +x setup.sh

# Run setup (requires sudo)
sudo ./setup.sh
```

**Setup script sẽ:**
- Cài đặt system dependencies
- Enable hardware interfaces
- Tạo Python virtual environment
- Cài đặt Python packages
- Tạo directories cần thiết
- Setup permissions

## Bước 5: Manual Configuration (Nếu Cần)

### 5.1. Cài Đặt Dependencies Thủ Công

```bash
# System packages
sudo apt install -y \
    python3 python3-pip python3-venv \
    i2c-tools libnfc-bin libnfc-dev \
    libusb-1.0-0-dev libpcsclite-dev pcscd \
    lirc bluetooth bluez bluez-tools rfkill \
    build-essential cmake

# Enable SPI
sudo raspi-config nonint do_spi 0

# Enable I2C
sudo raspi-config nonint do_i2c 0

# Enable Serial
sudo raspi-config nonint do_serial 0
```

### 5.2. Python Virtual Environment

```bash
# Create venv
python3 -m venv raspflip-env

# Activate
source raspflip-env/bin/activate

# Install packages
pip install --upgrade pip
pip install -r requirements.txt
```

## Bước 6: Hardware-Specific Setup

### 6.1. RFID/NFC

```bash
# Test SPI
ls /dev/spi*
# Should show: /dev/spidev0.0 /dev/spidev0.1

# Test I2C
i2cdetect -y 1
# Should show connected I2C devices
```

### 6.2. LIRC (Infrared)

```bash
# Install LIRC
sudo apt install -y lirc

# Edit /etc/lirc/lirc_options.conf
sudo nano /etc/lirc/lirc_options.conf
# Set:
#   driver = default
#   device = /dev/lirc0

# Edit /boot/config.txt
sudo nano /boot/config.txt
# Add:
#   dtoverlay=gpio-ir,gpio_pin=23
#   dtoverlay=gpio-ir-tx,gpio_pin=18

# Reboot
sudo reboot

# Test
mode2 -d /dev/lirc0
# Point IR remote at receiver and press buttons
```

### 6.3. BadUSB (Raspberry Pi Zero Only)

```bash
# Run BadUSB setup script
sudo bash scripts/setup_badusb.sh

# Reboot
sudo reboot

# Test
ls /dev/hidg*
# Should show: /dev/hidg0
```

### 6.4. Bluetooth

```bash
# Install BlueZ tools
sudo apt install -y bluetooth bluez bluez-tools

# Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Test
hciconfig
bluetoothctl
```

## Bước 7: Verify Installation

```bash
# Activate virtual environment
source raspflip-env/bin/activate

# Run diagnostics
python3 scripts/check_hardware.py

# Should show status of all hardware modules
```

## Bước 8: First Run

```bash
# Activate virtual environment
source raspflip-env/bin/activate

# Run with sudo (some features require root)
sudo $(which python3) main.py

# Or without sudo (limited features)
python3 main.py
```

## 📝 Configuration Files

### config.yaml (Tạo file này)

```yaml
# RaspFlip Configuration

hardware:
  rfid:
    enabled: true
    type: rc522  # rc522 or pn532
    
  subghz:
    enabled: false
    default_frequency: 433.92
    
  ir:
    enabled: true
    rx_pin: 23
    tx_pin: 18
    
  badusb:
    enabled: false  # Only on Pi Zero
    
  display:
    enabled: false
    type: ssd1306  # ssd1306 or tft

logging:
  level: INFO
  file: logs/raspflip.log

paths:
  dumps: dumps/
  captures: captures/
  payloads: payloads/
  databases: databases/
```

## 🔧 Troubleshooting

### Issue: SPI not working

```bash
# Check if SPI is enabled
lsmod | grep spi
# Should show: spi_bcm2835

# Enable manually
sudo raspi-config nonint do_spi 0
sudo reboot
```

### Issue: I2C device not detected

```bash
# Check I2C modules
lsmod | grep i2c
# Should show: i2c_bcm2835

# Scan I2C bus
i2cdetect -y 1

# Check wiring and power
```

### Issue: Permission denied on GPIO

```bash
# Add user to gpio group
sudo usermod -a -G gpio $USER

# Logout and login again
```

### Issue: Python module import errors

```bash
# Ensure virtual environment is activated
source raspflip-env/bin/activate

# Reinstall requirements
pip install --upgrade -r requirements.txt
```

## 📚 Additional Resources

- [Raspberry Pi Documentation](https://www.raspberrypi.org/documentation/)
- [Python GPIO Library](https://sourceforge.net/projects/raspberry-gpio-python/)
- [LIRC Documentation](https://www.lirc.org/)
- [NFC Tools](https://nfctools.github.io/)

## ✅ Quick Start Commands

```bash
# Daily workflow:

# 1. Connect to Pi
ssh pi@raspberrypi.local

# 2. Navigate to project
cd ~/raspflip

# 3. Activate environment
source raspflip-env/bin/activate

# 4. Update code (if needed)
git pull

# 5. Run application
sudo $(which python3) main.py

# 6. Exit
# Press Ctrl+C then exit terminal
```

## 🔄 Update RaspFlip

```bash
cd ~/raspflip
git pull
source raspflip-env/bin/activate
pip install --upgrade -r requirements.txt
```
