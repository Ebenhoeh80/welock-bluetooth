# WeLock Smart Lock — Home Assistant HACS Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/badge/version-v1.2.0-blue.svg?style=for-the-badge)](https://github.com/Ebenhoeh80/welock/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=home-assistant)](https://www.home-assistant.io)
[![Languages](https://img.shields.io/badge/languages-DE%20%7C%20EN%20%7C%20ES%20%7C%20FR-success.svg?style=for-the-badge)](#localization)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg?style=for-the-badge)](LICENSE)

Integration for **WeLock Smart Door Locks** (Touch41, SECBN51, PCB41, etc.) and the **WeLock WiFiBox Gateway** into **Home Assistant** via **HACS** (Home Assistant Community Store / Marketplace).

---

## 🌍 Languages / Sprachen / Idiomas / Langues

This integration is completely localized in 4 languages:
* 🇩🇪 **Deutsch** (Vollständige Benutzeroberfläche, Konfigurationsassistent & Sensorbeschriftung)
* 🇬🇧 **English** (Full UI, config flow, option flow, and sensor attributes)
* 🇪🇸 **Español** (Interfaz completa, asistente de configuración y entidades)
* 🇫🇷 **Français** (Interface complète, flux de configuration et entités)

---

## ✨ Features

- 🔐 **Remote Lock Control**: Trigger electronic unlock from Home Assistant dashboards, voice assistants, or automations.
- 🔋 **Battery Monitoring**: Accurate percentage sensor with low-battery alerts (`sensor.<lock_name>_battery`).
- 📶 **Gateway & Lock Connectivity**: Online/offline binary sensors for both the lock cylinder and the WeLock WiFiBox gateway.
- 🕒 **Last Unlock Method**: Tracks whether the lock was unlocked via Fingerprint, RFID Card, Passcode, App, or Cloud Gateway.
- ⚙️ **Config Flow UI**: Seamless setup directly in the Home Assistant web interface (no manual `configuration.yaml` required).
- 🔄 **Options Flow**: Customizable polling interval (10-300s) and auto-relock reset timer (3-60s).

---

## 📦 Installation

### Method 1: Via HACS (Recommended)

1. Open **Home Assistant** and navigate to **HACS** (or Community Store / Marketplace).
2. Click the three dots in the top right corner and choose **Custom repositories**.
3. Enter the repository URL:
   ```text
   https://github.com/Ebenhoeh80/welock
   ```
4. Select category **Integration** and click **Add**.
5. Search for **WeLock Smart Lock** in HACS, click **Download**, and restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release `.zip` or clone this repository.
2. Copy the `custom_components/welock` folder to your Home Assistant `config/custom_components/` directory:
   ```bash
   # Resulting directory structure:
   /config/custom_components/welock/__init__.py
   /config/custom_components/welock/manifest.json
   ...
   ```
3. Restart Home Assistant.

---

## 🔑 Obtaining API Credentials (WeLock Mobile App)

To connect your locks, you need a `Client ID` and `Client Secret`:

1. Open the official **WeLock** app on your smartphone (iOS or Android).
2. Ensure your smart lock is paired to a **WeLock WiFiBox** (required for cloud communication).
3. Open the left sidebar menu (☰) in the app.
4. Tap on the **Home Assistant** icon.
5. Copy your generated **Client ID** and **Client Secret**.

---

## 🚀 Setup in Home Assistant

1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** (bottom right).
3. Search for **WeLock Smart Lock**.
4. Enter your `Client ID` and `Client Secret` and submit.
5. Your WeLock locks and WiFiBox gateways will automatically be discovered!

---

## 💡 Automation Examples

### 1. Low Battery Alert Notification (YAML)
```yaml
alias: "WeLock Low Battery Notification"
description: "Send push notification when lock battery drops below 20%"
trigger:
  - platform: numeric_state
    entity_id: sensor.welock_front_door_battery
    below: 20
action:
  - service: notify.notify
    data:
      title: "WeLock Battery Low"
      message: "The front door lock battery is down to {{ states('sensor.welock_front_door_battery') }}%. Please replace AAA batteries soon."
mode: single
```

### 2. Auto-Unlock with NFC Tag / Doorbell
```yaml
alias: "WeLock Unlock with NFC Tag"
description: "Unlock door when authorized NFC tag is scanned"
trigger:
  - platform: tag
    tag_id: your-nfc-tag-id-here
action:
  - service: lock.unlock
    target:
      entity_id: lock.welock_front_door
```

---

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
