# Security Best Practices

## ⚠️ Tuyên Bố Quan Trọng

**RaspFlip là công cụ giáo dục và nghiên cứu bảo mật.** Việc sử dụng các công cụ này cho mục đích bất hợp pháp là vi phạm pháp luật và đạo đức.

## 🔒 Nguyên Tắc Ethical Hacking

### 1. Permission & Authorization

**LUÔN LUÔN xin phép trước khi test:**
- ✅ Chỉ test trên thiết bị và mạng của bạn
- ✅ Có văn bản cho phép khi test cho người khác
- ✅ Trong môi trường lab/isolated
- ❌ KHÔNG test trên thiết bị không được phép
- ❌ KHÔNG test trên mạng công cộng
- ❌ KHÔNG gây thiệt hại hoặc truy cập trái phép

### 2. Responsible Disclosure

Nếu phát hiện lỗ hổng:
1. KHÔNG công khai ngay lập tức
2. Báo cáo cho vendor/tổ chức liên quan
3. Cho thời gian để họ patch
4. Công khai có trách nhiệm (nếu cần)

### 3. Legal Compliance

Tuân thủ luật pháp:
- Luật an ninh mạng
- Luật sử dụng tần số radio
- Luật bảo vệ dữ liệu cá nhân
- Quy định về thiết bị viễn thông

## 🛡️ Physical Security

### Bảo Vệ Thiết Bị

1. **Password Protection:**
```bash
# Đổi password default
passwd

# Disable password login, use SSH keys
ssh-keygen -t ed25519
```

2. **Encrypt Data:**
```bash
# Encrypt dumps và captures
gpg --symmetric sensitive_data.dump
```

3. **Secure Storage:**
- Không để thiết bị nơi công cộng
- Lock screen khi không dùng
- Xóa dữ liệu nhạy cảm sau khi test

### Physical Access Control

```bash
# Disable unused services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon

# Enable firewall
sudo apt install ufw
sudo ufw enable
```

## 🌐 Network Security

### 1. Secure SSH

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config

# Recommended settings:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
Port 2222  # Change default port

# Restart SSH
sudo systemctl restart ssh
```

### 2. VPN Usage

Khi test network security:
```bash
# Use VPN để bảo vệ traffic
sudo apt install openvpn
sudo openvpn --config your_vpn.ovpn
```

### 3. Isolated Network

- Tạo network riêng cho testing
- Không kết nối vào production network
- Sử dụng router riêng

## 📡 RF/Radio Security

### Compliance

1. **Frequency Regulations:**
   - Kiểm tra tần số được phép sử dụng
   - Tuân thủ công suất phát tối đa
   - Không gây nhiễu thiết bị khác

2. **Common Frequency Bands:**
   - 315 MHz: Chỉ US
   - 433.92 MHz: EU, Asia (ISM band)
   - 868 MHz: EU
   - 915 MHz: US

3. **Testing Guidelines:**
   - Test trong Faraday cage (nếu có thể)
   - Giới hạn công suất phát
   - Ngắt anten khi không test

### Legal Considerations

```python
# Example: Frequency checker
LEGAL_FREQUENCIES = {
    'US': [315.0, 433.92, 915.0],
    'EU': [433.92, 868.35],
    'AS': [433.92]
}

def check_frequency_legal(freq_mhz, region):
    """Check if frequency is legal in region"""
    return freq_mhz in LEGAL_FREQUENCIES.get(region, [])
```

## 🔐 RFID/NFC Security

### Ethical Usage

**Được phép:**
- ✅ Clone thẻ cá nhân của bạn
- ✅ Test bảo mật hệ thống của bạn
- ✅ Nghiên cứu giao thức RFID

**KHÔNG được phép:**
- ❌ Clone thẻ của người khác
- ❌ Truy cập trái phép
- ❌ Fraud/tạo thẻ giả

### Best Practices

```python
# Luôn log các hoạt động
import logging

logger.info(f"RFID Read: UID={uid}, User={current_user}, Purpose={purpose}")
```

## 💻 BadUSB Ethics

### Cực Kỳ Nguy Hiểm!

BadUSB có thể gây hại nghiêm trọng:
- Cài malware
- Steal credentials
- Encrypt ransomware
- Data exfiltration

### Safety Guidelines

1. **Test Environment Only:**
```python
# Example: Safety check
def execute_payload(payload_path):
    if not is_test_environment():
        raise SecurityError("Cannot execute payload in production!")
    # ... execute
```

2. **Payload Review:**
- Đọc và hiểu payload trước khi chạy
- Test trên VM trước
- Không dùng payload từ nguồn không tin cậy

3. **Disclosure:**
- Luôn thông báo khi demo BadUSB
- Chỉ demo trên máy của bạn
- Giải thích rủi ro

## 📊 Data Protection

### 1. Sensitive Data Handling

```python
# Don't log sensitive data
logger.info(f"Card read: UID={uid[:4]}****")  # Mask UID

# Encrypt stored dumps
import gnupg
gpg = gnupg.GPG()
encrypted = gpg.encrypt(dump_data, passphrase='your_passphrase')
```

### 2. Secure Deletion

```bash
# Secure delete files
sudo apt install secure-delete
srm -v sensitive_file.dump

# Wipe free space
sfill -v /path/to/directory
```

### 3. Access Control

```bash
# Restrict file permissions
chmod 600 ~/.raspflip/config
chmod 700 ~/raspflip/dumps/
```

## 🎓 Learning Resources

### Recommended Reading

1. **Laws & Regulations:**
   - Computer Fraud and Abuse Act (CFAA)
   - Luật An ninh mạng Việt Nam
   - GDPR (EU)

2. **Ethical Hacking:**
   - OWASP Testing Guide
   - NIST Cybersecurity Framework
   - CEH Study Materials

3. **RF Security:**
   - FCC Regulations (US)
   - ETSI Standards (EU)
   - Local telecommunications laws

### Certifications

Consider pursuing:
- CEH (Certified Ethical Hacker)
- OSCP (Offensive Security Certified Professional)
- Security+ (CompTIA)

## ⚖️ Legal Disclaimer

**Sử dụng RaspFlip có nghĩa là bạn đồng ý:**

1. Chịu trách nhiệm hoàn toàn về hành động của mình
2. Tuân thủ luật pháp địa phương và quốc tế
3. Không sử dụng cho mục đích bất hợp pháp
4. Có kiến thức và kỹ năng đầy đủ
5. Hiểu rủi ro và hậu quả

**Tác giả và contributors KHÔNG chịu trách nhiệm về:**
- Việc sử dụng sai mục đích
- Thiệt hại gây ra bởi người dùng
- Vi phạm pháp luật
- Mất mát dữ liệu hoặc thiết bị

## 📞 Reporting Issues

Nếu phát hiện:
- Lỗ hổng trong code
- Vấn đề bảo mật
- Tính năng có thể bị lạm dụng

**Liên hệ:**
- Email: security@raspflip-project.org
- PGP Key: [public key]
- Issue tracker (for non-security bugs)

## ✅ Security Checklist

Trước khi sử dụng RaspFlip:

- [ ] Đã đọc và hiểu tài liệu này
- [ ] Có permission để test
- [ ] Trong môi trường an toàn/isolated
- [ ] Backup dữ liệu quan trọng
- [ ] Hiểu rủi ro pháp lý
- [ ] Có kế hoạch responsible disclosure
- [ ] Đã cấu hình bảo mật thiết bị
- [ ] Không kết nối mạng production
- [ ] Tuân thủ quy định RF (nếu dùng radio)
- [ ] Prepared to stop if something goes wrong

---

**Remember: With great power comes great responsibility!** 🕷️

Use RaspFlip to learn, understand, and improve security - never to harm or exploit.
