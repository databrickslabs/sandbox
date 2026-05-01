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

## Authentication Model

This app uses the **Databricks App service principal** for all Databricks
operations (SQL statements, Files API, Genie space CRUD, SCIM lookups,
permission grants). Credentials are obtained from the
`databricks.sdk.WorkspaceClient` at runtime — the app never reads a
`DATABRICKS_TOKEN` environment variable and never accepts a PAT from the
user.

### Why service-principal-only (no on-behalf-of-user)

Provisioning a scenario requires privileged operations that an unprivileged
end user typically cannot perform in a shared workspace:

- Creating Unity Catalog catalogs, schemas, volumes, and tables
- Uploading CSV/Parquet data into managed volumes
- Granting `USE_CATALOG`, `USE_SCHEMA`, and `SELECT` to the end user
- Creating Genie spaces and granting the user `CAN_RUN`

The Marketplace deployment targets Databricks Free Edition workspaces where
the installing user *is* the workspace admin, so the app service principal
runs with admin-equivalent authority by design. Users only receive the
minimum grants needed to query their provisioned scenario.

### What the app never does

- Does not store or log user tokens, session cookies, or PATs
- Does not accept credentials via the UI or API payloads
- Does not call external (non-Databricks) services
- Does not persist customer data beyond the user's own workspace

## Input Validation

- All Unity Catalog identifiers (catalog, schema, table, column names) are
  validated against a strict identifier regex before being interpolated
  into SQL. See `provisioner._check_ident` / `_check_dotted_ident`.
- Parameterized SQL bindings are used for all user-supplied values.
- Mystery text is length-capped and passed through a word-boundary
  profanity filter.

## Security Practices

- Dependencies are tracked in `requirements.txt` (Python) and
  `package.json` (Node.js).
- No user credentials are stored by the application.
- The app uses SQLite for transient game state only (reset on each
  deployment).
- The in-memory provisioning-status dict is capped to prevent unbounded
  growth.
- Exception messages surfaced to the UI are sanitized; full tracebacks are
  only written to server logs.
