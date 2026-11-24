# Engineering notes: architecture, failure modes, measurements, quality gates

This page records how the integration works, where its time goes, what can fail and how it
recovers, what is checked automatically, and which options were rejected and why. Numbers are
measured, with date and method; where something was not measured, it says so.
Last updated: 2026-11-23 (version 2.6.1).

## 1. Architecture and data flow

```
 Home Assistant                       integration "welock_ble"                       outside
 ───────────────                        ──────────────────────                     ───────
 lock.unlock  ─────────────►  lock.py ──► coordinator.async_unlock()
 switch / options ─────────►  switch.py   │  _ensure_unlock_possible()  (12 s interval, busy lock)
                                          │  _ble_lock                  (one BLE session at a time)
                                          ▼
                                    ble.async_exchange()  ───────────►  lock (Nordic UART, BLE)
                                     _async_connect → _async_read_status → _async_send_command
                                          │  command_provider(state)
                                          ▼
                              choose_unlock_command()  ──► cache (256 learned commands) ──► offline
                                          └──────────────► api.WeLockApiClient ───────────► cloud (HTTPS)
```

`choose_unlock_command()` learns a cloud answer only while the offline-unlock switch is on;
with the switch off it returns the cloud command without writing to the cache.

- **Coordinator** (`coordinator.py`) is the only place with state: presence/RSSI poll every 60 s (reads
  Home Assistant's Bluetooth cache, no radio traffic), battery read over BLE every 24 h, unlock
  statistics (`stats.py`, last 100 attempts), repair issues (`issues.py`, thresholds in `health.py`).
- **BLE transport** (`ble.py`) is split into small steps: `_Notifications` (what the lock sends back),
  `_note_advertisement`, `_async_connect` (retry helper, counts attempts), `_async_read_status`,
  `_async_send_command`, `_async_teardown`. The connection is closed in the background after a
  completed unlock (`teardown_runner`), so the service call returns earlier.
- **Cloud** (`api.py`): every call logs in, sends one request and drops the token (single use; a login
  ends other sessions of the account). MD5 in `md5_hex` is part of the cloud protocol (signature and a
  client identifier), not a security choice.
- **Storage:** command table and statistics use Home Assistant's versioned `Store`.

## 2. Concurrency and lifecycle

- All BLE access to one lock is serialised by `_ble_lock`; an unlock while it is held is refused
  (`lock_busy`), a second unlock within 12 s is refused (`unlock_too_soon`, the knob stays engaged for
  about 10 s).
- The background teardown keeps `_ble_lock` until the connection is closed (about 2 to 2.7 s) and then
  adds the teardown time to the already recorded attempt.
- Unloading waits (up to 10 s) for connections that are still closing (`async_shutdown`).

## 3. Failure modes and recovery

| Failure | Effect | Recovery / mitigation |
|---|---|---|
| Lock out of Bluetooth range | unlock refused with a clear message | entity unavailable; repair issue after 6 h |
| Slow or failed connection | unlock fails or takes long | up to 3 attempts in the retry helper; connection-quality sensor and repair issue |
| Cloud unreachable | no new command | with offline unlock and a stored command the cloud is not needed |
| Wrong/changed password | `InvalidAuth` | re-authentication flow starts |
| Stored command fails while being written | could fail again | the command is dropped, the next attempt asks the cloud |
| Exchange returns no status (internal) | possible uninitialised variable (found by CodeQL) | now handled explicitly as a failed attempt |
| Damaged storage | wrong numbers | tolerant loading ignores damaged parts, including a `commands` value of the wrong shape |
| Bluetooth disconnect never returns | the single per-lock slot stays reserved, later unlocks are refused | `TEARDOWN_TIMEOUT` bounds `stop_notify()` and `disconnect()` to 5 s each |
| Background teardown cannot be scheduled | connection stays open and the slot stays busy | the handoff flag is set only after scheduling; on failure the connection is closed and the lock released here |

## 4. Where the time goes (measured)

Method: the integration records phase times for every unlock; ten consecutive unlocks on the real
lock (ASUS USB-BT500 adapter, RSSI about -66 to -76 dBm) were read on 2026-11-20.

| Phase | Result |
|---|---|
| Bluetooth connection | 2.9 to 32.2 s, median 11 s (more than 95 % of the total) |
| Status request and answer | 53 to 196 ms |
| Cloud command (login and request) | 218 ms; none on the offline path |
| Wait for the lock's confirmation | about 500 ms (493 to 657 ms) on 9 of 10, 1.2 s once |
| Teardown (background, not part of the call) | 1.8 to 2.7 s |
| Software of the integration, test with a fake lock | median 0.8 ms (budget test `test_the_software_part_of_an_unlock_stays_small`, limit 250 ms) |

The connection time does not follow the age of the lock's last advertisement (6.9 s at 1.1 s age,
3.3 s at 26 s age): the radio path decides, not the strategy of the integration. Reaching an unlock
time of about 2 s therefore needs a shorter radio path (an ESP32 Bluetooth proxy close to the lock) or
a standing connection, not different code.

## 5. Quality gates

The gates below are enforced in CI unless a row says *manual*; manual rows are measurements, not
blocking checks.

| Judge | Gate | Result 2026-11-23 |
|---|---|---|
| Ruff (E, W, F, I, B, C4, UP) | no findings | pass; extended rules (SIM, RET, PL, C901, ANN) are *manual* and not configured in `pyproject.toml` (201 findings with the current tool version, deliberately not enabled) |
| black | formatting (the CI and `RELEASING.md` use black; `ruff format` would change 3 further files) | pass |
| MyPy with the real Home Assistant types | no errors | pass (19 source files checked) |
| pytest, unit tests (Python 3.10 to 3.13) | all pass | 131 passed, 1 deselected (live test, `-m "not live"`) |
| pytest in a real Home Assistant core | all pass | 87 passed |
| Coverage (both suites combined) | at least 95 % | 98.46 % |
| hassfest | valid manifest, strings, quality scale | pass |
| xenon | absolute B, modules A, average A | pass |
| CodeQL (security-and-quality) | no new alerts | pass; one rule switched off for the MD5 protocol hashing (`.github/codeql/codeql-config.yml`) |
| Diagnostics | the whole JSON contains no account, title, lock number, address, command | pass (test searches every identifier) |
| Supply chain (CI) | `contents: read`, actions pinned to SHAs, test package pinned | pass; hassfest and hacs/action deliberately stay on their documented references |
| Home Assistant Quality Scale | `quality_scale.yaml` | Gold; only Platinum `strict-typing` open |

Not run: SonarQube, Semgrep (not available on the development machine), py-spy and Scalene (the
numbers above come from the integration's own phase times and a benchmark with a fake lock).

## 6. Decisions and rejected options

- **Cloud login in parallel with the Bluetooth connection** rejected: the cloud step is 218 ms of
  about 11 s; the gain is below 2 %.
- **Reporting success before the lock's confirmation** not done yet: it would save about 0.5 s (5 %) but
  changes the recording of the attempt on the safety-relevant path; it needs a test at the lock first.
- **Standing Bluetooth connection / connect on arrival** not done: battery drain and untestable without
  the lock; remains a strategic option.
- **Identity of the entry = Bluetooth address of the module** (kept). Home Assistant's Bluetooth discovery
  reports exactly this address, and the address of a lock module is fixed (unlike an IP address). Using the lock
  number instead would rebuild discovery and the unlock path for a case that hardly happens (a replaced module)
  and carries the risk of losing entities of a safety-relevant device. The title shows the lock number in
  parentheses (`WeLock (22231059)`); the module name (`WeLockFMHAE`) is only what the cloud needs to unlock.
- **Voluptuous to probatio:** Home Assistant's type hints already name another schema library; mypy
  reports it for three modules (`pyproject.toml`, documented override). Watch Home Assistant release notes.

## 7. Open items

- Platinum rule `strict-typing`.
- Field test of every release candidate at the lock (unlock several times, offline and cloud). 2.5.0-rc.1 was tested on 2026-11-20 and released as 2.5.0.
- 2.6.0 has not been tried at the lock yet. It changes nothing on the unlock path, but each recorded attempt now also carries the scanner label: after the update, check that an unlock is still recorded in the history and in the diagnostics.
