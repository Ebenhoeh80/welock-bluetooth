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
CONF_LOCAL_UNLOCK: Final = "local_unlock"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds, local Bluetooth presence/RSSI only
DEFAULT_AUTO_RELOCK_DELAY: Final = 10  # seconds (measured: the knob engages for 10 s)
DEFAULT_BATTERY_INTERVAL: Final = 24  # hours between BLE battery reads, 0 = only on unlock
DEFAULT_LOCAL_UNLOCK: Final = False  # use the locally learned command cache to unlock
# The lock cannot take another unlock command while its knob is engaged (measured: 10 s),
# so the next one is held back a little longer than that.
MIN_UNLOCK_INTERVAL: Final = 12  # seconds between two unlock commands
BLE_TIMEOUT: Final = 15.0  # seconds to wait for the lock's status answer
# After the unlock command was written the lock normally answers within about
# half a second (seen in the app's Bluetooth trace). Waiting longer only delays
# the unlocked state in Home Assistant when no answer comes.
CONFIRM_TIMEOUT: Final = 3.0  # seconds to wait for that confirmation
# Closing a BLE connection must never hold the single per-lock slot forever.
TEARDOWN_TIMEOUT: Final = 5.0  # seconds each for stop_notify() and disconnect()

# Local offline command cache (rf -> command). The cloud unlock command depends
# only on the one-byte randomFactor of the BLE challenge, so there are at most
# 256 distinct commands per lock. They are learned from the cloud during normal
# use and persisted per config entry; battery and devicePassword do not change
# the command.
COMMAND_SPACE: Final = 256  # number of possible randomFactor values (0..255)
STORAGE_VERSION: Final = 1

# Unlock statistics and history (persisted per config entry).
STATS_STORAGE_VERSION: Final = 1
HISTORY_LIMIT: Final = 100  # unlock attempts kept in the history

# How an unlock command was obtained.
PATH_CLOUD: Final = "cloud"  # command requested from the WeLock cloud
PATH_OFFLINE: Final = "offline"  # command taken from the local command cache
PATH_NONE: Final = "none"  # failed before a command was needed (Bluetooth)

# What happened to an unlock attempt.
RESULT_CONFIRMED: Final = "confirmed"  # command written and the lock answered
RESULT_UNCONFIRMED: Final = "unconfirmed"  # command written, no answer seen
RESULT_FAILED: Final = "failed"  # error before or while writing the command

# WeLock mobile cloud API
DEFAULT_CLOUD_API_URL: Final = "https://clientapi.welock.com.cn/api"
BASE_API_URL: Final = DEFAULT_CLOUD_API_URL
ENDPOINT_AUTH: Final = "/Account/token/welock"
ENDPOINT_DEVICES: Final = "/Device/GetDevices"
ENDPOINT_UNLOCK: Final = "/Command/UnLock"
# Read-only access log (who opened the lock, when and how). Each read requires a
# cloud login, which ends other sessions of the account (e.g. the WeLock app),
# so it is fetched only on demand via the welock.fetch_access_log service.
ENDPOINT_UNLOCK_RECORD: Final = "/device/GetUnlockRecord"

# Service names
SERVICE_FETCH_ACCESS_LOG: Final = "fetch_access_log"
SERVICE_IMPORT_COMMANDS: Final = "import_commands"
SERVICE_CLEAR_COMMANDS: Final = "clear_commands"
# Default file name of a command table, relative to the Home Assistant config folder.
DEFAULT_IMPORT_FILE: Final = "welock-oracle-table.json"
MAX_IMPORT_FILE_BYTES: Final = 200_000  # a full table is about 8 KB
DEFAULT_ACCESS_LOG_PAGE_SIZE: Final = 20
