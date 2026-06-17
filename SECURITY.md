# Security Policy

## Supported Versions

Security fixes are provided for the latest release of succulent. Older versions are not actively maintained.

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |
| Older   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in succulent, please **do not open a public GitHub issue**.

Instead, report it privately by emailing:

**iztok@iztok.xyz**

Please include:

- A description of the vulnerability and its potential impact
- Steps to reproduce the issue (proof-of-concept code if possible)
- The version of succulent affected

You should receive an acknowledgement within a few days. We will work with you to understand and address the issue, and we will credit reporters (unless you prefer to remain anonymous) once a fix is released.

## Scope

succulent is a lightweight framework that exposes an HTTP endpoint for collecting POST request data. Given its intended use (receiving data from embedded devices, microcontrollers, and sensors over a network), areas of particular security interest include:

- Authentication / password handling for data access and export endpoints
- Input validation of incoming POST data (including file/image uploads)
- Safe handling of the configuration file (e.g. avoid committing secrets)
- Denial-of-service resilience (large payloads, request flooding)

## Recommendations for Deployments

- Run succulent behind a reverse proxy (e.g. nginx, Caddy) with HTTPS/TLS enabled.
- Avoid storing secrets (such as the access password) in plaintext configuration files committed to version control; prefer environment variables or a secrets manager.
- Restrict network access to trusted devices where possible (e.g. firewall rules, VPN).
