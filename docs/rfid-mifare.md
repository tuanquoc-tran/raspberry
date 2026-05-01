# RFID/NFC — MIFARE Classic 1K

## Cấu Trúc Vật Lý Của Thẻ

Mỗi thẻ RFID là một **chip bán dẫn** được nhúng trong lớp nhựa, gồm hai thành phần:

```
┌─────────────────────────────────┐
│          Thẻ nhựa               │
│                                 │
│   ┌──────────┐   ┌──────────┐  │
│   │  Antenna │   │   Chip   │  │
│   │ (cuộn dây)│──│ EEPROM   │  │
│   │          │   │ 1024 byte│  │
│   └──────────┘   └──────────┘  │
└─────────────────────────────────┘
```

| Thành phần | Mô tả |
|---|---|
| **Antenna** | Cuộn dây thu năng lượng từ sóng 13.56 MHz của RC522 |
| **Chip** | Vi xử lý nhỏ xử lý authentication và mã hoá |
| **EEPROM** | Bộ nhớ flash 1 KB lưu dữ liệu — không cần pin, giữ nguyên vĩnh viễn |

> Thẻ **không có pin**. Toàn bộ điện năng được cảm ứng từ từ trường của reader.
> Khi rời khỏi reader, chip mất điện nhưng EEPROM vẫn giữ nguyên dữ liệu.

---

## Cấu Trúc Bộ Nhớ MIFARE Classic 1K

```
1024 bytes tổng
├── 16 Sectors (sector 0 → 15)
│   └── mỗi sector có 4 Blocks
│       └── mỗi block có 16 bytes
│
│   = 16 × 4 × 16 = 1024 bytes
```

### Sơ đồ chi tiết

```
Sector 0  ┌─ Block  0  │ 16 bytes │ ← Manufacturer data (READ ONLY, chứa UID)
          ├─ Block  1  │ 16 bytes │ ← Data
          ├─ Block  2  │ 16 bytes │ ← Data
          └─ Block  3  │ 16 bytes │ ← Sector Trailer (Key A | Access bits | Key B)

Sector 1  ┌─ Block  4  │ 16 bytes │ ← Data
          ├─ Block  5  │ 16 bytes │ ← Data
          ├─ Block  6  │ 16 bytes │ ← Data
          └─ Block  7  │ 16 bytes │ ← Sector Trailer
...
Sector 15 ┌─ Block 60  │ 16 bytes │
          ├─ Block 61  │ 16 bytes │
          ├─ Block 62  │ 16 bytes │
          └─ Block 63  │ 16 bytes │ ← Sector Trailer
```

### Công thức tính block

$$\text{block} = \text{sector} \times 4 + \text{offset}$$

Sector trailer = block offset thứ 3: $\text{sector} \times 4 + 3$

### Loại block

| Loại | Vị trí | Nội dung | Ghi được? |
|---|---|---|---|
| **Manufacturer block** | Block 0 | UID + chip info | ❌ Không (thẻ thường) |
| **Data block** | Còn lại | Dữ liệu tuỳ ý | ✅ Cần authenticate trước |
| **Sector Trailer** | Block 3, 7, 11, 15... | Key A + Access bits + Key B | ⚠️ Cẩn thận — sai là mất access |

---

## Sector Trailer

Mỗi sector trailer (16 bytes) có cấu trúc:

```
[Key A — 6 bytes] [Access bits — 4 bytes] [Key B — 6 bytes]
```

### Key mặc định (thẻ mới xuất xưởng)

```
Key A = FF FF FF FF FF FF
Key B = FF FF FF FF FF FF
```

> **Cảnh báo bảo mật:** Nếu dùng thẻ cho access control thực tế, **bắt buộc phải đổi key** sang giá trị bí mật. Thẻ dùng key mặc định có thể bị đọc/ghi bởi bất kỳ reader nào.

### Access bits mặc định

`FF 07 80 69` — đây là default condition của thẻ mới, cho phép đọc/ghi với cả Key A và Key B.

---

## Block 0 — Manufacturer Data

```
E5 72 0B 53 | CF | 08 | 04 00 | 62 63 64 65 66 67 68 69
└─── UID ──┘  BCC  SAK  ATQA    └────── Manufacturer ────┘
```

| Field | Bytes | Ý nghĩa |
|---|---|---|
| **UID** | 4 bytes (offset 0-3) | Số định danh duy nhất của thẻ |
| **BCC** | 1 byte (offset 4) | Checksum = XOR của 4 byte UID |
| **SAK** | 1 byte (offset 5) | `0x08` = MIFARE Classic 1K |
| **ATQA** | 2 bytes (offset 6-7) | Answer To Request Type A |
| **Manufacturer** | 8 bytes (offset 8-15) | Thông tin nhà sản xuất chip |

Giá trị SAK phổ biến:

| SAK | Loại thẻ |
|---|---|
| `0x08` | MIFARE Classic 1K |
| `0x09` | MIFARE Mini |
| `0x18` | MIFARE Classic 4K |
| `0x20` | MIFARE Plus / DESFire |
| `0x28` | JCOP30 |

---

## SimpleMFRC522 ghi vào đâu?

`SimpleMFRC522.write(text)` ghi vào **blocks 8, 9, 10** (sector 2).

- Tối đa **48 ký tự** (3 blocks × 16 bytes)
- Text được padding bằng space đến hết block

---

## Thẻ Magic / Chinese Backdoor Card

Thẻ thường **không thể** ghi vào block 0 (UID là cố định từ nhà máy).  
Để clone hoàn toàn bao gồm UID, cần dùng **Magic Card (Gen1/Gen2)**:

| Loại | Đặc điểm |
|---|---|
| **Gen1 (UID changeable)** | Ghi block 0 bằng backdoor command |
| **Gen2 (CUID)** | Ghi block 0 bằng lệnh write thông thường |

---

## Ví Dụ Thực Tế — Dump Thẻ Trắng Mới

Đây là output từ `dump_card()` của một thẻ MIFARE Classic 1K **chưa ghi dữ liệu**:

```
UID: E5:72:0B:53:CF  Type: Unknown (0x10)
```

> **Lưu ý:** `Unknown (0x10)` xuất hiện vì hàm `MFRC522_Request` trả về số bit của ATQA
> (16 bit = `0x10`), không phải giá trị SAK. Loại thẻ thực tế xác định được từ SAK ở
> block 0 = `0x08` → **MIFARE Classic 1K**. Đây là hạn chế của thư viện mfrc522.
>
> UID thực tế là **4 bytes**: `E5:72:0B:53`. Byte thứ 5 (`CF`) là BCC checksum
> bị hiển thị nhầm vào UID.

### Phân Tích Block 0 (Manufacturer Data)

```
E5 72 0B 53 | CF | 08 | 04 00 | 62 63 64 65 66 67 68 69
└─── UID ──┘  BCC  SAK  ATQA    └────── Manufacturer ────┘
```

| Field | Giá trị | Kết luận |
|---|---|---|
| UID | `E5:72:0B:53` | Số định danh duy nhất |
| BCC | `CF` | `E5^72^0B^53 = CF` ✓ checksum hợp lệ |
| SAK | `08` | MIFARE Classic 1K |
| ATQA | `04 00` | ISO 14443-3 Type A |
| Manufacturer | `62 63 64 65 66 67 68 69` | ASCII: `bcdefghi` |

### Phân Tích Sector Trailer (Block 3, 7, 11, ... 63)

Tất cả 16 sector trailer đều giống nhau:

```
00 00 00 00 00 00 | FF 07 80 69 | FF FF FF FF FF FF
└──── Key A ─────┘ └─Access bits┘ └───── Key B ────┘
```

| Field | Giá trị | Kết luận |
|---|---|---|
| Key A | `00 00 00 00 00 00` | Bị mask theo spec — thực tế vẫn là `FF:FF:FF:FF:FF:FF` |
| Access bits | `FF 07 80 69` | Default factory condition |
| Key B | `FF FF FF FF FF FF` | Key mặc định — chưa thay đổi |

### Kết Luận

| Quan sát | Ý nghĩa |
|---|---|
| Blocks 1–2, 4–62 đều = `00` | Thẻ trống, chưa ghi dữ liệu |
| Key B = `FF FF FF FF FF FF` | Chưa cấu hình bảo mật |
| Access bits = `FF 07 80 69` | Default — đọc/ghi tự do với cả Key A và Key B |

**Thẻ này an toàn để thực hành ghi dữ liệu vào bất kỳ data block nào (1, 2, 4–6, 8–10...)**

---

## Tham Khảo

- [MIFARE Classic 1K Datasheet — NXP](https://www.nxp.com/docs/en/data-sheet/MF1S50YYX_V1.pdf)
- [mfrc522 Python library](https://github.com/pimylifeup/MFRC522-python)
- [Test RFID + LED](rfid-led-test.md)
