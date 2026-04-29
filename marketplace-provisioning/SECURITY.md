# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email [security@databricks.com](mailto:security@databricks.com) with:

- A description of the vulnerability
- Steps to reproduce the issue
- Any potential impact assessment

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |

## Security Practices

- Dependencies are tracked in `requirements.txt` (Python) and `package.json` (Node.js)
- Authentication uses Databricks SDK service principal credentials
- No user credentials are stored by the application
- The app uses SQLite for transient session state only (reset on each deployment)
