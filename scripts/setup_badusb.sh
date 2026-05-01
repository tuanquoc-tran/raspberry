#!/bin/bash

# BadUSB Setup Script for Raspberry Pi Zero
# This configures the Pi Zero as a USB HID gadget

set -e

echo "================================"
echo "  BadUSB Setup Script"
echo "  For Raspberry Pi Zero W/2W"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if running on Pi Zero
PI_MODEL=$(cat /proc/cpuinfo | grep Model | cut -d ':' -f 2 | xargs)
if [[ ! "$PI_MODEL" =~ "Zero" ]]; then
    echo "Warning: This script is designed for Raspberry Pi Zero"
    echo "Current model: $PI_MODEL"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "[1/6] Enabling USB OTG in config.txt..."
if ! grep -q "dtoverlay=dwc2" /boot/config.txt; then
    echo "dtoverlay=dwc2" >> /boot/config.txt
    echo "  ✓ Added dtoverlay=dwc2"
else
    echo "  - Already configured"
fi

echo "[2/6] Adding modules to load at boot..."
if ! grep -q "dwc2" /etc/modules; then
    echo "dwc2" >> /etc/modules
    echo "  ✓ Added dwc2"
fi

if ! grep -q "libcomposite" /etc/modules; then
    echo "libcomposite" >> /etc/modules
    echo "  ✓ Added libcomposite"
fi

echo "[3/6] Creating USB gadget configuration script..."
cat > /usr/local/bin/usb_gadget_hid << 'EOF'
#!/bin/bash
# USB HID Gadget Configuration

cd /sys/kernel/config/usb_gadget/
mkdir -p raspflip
cd raspflip

# USB Device Descriptor
echo 0x1d6b > idVendor  # Linux Foundation
echo 0x0104 > idProduct # Multifunction Composite Gadget
echo 0x0100 > bcdDevice # v1.0.0
echo 0x0200 > bcdUSB    # USB 2.0

# USB Strings
mkdir -p strings/0x409
echo "fedcba9876543210" > strings/0x409/serialnumber
echo "RaspFlip Project" > strings/0x409/manufacturer
echo "RaspFlip HID" > strings/0x409/product

# USB Configuration
mkdir -p configs/c.1/strings/0x409
echo "Config 1: HID" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# HID Function (Keyboard)
mkdir -p functions/hid.usb0
echo 1 > functions/hid.usb0/protocol # Keyboard
echo 1 > functions/hid.usb0/subclass # Boot Interface Subclass
echo 8 > functions/hid.usb0/report_length

# HID Report Descriptor (Keyboard)
echo -ne \\x05\\x01\\x09\\x06\\xa1\\x01\\x05\\x07\\x19\\xe0\\x29\\xe7\\x15\\x00\\x25\\x01\\x75\\x01\\x95\\x08\\x81\\x02\\x95\\x01\\x75\\x08\\x81\\x03\\x95\\x05\\x75\\x01\\x05\\x08\\x19\\x01\\x29\\x05\\x91\\x02\\x95\\x01\\x75\\x03\\x91\\x03\\x95\\x06\\x75\\x08\\x15\\x00\\x25\\x65\\x05\\x07\\x19\\x00\\x29\\x65\\x81\\x00\\xc0 > functions/hid.usb0/report_desc

# Link function to configuration
ln -s functions/hid.usb0 configs/c.1/

# Enable gadget
ls /sys/class/udc > UDC

echo "USB HID Gadget configured"
EOF

chmod +x /usr/local/bin/usb_gadget_hid

echo "[4/6] Creating systemd service..."
cat > /etc/systemd/system/usb-gadget-hid.service << EOF
[Unit]
Description=USB HID Gadget
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/usb_gadget_hid
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[5/6] Enabling service..."
systemctl daemon-reload
systemctl enable usb-gadget-hid.service

echo "[6/6] Setting up udev rules..."
cat > /etc/udev/rules.d/99-hidg.rules << EOF
KERNEL=="hidg0", MODE="0666", GROUP="plugdev"
EOF

echo ""
echo "================================"
echo "  Setup Complete!"
echo "================================"
echo ""
echo "IMPORTANT: You must reboot for changes to take effect."
echo ""
echo "After reboot:"
echo "  1. Connect Pi Zero to computer via USB data port (not power port)"
echo "  2. Pi will appear as a USB keyboard"
echo "  3. Run: sudo python3 main.py"
echo "  4. Select BadUSB module"
echo ""
echo "Reboot now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    reboot
fi
