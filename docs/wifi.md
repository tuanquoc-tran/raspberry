# Wi-Fi Module

> **Yêu cầu:** Hầu hết các thao tác cần quyền `root` (`sudo`) vì kernel không cho phép
> user thường thực hiện scan hoặc thay đổi trạng thái interface.

---

## Hardware — BCM43455 (Raspberry Pi 4 built-in)

| Thông số | Giá trị |
|---|---|
| Chip | Cypress/Broadcom BCM43455 |
| Interface | `wlan0` |
| Bands | 2.4 GHz (802.11b/g/n) + 5 GHz (802.11a/n/ac) |
| Monitor mode | ❌ **Không hỗ trợ** |
| Packet injection | ❌ Không hỗ trợ |
| Supported modes | managed, AP, IBSS, P2P-client, P2P-GO |
| Ciphers | WEP40, WEP104, TKIP, CCMP-128, CMAC |

> **Tại sao không có monitor mode?**  
> BCM43455 dùng firmware độc quyền của Broadcom. Driver `brcmfmac` không expose
> monitor mode. Để có monitor mode/injection cần USB adapter ngoài (ví dụ: Alfa AWUS036ACH
> với chip RTL8812AU hoặc AR9271).

---

## Cấu Trúc Module

```
modules/wifi/__init__.py
├── class Network          — dữ liệu một BSS (AP)
├── class InterfaceInfo    — trạng thái interface
├── class WiFiManager      — API chính
│   ├── interface_up()
│   ├── interface_down()
│   ├── scan()
│   ├── get_interface_info()
│   ├── get_network_info()
│   ├── get_connection_status()
│   ├── list_saved_networks()
│   ├── connect()
│   ├── disconnect()
│   ├── get_capabilities()
│   ├── monitor_signal()
│   └── channel_analysis()
├── signal_to_quality()    — dBm → label
└── encryption_risk()      — mức rủi ro bảo mật
```

---

## RF-Kill

Raspberry Pi có hardware RF-kill switch (có thể bị kích hoạt qua software).
Khi `wlan0` không thể up, kiểm tra:

```bash
rfkill list
# 0: phy0: Wireless LAN
#    Soft blocked: yes   ← software block, có thể unblock
#    Hard blocked: no    ← hardware switch

sudo rfkill unblock wifi
sudo ip link set wlan0 up
```

Module tự động xử lý soft-block trong `interface_up()`. Hard-block phải giải quyết thủ công.

---

## Scan Networks

```python
from modules.wifi import WiFiManager, signal_to_quality, encryption_risk

mgr = WiFiManager('wlan0')
networks = mgr.scan()   # yêu cầu sudo

for n in networks:
    print(f"{n.ssid:20} {n.bssid}  ch{n.channel:3}  {n.signal_dbm} dBm  {n.encryption}")
```

### Cấu trúc `Network`

| Field | Kiểu | Mô tả |
|---|---|---|
| `bssid` | str | MAC address của AP |
| `ssid` | str | Tên mạng |
| `channel` | int | Kênh (1-13 cho 2.4GHz, 36-165 cho 5GHz) |
| `frequency_ghz` | float | Tần số GHz |
| `band` | str | `'2.4GHz'` hoặc `'5GHz'` |
| `signal_dbm` | int | Cường độ tín hiệu (dBm, càng gần 0 càng tốt) |
| `quality_pct` | int | Chất lượng 0-100% |
| `encryption` | str | `Open` / `WEP` / `WPA` / `WPA2` / `WPA2/WPA3` / `WPA3` |
| `cipher` | str | `CCMP` / `TKIP` / `TKIP/CCMP` |
| `auth` | str | `PSK` / `SAE` / `Enterprise` |

---

## Tín Hiệu Wi-Fi (dBm)

Đây là thang đo **logarithmic** (decibel-milliwatt):

$$P_{dBm} = 10 \cdot \log_{10}\left(\frac{P_{mW}}{1 \text{ mW}}\right)$$

| dBm | Chất lượng | Ghi chú |
|---|---|---|
| ≥ −50 | Excellent | Rất gần AP, ~1m |
| −50 → −60 | Good | Dùng tốt cho video streaming |
| −60 → −70 | Fair | Dùng được cho web, chat |
| −70 → −80 | Weak | Kết nối không ổn định |
| < −80 | Very Weak | Gần như mất kết nối |

---

## Bảo Mật Encryption

| Loại | Rủi ro | Lý do |
|---|---|---|
| **Open** | 🔴 CRITICAL | Không mã hoá, bất kỳ ai cũng nghe được traffic |
| **WEP** | 🔴 HIGH | Bị crack trong < 60 giây (aircrack-ng, RC4 flaw) |
| **WPA (TKIP)** | 🟡 MEDIUM | TKIP bị Beck-Tews attack, dễ bị MITM |
| **WPA2 (CCMP)** | 🟢 LOW | AES-CCMP an toàn với password mạnh |
| **WPA2/WPA3** | 🟢 LOW | Transition mode — vẫn chấp nhận WPA2 |
| **WPA3 (SAE)** | 🟢 VERY LOW | SAE chống offline dictionary attack |

### Tại sao WEP không an toàn?

WEP dùng RC4 với IV 24-bit (chỉ ~16 triệu giá trị). Sau ~5000-10000 gói, IV bị lặp
(birthday paradox) → attacker có thể giải mã keystream → phá key trong vài phút.

---

## Channel — Chọn Kênh Ít Nhiễu

### 2.4 GHz

Chỉ có **3 kênh không overlap**: 1, 6, 11.

```
Ch 1  ████████████
Ch 2    ████████████
Ch 3      ████████████
Ch 4        ████████████
Ch 5          ████████████
Ch 6            ████████████  ← non-overlapping
Ch 7              ████████████
...
Ch 11                       ████████████  ← non-overlapping
```

> Nếu hàng xóm dùng Ch 1 và Ch 6, chọn **Ch 11** cho AP của bạn.

### 5 GHz

Có nhiều kênh hơn, ít nhiễu hơn nhưng range ngắn hơn (~60% so với 2.4GHz).
Các kênh DFS (52-144) cần radar detection (không dùng được mọi nơi).

---

## Phân Tích Channel (ví dụ từ scan thực tế)

Từ scan trong môi trường thực:

```
Channel  APs  SSIDs
1        3    Minh Thu, Boeing Home, Boeing Home
34       1    (current channel)
```

→ Kênh 1 đang bị dùng bởi 3 AP — **tránh kênh 1**, chuyển sang kênh 6 hoặc 11.

---

## Interface Info

```python
info = mgr.get_interface_info()
print(f"MAC: {info.mac}")
print(f"State: {info.state}")         # UP | DOWN
print(f"SSID: {info.ssid}")
print(f"Signal: {info.signal_dbm} dBm")
print(f"Bitrate: {info.bitrate_mbps} Mb/s")
print(f"IP: {info.ip}")
```

---

## Signal Monitor

```python
# Đọc 20 lần, mỗi 0.5s
readings = mgr.monitor_signal(interval=0.5, count=20)
for r in readings:
    print(f"{r['signal_dbm']} dBm  {r['bitrate_mbps']} Mb/s")
```

---

## Kết Nối (wpa_supplicant)

```python
# WPA2
mgr.connect('MySSID', 'mypassword')

# Open
mgr.connect('FreeWifi', password=None)

# Kiểm tra trạng thái sau vài giây
import time; time.sleep(3)
status = mgr.get_connection_status()
print(status.get('wpa_state'))   # COMPLETED = kết nối thành công
```

---

## AP Mode

Raspberry Pi 4 hỗ trợ AP mode qua `hostapd`. Module hiện chưa implement trực tiếp
nhưng có thể dùng lệnh hệ thống:

```bash
# Cài hostapd và dnsmasq
sudo apt install hostapd dnsmasq

# Cấu hình /etc/hostapd/hostapd.conf
interface=wlan0
ssid=RaspFlip-AP
hw_mode=g
channel=6
wpa=2
wpa_passphrase=yourpassword
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
```

---

## Yêu Cầu Hệ Thống

| Tool | Package | Dùng cho |
|---|---|---|
| `iw` | `iw` | Interface info, capabilities |
| `iwlist` | `wireless-tools` | Scan |
| `iwconfig` | `wireless-tools` | Signal, bitrate |
| `ip` | `iproute2` | IP address, routing |
| `rfkill` | `rfkill` | RF kill management |
| `wpa_cli` | `wpasupplicant` | Connection management |
| `resolvectl` | `systemd` | DNS info |

```bash
sudo apt install iw wireless-tools iproute2 rfkill wpasupplicant
```

---

## Xem Thêm

- [Wi-Fi Frame & Connection Internals](wifi-frames.md) — 802.11 frame, 4-way handshake, AES-CCMP
- [Hardware Setup Guide](hardware-setup.md)
- [Security Best Practices](security.md)
- [Aircrack-ng Project](https://www.aircrack-ng.org/) — yêu cầu adapter có monitor mode
- [IEEE 802.11-2020 Standard](https://standards.ieee.org/ieee/802.11/7028/)
