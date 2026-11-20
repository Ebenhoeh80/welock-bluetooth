# How the integration talks to the lock

A short description of what this integration does, written for users who want to
understand it. It is not a specification of the vendor's protocol and it covers
only what this integration needs.

This integration is not affiliated with or endorsed by the manufacturer of the
lock. It works with a lock you own and your own WeLock account.

## Bluetooth exchange

The lock exposes a Nordic UART service:

| Role | UUID |
| :--- | :--- |
| Service | `6e400001-b5a3-f393-e0a9-e50e24dcca9e` |
| Write (to the lock) | `6e400002-b5a3-f393-e0a9-e50e24dcca9e` |
| Notify (from the lock) | `6e400003-b5a3-f393-e0a9-e50e24dcca9e` |

An unlock takes these steps over one Bluetooth connection:

1. Home Assistant connects to the lock through any adapter or ESPHome Bluetooth
   proxy it has in range and subscribes to the notify characteristic.
2. It writes a 15-byte **status request** (`55 30` followed by zeros). The lock
   answers with four bytes: `55 30`, a one-byte **challenge value** (called
   `randomFactor`), and the **battery level**.
3. It obtains the matching 15-byte **unlock command** (it starts with `U1`) and
   writes it once to the lock. See below for where the command comes from.
4. The lock usually answers with a notification, which counts as a confirmation.
   A missing answer is not an error in itself (the command may still have worked).
5. The connection is closed.

The status request alone does **not** unlock; it is also used to read the battery.

## Where the unlock command comes from

- **Cloud (default):** the integration logs in to your WeLock account and asks the
  cloud's unlock endpoint (`/Command/UnLock`) for a command, passing the device
  number, the device name, the challenge value and the battery level. A cloud login
  ends other sessions of the same account, so the WeLock app is logged out.
- **Local command table (optional, experimental):** the command depends only on
  the one-byte challenge value, so there are at most 256 different commands.
  Commands that the cloud has returned are stored, and a table can be imported.
  With the *Offline unlock* switch on, a stored command for the current challenge
  value is used and no cloud request is made. If writing a stored command fails,
  it is dropped from the table and the next attempt asks the cloud again.

## Timing

- Connecting is the slow part: the lock advertises only about every 3 s, and a weak
  signal makes Home Assistant wait for more advertisements. A Bluetooth adapter or
  proxy within about 20 cm of the lock connected in about 7 s on average in tests;
  at 50 cm with a weak signal it took about 17 s.
- After a successful unlock the outer knob stays engaged for about 10 s and the
  lock takes no further command meanwhile, so the integration waits at least 12 s
  between two unlocks.
- Status and command exchange take well under a second once connected.

## What is stored

Account data, the stored command table and unlock statistics stay in Home Assistant
(config entry and `.storage`). Diagnostics downloads redact the account, the
Bluetooth address and the device number, and contain only the *number* of stored
commands, never the commands themselves.
