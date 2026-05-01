# Contributing to RaspFlip

Cảm ơn bạn đã quan tâm đến việc đóng góp cho RaspFlip! 🎉

## 📋 Code of Conduct

### Nguyên Tắc Cơ Bản

1. **Mục đích giáo dục:** Mọi đóng góp phải phục vụ mục đích học tập và nghiên cứu hợp pháp
2. **Tôn trọng:** Tôn trọng tất cả contributors và maintainers
3. **Ethical hacking:** Tuân thủ nguyên tắc ethical hacking
4. **Open source spirit:** Chia sẻ kiến thức và giúp đỡ lẫn nhau

## 🚀 Cách Đóng Góp

### 1. Báo Cáo Bug

Nếu phát hiện bug, vui lòng:

1. Kiểm tra [Issues](../../issues) xem bug đã được báo cáo chưa
2. Tạo issue mới với template:

```markdown
**Mô tả bug:**
[Mô tả ngắn gọn về bug]

**Các bước tái hiện:**
1. ...
2. ...
3. ...

**Kết quả mong đợi:**
[Điều bạn mong đợi xảy ra]

**Kết quả thực tế:**
[Điều thực sự xảy ra]

**Môi trường:**
- Raspberry Pi Model: [e.g., Pi 4 Model B 4GB]
- OS: [e.g., Raspberry Pi OS 64-bit]
- Python version: [e.g., 3.9.2]
- RaspFlip version: [e.g., 0.1.0]

**Thông tin bổ sung:**
[Screenshots, logs, etc.]
```

### 2. Đề Xuất Tính Năng

Để đề xuất tính năng mới:

1. Tạo issue với label `enhancement`
2. Mô tả rõ:
   - Tính năng muốn thêm
   - Use case
   - Tại sao nó hữu ích
   - Cách implement (nếu có ý tưởng)

### 3. Pull Request

#### Quy Trình

1. **Fork repository**
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/raspflip.git
cd raspflip
```

2. **Create branch**
```bash
# Create feature branch
git checkout -b feature/amazing-feature

# Or bugfix branch
git checkout -b fix/bug-description
```

3. **Make changes**
```bash
# Make your changes
# Test thoroughly

# Commit with meaningful message
git commit -m "Add amazing feature: description"
```

4. **Push and create PR**
```bash
git push origin feature/amazing-feature
```

Then create Pull Request on GitHub.

#### Code Standards

**Python Code Style:**
```python
# Follow PEP 8
# Use type hints
def read_card(self, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
    """
    Read RFID card
    
    Args:
        timeout: Maximum wait time in seconds
    
    Returns:
        Dictionary with card data or None
    """
    pass

# Use descriptive variable names
card_data = reader.read()  # Good
d = r.read()  # Bad

# Add docstrings to all public functions/classes
# Use logging instead of print()
logger.info("Card detected")  # Good
print("Card detected")  # Bad
```

**File Organization:**
```
modules/
├── module_name/
│   ├── __init__.py      # Main module code
│   ├── utils.py         # Utility functions
│   ├── protocols.py     # Protocol implementations
│   └── tests/           # Unit tests
│       └── test_module.py
```

**Documentation:**
- Add docstrings to all functions
- Update README.md if adding major features
- Add examples in docs/ folder
- Comment complex logic

**Testing:**
```bash
# Add tests for new features
# Run tests before submitting PR
python -m pytest tests/

# Check code style
flake8 modules/
```

### 4. Documentation

Documentation improvements are always welcome!

Areas to contribute:
- Fix typos
- Improve clarity
- Add tutorials
- Translate to other languages
- Add hardware guides for new modules

## 📦 Module Development

### Adding New Module

1. **Create module structure:**
```bash
mkdir modules/new_module
touch modules/new_module/__init__.py
```

2. **Implement base class:**
```python
"""
New Module for RaspFlip
Description of what it does
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class NewModule:
    """Main class for new module"""
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize hardware"""
        try:
            # Setup code here
            self.initialized = True
            logger.info("New module initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        pass
```

3. **Add to main menu** in `ui/cli.py`

4. **Add documentation** in `docs/`

5. **Add hardware guide** if needed

6. **Add tests**

### Hardware Module Guidelines

- Always check `self.initialized` before operations
- Provide meaningful error messages
- Use logging for debugging
- Cleanup resources in `cleanup()` method
- Handle exceptions gracefully
- Add safety checks

## 🔒 Security Contributions

### Reporting Security Issues

**DO NOT** open public issues for security vulnerabilities!

Instead:
1. Email: security@raspflip-project.org
2. Include detailed description
3. Steps to reproduce
4. Potential impact
5. Suggested fix (if any)

We will respond within 48 hours.

### Security-Related Code

When contributing security features:
- Add warnings for dangerous operations
- Implement safety checks
- Add ethical use guidelines
- Document legal considerations
- Test thoroughly in isolated environment

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=modules tests/

# Run specific test
pytest tests/test_rfid.py
```

### Writing Tests

```python
import pytest
from modules.rfid import RC522Reader

def test_reader_initialization():
    """Test RFID reader initialization"""
    reader = RC522Reader()
    # Mock hardware if needed
    assert reader is not None

def test_read_card():
    """Test card reading"""
    # Add test logic
    pass
```

## 📝 Commit Messages

Follow conventional commits:

```
feat: add NFC card emulation
fix: correct IR timing calculation
docs: update hardware setup guide
test: add RFID module tests
refactor: improve GPIO error handling
style: format code with black
perf: optimize signal processing
```

## 🎯 Areas Needing Help

Current priorities:

- [ ] GUI interface (PyQt/Tkinter)
- [ ] Mobile app companion
- [ ] More IR protocols
- [ ] Additional Sub-GHz protocols
- [ ] Better error handling
- [ ] More example payloads
- [ ] Hardware PCB design
- [ ] 3D printable case designs
- [ ] Translations
- [ ] Video tutorials

## 📞 Contact

- **Discussions:** GitHub Discussions
- **Chat:** Discord/Telegram (if available)
- **Email:** project@raspflip.org

## ⚖️ Legal

By contributing, you agree that:

1. Your contributions will be licensed under MIT License
2. You have the right to submit the contribution
3. Your contributions are for educational purposes
4. You understand and accept the project's ethical guidelines

## 🙏 Recognition

All contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in documentation

Thank you for making RaspFlip better! 🚀
