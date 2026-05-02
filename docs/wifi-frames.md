# Wi-Fi Frame & Connection Internals

> Tài liệu này đi sâu vào cơ chế hoạt động của Wi-Fi từ lớp vật lý đến ứng dụng —
> cách một thiết bị tìm thấy AP, xác thực, kết nối, và truyền dữ liệu.

---

## Mô Hình Phân Lớp

```
┌─────────────────────────────────┐
│  Application  (HTTP, DNS, SSH)  │  L7
├─────────────────────────────────┤
│  Transport    (TCP / UDP)       │  L4
├─────────────────────────────────┤
│  Network      (IP)              │  L3
├─────────────────────────────────┤
│  Data Link    (802.11 MAC)      │  L2  ← Wi-Fi bắt đầu ở đây
├─────────────────────────────────┤
│  Physical     (802.11 PHY)      │  L1
└─────────────────────────────────┘
```

Wi-Fi (IEEE 802.11) hoạt động ở **L1 + L2**. Mọi thứ bên trên (IP, TCP, HTTP) không
"biết" đang chạy trên Wi-Fi hay Ethernet — chúng chỉ thấy một interface L2.

---

## Cấu Trúc Frame 802.11

Mỗi frame Wi-Fi truyền qua không khí gồm:

```
┌──────────┬──────────┬────────┬─────┬──────┬──────┬──────┬──────┬──────────┬─────┬─────┐
│Frame Ctrl│ Duration │ Addr1  │Addr2│Addr3 │SeqCtl│Addr4 │ QoS  │  Payload │ FCS │     │
│  2 bytes │  2 bytes │6 bytes │  6  │  6   │  2   │  6   │  2   │ variable │  4  │     │
└──────────┴──────────┴────────┴─────┴──────┴──────┴──────┴──────┴──────────┴─────┴─────┘
```

### Frame Control (2 bytes — quan trọng nhất)

```
Bits: 0-1    Protocol Version  (luôn = 00)
      2-3    Type              00=Management  01=Control  10=Data
      4-7    Subtype           (xem bảng bên dưới)
      8      To DS             1 = gửi vào distribution system (đến AP)
      9      From DS           1 = ra khỏi distribution system (từ AP)
      10     More Frag
      11     Retry
      12     Power Mgmt
      13     More Data
      14     Protected Frame   1 = payload đã mã hoá (WPA2/WPA3)
      15     Order
```

### Ba loại frame

| Type | Subtype phổ biến | Mục đích |
|---|---|---|
| **Management** | Beacon, Probe, Auth, AssocReq/Resp, Deauth, Disassoc | Quản lý kết nối |
| **Control** | ACK, RTS, CTS, BlockACK | Điều khiển truy cập medium |
| **Data** | Data, QoS Data, Null | Mang IP packet |

### Địa chỉ trong frame

| Trường | Ý nghĩa khi To DS=1, From DS=0 (client → AP) |
|---|---|
| Addr1 | BSSID (MAC của AP) |
| Addr2 | Source (MAC của client) |
| Addr3 | Destination (MAC đích trong mạng có dây) |

---

## Quá Trình Kết Nối — Từng Bước

### Bước 1: Discovery

AP liên tục phát **Beacon frame** mỗi **102.4ms** (mặc định):

```
AP → Broadcast (FF:FF:FF:FF:FF:FF)
     Beacon
       SSID: "MyNetwork"
       BSSID: AA:BB:CC:DD:EE:FF
       Channel: 6
       Capabilities: WPA2, CCMP, 802.11n
       Supported Rates: 6,9,12,18,24,36,48,54 Mbps
       HT Capabilities: (nếu 802.11n)
```

Client cũng có thể chủ động hỏi bằng **Probe Request**:

```
Client → Broadcast
         Probe Request
           SSID: "MyNetwork"  (hoặc wildcard nếu scan tất cả)

AP → Client
     Probe Response  (giống Beacon, reply trực tiếp)
```

> `iwlist wlan0 scan` thực chất gửi Probe Request trên từng channel và thu Probe Response.

---

### Bước 2: Authentication (Open System)

Đây là **authentication giả** — WPA2 không dùng bước này để xác thực thực sự.
Chỉ là handshake "xin vào":

```
Client → AP
         Authentication Request
           Algorithm: Open System (0)
           Seq: 1

AP → Client
         Authentication Response
           Algorithm: Open System (0)
           Seq: 2
           Status: 0 (Success)
```

> Với WPA3-SAE, bước này thay bằng SAE Commit/Confirm (Dragonfly handshake).

---

### Bước 3: Association

Client khai báo khả năng của mình và "đăng ký" với AP:

```
Client → AP
         Association Request
           SSID: "MyNetwork"
           Supported Rates: ...
           RSN Information Element:
             WPA Version: 2
             Group Cipher: CCMP
             Pairwise Cipher: CCMP
             Auth Key Management: PSK

AP → Client
         Association Response
           Status: 0 (Success)
           Association ID (AID): 1  ← ID định danh client trong BSS
           Supported Rates: ...
```

Tại thời điểm này client đã **associated** nhưng chưa được phép truyền data —
còn phải qua 4-Way Handshake.

---

### Bước 4: 4-Way Handshake (WPA2 — quan trọng nhất)

Mục tiêu: **chứng minh cả hai bên đều biết PSK** mà không truyền PSK trực tiếp,
và thống nhất **PTK** (Pairwise Transient Key) để mã hoá data.

```
PMK (Pairwise Master Key) = PBKDF2-SHA1(PSK, SSID, 4096 iterations, 256 bits)
                          ← derive từ password, không bao giờ truyền qua air
```

```
PTK = PRF-512(PMK, "Pairwise key expansion",
              min(AP_MAC, Client_MAC) || max(AP_MAC, Client_MAC) ||
              min(ANonce, SNonce) || max(ANonce, SNonce))

PTK gồm 3 phần:
  KCK (Key Confirmation Key, 128 bit) — dùng để tạo MIC trong handshake
  KEK (Key Encryption Key, 128 bit)   — dùng để mã hoá GTK
  TK  (Temporal Key, 128 bit)         — AES-CCMP key thực sự dùng cho data
```

#### Diễn biến 4 message:

```
AP → Client   [Message 1]
              EAPOL-Key
                ANonce = random 32 bytes do AP tạo

Client → AP   [Message 2]
              EAPOL-Key
                SNonce = random 32 bytes do Client tạo
                MIC    = HMAC-SHA1(KCK, frame)  ← chứng minh biết PMK
                RSN IE = cipher suites client muốn dùng

              ← AP verify MIC. Nếu đúng → client biết password.

AP → Client   [Message 3]
              EAPOL-Key
                GTK encrypted với KEK  ← Group Temporal Key (dùng cho broadcast)
                MIC = HMAC-SHA1(KCK, frame)

              ← Client verify MIC. Nếu đúng → AP biết password.

Client → AP   [Message 4]
              EAPOL-Key (ACK)
                MIC = HMAC-SHA1(KCK, frame)

              ← Cả hai bên install TK vào hardware → bắt đầu mã hoá data
```

> **KRACK attack (2017)** khai thác việc Message 3 có thể replay để reinstall TK = 0,
> cho phép decrypt data. Đã vá trong kernel Linux và wpa_supplicant.

---

### Bước 5: DHCP — Lấy IP

Sau khi Wi-Fi kết nối xong, client vẫn chưa có IP. DHCP chạy bên trên UDP/IP:

```
Client → Broadcast 255.255.255.255
         DHCP Discover
           "Tôi cần IP, ai là DHCP server?"

Router → Broadcast
         DHCP Offer
           Offered IP: 192.168.1.105
           Subnet: 255.255.255.0
           Gateway: 192.168.1.1
           DNS: 8.8.8.8
           Lease: 86400s

Client → Broadcast
         DHCP Request
           "Tôi chấp nhận 192.168.1.105"

Router → Client
         DHCP ACK
           "Confirmed. IP của bạn là 192.168.1.105 trong 24h"
```

---

## Truyền Data — Frame Flow Thực Tế

Giả sử bạn `curl https://example.com` từ Raspberry Pi:

```
Application: HTTP GET /
     ↓ write()
Transport:   TCP segment (src:443xx dst:443)
     ↓ IP routing
Network:     IP packet (src:192.168.1.105 dst:93.184.216.34)
     ↓ ARP lookup (hoặc dùng cache)
Data Link:   802.11 Data frame
               Addr1: AP MAC (BSSID)       ← To DS = 1
               Addr2: Client MAC
               Addr3: Router MAC (gateway)
               Protected Frame = 1
               Payload: AES-CCMP(IP packet)
     ↓ RF
Physical:    OFDM symbols trên không khí (ch 6, 2.437 GHz)
```

AP nhận được, giải mã CCMP, forward lên Ethernet:

```
AP (wired side):
     Ethernet frame
       src: Client MAC
       dst: Router MAC (gateway)
       payload: IP packet
     → Internet
```

---

## AES-CCMP — Mã Hoá Data Frame

WPA2 dùng **AES-128-CCM** (Counter with CBC-MAC):

```
Plaintext: IP packet
    ↓
CCM Encrypt(TK, Nonce, AAD, Plaintext)
    Nonce = PN (Packet Number, 6 bytes, tăng dần — chống replay)
    AAD   = 802.11 header fields
    ↓
Output:
  802.11 Header (unencrypted, nhưng covered bởi MIC)
  CCMP Header (8 bytes: PN fields + ExtIV bit)
  Ciphertext
  MIC (8 bytes — Message Integrity Code)
```

Nếu attacker flip 1 bit trong ciphertext → MIC check fail → frame bị drop.
Đây là lý do WPA2 an toàn hơn TKIP rất nhiều.

---

## ACK Mechanism — Wi-Fi Không Như Ethernet

Wi-Fi là **half-duplex** — không thể send và receive cùng lúc trên cùng channel.
Mỗi unicast data frame phải được ACK:

```
Client → AP   Data frame
AP → Client   ACK (trong 16μs SIFS — Short Interframe Space)

Nếu không có ACK trong timeout → retransmit (tối đa 7 lần)
```

**RTS/CTS** (Request to Send / Clear to Send) — dùng khi frame lớn hoặc hidden node:

```
Client → AP   RTS (20 bytes — báo trước "tôi sắp gửi X bytes trong Y μs")
AP → All      CTS (14 bytes — broadcast "im lặng trong Y μs")
Client → AP   Data frame
AP → Client   ACK
```

---

## CSMA/CA — Tránh Va Chạm

Wi-Fi không dùng CSMA/CD (như Ethernet) vì không detect collision được.
Dùng **CSMA/CA** (Collision Avoidance):

```
1. Muốn gửi → kiểm tra medium có rảnh không (carrier sense)
2. Nếu bận → đợi cho đến rảnh
3. Rảnh → đợi thêm DIFS (34μs)
4. Random backoff: chọn số random trong [0, CW] × slot time (9μs)
5. Đếm ngược backoff. Nếu medium bận → dừng đếm, đợi rảnh rồi tiếp tục
6. Backoff = 0 → gửi frame
7. Nếu collision (không có ACK) → tăng CW gấp đôi (Binary Exponential Backoff)
```

$$CW_{max} = 2^{n} \times CW_{min}, \quad n = \text{số lần retry}$$

---

## Power Save Mode

Client có thể báo AP `Power Management = 1` trong frame header.
AP sẽ **buffer packet** cho client thay vì gửi ngay.
Client định kỳ thức dậy nghe Beacon → nếu có **TIM bit** (Traffic Indication Map) → gửi PS-Poll để lấy packet.

Đây là lý do Wi-Fi trên phone tiêu thụ ít pin hơn Ethernet.

---

## Sequence Diagram Tổng Quan

```
Client                          AP                        Internet
  |                              |                            |
  |──── Probe Request ──────────>|                            |
  |<─── Probe Response ──────────|                            |
  |                              |                            |
  |──── Auth Request ───────────>|                            |
  |<─── Auth Response ───────────|                            |
  |                              |                            |
  |──── Assoc Request ──────────>|                            |
  |<─── Assoc Response ──────────|                            |
  |                              |                            |
  |<─── EAPOL Msg1 (ANonce) ─────|                            |
  |──── EAPOL Msg2 (SNonce+MIC) >|                            |
  |<─── EAPOL Msg3 (GTK+MIC) ────|                            |
  |──── EAPOL Msg4 (ACK) ───────>|                            |
  |         [TK installed]       |                            |
  |                              |                            |
  |──── DHCP Discover ──────────>|──── DHCP Discover ────────>|
  |<─── DHCP Offer ──────────────|<─── DHCP Offer ────────────|
  |──── DHCP Request ───────────>|──── DHCP Request ─────────>|
  |<─── DHCP ACK ────────────────|<─── DHCP ACK ──────────────|
  |         [IP: 192.168.1.105]  |                            |
  |                              |                            |
  |──── AES-CCMP(TCP SYN) ──────>|──── TCP SYN ──────────────>|
  |<─── AES-CCMP(TCP SYN-ACK) ───|<─── TCP SYN-ACK ───────────|
  |──── AES-CCMP(HTTP GET) ─────>|──── HTTP GET ─────────────>|
  |<─── AES-CCMP(HTTP 200) ──────|<─── HTTP 200 ──────────────|
```

---

## Những Con Số Cần Nhớ

| Thông số | Giá trị |
|---|---|
| Beacon interval | 102.4 ms |
| SIFS (ACK timeout) | 16 μs |
| DIFS | 34 μs |
| Slot time (802.11n) | 9 μs |
| PBKDF2 iterations (PMK) | 4096 |
| PTK size | 512 bit |
| TK size (AES) | 128 bit |
| CCMP MIC | 8 bytes |
| Packet Number (PN) size | 6 bytes (48 bit — đủ cho 2⁴⁸ frames) |
| Max retransmit | 7 lần |
| DHCP lease default | 86400s (24h) |

---

## Xem Thêm

- [Wi-Fi Pentest Guide](wifi-pentest.md) — monitor mode, deauth, handshake capture, crack
- [Wi-Fi Module API](wifi.md)
- [IEEE 802.11-2020 Full Standard](https://standards.ieee.org/ieee/802.11/7028/)
- [RFC 3748 — EAP](https://www.rfc-editor.org/rfc/rfc3748)
- [KRACK Attack Paper](https://www.krackattacks.com/)
- [Wireshark 802.11 dissector](https://wiki.wireshark.org/Wi-Fi)
