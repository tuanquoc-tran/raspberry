#!/bin/bash

# RaspFlip Setup Script
# This script sets up the Raspberry Pi environment for RaspFlip

set -e

echo "================================"
echo "  RaspFlip Setup Script"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "[1/8] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install system dependencies
echo "[2/8] Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    i2c-tools \
    libnfc-bin \
    libnfc-dev \
    libusb-1.0-0-dev \
    libpcsclite-dev \
    pcscd \
    lirc \
    bluetooth \
    bluez \
    bluez-tools \
    rfkill \
    build-essential \
    cmake

# Enable hardware interfaces
echo "[3/8] Enabling hardware interfaces..."
raspi-config nonint do_spi 0
raspi-config nonint do_i2c 0
raspi-config nonint do_serial 0
raspi-config nonint do_ssh 0

# Create virtual environment
echo "[4/8] Creating Python virtual environment..."
python3 -m venv raspflip-env
source raspflip-env/bin/activate

# Install Python dependencies
echo "[5/8] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "[6/8] Creating project directories..."
mkdir -p logs
mkdir -p dumps
mkdir -p captures
mkdir -p payloads/badusb
mkdir -p databases/ir
mkdir -p databases/rfid
mkdir -p tmp

# Set permissions
echo "[7/8] Setting up permissions..."
usermod -a -G dialout,gpio,i2c,spi,bluetooth pi
chmod +x scripts/*.sh 2>/dev/null || true

# Configure services
echo "[8/8] Configuring services..."
# Add user to necessary groups
groups pi | grep -q gpio || usermod -a -G gpio pi
groups pi | grep -q i2c || usermod -a -G i2c pi
groups pi | grep -q spi || usermod -a -G spi pi

echo ""
echo "================================"
echo "  Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Reboot your Raspberry Pi: sudo reboot"
echo "2. Activate virtual environment: source raspflip-env/bin/activate"
echo "3. Run the main application: python3 main.py"
echo ""
echo "Hardware setup guide: docs/hardware-setup.md"
echo ""
