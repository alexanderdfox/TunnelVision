#!/bin/bash

# Assumes VPN1 is utun0, VPN2 is utun1
VPN1_IFACE="utun0"
VPN2_IFACE="utun1"

# IPs or hosts to route through each VPN
VPN1_TARGET="httpbin.org"
VPN2_TARGET="httpbin.org"

# Resolve the IP addresses
VPN1_IP=$(dig +short $VPN1_TARGET | head -n 1)
VPN2_IP=$VPN1_IP  # same destination

# Route IP via respective interface
sudo route -n add -host $VPN1_IP -interface $VPN1_IFACE
sudo route -n add -host $VPN2_IP -interface $VPN2_IFACE

echo "Routing set: $VPN1_IP -> $VPN1_IFACE, $VPN2_IP -> $VPN2_IFACE"
