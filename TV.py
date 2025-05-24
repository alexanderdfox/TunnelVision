import subprocess
import re
import socket
import threading
import time
from flask import Flask, render_template_string, request, jsonify

# ---------------- USER CONFIG -------------------

VPN1_OVPN_PATH = "/path/to/vpn_usb.ovpn"
VPN2_OVPN_PATH = "/path/to/vpn_wifi.ovpn"

VPN1_NAME = "VPN-USB"
VPN2_NAME = "VPN-WiFi"

VPN1_SERVER_DOMAIN = "vpn-usb.example.com"
VPN2_SERVER_DOMAIN = "vpn-wifi.example.com"

VPN1_UDP_IP = None
VPN1_UDP_PORT = 5000

VPN2_UDP_IP = None
VPN2_UDP_PORT = 5001

LOGIC_GATE = "AND"  # Options: AND, OR, XOR, NAND, NOR, XNOR

# ----------------------------------------------

app = Flask(__name__)

# Shared data store
data_store = {
    "vpn1_msgs": [],
    "vpn2_msgs": [],
    "logic_gate": LOGIC_GATE,
    "vpn1_connected": False,
    "vpn2_connected": False
}

data_store_lock = threading.Lock()

def run_cmd(cmd, sudo=False):
    if sudo:
        cmd = ["sudo"] + cmd
    print(f"Running command: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Error running command: {proc.stderr}")
    return proc.stdout.strip()

def get_interfaces():
    output = run_cmd(["ifconfig"])
    interfaces = {}
    blocks = output.split("\n\n")
    for block in blocks:
        lines = block.splitlines()
        if not lines:
            continue
        iface = lines[0].split(":")[0]
        ip_match = None
        for line in lines:
            m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
            if m:
                ip_match = m.group(1)
                break
        if ip_match:
            interfaces[iface] = ip_match
    return interfaces

def guess_usb_wifi_interfaces(interfaces):
    usb_if = None
    wifi_if = None
    for iface, ip in interfaces.items():
        if "en" in iface:
            if iface in ("en0", "en1"):
                wifi_if = iface
            else:
                usb_if = iface
    print(f"Detected Wi-Fi interface: {wifi_if}, USB tether interface: {usb_if}")
    return usb_if, wifi_if

def resolve_ip(domain):
    try:
        ip = socket.gethostbyname(domain)
        print(f"Resolved {domain} to {ip}")
        return ip
    except socket.gaierror:
        print(f"Could not resolve domain {domain}")
        return None

def add_route(ip, iface):
    if ip is None or iface is None:
        print(f"Skipping route for IP {ip} iface {iface}")
        return
    cmd = ["route", "-nv", "add", "-host", ip, "-interface", iface]
    run_cmd(cmd, sudo=True)

def connect_vpn(tunnelblick_name):
    cmd = ["/Applications/Tunnelblick.app/Contents/Resources/client/bin/tunnelblickcli", "-c", tunnelblick_name]
    output = run_cmd(cmd)
    print(f"Tunnelblick connect output for {tunnelblick_name}:\n{output}")
    with data_store_lock:
        if tunnelblick_name == VPN1_NAME:
            data_store["vpn1_connected"] = True
        elif tunnelblick_name == VPN2_NAME:
            data_store["vpn2_connected"] = True

def disconnect_vpn(tunnelblick_name):
    cmd = ["/Applications/Tunnelblick.app/Contents/Resources/client/bin/tunnelblickcli", "-d", tunnelblick_name]
    output = run_cmd(cmd)
    print(f"Tunnelblick disconnect output for {tunnelblick_name}:\n{output}")
    with data_store_lock:
        if tunnelblick_name == VPN1_NAME:
            data_store["vpn1_connected"] = False
        elif tunnelblick_name == VPN2_NAME:
            data_store["vpn2_connected"] = False

def logic_gate_eval(gate, sources):
    vals = list(sources.values())
    if gate == "AND":
        return all(vals)
    elif gate == "OR":
        return any(vals)
    elif gate == "XOR":
        return sum(vals) == 1
    elif gate == "NAND":
        return not all(vals)
    elif gate == "NOR":
        return not any(vals)
    elif gate == "XNOR":
        return sum(vals) != 1
    return False

def listen_on(ip, port, vpn_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((ip, port))
    except Exception as e:
        print(f"Error binding {ip}:{port} - {e}")
        return

    print(f"Listening on {ip}:{port} for VPN{vpn_id}")

    while True:
        data, addr = sock.recvfrom(4096)
        decoded_data = data.decode(errors='replace')
        print(f"Received on VPN{vpn_id}: {decoded_data} from {addr}")

        key = decoded_data.strip()
        with data_store_lock:
            msg_list = data_store[f"vpn{vpn_id}_msgs"]
            msg_list.append(f"{time.strftime('%H:%M:%S')} - {decoded_data}")
            if len(msg_list) > 50:
                msg_list.pop(0)

            # For logic gate evaluation - simplified demo: track if message received from both VPNs
            sources = {
                1: bool(data_store["vpn1_msgs"]),
                2: bool(data_store["vpn2_msgs"]),
            }
            if logic_gate_eval(data_store["logic_gate"], sources):
                print(f"{data_store['logic_gate']} Logic Passed: condition met for data: {decoded_data}")
                # Clear messages after logic passes
                data_store["vpn1_msgs"].clear()
                data_store["vpn2_msgs"].clear()

@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>VPN Logic Gate Monitor</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.4.1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 2rem; background: #f8f9fa; }
        pre { background: #212529; color: #0d6efd; padding: 1rem; border-radius: 5px; height: 300px; overflow-y: scroll; }
        .status-connected { color: #198754; font-weight: bold; }
        .status-disconnected { color: #dc3545; font-weight: bold; }
    </style>
</head>
<body>
<div class="container">
    <h1 class="mb-4">VPN Logic Gate Monitor</h1>
    <div class="mb-3">
        <label for="logicGateSelect" class="form-label"><strong>Logic Gate</strong></label>
        <select id="logicGateSelect" class="form-select" style="max-width: 200px;">
            <option>AND</option>
            <option>OR</option>
            <option>XOR</option>
            <option>NAND</option>
            <option>NOR</option>
            <option>XNOR</option>
        </select>
    </div>
    <div class="row mb-4">
        <div class="col-md-6">
            <h3>VPN1 (USB) Status: <span id="vpn1_status" class="status-disconnected">Disconnected</span></h3>
            <button class="btn btn-success me-2" onclick="sendCommand('connect', 'vpn1')">Connect VPN1</button>
            <button class="btn btn-danger" onclick="sendCommand('disconnect', 'vpn1')">Disconnect VPN1</button>
            <h5 class="mt-3">VPN1 Messages:</h5>
            <pre id="vpn1_msgs"></pre>
        </div>
        <div class="col-md-6">
            <h3>VPN2 (WiFi) Status: <span id="vpn2_status" class="status-disconnected">Disconnected</span></h3>
            <button class="btn btn-success me-2" onclick="sendCommand('connect', 'vpn2')">Connect VPN2</button>
            <button class="btn btn-danger" onclick="sendCommand('disconnect', 'vpn2')">Disconnect VPN2</button>
            <h5 class="mt-3">VPN2 Messages:</h5>
            <pre id="vpn2_msgs"></pre>
        </div>
    </div>
</div>

<script>
    async function fetchStatus() {
        const res = await fetch('/status');
        const data = await res.json();

        document.getElementById('vpn1_status').textContent = data.vpn1_connected ? "Connected" : "Disconnected";
        document.getElementById('vpn1_status').className = data.vpn1_connected ? "status-connected" : "status-disconnected";

        document.getElementById('vpn2_status').textContent = data.vpn2_connected ? "Connected" : "Disconnected";
        document.getElementById('vpn2_status').className = data.vpn2_connected ? "status-connected" : "status-disconnected";

        document.getElementById('vpn1_msgs').textContent = data.vpn1_msgs.join("\\n");
        document.getElementById('vpn2_msgs').textContent = data.vpn2_msgs.join("\\n");

        const logicGateSelect = document.getElementById('logicGateSelect');
        if (logicGateSelect.value !== data.logic_gate) {
            logicGateSelect.value = data.logic_gate;
        }
    }

    async function sendCommand(action, vpn) {
        await fetch('/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action: action, vpn: vpn})
        });
        await fetchStatus();
    }

    document.getElementById('logicGateSelect').addEventListener('change', async (e) => {
        await fetch('/set_logic_gate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({logic_gate: e.target.value})
        });
        await fetchStatus();
    });

    setInterval(fetchStatus, 3000);
    window.onload = fetchStatus;
</script>

</body>
</html>
""")

@app.route("/status")
def status():
    with data_store_lock:
        return jsonify(data_store)

@app.route("/command", methods=["POST"])
def command():
    cmd = request.json
    vpn = cmd.get("vpn")
    action = cmd.get("action")

    if vpn == "vpn1":
        if action == "connect":
            threading.Thread(target=connect_vpn, args=(VPN1_NAME,), daemon=True).start()
        elif action == "disconnect":
            threading.Thread(target=disconnect_vpn, args=(VPN1_NAME,), daemon=True).start()
    elif vpn == "vpn2":
        if action == "connect":
            threading.Thread(target=connect_vpn, args=(VPN2_NAME,), daemon=True).start()
        elif action == "disconnect":
            threading.Thread(target=disconnect_vpn, args=(VPN2_NAME,), daemon=True).start()
    return jsonify({"status": "ok"})

@app.route("/set_logic_gate", methods=["POST"])
def set_logic_gate():
    req = request.json
    logic_gate = req.get("logic_gate", "").upper()
    if logic_gate in ["AND", "OR", "XOR", "NAND", "NOR", "XNOR"]:
        with data_store_lock:
            data_store["logic_gate"] = logic_gate
        print(f"Logic gate set to {logic_gate}")
        return jsonify({"status": "ok"})
    else:
        return jsonify({"status": "error", "message": "Invalid logic gate"}), 400

def main():
    print("Starting setup...")

    interfaces = get_interfaces()
    usb_if, wifi_if = guess_usb_wifi_interfaces(interfaces)

    vpn1_ip = resolve_ip(VPN1_SERVER_DOMAIN)
    vpn2_ip = resolve_ip(VPN2_SERVER_DOMAIN)

    print("Adding routes to bind VPN servers to correct interfaces...")
    add_route(vpn1_ip, usb_if)
    add_route(vpn2_ip, wifi_if)

    print("Connecting to VPNs via Tunnelblick...")
    connect_vpn(VPN1_NAME)
    time.sleep(5)
    connect_vpn(VPN2_NAME)
    time.sleep(5)

    interfaces = get_interfaces()
    vpn_ips = [ip for iface, ip in interfaces.items() if iface.startswith("utun")]
    print(f"Detected VPN tunnel IPs: {vpn_ips}")

    global VPN1_UDP_IP, VPN2_UDP_IP
    if len(vpn_ips) >= 2:
        VPN1_UDP_IP, VPN2_UDP_IP = vpn_ips[0], vpn_ips[1]
    else:
        print("Could not detect two VPN tunnel IPs, please enter manually:")
        VPN1_UDP_IP = input("VPN1 UDP IP: ")
        VPN2_UDP_IP = input("VPN2 UDP IP: ")

    # Start UDP listener threads
    threading.Thread(target=listen_on, args=(VPN1_UDP_IP, VPN1_UDP_PORT, 1), daemon=True).start()
    threading.Thread(target=listen_on, args=(VPN2_UDP_IP, VPN2_UDP_PORT, 2), daemon=True).start()

    # Run Flask app in main thread
    app.run(port=5000)

if __name__ == "__main__":
    main()
