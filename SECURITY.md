# Security Policy

## Supported Versions

We provide security patches and updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :white_check_mark: |
| < 1.2.0 | :x:                |

## Security Considerations for Smart Locks

This project interfaces with physical access control hardware (smart door locks). We enforce strict security-by-design principles:
- **No persistent secret logging**: Credentials, tokens, and authorization payloads are redacted from logs and diagnostic exports.
- **Challenge-Response freshness**: Unlocking requests require an active, fresh `random_factor` challenge from the lock to prevent replay attacks.
- **TLS & Redirect Restrictions**: Cloud API calls enforce strict HTTPS and reject open HTTP redirects.

## Reporting a Vulnerability

If you discover a security vulnerability within this project:

1. **Do NOT open a public GitHub issue.**
2. Report the vulnerability privately via **GitHub Private Vulnerability Reporting** at:
   `https://github.com/Ebenhoeh80/welock-aistudio/security/advisories/new`
3. Include detailed reproduction steps, affected firmware/versions, and a proof of concept if available.

We will acknowledge receipt within 48 hours and work with you on a coordinated disclosure timeline.
