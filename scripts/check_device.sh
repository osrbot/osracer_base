#!/usr/bin/env bash
set -euo pipefail

DEVICE="${1:-/dev/osrbot_base}"

echo "Checking OSRacer device: ${DEVICE}"
if [[ -e "${DEVICE}" ]]; then
  ls -l "${DEVICE}"
  if command -v udevadm >/dev/null 2>&1; then
    UDEV_INFO="$(udevadm info --query=property --name="${DEVICE}" 2>/dev/null || true)"
    VENDOR_ID="$(printf '%s\n' "${UDEV_INFO}" | awk -F= '$1 == "ID_VENDOR_ID" {print $2; exit}')"
    MODEL_ID="$(printf '%s\n' "${UDEV_INFO}" | awk -F= '$1 == "ID_MODEL_ID" {print $2; exit}')"
    SERIAL="$(printf '%s\n' "${UDEV_INFO}" | awk -F= '$1 == "ID_SERIAL_SHORT" {print $2; exit}')"
    RAW_VENDOR="$(printf '%s\n' "${UDEV_INFO}" | awk -F= '$1 == "ID_VENDOR" {print $2; exit}')"
    RAW_MODEL="$(printf '%s\n' "${UDEV_INFO}" | awk -F= '$1 == "ID_MODEL" {print $2; exit}')"

    MANUFACTURER="${RAW_VENDOR//_/ }"
    PRODUCT="${RAW_MODEL//_/ }"

    [[ -n "${VENDOR_ID}" ]] && echo "USB vendor ID: ${VENDOR_ID}"
    [[ -n "${MODEL_ID}" ]] && echo "USB product ID: ${MODEL_ID}"
    [[ -n "${MANUFACTURER}" ]] && echo "Manufacturer: ${MANUFACTURER}"
    [[ -n "${PRODUCT}" ]] && echo "Product: ${PRODUCT}"
    [[ -n "${SERIAL}" ]] && echo "Serial: ${SERIAL}"
  fi
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
