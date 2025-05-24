TOR.md

Dual-VPN Logic Gate Over Tor

This system sets up two Tor Hidden Services, each representing a VPN endpoint. The server listens for incoming TCP connections on two ports (e.g. 5000 and 5001) and evaluates incoming data based on a logic gate (AND, OR, XOR, etc.).

Features
	•	Fully over Tor (no VPN or UDP required)
	•	TCP-based communication
	•	Logic gate filtering on incoming messages
	•	Runs two independent listener threads
	•	Tor SOCKS5 proxy client support

⸻

1. Requirements
	•	Python 3.7+
	•	Tor installed and running locally
	•	PySocks:

pip install pysocks



⸻

2. Tor Hidden Service Configuration

Edit your Tor config file (usually /etc/tor/torrc or /usr/local/etc/tor/torrc):

# VPN1 Hidden Service
HiddenServiceDir /var/lib/tor/vpn1_service/
HiddenServicePort 5000 127.0.0.1:5000

# VPN2 Hidden Service
HiddenServiceDir /var/lib/tor/vpn2_service/
HiddenServicePort 5001 127.0.0.1:5001

Then restart Tor:

sudo systemctl restart tor

Check the .onion addresses:

cat /var/lib/tor/vpn1_service/hostname
cat /var/lib/tor/vpn2_service/hostname

Update your Python script with those .onion addresses:

VPN1_ONION_ADDR = "xyz123abc456.onion"
VPN2_ONION_ADDR = "uvw789def012.onion"


⸻

3. Running the Server

Start the server with:

python tor_logic_server.py

It will:
	•	Listen on 127.0.0.1:5000 and 127.0.0.1:5001
	•	Accept connections from Tor Hidden Services
	•	Process incoming messages using the selected LOGIC_GATE type

You can modify this in the script:

LOGIC_GATE = "AND"  # or OR, XOR, NAND, NOR, XNOR


⸻

4. Sending Messages via Tor

Use the connect_via_tor() function (included in the script) to send test messages through Tor:

connect_via_tor("xyz123abc456.onion", 5000, b"hello")
connect_via_tor("uvw789def012.onion", 5001, b"hello")

Tor must be running and listening on 127.0.0.1:9050.

⸻

5. Logic Gate Behavior

The logic gate processes incoming identical messages (b"hello", etc.) from both services and only acknowledges when the logic condition is met. Example:
	•	AND → requires both VPN1 and VPN2 to send the same message.
	•	OR → requires at least one.
	•	XOR → only if exactly one sends the message.
	•	etc.

Once the condition is satisfied, the key is deleted from memory.

⸻

6. Security Notes
	•	All data is transmitted over Tor (end-to-end encrypted and anonymized).
	•	Messages are ephemeral and stored in-memory only.
	•	You may add HMAC signatures or encryption for message authenticity and integrity.

⸻

7. Example Workflow

Step 1: Start the server

python tor_logic_server.py

Step 2: On another device or through another Tor instance, send a message:

connect_via_tor("xyz123abc456.onion", 5000, b"unlock")
connect_via_tor("uvw789def012.onion", 5001, b"unlock")

Server output:

Received on VPN1: b'unlock'
Received on VPN2: b'unlock'
AND Logic Passed: condition met for data: b'unlock'


⸻

8. Troubleshooting
	•	Can’t connect via onion address: Ensure the hidden service is running and Tor is listening on port 9050.
	•	Socket bind error: Make sure no other service is using ports 5000 and 5001.
	•	Tor not running: Start Tor via sudo systemctl start tor or equivalent on your system.

⸻

9. Optional Enhancements
	•	Add logging or database persistence
	•	Add HMAC authentication on messages
	•	Integrate a GUI or web dashboard
	•	Support more advanced message routing/filtering

⸻
