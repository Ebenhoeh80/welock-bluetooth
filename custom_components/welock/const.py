"""Constants for the WeLock Smart Lock integration."""
from typing import Final

DOMAIN: Final = "welock"

# Configuration keys
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_AUTO_RELOCK_DELAY: Final = "auto_relock_delay"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
DEFAULT_AUTO_RELOCK_DELAY: Final = 7  # seconds (WeLock locks mechanically lock after turning)

# API endpoints
BASE_API_URL: Final = "https://api.welockglobal.com"
ENDPOINT_AUTH: Final = "/app/v1/open/oauth/token"
ENDPOINT_LOCK_LIST: Final = "/app/v1/open/lock/list"
ENDPOINT_LOCK_DETAIL: Final = "/app/v1/open/lock/detail"
ENDPOINT_UNLOCK: Final = "/app/v1/open/lock/unlock"
ENDPOINT_GATEWAY_LIST: Final = "/app/v1/open/gateway/list"

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
