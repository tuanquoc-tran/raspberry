# RaspFlip Example Payloads

## ⚠️ Warning

These payloads are for **EDUCATIONAL AND TESTING PURPOSES ONLY**.

Only use on systems you own or have explicit permission to test.

## 📁 Payload Categories

### 1. Test Payloads
- `hello_world.txt` - Simple test on Windows
- `terminal_test.txt` - Terminal test on Linux

### 2. Information Gathering (Educational)
- System information collection
- Network configuration display
- Process listing

### 3. Pranks (Harmless)
- Message boxes
- Text manipulations
- Safe system interactions

## 🔧 Creating Custom Payloads

### DuckyScript Commands

```
REM     - Comment
DELAY   - Delay in milliseconds
STRING  - Type string
ENTER   - Press Enter
GUI     - Windows/Command key
CTRL    - Control key
ALT     - Alt key
SHIFT   - Shift modifier
TAB     - Tab key
ESC     - Escape key
F1-F12  - Function keys
UP/DOWN/LEFT/RIGHT - Arrow keys
```

### Example: Open Calculator (Windows)

```
REM Open Windows Calculator
DELAY 1000
GUI r
DELAY 500
STRING calc
ENTER
```

### Example: Create Text File (Linux)

```
REM Create a text file with content
CTRL ALT t
DELAY 1000
STRING echo "Test content" > test.txt
ENTER
STRING cat test.txt
ENTER
DELAY 2000
STRING rm test.txt
ENTER
STRING exit
ENTER
```

## 🛡️ Safety Guidelines

1. **Test in VM First:** Always test payloads in a virtual machine
2. **Review Code:** Understand every line before executing
3. **Reversible Actions:** Use payloads that can be easily undone
4. **No Persistence:** Avoid payloads that install software or create backdoors
5. **Ethical Use:** Only use on systems you own or have permission to test

## 📝 Payload Template

```
REM ================================
REM Payload Name: [Name]
REM Author: [Your Name]
REM Target: [OS/Environment]
REM Description: [What it does]
REM Tested on: [System info]
REM ================================

DELAY 1000
REM Your commands here
```

## 🚫 Prohibited Payloads

Do NOT create or use payloads that:
- Install malware or backdoors
- Steal credentials or personal data
- Cause system damage
- Violate privacy
- Are illegal in any way

## 📚 Learning Resources

- [USB Rubber Ducky Wiki](https://github.com/hak5darren/USB-Rubber-Ducky/wiki)
- [DuckyScript Documentation](https://github.com/hak5darren/USB-Rubber-Ducky/wiki/Duckyscript)
- [Payload Examples](https://github.com/hak5darren/USB-Rubber-Ducky/wiki/Payloads)

## ⚖️ Legal Disclaimer

Creating or using malicious payloads is illegal and unethical.

This directory contains only educational examples for authorized testing.

Users are solely responsible for how they use these tools.
