import socket
import threading
import time
import socks
from flask import Flask, render_template_string, request, jsonify

# -------- USER CONFIG ---------

LOGIC_GATE = "AND"  # Options: AND, OR, XOR, NAND, NOR, XNOR

VPN1_ONION_ADDR = "abcdefg12345.onion"
VPN2_ONION_ADDR = "hijklmn67890.onion"

VPN1_PORT = 5000
VPN2_PORT = 5001

TOR_SOCKS_PROXY_HOST = "127.0.0.1"
TOR_SOCKS_PROXY_PORT = 9050

# -----------------------------

app = Flask(__name__)

data_store = {
    "vpn1_msgs": [],
    "vpn2_msgs": [],
    "logic_gate": LOGIC_GATE,
    "vpn1_connected": False,
    "vpn2_connected": False,
}

data_store_lock = threading.Lock()


def logic_gate_eval(gate, sources):
    vals = list(sources.values())
    unique_vals = set(vals)
    # Simplified logic: True means message received (1), False means no message (0)
    # For demo, consider non-empty source as True
    vals_bool = [bool(v) for v in vals]

    if gate == "AND":
        return all(vals_bool)
    elif gate == "OR":
        return any(vals_bool)
    elif gate == "XOR":
        return sum(vals_bool) == 1
    elif gate == "NAND":
        return not all(vals_bool)
    elif gate == "NOR":
        return not any(vals_bool)
    elif gate == "XNOR":
        return sum(vals_bool) != 1
    return False


def listen_on_tcp(ip, port, vpn_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((ip, port))
        sock.listen()
    except Exception as e:
        print(f"Error binding {ip}:{port} - {e}")
        return

    print(f"Listening on {ip}:{port} for VPN{vpn_id}")

    while True:
        conn, addr = sock.accept()
        with conn:
            print(f"Connected by {addr} on VPN{vpn_id}")
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                message = data.decode(errors='replace').strip()
                print(f"Received on VPN{vpn_id}: {message} from {addr}")

                with data_store_lock:
                    msg_list = data_store[f"vpn{vpn_id}_msgs"]
                    msg_list.append(f"{time.strftime('%H:%M:%S')} - {message}")
                    if len(msg_list) > 50:
                        msg_list.pop(0)

                    # Mark this VPN as having received a message
                    sources = {
                        1: bool(data_store["vpn1_msgs"]),
                        2: bool(data_store["vpn2_msgs"]),
                    }
                    if logic_gate_eval(data_store["logic_gate"], sources):
                        print(f"{data_store['logic_gate']} Logic Passed: condition met for message: {message}")
                        # Clear messages after logic passes
                        data_store["vpn1_msgs"].clear()
                        data_store["vpn2_msgs"].clear()


def connect_via_tor(onion_address, port, message):
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, TOR_SOCKS_PROXY_HOST, TOR_SOCKS_PROXY_PORT)
    try:
        print(f"Connecting to {onion_address}:{port} via Tor SOCKS5 proxy...")
        s.connect((onion_address, port))
        s.sendall(message.encode())
        print(f"Sent message to {onion_address}:{port}: {message}")
        with data_store_lock:
            if onion_address == VPN1_ONION_ADDR:
                data_store["vpn1_connected"] = True
            elif onion_address == VPN2_ONION_ADDR:
                data_store["vpn2_connected"] = True
    except Exception as e:
        print(f"Error connecting to Tor service: {e}")
        with data_store_lock:
            if onion_address == VPN1_ONION_ADDR:
                data_store["vpn1_connected"] = False
            elif onion_address == VPN2_ONION_ADDR:
                data_store["vpn2_connected"] = False
    finally:
        s.close()


@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Tor TCP Logic Gate Monitor</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.4.1/dist/css/bootstrap.min.css" rel="stylesheet" />
<style>
    body { padding: 2rem; background: #f8f9fa; }
    pre { background: #212529; color: #0d6efd; padding: 1rem; border-radius: 5px; height: 300px; overflow-y: scroll; }
    .status-connected { color: #198754; font-weight: bold; }
    .status-disconnected { color: #dc3545; font-weight: bold; }
</style>
</head>
<body>
<div class="container">
    <h1 class="mb-4">Tor TCP Logic Gate Monitor</h1>

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
            <h3>VPN1 ({{ vpn1_onion }}) Status: <span id="vpn1_status" class="status-disconnected">Disconnected</span></h3>
            <button class="btn btn-primary me-2" onclick="sendTestMessage('vpn1')">Send Test Message to VPN1</button>
            <h5 class="mt-3">VPN1 Messages:</h5>
            <pre id="vpn1_msgs"></pre>
        </div>
        <div class="col-md-6">
            <h3>VPN2 ({{ vpn2_onion }}) Status: <span id="vpn2_status" class="status-disconnected">Disconnected</span></h3>
            <button class="btn btn-primary me-2" onclick="sendTestMessage('vpn2')">Send Test Message to VPN2</button>
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

async function sendTestMessage(vpn) {
    const msg = prompt("Enter test message to send:");
    if (!msg) return;
    await fetch('/send_message', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({vpn: vpn, message: msg})
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
""", vpn1_onion=VPN1_ONION_ADDR, vpn2_onion=VPN2_ONION_ADDR)


@app.route("/status")
def status():
    with data_store_lock:
        return jsonify(data_store)


@app.route("/set_logic_gate", methods=["POST"])
def set_logic_gate():
    req = request.json
    logic_gate = req.get("logic_gate", "").upper()
    if logic_gate in ["AND", "OR", "XOR", "NAND", "NOR", "XNOR"]:
        with data_store_lock:
            data_store["logic_gate"] = logic_gate
        print(f"Logic gate set to {
