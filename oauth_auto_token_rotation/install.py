#!/usr/bin/env python3
"""
Installation helper for setting up the OAuth rotation service as a background daemon
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict


class ServiceInstaller:
    """Installs and manages the OAuth rotation service"""

    def __init__(self):
        self.home = Path.home()
        self.service_name = "com.databricks.oauth.rotator"

        # Detect platform
        self.is_macos = sys.platform == 'darwin'
        self.is_linux = sys.platform.startswith('linux')

        if self.is_macos:
            self.service_dir = self.home / "Library" / "LaunchAgents"
            self.service_file = self.service_dir / f"{self.service_name}.plist"
        elif self.is_linux:
            self.service_dir = self.home / ".config" / "systemd" / "user"
            self.service_file = self.service_dir / f"{self.service_name}.service"
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

    def get_python_path(self) -> str:
        """Get the current Python interpreter path"""
        return sys.executable

    def generate_launchd_plist(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        extra_args: Optional[list] = None
    ) -> str:
        """Generate macOS LaunchAgent plist content"""
        python_path = self.get_python_path()

        # Build environment variables section
        env_section = ""
        if env_vars:
            for key, value in env_vars.items():
                env_section += f"""        <key>{key}</key>
        <string>{value}</string>
"""

        # Add PATH
        path_dirs = [
            str(Path(python_path).parent),
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/sbin",
            "/sbin"
        ]
        env_section += f"""        <key>PATH</key>
        <string>{':'.join(path_dirs)}</string>"""

        # Build extra arguments
        args_section = ""
        if extra_args:
            for arg in extra_args:
                args_section += f"""        <string>{arg}</string>
"""

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.service_name}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>databricks_oauth_rotator.cli</string>
{args_section}    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{self.home}/.databricks_oauth_rotator_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>{self.home}/.databricks_oauth_rotator_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
{env_section}
    </dict>

    <key>WorkingDirectory</key>
    <string>{self.home}</string>

    <key>ProcessType</key>
    <string>Background</string>

    <key>Nice</key>
    <integer>1</integer>
</dict>
</plist>
"""
        return plist_content

    def generate_systemd_service(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        extra_args: Optional[list] = None
    ) -> str:
        """Generate Linux systemd service content"""
        python_path = self.get_python_path()

        # Build environment variables
        env_section = ""
        if env_vars:
            for key, value in env_vars.items():
                env_section += f'Environment="{key}={value}"\n'

        # Build command with extra arguments
        cmd_args = ""
        if extra_args:
            cmd_args = " " + " ".join(extra_args)

        service_content = f"""[Unit]
Description=Databricks OAuth Token Auto-Rotation Service
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m databricks_oauth_rotator.cli{cmd_args}
Restart=always
RestartSec=10
{env_section}
StandardOutput=append:{self.home}/.databricks_oauth_rotator_stdout.log
StandardError=append:{self.home}/.databricks_oauth_rotator_stderr.log

[Install]
WantedBy=default.target
"""
        return service_content

    def install(
        self,
        env_vars: Optional[Dict[str, str]] = None,
        extra_args: Optional[list] = None
    ):
        """Install the service"""
        print(f"Installing OAuth rotation service on {sys.platform}...")

        # Create service directory
        self.service_dir.mkdir(parents=True, exist_ok=True)

        # Generate service file
        if self.is_macos:
            content = self.generate_launchd_plist(env_vars, extra_args)
        else:
            content = self.generate_systemd_service(env_vars, extra_args)

        # Write service file
        with open(self.service_file, 'w') as f:
            f.write(content)

        print(f"✓ Created service file: {self.service_file}")

        # Load/enable service
        self.start()

        print("\n✓ Service installed and started successfully!")
        print(f"\nMonitor logs:")
        print(f"  tail -f ~/.databricks_oauth_rotator.log")

    def uninstall(self):
        """Uninstall the service"""
        print("Uninstalling OAuth rotation service...")

        # Stop service
        self.stop()

        # Remove service file
        if self.service_file.exists():
            self.service_file.unlink()
            print(f"✓ Removed service file: {self.service_file}")

        print("✓ Service uninstalled successfully!")

    def start(self):
        """Start the service"""
        if self.is_macos:
            subprocess.run(['launchctl', 'load', str(self.service_file)], check=False)
            print("✓ Service started (macOS LaunchAgent)")
        else:
            subprocess.run(['systemctl', '--user', 'enable', f'{self.service_name}.service'], check=False)
            subprocess.run(['systemctl', '--user', 'start', f'{self.service_name}.service'], check=False)
            print("✓ Service started (systemd)")

    def stop(self):
        """Stop the service"""
        if self.is_macos:
            subprocess.run(['launchctl', 'unload', str(self.service_file)], check=False, stderr=subprocess.DEVNULL)
            print("✓ Service stopped (macOS LaunchAgent)")
        else:
            subprocess.run(['systemctl', '--user', 'stop', f'{self.service_name}.service'], check=False)
            print("✓ Service stopped (systemd)")

    def restart(self):
        """Restart the service"""
        print("Restarting service...")
        self.stop()
        self.start()

    def status(self):
        """Check service status"""
        if self.is_macos:
            result = subprocess.run(
                ['launchctl', 'list'],
                capture_output=True,
                text=True
            )
            if self.service_name in result.stdout:
                print("✓ Service is running")
                for line in result.stdout.split('\n'):
                    if self.service_name in line:
                        print(f"  {line}")
            else:
                print("✗ Service is not running")
        else:
            subprocess.run(['systemctl', '--user', 'status', f'{self.service_name}.service'])


def install_command():
    """CLI command for installing the service"""
    import argparse

    parser = argparse.ArgumentParser(description='Install Databricks OAuth rotation service')
    parser.add_argument('--workspace-url', help='Databricks workspace URL')
    parser.add_argument('--pg-host', help='PostgreSQL hostname')
    parser.add_argument('--pg-username', help='PostgreSQL username')
    parser.add_argument('--interval', type=int, default=50, help='Rotation interval in minutes')

    args = parser.parse_args()

    # Prepare environment variables
    env_vars = {}
    if args.workspace_url:
        env_vars['DATABRICKS_HOST'] = args.workspace_url
    if args.pg_host:
        env_vars['DATABRICKS_PG_HOST'] = args.pg_host
    if args.pg_username:
        env_vars['DATABRICKS_PG_USERNAME'] = args.pg_username

    # Prepare extra arguments
    extra_args = []
    if args.interval != 50:
        extra_args.extend(['--interval', str(args.interval)])

    # Install
    installer = ServiceInstaller()
    installer.install(env_vars=env_vars if env_vars else None, extra_args=extra_args if extra_args else None)


def uninstall_command():
    """CLI command for uninstalling the service"""
    installer = ServiceInstaller()
    installer.uninstall()


def status_command():
    """CLI command for checking service status"""
    installer = ServiceInstaller()
    installer.status()


def restart_command():
    """CLI command for restarting the service"""
    installer = ServiceInstaller()
    installer.restart()


if __name__ == '__main__':
    install_command()
