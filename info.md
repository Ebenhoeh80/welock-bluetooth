# WeLock Smart Lock BLE

Unlock **WeLock smart cylinders** (Touch41, SECBN51, PCB41, SECBREBL01, …) from Home Assistant over **Bluetooth**, using a local adapter or an **ESPHome Bluetooth proxy**. The WeLock cloud is only used to compute the one-time unlock command for a fresh challenge from the lock. The cloud is never polled.

## Features
- 🔓 Unlock: BLE challenge → cloud command → BLE write (state is assumed, the knob relocks mechanically)
- 🧭 Guided setup that enforces the workflow: Bluetooth discovery → cloud login → lock selection → Bluetooth check (no unlock)
- 🔋 Battery read directly from the lock, 📶 RSSI, 🟢 "Bluetooth reachable" sensor
- 🔁 Reauthentication flow, options for relock display, battery interval and reachability interval
- 🛡️ Password and token never logged; diagnostics redact account and password
- 🌐 Deutsch · English · Español · Français

## Requirements
- Home Assistant **2024.11** or newer
- Bluetooth adapter or ESPHome Bluetooth proxy (active connections) within reach of the door
- WeLock app account (email + password). No WiFiBox and no client ID required.

## Notes
- ⚠️ Every cloud login (setup and **every unlock**) ends other sessions of the account, e.g. the WeLock app.
- Minimum 30 s between two unlocks.

Full documentation: [README](https://github.com/Ebenhoeh80/welock-bluetooth#readme)
