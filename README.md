# WeLock Smart Lock BLE — Home Assistant HACS Integration & BLE Diagnostic Tools

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/Ebenhoeh80/welock-bluetooth?style=for-the-badge&color=blue)](https://github.com/Ebenhoeh80/welock-bluetooth/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.11+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#-languages)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Donate via PayPal](https://img.shields.io/badge/❤%20Donate-PayPal-00457C.svg?style=for-the-badge&logo=paypal&logoColor=white)](https://www.paypal.com/pool/9p84qTHCFr?sr=wccr)
[![Buy Me a Coffee](https://img.shields.io/badge/%E2%98%95%20Buy%20me%20a%20coffee-FFDD00.svg?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/daneben)

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
     │  3. write command  ──────────────────▶│  knob engages for ~10 s    │
```

* The cloud is contacted **only** during setup, re-authentication and unlocking. There is **no cloud polling**.
* Reachability and signal strength come from the Home Assistant Bluetooth stack; the battery level is read directly from the lock.
* Each unlock command is tied to the lock's one-byte challenge (`randomFactor`), which has only **256** possible values, so a captured command can work again whenever the same challenge value recurs — the BLE traffic is **not** replay-proof. Learned commands are also cached locally in Home Assistant's storage.

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
| `switch.<name>_offline_unlock` | Switch (configuration) | Turns [offline unlocking](#-local-offline-unlock-experimental) on or off with immediate effect; the setting is remembered across restarts. Off by default. |
| `sensor.<name>_unlocks_via_cloud` | Sensor | Number of unlocks whose command came from the WeLock cloud. Attributes: `confirmed`, `unconfirmed`, `failed`, `average_duration_ms`. |
| `sensor.<name>_unlocks_offline` | Sensor | Number of unlocks whose command came from the local cache (no cloud contact). Same attributes. |
| `event.<name>_unlock_history` | Event | One event per unlock attempt (`unlock_cloud`, `unlock_offline`, `unlock_failed`) with path, result, duration and challenge value. Shows up in the logbook and history. |
| `sensor.<name>_last_unlock_attempt` | Sensor (diagnostic) | Time of the last unlock attempt; attributes carry its result and the ten most recent attempts. |
| `sensor.<name>_last_access` | Sensor (diagnostic, disabled by default) | Last entry of the access log (who, when, how). Stays `unknown` until the `welock.fetch_access_log` service has been run once; the last fetched entries are kept across restarts. |

The exact entity IDs depend on the BLE name and the HA language.

---

## ⚙️ Options

**Settings → Devices & Services → WeLock → Configure**

| Option | Default | Range | Meaning |
| :--- | :---: | :---: | :--- |
| Show as unlocked for | 10 s | 3–60 s | How long the lock shows “unlocked” after unlocking. Then it returns to “locked”. |
| Read battery over Bluetooth every | 24 h | 0–168 h | Periodic BLE status read. `0` = only on unlock (saves the lock battery). |
| Check Bluetooth reachability every | 60 s | 10–600 s | How often reachability and RSSI are refreshed from the HA Bluetooth cache. Creates **no** radio traffic. |
| Build and use the local command cache | off | on/off | **Experimental.** Unlocks locally without the cloud when the challenge value is already known. Also available as a switch entity. See below. |

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

* **Switch:** `switch.<name>_offline_unlock` turns the feature on or off at any
  time, from the UI or an automation. It applies immediately (no reload), is
  remembered across restarts and is the same setting as the option in the
  integration's *Configure* dialog.
* **Statistics and history:** every unlock made through Home Assistant is
  recorded with the path that delivered the command (`cloud` or `offline`), the
  result and the duration. The counters and the last 100 attempts survive
  restarts and appear as the *Unlocks via cloud* / *Unlocks offline* sensors, the
  *Unlock history* event entity (logbook) and in the diagnostics download.
  *Confirmed* means the lock answered the command with a notification;
  *unconfirmed* means the command was written but no answer was seen (the lock
  does not always send one); *failed* means an error before or while writing.
* **Safety net:** if writing a **stored** command fails, that command is dropped
  from the cache, so the next unlock for that challenge value asks the cloud
  again.

### Importing a command table

If you already have the commands of your lock (a JSON file with `device_number`
and a `table` of randomFactor `"0"`..`"255"` to command, as written by
`tools/welock_offline_oracle.py --harvest`), you do not have to wait until the
integration has learned them one by one:

1. Copy the file into the Home Assistant configuration folder, for example as
   `welock-oracle-table.json` (the File editor add-on or Samba will do).
2. **Developer tools → Actions → WeLock: Import command table**, set the file
   name (the default is `welock-oracle-table.json`) and run it. The response
   shows `added`, `unchanged`, `conflicts` and `known`.
3. Turn the *Offline unlock* switch on when you want to use the commands.

The file is checked completely before anything is stored: a wrong format, an
invalid command or a table of a different lock (the `device_number` must match
the lock) rejects it. A command that is already stored is never overwritten; if
the file differs from a command learned from the cloud, the randomFactor is
listed under `conflicts` and the learned command stays. The service neither
switches offline unlocking on nor writes anything to the lock.

> ⚠️ A command table is **security-sensitive**: together with Bluetooth range it
> may be enough to unlock your door if the lock accepts the commands again. Keep
> the file private, never commit or share it, and delete it from the
> configuration folder after the import if you do not need it.

### Testing offline unlock on your own lock

To check that offline unlocking really works (and to document it), run a series
of unlocks and read the counters:

1. Let the table fill (normal use with the switch **off**) or check
   `learned_commands` on the switch.
2. Turn the switch **on**. Unlock the door several times, at least 12 s apart,
   and note by eye each time whether the cylinder really released.
3. Compare *Unlocks offline* with your notes: `confirmed` + `unconfirmed` is what
   the lock was sent, your observation is the ground truth. Challenge values that
   are not yet stored are answered by the cloud and show up under *Unlocks via
   cloud* instead.
4. For proof that **no cloud is needed**, block internet access for Home
   Assistant (or the WeLock cloud host) while repeating step 2. Offline unlocks
   still count; `unlock_failed` events with `path: cloud` show the cloud being
   unreachable.
5. Optionally run `welock.fetch_access_log` afterwards. The lock's own log
   should list the same unlocks (this logs the WeLock app out once).

> ✅ **Verified on the maintainer's lock (2026-11-20):** in a series of 30 offline
> unlocks, each with a command from the local table and without a cloud request,
> the cylinder released every time (checked by eye), and the lock confirmed all of
> them (45 of 45 offline unlocks counted in total, none failed). This is one lock
> with one firmware. A test with the cloud blocked is still to be documented. The
> option stays **off** by default and the cloud remains the default path; enable it
> once you have tested it on your own lock (see above).

> 📚 **How it works:** a short description of the Bluetooth exchange and the cloud
> request is in [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## 📜 Access log (service)

The **`welock.fetch_access_log`** service fetches the access log (who, when, by
which method) from the cloud and writes it into the *Last access* sensor
(attributes include the most recent entries).

The sensor therefore shows `unknown` until you have run the service once. It is
never refreshed by itself, but the last fetched entries are **restored after a
restart or reload**. Run the service again whenever you want fresh data, for
example from a script or an automation that you trigger yourself.

> ⚠️ Each fetch **logs other sessions of the account out** (e.g. the WeLock app),
> because a cloud login is required. It is therefore loaded **on demand only**,
> not automatically. The phone number in the raw record is intentionally **not**
> kept.

---

## 🔄 Operation & behaviour

* **Unlocking via the cloud logs the WeLock app out.** A fresh cloud login is then needed for the command — a property of the WeLock cloud. On a hit in the [local command cache](#-local-offline-unlock-experimental), the cloud login (and thus the logout) is skipped.
* **At least 12 s between two unlocks.** The knob stays engaged for 10 s and the lock takes no further command meanwhile; an earlier attempt is rejected with a message.
* **Assumed state:** the lock does not report its state. The cylinder engages the outer knob for 10 s (measured) and then re-locks mechanically on its own. “Lock” in HA only resets the display.
* **Without Bluetooth range** the lock is *unavailable*. The cloud alone cannot unlock.
* All BLE access to one lock is serialised so that battery reads and unlocks do not collide.

### How long is the cylinder free?

On the maintainer's lock the outer knob stays engaged for **10 seconds** after the
unlock command arrives and then re-locks mechanically on its own (the lock reports
no state, so this was measured by trying: the knob still turned at 10 s). That is
why *Show as unlocked for* defaults to 10 s and why the lock takes **no second
command** during that time (see the 12 s minimum between two unlocks above).
*Show as unlocked for* only controls how long Home Assistant *displays*
"unlocked"; it does not change the lock.

Other lock models or firmware may differ. To check yours: unlock through Home
Assistant, start a stopwatch when the door switches to *unlocked*, and try to turn
the cylinder after 5, 10 and 15 s (a fresh unlock for each attempt, at least 12 s
apart). Then set *Show as unlocked for* a little below the point where it stops
working.

The *Unlock history* event and the *Last unlock attempt* sensor record when the
command was written, which helps to compare the timing of several attempts.

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
| *Please wait … s* | The 12-second lock-out between two unlocks is still active. |

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

> Every unlock logs the WeLock app out, and there are at least 12 s between two unlocks.

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
├── docs/                          # Short protocol description
├── tools/                         # BLE & cloud diagnostic tools (see tools/README.md)
├── tests/                         # Unit tests + optional live smoke test (marker "live")
├── src/, index.html, package.json # Companion web app (AI Studio)
├── hacs.json · info.md            # HACS metadata & store description
├── CHANGELOG.md · CONTRIBUTING.md · SECURITY.md
└── LICENSE                        # MIT
```

---

## 🗺️ Roadmap & ideas

Planned and under consideration — **give a 👍 to what matters to you**, and bring your own ideas:

- 🔜 Optional automatic access-log refresh after each unlock
- 💡 Connect ahead when you arrive (shorter wait for an unlock)
- 💡 Guide for a Bluetooth proxy next to the door
- ✅ Offline unlock verified on a real lock (2.3.0)

➡️ All ideas & voting: **[Discussions → Ideas](https://github.com/Ebenhoeh80/welock-bluetooth/discussions/categories/ideas)**

---

## 📄 License

Licensed under the MIT License, see [LICENSE](LICENSE).

---

## ❤️ Support this project

<div align="center">

**I build and maintain this integration in my free time, and cover the running costs — my time, electricity, and the development tools and IT equipment I use — out of my own pocket.**

If it saves you time or trouble, a small voluntary tip helps keep the project going. Every contribution, however small, is hugely appreciated. Thank you! 🙏

<a href="https://www.paypal.com/pool/9p84qTHCFr?sr=wccr">
  <img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate via PayPal" height="42">
</a>
<a href="https://buymeacoffee.com/daneben">
  <img src="https://img.shields.io/badge/%E2%98%95%20Buy%20me%20a%20coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee" height="42">
</a>

</div>
