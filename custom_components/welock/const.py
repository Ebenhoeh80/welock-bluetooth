"""Constants for the WeLock Smart Lock integration."""

from typing import Final

DOMAIN: Final = "welock"

# Configuration keys
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AUTO_RELOCK_DELAY: Final = "auto_relock_delay"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
DEFAULT_AUTO_RELOCK_DELAY: Final = 7  # seconds (WeLock locks mechanically lock after turning)

# API endpoints (Official WeLock Mobile Cloud API)
DEFAULT_CLOUD_API_URL: Final = "https://clientapi.welock.com.cn/api"
BASE_API_URL: Final = DEFAULT_CLOUD_API_URL
ENDPOINT_AUTH: Final = "/Account/token/welock"
ENDPOINT_DEVICES: Final = "/Device/GetDevices"
ENDPOINT_LOCK_LIST: Final = ENDPOINT_DEVICES
ENDPOINT_LOCK_DETAIL: Final = ENDPOINT_DEVICES
ENDPOINT_UNLOCK: Final = "/Command/UnLock"
ENDPOINT_GATEWAY_LIST: Final = ENDPOINT_DEVICES

# Device attributes
ATTR_LOCK_SN: Final = "lock_sn"
ATTR_MAC: Final = "mac"
ATTR_MODEL: Final = "model"
ATTR_BATTERY: Final = "battery"
ATTR_WIFI_BOX_ID: Final = "wifi_box_id"
ATTR_LAST_UNLOCK_TIME: Final = "last_unlock_time"
ATTR_LAST_UNLOCK_TYPE: Final = "last_unlock_type"
ATTR_FIRMWARE_VERSION: Final = "firmware_version"
ATTR_SIGNAL_STRENGTH: Final = "signal_strength"
