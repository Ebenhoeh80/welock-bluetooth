"""Constants for the WeLock Smart Lock integration."""

from typing import Final

DOMAIN: Final = "welock"

# Config entry data keys
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_ADDRESS: Final = "address"
CONF_DEVICE_NUMBER: Final = "device_number"
CONF_BLE_NAME: Final = "ble_name"
CONF_MODEL: Final = "model"

# Option keys
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AUTO_RELOCK_DELAY: Final = "auto_relock_delay"
CONF_BATTERY_INTERVAL: Final = "battery_interval"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds, local Bluetooth presence/RSSI only
DEFAULT_AUTO_RELOCK_DELAY: Final = 7  # seconds (knob engages for ~7 s)
DEFAULT_BATTERY_INTERVAL: Final = 24  # hours between BLE battery reads, 0 = only on unlock
MIN_UNLOCK_INTERVAL: Final = 30  # seconds between two unlock commands
BLE_TIMEOUT: Final = 15.0  # seconds

# WeLock mobile cloud API
DEFAULT_CLOUD_API_URL: Final = "https://clientapi.welock.com.cn/api"
BASE_API_URL: Final = DEFAULT_CLOUD_API_URL
ENDPOINT_AUTH: Final = "/Account/token/welock"
ENDPOINT_DEVICES: Final = "/Device/GetDevices"
ENDPOINT_UNLOCK: Final = "/Command/UnLock"
