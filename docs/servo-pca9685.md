# PCA9685 — Driver Servo PWM 16 Kênh

## Tổng Quan

PCA9685 là IC điều khiển PWM 16 kênh 12-bit qua giao tiếp I2C, thường dùng để điều khiển servo hobby, ESC, và LED. Chỉ cần 2 chân GPIO (SDA + SCL) dù dùng bao nhiêu kênh.

- **Số kênh:** 16 đầu ra PWM độc lập
- **Độ phân giải:** 12-bit (0–4095 bước)
- **Dải tần số:** 24–1526 Hz (50 Hz cho servo tiêu chuẩn)
- **Địa chỉ I2C:** 0x40 (mặc định) — cấu hình được đến 0x4F qua chân A0–A5
- **Điện áp logic:** 3.3 V hoặc 5 V
- **Nguồn servo (V+):** 4.5 V–6 V (tách biệt với nguồn logic)

---

## Kết Nối Với Raspberry Pi 4

| Chân PCA9685 | Raspberry Pi 4           | Chân vật lý |
|--------------|--------------------------|-------------|
| **VCC**      | 3.3 V                    | Pin 1       |
| **GND**      | GND                      | Pin 6       |
| **SDA**      | GPIO 2 (SDA1)            | Pin 3       |
| **SCL**      | GPIO 3 (SCL1)            | Pin 5       |
| **V+**       | 5 V *(chỉ cấp cho servo)* | Pin 2 hoặc 4 |

> **V+** cấp nguồn cho servo, **không phải** cho chip PCA9685.  
> Nếu dùng nhiều hơn 2–3 servo, hoặc servo cỡ lớn, hãy dùng **nguồn ngoài 5 V–6 V** cho V+/GND thay vì lấy từ nguồn 5 V của Pi để tránh sụt áp.

---

## Bật I2C Trên Raspberry Pi

```bash
sudo raspi-config
# → Interface Options → I2C → Enable → Reboot
```

Hoặc thêm vào `/boot/config.txt` rồi reboot:

```
dtparam=i2c_arm=on
```

Tải module không cần reboot:

```bash
sudo modprobe i2c-dev
```

---

## Kiểm Tra Kết Nối

```bash
# Xem các I2C bus có sẵn
ls /dev/i2c*

# Quét thiết bị (cần cài i2c-tools)
sudo apt install i2c-tools
i2cdetect -y 1
```

Địa chỉ mặc định của PCA9685 là **0x40** — nếu thấy `40` trong bảng scan là kết nối thành công.

---

## Chọn Địa Chỉ I2C (dùng nhiều board)

Mỗi chip có 6 chân địa chỉ A0–A5 (pad hàn trên PCB):

| Chân hàn     | Địa chỉ I2C |
|-------------|-------------|
| Không hàn   | 0x40        |
| A0          | 0x41        |
| A1          | 0x42        |
| A0 + A1     | 0x43        |
| A2          | 0x44        |
| A2 + A0     | 0x45        |
| A2 + A1     | 0x46        |
| A2 + A1 + A0| 0x47        |
| …           | đến 0x4F   |

Một I2C bus có thể mang tối đa 62 board.

---

## Sơ Đồ Chân Servo

Mỗi kênh trong 16 kênh (0–15) có 3 chân:

```
PWM  →  Dây tín hiệu  (cam / vàng)
V+   →  VCC servo     (đỏ)
GND  →  GND servo     (nâu / đen)
```

---

## Bảng Tham Chiếu Độ Rộng Xung

| Góc  | Độ rộng xung (thông thường) |
|------|-----------------------------|
| 0°   | 500 µs                      |
| 90°  | 1500 µs                     |
| 180° | 2500 µs                     |

Một số servo dùng dải hẹp hơn (1000–2000 µs). Điều chỉnh qua tùy chọn 7 trong RaspFlip.

---

## Sử Dụng Trong RaspFlip

Menu chính → **tùy chọn 12 (Servo)**

| Tùy chọn | Chức năng |
|----------|-----------|
| 1 | Dò tìm PCA9685 trên bus I2C (tự lưu địa chỉ) |
| 2 | Đặt góc cho một kênh cụ thể |
| 3 | Quét thử: 0° → 180° → 0° với thanh tiến trình |
| 4 | Căn giữa tất cả 16 kênh về 90° |
| 5 | Tắt tất cả kênh (PWM off, servo thả lỏng) |
| 6 | Đặt nhiều kênh cùng lúc (VD: `0:90 1:45 3:135`) |
| 7 | Cấu hình bus, địa chỉ, tần số, dải xung |

Dải xung mặc định: **500–2500 µs** (0°–180°).  
Nếu servo dùng dải hẹp hơn (VD: 1000–2000 µs), cập nhật qua tùy chọn 7.

---

## Xử Lý Sự Cố

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|-------------|-------------|----------------|
| `No such file /dev/i2c-1` | I2C chưa bật | Chạy `raspi-config` → I2C → Enable |
| `Permission denied` | User không thuộc nhóm `i2c` | `sudo usermod -aG i2c $USER` rồi đăng nhập lại |
| `Remote I/O error` | Sai địa chỉ hoặc không có thiết bị | Chạy tùy chọn 1 (Detect) để tìm đúng địa chỉ |
| Servo không quay | Dải xung không khớp | Thử 1000–2000 µs ở tùy chọn 7 |
| Servo rung / kêu | Tần số PWM sai | Đặt lại 50 Hz ở tùy chọn 7 |
| Servo quay rồi thả lỏng | *(đã sửa)* lỗi `all_off()` khi đóng | Đã được vá trong phiên bản hiện tại |
| Pi reboot khi servo hoạt động | Nguồn servo không đủ | Dùng nguồn ngoài 5 V cho V+ |

