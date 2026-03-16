#!/usr/bin/env python3
"""
Databricks OAuth Token Rotator

Core rotation logic for automatically refreshing OAuth tokens
and updating PostgreSQL .pgpass files.
"""

import os
import sys
import time
import json
import subprocess
import logging
import signal
import jwt
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler


class DatabricksOAuthRotator:
    """Manages automatic OAuth token rotation for Databricks services"""

    def __init__(
        self,
        workspace_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        pg_host: Optional[str] = None,
        pg_port: str = "5432",
        pg_database: str = "databricks_postgres",
        pg_username: Optional[str] = None,
        pgpass_file: str = "~/.pgpass",
        log_file: str = "~/.databricks_oauth_rotator.log",
        rotation_interval: int = 50
    ):
        """
        Initialize the OAuth rotator.

        Args:
            workspace_url: Databricks workspace URL (e.g., https://workspace.cloud.databricks.com)
            client_id: OAuth client ID (for M2M auth)
            client_secret: OAuth client secret (for M2M auth)
            pg_host: PostgreSQL hostname
            pg_port: PostgreSQL port (default: 5432)
            pg_database: PostgreSQL database name (default: databricks_postgres)
            pg_username: PostgreSQL username
            pgpass_file: Path to .pgpass file (default: ~/.pgpass)
            log_file: Path to log file (default: ~/.databricks_oauth_rotator.log)
            rotation_interval: Rotation interval in minutes (default: 50)
        """
        # Databricks configuration (with environment variable fallbacks)
        self.workspace_url = workspace_url or os.getenv('DATABRICKS_HOST')
        self.client_id = client_id or os.getenv('DATABRICKS_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('DATABRICKS_CLIENT_SECRET')

        # PostgreSQL configuration
        self.pg_host = pg_host or os.getenv('DATABRICKS_PG_HOST')
        self.pg_port = pg_port
        self.pg_database = pg_database
        self.pg_username = pg_username or os.getenv('DATABRICKS_PG_USERNAME')

        # File paths
        self.pgpass_file = Path(pgpass_file).expanduser()
        self.log_file = Path(log_file).expanduser()

        # Rotation settings
        self.rotation_interval = rotation_interval * 60  # Convert to seconds

        # Validate required fields
        if not self.workspace_url:
            raise ValueError("workspace_url is required (or set DATABRICKS_HOST)")
        if not self.pg_host:
            raise ValueError("pg_host is required (or set DATABRICKS_PG_HOST)")
        if not self.pg_username:
            raise ValueError("pg_username is required (or set DATABRICKS_PG_USERNAME)")

        # Setup logging
        self._setup_logging()

        # Signal handling
        self.running = True
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _setup_logging(self):
        """Configure logging with rotation"""
        self.logger = logging.getLogger('DatabricksOAuthRotator')
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)

        # File handler with rotation (10MB max, 5 backups)
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False

    def get_token_info(self, token: str) -> Dict[str, Any]:
        """Extract information from JWT token"""
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})

            exp_timestamp = decoded.get('exp')
            iat_timestamp = decoded.get('iat')

            info = {
                'subject': decoded.get('sub'),
                'client_id': decoded.get('client_id'),
                'scopes': decoded.get('scope', '').split(' '),
                'issuer': decoded.get('iss'),
                'audience': decoded.get('aud'),
            }

            if exp_timestamp:
                expiry = datetime.fromtimestamp(exp_timestamp)
                info['expires_at'] = expiry.isoformat()
                info['expires_in_minutes'] = int(
                    (expiry - datetime.now()).total_seconds() / 60
                )
                info['is_expired'] = datetime.now() >= expiry

            if iat_timestamp:
                info['issued_at'] = datetime.fromtimestamp(iat_timestamp).isoformat()

            return info

        except Exception as e:
            self.logger.error(f"Error decoding token: {e}")
            return {'error': str(e)}

    def get_new_token_via_cli(self) -> Optional[str]:
        """
        Get new OAuth token using Databricks CLI
        This is the recommended method for development/personal use
        """
        self.logger.info("Obtaining new token via Databricks CLI...")

        try:
            # Check if databricks CLI is installed
            subprocess.run(
                ['databricks', '--version'],
                capture_output=True,
                check=True,
                timeout=10
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            self.logger.error(f"Databricks CLI not available: {e}")
            return None

        try:
            # Get OAuth token
            result = subprocess.run(
                ['databricks', 'auth', 'token', '--host', self.workspace_url],
                capture_output=True,
                text=True,
                check=False,
                timeout=30
            )

            if result.returncode != 0:
                self.logger.warning("Not logged in to Databricks CLI. Attempting login...")
                login_result = subprocess.run(
                    ['databricks', 'auth', 'login', '--host', self.workspace_url],
                    check=False,
                    timeout=60
                )

                if login_result.returncode != 0:
                    self.logger.error("Databricks CLI login failed")
                    return None

                # Retry token fetch
                result = subprocess.run(
                    ['databricks', 'auth', 'token', '--host', self.workspace_url],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )

            # Parse token from output
            output = result.stdout.strip()
            if output.startswith('eyJ'):  # JWT tokens start with eyJ
                self.logger.info("Successfully obtained token via CLI")
                return output
            else:
                try:
                    data = json.loads(output)
                    token = data.get('access_token')
                    if token:
                        self.logger.info("Successfully obtained token via CLI")
                        return token
                except json.JSONDecodeError:
                    self.logger.error(f"Unexpected CLI output: {output[:100]}")
                    return None

        except subprocess.TimeoutExpired:
            self.logger.error("Databricks CLI command timed out")
            return None
        except Exception as e:
            self.logger.error(f"Error getting token via CLI: {e}")
            return None

    def get_new_token_via_oauth(self) -> Optional[str]:
        """
        Get new OAuth token using OAuth M2M client credentials flow
        This is the recommended method for production/automated use
        """
        if not self.client_id or not self.client_secret:
            self.logger.debug("OAuth M2M credentials not configured")
            return None

        self.logger.info("Obtaining new token via OAuth M2M flow...")

        # Workspace-level token endpoint
        token_endpoint = f"{self.workspace_url}/oidc/v1/token"

        try:
            response = requests.post(
                token_endpoint,
                auth=(self.client_id, self.client_secret),
                data={
                    'grant_type': 'client_credentials',
                    'scope': 'all-apis'
                },
                timeout=30
            )

            response.raise_for_status()

            data = response.json()
            access_token = data.get('access_token')

            if access_token:
                self.logger.info("Successfully obtained token via OAuth M2M")
                return access_token
            else:
                self.logger.error("No access_token in OAuth response")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OAuth token request failed: {e}")
            return None

    def get_new_token(self) -> Optional[str]:
        """
        Get new OAuth token using the best available method
        Priority: OAuth M2M > Databricks CLI
        """
        # Try OAuth M2M first (production method)
        token = self.get_new_token_via_oauth()
        if token:
            return token

        # Fallback to CLI (development method)
        self.logger.info("OAuth M2M not available, falling back to Databricks CLI")
        token = self.get_new_token_via_cli()
        if token:
            return token

        self.logger.error("Failed to obtain token via any method")
        return None

    def update_pgpass_file(self, new_token: str) -> bool:
        """
        Update .pgpass file with new OAuth token atomically
        Format: hostname:port:database:username:password
        """
        try:
            # Create .pgpass entry
            pgpass_entry = (
                f"{self.pg_host}:{self.pg_port}:{self.pg_database}:"
                f"{self.pg_username}:{new_token}\n"
            )

            # Read existing .pgpass if it exists
            existing_lines = []
            if self.pgpass_file.exists():
                with open(self.pgpass_file, 'r') as f:
                    existing_lines = f.readlines()

            # Update or append the entry for this instance
            updated = False
            for i, line in enumerate(existing_lines):
                if line.startswith(f"{self.pg_host}:{self.pg_port}:{self.pg_database}:"):
                    existing_lines[i] = pgpass_entry
                    updated = True
                    break

            if not updated:
                existing_lines.append(pgpass_entry)

            # Write atomically using a temporary file
            temp_file = self.pgpass_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                f.writelines(existing_lines)

            # Set correct permissions (0600 - owner read/write only)
            os.chmod(temp_file, 0o600)

            # Atomic rename
            temp_file.replace(self.pgpass_file)

            self.logger.info(f"Successfully updated {self.pgpass_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error updating .pgpass file: {e}")
            return False

    def rotate_token(self) -> bool:
        """Execute one token rotation cycle"""
        self.logger.info("=" * 70)
        self.logger.info("Starting OAuth token rotation cycle")
        self.logger.info("=" * 70)

        # Get new token
        new_token = self.get_new_token()
        if not new_token:
            self.logger.error("Failed to obtain new token")
            return False

        # Verify and log token info
        token_info = self.get_token_info(new_token)
        if 'error' not in token_info:
            self.logger.info(f"New token details:")
            self.logger.info(f"  - Subject: {token_info.get('subject')}")
            self.logger.info(f"  - Expires at: {token_info.get('expires_at')}")
            self.logger.info(f"  - Valid for: {token_info.get('expires_in_minutes')} minutes")
        else:
            self.logger.warning(f"Could not verify token: {token_info['error']}")

        # Update .pgpass file
        if self.update_pgpass_file(new_token):
            self.logger.info("Token rotation completed successfully")
            self.logger.info("=" * 70)
            return True
        else:
            self.logger.error("Failed to update .pgpass file")
            self.logger.error("=" * 70)
            return False

    def run_once(self) -> bool:
        """Run one rotation cycle and exit"""
        self.logger.info("Running in one-shot mode")
        return self.rotate_token()

    def run_daemon(self):
        """Run as a daemon, rotating tokens every N minutes"""
        self.logger.info("Starting OAuth token rotation daemon")
        self.logger.info(f"Rotation interval: {self.rotation_interval // 60} minutes")
        self.logger.info(f"Workspace URL: {self.workspace_url}")
        self.logger.info(f"PostgreSQL host: {self.pg_host}")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info(f"PID: {os.getpid()}")

        # Initial rotation
        self.rotate_token()

        # Continuous rotation loop
        while self.running:
            try:
                # Sleep in small intervals to allow graceful shutdown
                sleep_remaining = self.rotation_interval
                while sleep_remaining > 0 and self.running:
                    sleep_time = min(60, sleep_remaining)
                    time.sleep(sleep_time)
                    sleep_remaining -= sleep_time

                if self.running:
                    success = self.rotate_token()
                    if not success:
                        self.logger.warning("Rotation failed, will retry on next cycle")

            except Exception as e:
                self.logger.error(f"Unexpected error in daemon loop: {e}", exc_info=True)
                time.sleep(60)

        self.logger.info("Daemon stopped")
