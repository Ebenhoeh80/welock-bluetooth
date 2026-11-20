# Security Policy

## Supported Versions

We provide security patches and updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.6.x   | :white_check_mark: |
| 2.5.x   | :white_check_mark: |
| < 2.5.0 | :x:                |

Fixes are made in the latest release; the previous minor version (2.5.x) is supported while 2.6.x is rolled out.

## Security Considerations for Smart Locks

This project interfaces with physical access control hardware (smart door locks). We enforce strict security-by-design principles:
- **No persistent secret logging**: Credentials, tokens, and authorization payloads are redacted from logs and diagnostic exports.
- **Challenge-Response freshness**: Unlocking requests require an active, fresh `random_factor` challenge from the lock to prevent replay attacks.
- **TLS & Redirect Restrictions**: Cloud API calls enforce strict HTTPS and do not follow HTTP redirects.
- **Token handling**: The cloud access token is kept in memory only and discarded after each request; it is never logged or written to disk.
- **Command validation**: Only 15-byte `U1…` commands are written to the lock: the one the cloud returned for the current challenge, or (only with the *Offline unlock* switch on) a stored command for exactly that challenge value. A stored command that fails while being written is dropped. At least 12 seconds between unlocks.
- **Stored commands are sensitive**: the local command table lets anyone who can read Home Assistant's storage and is within Bluetooth range open the lock. Diagnostics contain only the number of stored commands, never the commands. Protect access to your Home Assistant configuration and backups.
- **Least cloud contact**: The integration contacts the cloud only for setup, reauthentication and unlocking; it never polls.
- **Tests**: The optional live smoke test is read-only, blocks every unlock / BLE write path and never prints the password or token.

## Threat model

What the integration stores and who could misuse it:

| Asset | Where it is | Risk | What to do |
| ----- | ----------- | ---- | ---------- |
| WeLock account (user name, password) | Home Assistant config entry in `.storage` | Whoever can read the configuration or a backup can log in to the WeLock cloud as you. | Protect access to Home Assistant; use a password that is not used elsewhere. |
| **Learned unlock commands** (up to 256, one per challenge value) | `.storage` (`welock.<entry id>.commands`), and therefore in every **backup** of Home Assistant | A command opens the lock whenever the lock presents the challenge value it belongs to. With a full table every challenge can be answered. | Encrypt your backups and keep them off shared storage; use the `welock.clear_commands` service before giving a backup or the storage folder away. |
| Import file `welock-oracle-table.json` (default name of the `welock.import_commands` service) | Home Assistant configuration folder | The file contains the commands in plain text. | **Delete the file right after the import** (it is not needed afterwards) and do not copy it into backups or repositories. |
| Diagnostics download | Created on request | Contains no account data, no addresses, no lock number, no title, no commands, no challenge values. | Still check the file before sharing it. |

Combined risk: anyone who holds a copy of the command table **and** is within Bluetooth range of the lock (a few metres) can open it. The commands are not a way to open the lock from afar; they need a Bluetooth connection to the lock. Each stored command is only ever written for exactly the challenge value of the current connection, which the lock presents anew for every connection (see [docs/PROTOCOL.md](docs/PROTOCOL.md)); the table is therefore as sensitive as a key that is limited to radio range.

Recommendations:

- Turn on backup encryption in Home Assistant and keep the encryption key separately.
- Leave *Offline unlock* off (default) if you do not need it; the table is still learned along the way, so use the `welock.clear_commands` service if you want to remove it.
- Do not share Home Assistant backups, the `.storage` folder or the import file in issues or forums.

## Reporting a Vulnerability

If you discover a security vulnerability within this project:

1. **Do NOT open a public GitHub issue.**
2. Report the vulnerability privately via **GitHub Private Vulnerability Reporting** at:
   `https://github.com/Ebenhoeh80/welock-bluetooth/security/advisories/new`
3. Include detailed reproduction steps, affected firmware/versions, and a proof of concept if available.

We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure timeline.
