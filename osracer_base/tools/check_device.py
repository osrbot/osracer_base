import glob
from pathlib import Path


def main():
    device = Path('/dev/osrbot_base')
    print(f'Checking OSRacer device: {device}')
    if device.exists():
        print(device.resolve())
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


if __name__ == '__main__':
    main()
