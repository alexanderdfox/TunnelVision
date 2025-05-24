# 🔐 Dual-VPN Logic Gate System – Usage Guide

This tool verifies secure communication across **two VPNs** using logic gates like AND, OR, XOR, and NOT. It’s available in two versions:

* **SwiftUI App** (macOS GUI)
* **Python Script** (CLI with UDP server)

---

## ✅ Requirements

* macOS 13+
* Two VPN configs in **Tunnelblick**
* Admin access (for adding routes)
* Python 3.8+ (for CLI version)
* Xcode (for Swift version)

---

## 🧽 VPN Setup

1. Install and configure **Tunnelblick**.
2. Add your `.ovpn` files:

   * One for USB-tethered VPN (e.g., `VPN-USB`)
   * One for Wi-Fi VPN (e.g., `VPN-WiFi`)
3. Test both VPNs manually first.

---

## 💥 SwiftUI App (GUI)

### 1. Open Project

```bash
git clone https://github.com/yourname/DualVPNLogicGate
cd DualVPNLogicGate/swift
open DualVPNLogicGate.xcodeproj
```

### 2. Update Config

In `LogicGateService.swift`:

```swift
let vpn1Name = "VPN-USB"
let vpn2Name = "VPN-WiFi"
```

### 3. Run

* Build & Run in Xcode.
* Choose a logic gate mode (AND, OR, XOR, NOT).
* The app:

  * Starts both VPNs
  * Binds interfaces
  * Monitors UDP ports
  * Displays verified logic results in real-time

### 4. Send Test Data

From a terminal:

```bash
echo "ping" | nc -u <VPN1_IP> 5000
echo "ping" | nc -u <VPN2_IP> 5001
```

If logic matches, GUI shows ✅.

---

## 🐍 Python Script (CLI)

### 1. Setup

```bash
cd DualVPNLogicGate/python
```

Edit the config section at the top of `vpn_logic.py`:

```python
VPN1_NAME = "VPN-USB"
VPN2_NAME = "VPN-WiFi"
VPN1_SERVER_DOMAIN = "vpn-usb.example.com"
VPN2_SERVER_DOMAIN = "vpn-wifi.example.com"
```

### 2. Run

```bash
sudo python3 vpn_logic.py
```

The script will:

* Detect interfaces
* Add routes
* Connect both VPNs
* Listen on UDP ports 5000/5001
* Print logic matches in terminal

### 3. Test with Netcat

```bash
echo "ping" | nc -u <VPN1_IP> 5000
echo "ping" | nc -u <VPN2_IP> 5001
```

### 4. Logic Types

Default logic is **AND**. To switch to OR, XOR, NOT, change logic in `listen_on()` in the script.

---

## 🛯 Troubleshooting

| Issue                  | Fix                                                             |
| ---------------------- | --------------------------------------------------------------- |
| VPN won’t connect      | Open Tunnelblick manually, check profile names                  |
| No IP for VPN detected | Enter manually when prompted                                    |
| No match logged        | Double-check if test packets match and VPNs are bound correctly |
| Ports in use           | Change from 5000/5001 if needed                                 |

---

## 🧠 Summary

| Feature     | Swift GUI                | Python Script            |
| ----------- | ------------------------ | ------------------------ |
| Interface   | Graphical (Xcode)        | Terminal (CLI)           |
| Logic Modes | Selectable in UI         | Code-edit in script      |
| Realtime    | Yes (live logs)          | Yes (print to terminal)  |
| VPN Control | Built-in via Tunnelblick | Built-in via Tunnelblick |

---

Made with ❤️ using Swift, Python, and UDP logic.
