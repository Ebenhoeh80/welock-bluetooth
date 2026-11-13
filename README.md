# WeLock Smart Lock BLE — Home Assistant HACS Integration & BLE Diagnostic Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Ebenhoeh80/welock-bluetooth?style=for-the-badge&color=blue)](https://github.com/Ebenhoeh80/welock-bluetooth/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-languages)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)

**🌍 Language:** **🇬🇧 English** · [🇩🇪 Deutsch](README.de.md)

A suite for **WeLock smart door locks** (e.g. Touch41, SECBN51, PCB41, SECBREBL01):

1. 🏠 **Home Assistant HACS integration** (`custom_components/welock`): unlock over Bluetooth through the Home Assistant Bluetooth stack (a local adapter or an ESPHome Bluetooth proxy). The WeLock cloud only supplies the single-use unlock command. Includes a guided setup, Bluetooth discovery, and battery, signal and reachability sensors.
2. 🔬 **BLE & cloud diagnostic tools** ([`tools/`](tools/README.md)): Python utilities for BLE scanning, battery/challenge reads, GATT inspection, cloud login and unlock tests.

---

## 📑 Contents

- [How it works](#-how-it-works)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Setup in Home Assistant](#-setup-in-home-assistant)
- [Entities](#-entities)
- [Options](#-options)
- [Local offline unlock (experimental)](#-local-offline-unlock-experimental)
- [Access log (service)](#-access-log-service)
- [Operation & behaviour](#-operation--behaviour)
- [Troubleshooting](#-troubleshooting)
- [Privacy & security](#-privacy--security)
- [Diagnostic tools](#-diagnostic-tools-tools)
- [Development & tests](#-development--tests)
- [Lovelace & automation examples](#-lovelace--automation-examples)
- [Repository architecture](#-repository-architecture)

---

## 🔐 How it works

WeLock cylinders are driven locally over **Bluetooth Low Energy** (Nordic UART Service). The unlock command is computed by the **WeLock cloud** for a fresh challenge from the lock:

```text
Home Assistant                          Lock (BLE)                 WeLock cloud
     │  1. status request 55 30 00…  ───────▶│                            │
     │◀─────── 55 30 <random> <batt>  ───────│                            │
     │  2. login + /Command/UnLock (deviceNumber, deviceName, random, batt) ─▶│
     │◀──────────────────────────── 15-byte command "U1…" ─────────────────────│
     │  3. write command  ──────────────────▶│  knob engages for ~7 s     │
```

* The cloud is contacted **only** during setup, re-authentication and unlocking. There is **no cloud polling**.
* Reachability and signal strength come from the Home Assistant Bluetooth stack; the battery level is read directly from the lock.
* Each command is valid for a single challenge. An intercepted command cannot be replayed.

---

## 📋 Requirements

### For the Home Assistant integration
* **Home Assistant 2024.11.0** or newer, with **HACS** or file access to `/config/custom_components/`.
* **Bluetooth within range of the door:** a Bluetooth adapter on the HA host, or an **ESPHome Bluetooth proxy** with active connections (`bluetooth_proxy: active: true`). The integration needs a *connectable* path to the lock; passive listening is not enough.
* **WeLock account:** the email and password of the WeLock app (iOS/Android). A separate client ID or a WiFiBox is **not** required.
* The lock must be set up in the WeLock app. The integration reads the lock number (`deviceNumber`) and BLE module (`ble[].deviceName`, `ble[].deviceMac`) from the account.

### For the diagnostic tools
* Python **3.10+**, a Bluetooth 4.0 LE adapter, and the `bleak` package (`pip install -r tools/requirements-ble.txt`).
* Operating-system permissions: Linux with BlueZ (`rfkill list`, group `bluetooth`), macOS 12+ with Bluetooth access granted to the terminal, Windows 10 (1809+) or 11 with Bluetooth enabled.

### Radio & hardware
* Aim for **under 3–5 m** between the lock and the adapter/proxy. Metal doors, fittings and thick walls attenuate 2.4 GHz heavily.
* The lock accepts **only one BLE connection at a time**. If the WeLock app is connected in the foreground, it rejects further connections.
* On weak batteries (< 20 %) the firmware often refuses radio commands. Use fresh AAA batteries.

---

## 📦 Installation

### Via HACS (recommended)
1. Open **HACS** → three-dots menu → **Custom repositories**.
2. Enter the URL `https://github.com/Ebenhoeh80/welock-bluetooth`, choose category **Integration**, click **Add**.
3. Search for **WeLock Smart Lock BLE** → **Download** → **restart** Home Assistant.

### Manually
1. Download the latest [release](https://github.com/Ebenhoeh80/welock-bluetooth/releases).
2. Copy the folder `custom_components/welock` to `/config/custom_components/welock/`.
3. Restart Home Assistant.

---

## 🚀 Setup in Home Assistant

Setup follows the WeLock workflow and **validates each step before moving on**. One entry corresponds to one BLE module of a lock. For several locks, create several entries.

| Step | What happens | Condition to continue |
| :--- | :--- | :--- |
| **0. Start** | HA discovers `WeLock*` modules over Bluetooth and lists them under *Discovered*. Alternatively: **Settings → Devices & Services → Add Integration → WeLock Smart Lock BLE**. | – |
| **1. Cloud login** | Email and password of the WeLock app. ⚠️ Logging in **ends other sessions** of the account, e.g. the app. Do not use the app during setup. | Login succeeds and the account contains at least one lock with a BLE module. For discovery: the found module belongs to the account. |
| **2. Select lock** | List from the cloud: BLE name, MAC address, lock number, battery per cloud, and whether HA currently has the module **in range**. A module in range is preselected. | The module is not already set up. |
| **3. Bluetooth check** | HA connects to the lock and reads battery and challenge (`55 30`). **No unlock is sent.** | An adapter or proxy reaches the lock **and** the lock answers. Otherwise an error is shown and you can retry. |

After step 3, HA creates the device with all entities.

**Re-authentication:** if the cloud later rejects the password (e.g. after a password change), HA starts re-authentication automatically. You only enter the password there. HA also checks that the lock still belongs to the account.

---

## 🧩 Entities

| Entity | Type | Description |
| :--- | :--- | :--- |
| `lock.<name>` | Lock | Unlock via BLE + cloud command. The state is *assumed* (see below). Unavailable when no adapter/proxy reaches the lock. |
| `sensor.<name>_battery` | Sensor (diagnostic) | Battery level in %, read directly from the lock. |
| `sensor.<name>_signal_strength` | Sensor (diagnostic, disabled by default) | RSSI of the latest Bluetooth advertisements in dBm. |
| `binary_sensor.<name>_bluetooth_reachable` | Binary sensor (diagnostic) | On while a connectable adapter or proxy sees the lock. |
| `sensor.<name>_learned_offline_commands` | Sensor (diagnostic, disabled by default) | Number of locally learned unlock commands (out of 256) plus coverage. See [Local offline unlock](#-local-offline-unlock-experimental). |
| `sensor.<name>_last_access` | Sensor (diagnostic, disabled by default) | Last entry of the access log (who, when, how). Filled only by the `welock.fetch_access_log` service. |

The exact entity IDs depend on the BLE name and the HA language.

---

## ⚙️ Options

**Settings → Devices & Services → WeLock → Configure**

| Option | Default | Range | Meaning |
| :--- | :---: | :---: | :--- |
| Show as unlocked for | 7 s | 3–60 s | How long the lock shows “unlocked” after unlocking. Then it returns to “locked”. |
| Read battery over Bluetooth every | 24 h | 0–168 h | Periodic BLE status read. `0` = only on unlock (saves the lock battery). |
| Check Bluetooth reachability every | 60 s | 10–600 s | How often reachability and RSSI are refreshed from the HA Bluetooth cache. Creates **no** radio traffic. |
| Build and use the local command cache | off | on/off | **Experimental.** Unlocks locally without the cloud when the challenge value is already known. See below. |

---

## 🔓 Local offline unlock (experimental)

The cloud unlock command depends **only on the `randomFactor` byte** of the BLE
challenge (not on the battery level or the BLE key). There are therefore at most
**256 distinct commands** per lock. The integration **learns** every command the
cloud returns and stores it per config entry.

* The table fills itself **during normal use** — even while the option is off
  (the cloud is still used, but every command is learned along the way). The
  *Learned offline commands* sensor shows the progress (x/256).
* With the option enabled, a **known** challenge value is answered **locally
  without a cloud login** — faster and without logging the WeLock app out.
* A stored command is **byte-identical** to what the cloud would return (no
  self-generated payload) and is re-validated before every use.

> ⚠️ **Not yet mechanically verified on hardware.** The option is therefore **off**
> by default and the cloud stays the default path. Only enable it once you have
> successfully tested a locally generated command on the actual lock.

> 📚 **How this was found:** the full reverse-engineering methodology (BLE
> protocol, cloud API, differential analysis, legal basis § 69e UrhG / German
> copyright law) is documented under [`docs/`](docs/README.md).

## 📜 Access log (service)

The **`welock.fetch_access_log`** service fetches the access log (who, when, by
which method) from the cloud and writes it into the *Last access* sensor
(attributes include the most recent entries).

> ⚠️ Each fetch **logs other sessions of the account out** (e.g. the WeLock app),
> because a cloud login is required. It is therefore loaded **on demand only**,
> not automatically. The phone number in the raw record is intentionally **not**
> kept.

---

## 🔄 Operation & behaviour

* **Unlocking via the cloud logs the WeLock app out.** A fresh cloud login is then needed for the command — a property of the WeLock cloud. On a hit in the [local command cache](#-local-offline-unlock-experimental), the cloud login (and thus the logout) is skipped.
* **At least 30 s between two unlocks.** An earlier attempt is rejected with a message.
* **Assumed state:** the lock does not report its state. The cylinder engages the outer knob for about 7 s and then re-locks mechanically on its own. “Lock” in HA only resets the display.
* **Without Bluetooth range** the lock is *unavailable*. The cloud alone cannot unlock.
* All BLE access to one lock is serialised so that battery reads and unlocks do not collide.

---

## 🩺 Troubleshooting

| Message / symptom | Cause & fix |
| :--- | :--- |
| *Email address or password is incorrect* | Check the WeLock app credentials. Cross-check with the [tools](#-diagnostic-tools-tools): `tools/run_cloud_login.*`. |
| *No lock with a Bluetooth module was found in this account* | The lock is not set up in the app, or without a BLE module. |
| *The discovered lock does not belong to this WeLock account* | Discovery found a foreign or differently assigned module. Log in with the correct account or start setup manually. |
| *No Bluetooth adapter or proxy reaches the lock* | Move the proxy closer to the door, set `active: true` on the ESPHome proxy, close the app (only one BLE connection at a time). |
| *The lock did not answer the status request* | Wake the lock (touch the knob), check the batteries, retry. |
| Lock permanently *unavailable* | Check the “Bluetooth reachable” binary sensor. HA cannot see the lock; causes as above. |
| *Please wait … s* | The 30-second lock-out between two unlocks is still active. |

**Debug logs** (`configuration.yaml`):
```yaml
logger:
  logs:
    custom_components.welock: debug
```
The **diagnostics** (Device → Download diagnostics) contain neither the account nor the password.

---

## 🛡 Privacy & security

* Email and password live only in the Home Assistant config entry. The cloud token is kept in memory only and discarded after every request.
* Logs and error messages contain neither the password nor the token. The diagnostics redact the account and password.
* Cloud communication runs exclusively over HTTPS to `clientapi.welock.com.cn`, without redirects.
* Please report security issues confidentially, see [SECURITY.md](SECURITY.md).

---

## 🛠 Diagnostic tools (`tools/`)

For analysis and troubleshooting outside Home Assistant:

```bash
pip install -r tools/requirements-ble.txt

./tools/welock_tools.sh                    # Interactive menu (Windows: .\tools\welock_tools.ps1)
./tools/run_ble_scan.sh                    # Scan for BLE devices & locks
./tools/run_ble_battery.sh "AA:BB:CC:..."  # Read battery & challenge
./tools/run_ble_probe.sh --address "AA:BB:..." --connect
./tools/run_cloud_login.sh                 # Check cloud account & devices
./tools/run_command_probe.sh               # Challenge + cloud command, without unlocking
./tools/run_unlock.sh                      # Authorised unlock test
```

Every `.sh` has an identically named `.ps1` for Windows. All parameters, protocol details and workflows are in [**tools/README.md**](tools/README.md).

---

## 🧪 Development & tests

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install pytest aiohttp ruff black
pytest                       # Unit tests; the live test is skipped
ruff check custom_components/ tools/ tests/
black --check custom_components/ tools/ tests/
```

### Optional live smoke test against the real cloud
`tests/test_live_smoke.py` (marker `live`) checks cloud login and the lock list **read-only**, optionally also the HA Bluetooth cache. The unlock and BLE write paths are actively blocked in the test. It **never runs in CI** and only with an explicit opt-in:

```powershell
# Set variables in the current shell only — do not create a .env file!
$env:WELOCK_LIVE_TEST = "1"
$env:WELOCK_USER      = "<account>"
$env:WELOCK_PASSWORD  = Read-Host -MaskAsPlainText "WELOCK password"
# optional: $env:WELOCK_LOCK_ID, $env:WELOCK_HA_BT_CACHE = "<config>\.storage\bluetooth.remote_scanners"
pytest -m live -s
Remove-Item Env:WELOCK_PASSWORD
```

⚠️ The login ends the WeLock app session. Do not use the app during the test. The output contains neither the password nor the token.

Further notes are in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 💡 Lovelace & automation examples

### Tile card
```yaml
type: tile
entity: lock.welock_front_door
name: Front door
features:
  - type: lock-commands
```

### Low-battery warning (< 20 %)
```yaml
alias: "WeLock: battery low"
triggers:
  - trigger: numeric_state
    entity_id: sensor.welock_front_door_battery
    below: 20
actions:
  - action: notify.notify
    data:
      title: "⚠️ WeLock battery almost empty"
      message: "Battery: {{ states('sensor.welock_front_door_battery') }} %. Please replace the AAA batteries."
mode: single
```

### Open the front door with an NFC tag
```yaml
alias: "WeLock: unlock front door via NFC"
triggers:
  - trigger: tag
    tag_id: front-door-nfc
actions:
  - action: lock.unlock
    target:
      entity_id: lock.welock_front_door
mode: single
```

> Every unlock logs the WeLock app out, and there are at least 30 s between two unlocks.

---

## 🌍 Languages

Setup, options and entities are localised: 🇩🇪 Deutsch · 🇬🇧 English · 🇪🇸 Español · 🇫🇷 Français.

The project documentation is available in **[English](README.md)** and **[Deutsch](README.de.md)**.

---

## 🏗 Repository architecture

```text
welock-bluetooth/
├── custom_components/welock/      # Home Assistant HACS integration
│   ├── __init__.py                # Setup/unload
│   ├── manifest.json              # Manifest incl. Bluetooth matcher "WeLock*"
│   ├── config_flow.py             # Setup: discovery → login → select → BLE check; reauth; options
│   ├── api.py                     # WeLock cloud client (login, device list, unlock command)
│   ├── ble.py                     # BLE transport over HA Bluetooth (challenge, write command)
│   ├── protocol.py                # Nordic UART UUIDs, status/command formats (no I/O)
│   ├── coordinator.py             # Reachability, RSSI, battery; serialises BLE access
│   ├── entity.py                  # Shared device info
│   ├── lock.py                    # Lock entity (assumed state, auto-relock display)
│   ├── sensor.py                  # Battery, signal strength
│   ├── binary_sensor.py           # Bluetooth reachable
│   ├── diagnostics.py             # Diagnostics (redacted)
│   ├── strings.json               # Base strings (EN)
│   └── translations/              # de, en, es, fr
├── docs/                          # Reverse-engineering methodology (anonymised, § 69e UrhG)
├── tools/                         # BLE & cloud diagnostic tools (see tools/README.md)
├── tests/                         # Unit tests + optional live smoke test (marker "live")
├── archiv/                        # Archived development snapshots
├── src/, index.html, package.json # Companion web app (AI Studio)
├── hacs.json · info.md            # HACS metadata & store description
├── CHANGELOG.md · CONTRIBUTING.md · SECURITY.md
└── LICENSE                        # MIT
```

---

## 📄 License

Licensed under the MIT License, see [LICENSE](LICENSE).
