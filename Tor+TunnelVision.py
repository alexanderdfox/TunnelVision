import socket
import threading
import time
import socks

# --------------- USER CONFIG -------------------

LOGIC_GATE = "AND"  # Options: AND, OR, XOR, NAND, NOR, XNOR

VPN1_ONION_ADDR = "abcdefg12345.onion"
VPN2_ONION_ADDR = "hijklmn67890.onion"

VPN1_PORT = 5000
VPN2_PORT = 5001

# ----------------------------------------------

data_store = {}

def logic_gate_eval(gate, sources):
    set_sources = set(sources.values())
    if gate == "AND":
        return len(set_sources) == 2
    elif gate == "OR":
        return len(set_sources) >= 1
    elif gate == "XOR":
        return len(set_sources) == 2
    elif gate == "NAND":
        return not (len(set_sources) == 2)
    elif gate == "NOR":
        return len(set_sources) == 0
    elif gate == "XNOR":
        return len(set_sources) != 2
    return False

def listen_on_tcp(ip, port, vpn_id, data_store):
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
            data = conn.recv(4096)
            if not data:
                continue
            print(f"Received on VPN{vpn_id}: {data} from {addr}")

            key = data
            data_store[key] = vpn_id

            sources = {k: v for k, v in data_store.items() if k == key}
            if logic_gate_eval(LOGIC_GATE.upper(), sources):
                print(f"{LOGIC_GATE} Logic Passed: condition met for data: {data}")
                del data_store[key]

def connect_via_tor(onion_address, port, message):
    """Connects to a Tor hidden service via SOCKS5 and sends a message."""
    s = socks.socksocket()
    s.set_proxy(socks.SOCKS5, "127.0.0.1", 9050)  # Tor default SOCKS port
    try:
        print(f"Connecting to {onion_address}:{port} via Tor SOCKS5 proxy...")
        s.connect((onion_address, port))
        s.sendall(message)
        print(f"Sent message: {message}")
    except Exception as e:
        print(f"Error connecting to Tor service: {e}")
    finally:
        s.close()

def main():
    thread1 = threading.Thread(target=listen_on_tcp, args=("127.0.0.1", VPN1_PORT, 1, data_store), daemon=True)
    thread2 = threading.Thread(target=listen_on_tcp, args=("127.0.0.1", VPN2_PORT, 2, data_store), daemon=True)

    thread1.start()
    thread2.start()

    print(f"{LOGIC_GATE} logic TCP server over Tor running on ports {VPN1_PORT} and {VPN2_PORT}. Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")

if __name__ == "__main__":
    main()
