#!/usr/bin/env bash
set -euo pipefail

DEVICE="${1:-/dev/osrbot_base}"

echo "Checking OSRacer device: ${DEVICE}"
if [[ -e "${DEVICE}" ]]; then
  ls -l "${DEVICE}"
  exit 0
fi

echo "MISSING ${DEVICE}"
echo
echo "Available serial devices:"
ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true
echo
echo "If the vehicle is connected, install the udev rule and reconnect USB:"
echo "  ros2 run osracer_base install_udev_rules"
exit 1
