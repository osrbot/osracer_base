import glob
import subprocess
from pathlib import Path


def main():
    device = Path('/dev/osrbot_base')
    print(f'Checking OSRacer device: {device}')
    if device.exists():
        print(device.resolve())
        print_udev_info(device)
        return

    print(f'MISSING {device}')
    candidates = sorted(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))
    if candidates:
        print('Available serial devices:')
        for candidate in candidates:
            print(f'  {candidate}')
    else:
        print('No /dev/ttyACM* or /dev/ttyUSB* devices found.')
    print('Install the udev rule, then reconnect the vehicle USB cable.')
    raise SystemExit(1)


def print_udev_info(device):
    try:
        result = subprocess.run(
            ['udevadm', 'info', '--query=property', '--name', str(device)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        return

    wanted = ('ID_VENDOR_ID=', 'ID_MODEL_ID=', 'ID_SERIAL_SHORT=', 'ID_MODEL=', 'ID_VENDOR=')
    for line in result.stdout.splitlines():
        if line.startswith(wanted):
            print(line)


if __name__ == '__main__':
    main()
