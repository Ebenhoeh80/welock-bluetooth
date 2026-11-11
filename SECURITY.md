# Security Policy

## Supported Versions

We provide security patches and updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0.0 | :x:                |

## Security Considerations for Smart Locks

This project interfaces with physical access control hardware (smart door locks). We enforce strict security-by-design principles:
- **No persistent secret logging**: Credentials, tokens, and authorization payloads are redacted from logs and diagnostic exports.
- **Challenge-Response freshness**: Unlocking requests require an active, fresh `random_factor` challenge from the lock to prevent replay attacks.
- **TLS & Redirect Restrictions**: Cloud API calls enforce strict HTTPS and do not follow HTTP redirects.
- **Token handling**: The cloud access token is kept in memory only and discarded after each request; it is never logged or written to disk.
- **Command validation**: Only 15-byte `U1…` commands returned by the cloud for the current challenge are written to the lock; at least 30 seconds between unlocks.
- **Least cloud contact**: The integration contacts the cloud only for setup, reauthentication and unlocking; it never polls.
- **Tests**: The optional live smoke test is read-only, blocks every unlock / BLE write path and never prints the password or token.

## Reporting a Vulnerability

If you discover a security vulnerability within this project:

1. **Do NOT open a public GitHub issue.**
2. Report the vulnerability privately via **GitHub Private Vulnerability Reporting** at:
   `https://github.com/Ebenhoeh80/welock-aistudio/security/advisories/new`
3. Include detailed reproduction steps, affected firmware/versions, and a proof of concept if available.

We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure timeline.
