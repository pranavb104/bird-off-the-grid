#!/usr/bin/env bash
#
# Set up a Wi-Fi access point on Raspberry Pi OS Trixie using NetworkManager.
# Run on the Pi:   sudo ./setup-ap.sh
#
set -euo pipefail

SSID="birdnet"
CON_NAME="MyPiAP"
IFACE="${IFACE:-wlan0}"
BAND="bg"                 # bg = 2.4 GHz (compatible), a = 5 GHz
CHANNEL="${CHANNEL:-6}"
AP_IP="${AP_IP:-192.168.4.1/24}"   # blank = NM default (10.42.0.1/24)

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root (sudo)." >&2
  exit 1
fi

read -r -s -p "Wi-Fi password (8+ chars, blank = open network): " PSK
echo
if [ -n "$PSK" ] && [ "${#PSK}" -lt 8 ]; then
  echo "Password must be at least 8 characters." >&2
  exit 1
fi

if ! systemctl is-active --quiet NetworkManager; then
  echo "NetworkManager is not active. Enable it with:" >&2
  echo "  sudo systemctl enable --now NetworkManager" >&2
  exit 1
fi

if ! nmcli -t -f DEVICE device status | grep -qx "$IFACE"; then
  echo "Interface '$IFACE' not found. Available devices:" >&2
  nmcli device status >&2
  exit 1
fi

if nmcli -t -f NAME connection show | grep -qx "$CON_NAME"; then
  echo "Removing existing connection '$CON_NAME'..."
  nmcli connection delete "$CON_NAME"
fi

echo "Creating AP connection '$CON_NAME' (SSID: $SSID) on $IFACE..."
nmcli connection add \
  type wifi \
  ifname "$IFACE" \
  con-name "$CON_NAME" \
  autoconnect yes \
  ssid "$SSID"

nmcli connection modify "$CON_NAME" \
  802-11-wireless.mode ap \
  802-11-wireless.band "$BAND" \
  802-11-wireless.channel "$CHANNEL" \
  ipv4.method shared \
  ipv6.method disabled \
  connection.autoconnect-priority 100

if [ -n "$AP_IP" ]; then
  nmcli connection modify "$CON_NAME" ipv4.addresses "$AP_IP"
fi

if [ -n "$PSK" ]; then
  nmcli connection modify "$CON_NAME" \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.proto rsn \
    wifi-sec.pairwise ccmp \
    wifi-sec.group ccmp \
    wifi-sec.psk "$PSK"
  echo "WPA2 security enabled."
else
  echo "Open network (no password)."
fi

echo "Bringing AP up..."
nmcli connection up "$CON_NAME"

sleep 1
CURRENT_IP="$(ip -4 -o addr show "$IFACE" | awk '{print $4}' | head -n1)"

cat <<EOF

AP is up and will auto-start on every boot.
  Connection : $CON_NAME
  SSID       : $SSID
  Interface  : $IFACE
  AP IP      : ${CURRENT_IP:-pending}
  Clients    : get DHCP leases from NetworkManager (same /24 as AP IP).

Useful commands:
  nmcli connection show $CON_NAME            # inspect
  sudo nmcli connection down $CON_NAME       # stop AP
  sudo nmcli connection up   $CON_NAME       # start AP
  sudo nmcli connection delete $CON_NAME     # remove entirely
EOF
