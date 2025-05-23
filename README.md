# 🔐 Dual-VPN AND Logic Verifier (macOS)

This project performs **AND-style security verification** using **two simultaneous VPNs** on macOS. It ensures a website response is **only trusted if both VPN paths return identical content**.

## ✅ Features

- Binds HTTP requests to two different VPN interfaces (e.g., `utun0`, `utun1`)
- Sends requests via each VPN in parallel
- Uses `SHA-256` hash to compare responses
- Accepts content **only if both hashes match**

## 📦 Components

1. **Shell Script**: Sets up routing rules for each VPN.
2. **Swift CLI App**: Sends raw HTTP requests bound to each VPN interface.
3. **NWConnection**: Binds sockets to specific interfaces.
4. *(Optional)* SwiftUI GUI for live results (coming soon).

---

## 🛠 Requirements

- macOS Ventura or later
- Swift 5.5+
- Two active VPNs using distinct interfaces (`utun0`, `utun1`)
- Xcode or Swift CLI tools
- `dig` command (preinstalled on macOS)

---

## 🧪 Setup Instructions

### 1. Set Up VPNs
Connect to **two different VPNs** using a client like Tunnelblick, Viscosity, or `networksetup`. Confirm the interfaces:

```bash
ifconfig | grep utun
