"""Python-Skript zum Auslesen des Akkuzustands und Status von BLE-Geräten per Argument."""

import asyncio
import subprocess
import sys


def ensure_dependencies() -> None:
    """Prüft, ob pip und bleak vorhanden sind, und installiert bleak falls nötig."""
    try:
        import pip
    except ImportError:
        print("pip ist nicht installiert. Versuche pip zu installieren...", file=sys.stderr)
        try:
            import ensurepip
            ensurepip.bootstrap()
        except Exception as e:
            print(f"Fehler beim Installieren von pip: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        import bleak  # noqa: F401
    except ImportError:
        print("Die Bibliothek 'bleak' ist nicht installiert. Wird automatisch installiert...", file=sys.stderr)
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "bleak"])
            print("'bleak' wurde erfolgreich installiert.", file=sys.stderr)
        except subprocess.CalledProcessError as e:
            print(f"Fehler bei der Installation von 'bleak': {e}", file=sys.stderr)
            sys.exit(1)


# Abhängigkeiten vor dem Start prüfen
ensure_dependencies()

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

# UUIDs (Nordic UART Service, passend für WeLock / Smart Locks)
SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

BATTERY_REQUEST = b"\x55\x30" + b"\x00" * 13
TIMEOUT = 15.0


async def read_battery(address: str) -> None:
    print(f"Suche nach BLE-Gerät mit Adresse {address}...")
    device = await BleakScanner.find_device_by_address(address, timeout=TIMEOUT)
    if device is None:
        print(f"Fehler: Gerät mit Adresse {address} wurde nicht gefunden.", file=sys.stderr)
        return

    print("Gerät gefunden. Verbinde...")
    async with BleakClient(device, timeout=TIMEOUT) as client:
        print("Verbunden! Lese Service und Characteristics...")
        
        service = client.services.get_service(SERVICE_UUID)
        if service is None:
            print(f"Fehler: Der erwartete BLE-Service ({SERVICE_UUID}) fehlt auf dem Gerät.", file=sys.stderr)
            return

        chars = {c.uuid.lower(): c for c in service.characteristics}
        if WRITE_UUID not in chars or NOTIFY_UUID not in chars:
            print("Fehler: Erforderliche Schreib-/Benachrichtigungs-Characteristics fehlen.", file=sys.stderr)
            return

        battery_future: asyncio.Future[int] = asyncio.get_running_loop().create_future()

        def notification_handler(_sender: object, data: bytearray) -> None:
            print(f"Empfangene Rohdaten: {data.hex()}")
            if len(data) >= 4 and data[:2] == b"\x55\x30":
                battery_level = data[3]  # Prozentwert
                if not battery_future.done():
                    battery_future.set_result(battery_level)

        await client.start_notify(chars[NOTIFY_UUID], notification_handler)
        
        print("Sende Batterie-/Status-Anfrage...")
        await client.write_gatt_char(chars[WRITE_UUID], BATTERY_REQUEST, response=False)

        try:
            battery_level = await asyncio.wait_for(battery_future, timeout=5.0)
            print(f"\nAkkustand / Batteriestatus: {battery_level}%")
        except asyncio.TimeoutError:
            print("\nZeitüberschreitung: Keine gültige Batterie-Antwort vom Gerät erhalten.", file=sys.stderr)

        await client.stop_notify(chars[NOTIFY_UUID])


def main() -> int:
    if len(sys.argv) < 2:
        print("Fehler: Keine BLE-Adresse angegeben.", file=sys.stderr)
        print("Verwendung: python ble_accustatus.py <MAC-Adresse>")
        return 1

    address = sys.argv[1].strip()

    try:
        asyncio.run(read_battery(address))
        return 0
    except (BleakError, OSError, TimeoutError) as exc:
        print(f"Verbindungsfehler: {exc}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nVom Benutzer abgebrochen.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())