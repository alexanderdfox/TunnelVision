import subprocess
import re
import socket
import threading
import time
import os

# User inputs - edit these

VPN1_OVPN_PATH = "/path/to/vpn_usb.ovpn"
VPN2_OVPN_PATH = "/path/to/vpn_wifi.ovpn"

VPN1_NAME = "VPN-USB"   # The name as shown in Tunnelblick config (or you can parse from ovpn filename)
VPN2_NAME = "VPN-WiFi"

# VPN server domains (or IPs) to route correctly
VPN1_SERVER_DOMAIN = "vpn-usb.example.com"
VPN2_SERVER_DOMAIN = "vpn-wifi.example.com"

# Ports and IPs for the AND logic UDP server - change to VPN-assigned IPs after VPN connects
VPN1_UDP_IP = None  # will detect later or input manually
VPN1_UDP_PORT = 5000

VPN2_UDP_IP = None
VPN2_UDP_PORT = 5001

# ---------------------


def run_cmd(cmd, sudo=False):
	if sudo:
		cmd = ["sudo"] + cmd
	print(f"Running command: {' '.join(cmd)}")
	proc = subprocess.run(cmd, capture_output=True, text=True)
	if proc.returncode != 0:
		print(f"Error running command: {proc.stderr}")
	return proc.stdout.strip()


def get_interfaces():
	# Get all active interfaces with IPs (simple parsing)
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
	# Very rough guess: USB tether usually has 'en' and no 'Wi-Fi' in name, Wi-Fi is usually 'en0' or 'en1'
	# We'll ask user if ambiguous

	usb_if = None
	wifi_if = None

	# Check interfaces with IPs
	for iface, ip in interfaces.items():
		# iPhone USB tether is often called 'en5' or 'en6', Wi-Fi 'en0' or 'en1'
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
	# Tunnelblick CLI command to connect
	# tunnelblickcli -c "VPN Name"
	cmd = ["/Applications/Tunnelblick.app/Contents/Resources/client/bin/tunnelblickcli", "-c", tunnelblick_name]
	output = run_cmd(cmd)
	print(f"Tunnelblick connect output for {tunnelblick_name}:\n{output}")


def disconnect_vpn(tunnelblick_name):
	cmd = ["/Applications/Tunnelblick.app/Contents/Resources/client/bin/tunnelblickcli", "-d", tunnelblick_name]
	output = run_cmd(cmd)
	print(f"Tunnelblick disconnect output for {tunnelblick_name}:\n{output}")


def listen_on(ip, port, vpn_id, data_store):
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		sock.bind((ip, port))
	except Exception as e:
		print(f"Error binding {ip}:{port} - {e}")
		return

	print(f"Listening on {ip}:{port} for VPN{vpn_id}")

	while True:
		data, addr = sock.recvfrom(4096)
		print(f"Received on VPN{vpn_id}: {data} from {addr}")

		key = data
		if key in data_store and data_store[key] != vpn_id:
			print(f"AND Logic Passed: Matching data received from both VPNs: {data}")
			del data_store[key]  # remove processed
		else:
			data_store[key] = vpn_id


def main():
	print("Starting setup...")

	interfaces = get_interfaces()
	usb_if, wifi_if = guess_usb_wifi_interfaces(interfaces)

	vpn1_ip = resolve_ip(VPN1_SERVER_DOMAIN)
	vpn2_ip = resolve_ip(VPN2_SERVER_DOMAIN)

	print(f"Adding routes to bind VPN servers to correct interfaces...")
	add_route(vpn1_ip, usb_if)
	add_route(vpn2_ip, wifi_if)

	print("Connecting to VPNs via Tunnelblick...")
	connect_vpn(VPN1_NAME)
	time.sleep(5)  # wait for connection
	connect_vpn(VPN2_NAME)
	time.sleep(5)

	# Refresh interfaces to detect VPN IPs
	interfaces = get_interfaces()
	print(f"Updated interfaces after VPN connect: {interfaces}")

	# Guess VPN tunnel IPs by looking for utun interfaces or by IP range
	vpn_ips = [ip for iface, ip in interfaces.items() if iface.startswith("utun")]
	print(f"Detected VPN tunnel IPs: {vpn_ips}")

	if len(vpn_ips) >= 2:
		global VPN1_UDP_IP, VPN2_UDP_IP
		VPN1_UDP_IP, VPN2_UDP_IP = vpn_ips[0], vpn_ips[1]
	else:
		print("Could not detect two VPN tunnel IPs, please enter manually:")
		VPN1_UDP_IP = input("VPN1 UDP IP: ")
		VPN2_UDP_IP = input("VPN2 UDP IP: ")

	data_store = {}

	thread1 = threading.Thread(target=listen_on, args=(VPN1_UDP_IP, VPN1_UDP_PORT, 1, data_store), daemon=True)
	thread2 = threading.Thread(target=listen_on, args=(VPN2_UDP_IP, VPN2_UDP_PORT, 2, data_store), daemon=True)

	thread1.start()
	thread2.start()

	print("AND logic UDP server running. Press Ctrl+C to exit.")
	try:
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Exiting...")
		disconnect_vpn(VPN1_NAME)
		disconnect_vpn(VPN2_NAME)


if __name__ == "__main__":
	main()
