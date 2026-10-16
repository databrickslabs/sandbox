---
title: "OAuth Auto Token Rotation for Databricks PostgreSQL"
language: python
author: "Surya Sai Turaga"
date: 2024-11-22

tags:
- security
- oauth
- postgresql
- lakebase
- automation
- script
- installable
---

# OAuth Auto Token Rotation for Databricks PostgreSQL (Lakebase)

Automatic OAuth token rotation for Databricks PostgreSQL (Lakebase) connections. Eliminates the need for manual token updates by running as a background service that automatically refreshes OAuth tokens every 50 minutes and updates your `.pgpass` file.

## Features

- **Automatic Token Rotation** - Refreshes OAuth tokens every 50 minutes (before 60-minute expiry)
- **Zero Downtime** - Atomic `.pgpass` file updates prevent connection interruptions
- **Dual Authentication** - Supports both OAuth M2M (production) and CLI (development)
- **Background Service** - Runs as macOS LaunchAgent or Linux systemd service
- **Comprehensive Logging** - Rotating logs with detailed operation tracking
- **Easy Installation** - Simple `pip install` and one-command setup
- **Cross-Platform** - Works on macOS and Linux

## Installation

You need to have Python 3.8+ installed. Install the package:

```bash
pip install git+https://github.com/suryasai87/oauth_auto_token_rotation.git
```

Or install via Databricks Labs sandbox:

```sh
databricks labs install sandbox
```

## Quick Start

### Configuration

Set your Databricks workspace and PostgreSQL connection details:

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_PG_HOST="instance-xyz.database.cloud.databricks.com"
export DATABRICKS_PG_USERNAME="your-email@company.com"
```

### Test It

Run a test rotation to verify everything works:

```bash
databricks-oauth-rotator --once
```

### Install as Background Service

Install and start the automatic rotation service:

```bash
databricks-oauth-install \
  --workspace-url https://your-workspace.cloud.databricks.com \
  --pg-host instance-xyz.database.cloud.databricks.com \
  --pg-username your-email@company.com
```

That's it! The service will now automatically rotate your OAuth tokens every 50 minutes.

## How It Works

```
+-------------------------------------+
|   Background Service (every 50m)    |
+------------------+------------------+
                   |
                   v
+--------------------------------------+
|  1. Get fresh OAuth token            |
|     - Try OAuth M2M first            |
|     - Fallback to Databricks CLI     |
+------------------+-------------------+
                   |
                   v
+--------------------------------------+
|  2. Verify token validity (60 min)   |
+------------------+-------------------+
                   |
                   v
+--------------------------------------+
|  3. Update ~/.pgpass atomically      |
+------------------+-------------------+
                   |
                   v
+--------------------------------------+
|  4. Log success and sleep            |
+--------------------------------------+
```

## Authentication Methods

### Option 1: Databricks CLI (Recommended for Development)

Easiest for personal use - uses browser-based OAuth:

```bash
pip install databricks-cli
databricks auth login --host https://your-workspace.cloud.databricks.com
```

The rotator will automatically use your CLI credentials.

### Option 2: OAuth M2M (Recommended for Production)

Best for automation and production use:

1. Create a service principal in Databricks
2. Generate OAuth secret
3. Set environment variables:

```bash
export DATABRICKS_CLIENT_ID="your-service-principal-id"
export DATABRICKS_CLIENT_SECRET="your-oauth-secret"
```

## Usage

### Command-Line Interface

```bash
# Run once (test mode)
databricks-oauth-rotator --once

# Run as daemon with custom interval
databricks-oauth-rotator --interval 45

# Specify all parameters explicitly
databricks-oauth-rotator \
  --workspace-url https://workspace.cloud.databricks.com \
  --pg-host instance-xyz.database.cloud.databricks.com \
  --pg-username user@company.com \
  --pg-port 5432 \
  --pg-database databricks_postgres \
  --interval 50
```

### Service Management

```bash
# Install service
databricks-oauth-install

# Check service status
databricks-oauth-status

# Restart service
databricks-oauth-restart

# Uninstall service
databricks-oauth-uninstall
```

### Python API

Use the rotator programmatically in your Python code:

```python
from databricks_oauth_rotator import DatabricksOAuthRotator

# Create rotator instance
rotator = DatabricksOAuthRotator(
    workspace_url="https://workspace.cloud.databricks.com",
    pg_host="instance-xyz.database.cloud.databricks.com",
    pg_username="user@company.com",
    rotation_interval=50  # minutes
)

# Run once
rotator.run_once()

# Or run as daemon
rotator.run_daemon()
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABRICKS_HOST` | Workspace URL | Yes |
| `DATABRICKS_PG_HOST` | PostgreSQL hostname | Yes |
| `DATABRICKS_PG_USERNAME` | PostgreSQL username | Yes |
| `DATABRICKS_CLIENT_ID` | OAuth client ID (M2M) | No |
| `DATABRICKS_CLIENT_SECRET` | OAuth client secret (M2M) | No |

### Command-Line Arguments

```
--workspace-url URL        Databricks workspace URL
--pg-host HOST             PostgreSQL hostname
--pg-port PORT             PostgreSQL port (default: 5432)
--pg-database DB           Database name (default: databricks_postgres)
--pg-username USER         PostgreSQL username
--pgpass-file PATH         Path to .pgpass file (default: ~/.pgpass)
--log-file PATH            Log file path (default: ~/.databricks_oauth_rotator.log)
--interval MINUTES         Rotation interval (default: 50)
--once                     Run once and exit (test mode)
```

## Monitoring

### View Logs

```bash
# Follow logs in real-time
tail -f ~/.databricks_oauth_rotator.log

# Check recent activity
tail -50 ~/.databricks_oauth_rotator.log

# Search for errors
grep ERROR ~/.databricks_oauth_rotator.log
```

### Log Format

```
2025-01-22 14:30:00 - INFO - Starting OAuth token rotation cycle
2025-01-22 14:30:01 - INFO - Successfully obtained token via OAuth M2M
2025-01-22 14:30:01 - INFO - New token details:
2025-01-22 14:30:01 - INFO -   - Subject: user@company.com
2025-01-22 14:30:01 - INFO -   - Expires at: 2025-01-22T15:30:01
2025-01-22 14:30:01 - INFO -   - Valid for: 60 minutes
2025-01-22 14:30:01 - INFO - Successfully updated /Users/user/.pgpass
2025-01-22 14:30:01 - INFO - Token rotation completed successfully
```

## Troubleshooting

### Service Not Starting

Check the error logs:

```bash
cat ~/.databricks_oauth_rotator_stderr.log
```

Common issues:
- Missing environment variables
- Python dependencies not installed
- Authentication not configured

### Token Rotation Failing

1. **Verify authentication:**
   ```bash
   # For OAuth M2M
   echo $DATABRICKS_CLIENT_ID
   echo $DATABRICKS_CLIENT_SECRET

   # For CLI
   databricks auth login --host https://your-workspace.cloud.databricks.com
   ```

2. **Test manually:**
   ```bash
   databricks-oauth-rotator --once
   ```

3. **Check logs:**
   ```bash
   tail -100 ~/.databricks_oauth_rotator.log
   ```

### .pgpass Not Updating

1. **Check file permissions:**
   ```bash
   ls -la ~/.pgpass
   # Should be: -rw------- (0600)
   ```

2. **Verify service is running:**
   ```bash
   databricks-oauth-status
   ```

## Architecture

### Components

- **`rotator.py`** - Core rotation logic
- **`cli.py`** - Command-line interface
- **`install.py`** - Service installation and management
- **`templates/`** - LaunchAgent/systemd templates

### Authentication Flow

1. **OAuth M2M Flow** (Production):
   ```
   POST {workspace}/oidc/v1/token
   Authorization: Basic {client_id}:{client_secret}
   Body: grant_type=client_credentials&scope=all-apis
   -> Returns: access_token (valid 60 minutes)
   ```

2. **Databricks CLI Flow** (Development):
   ```
   databricks auth token --host {workspace}
   -> Uses stored refresh token
   -> Returns: access_token (valid 60 minutes)
   ```

### File Updates

The `.pgpass` file is updated atomically to prevent corruption:

1. Write new token to temporary file
2. Set permissions to 0600 (owner read/write only)
3. Atomic rename to `.pgpass`

## Security

- **Short-lived tokens:** Access tokens expire after 60 minutes
- **Proactive rotation:** Tokens rotated at 50 minutes (10-minute safety margin)
- **Secure storage:** `.pgpass` file has restricted permissions (0600)
- **Atomic updates:** Prevents file corruption during updates
- **No credentials in code:** Uses environment variables and OAuth flows

## Platform Support

| Platform | Service Type | Status |
|----------|-------------|--------|
| macOS | LaunchAgent | Supported |
| Linux | systemd | Supported |
| Windows | - | Not yet supported |

## References

- [Databricks OAuth M2M Documentation](https://docs.databricks.com/en/dev-tools/auth/oauth-m2m.html)
- [Databricks OAuth U2M Documentation](https://docs.databricks.com/en/dev-tools/auth/oauth-u2m.html)
- [Databricks CLI Authentication](https://docs.databricks.com/en/dev-tools/cli/authentication.html)
- [PostgreSQL .pgpass Documentation](https://www.postgresql.org/docs/current/libpq-pgpass.html)

## License

This project is licensed under the Apache License 2.0.
