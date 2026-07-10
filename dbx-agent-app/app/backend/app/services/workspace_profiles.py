"""
Service for discovering Databricks workspace profiles from ~/.databrickscfg.

Parses the CLI config file and validates authentication for each profile
by calling the Databricks SDK's current_user.me() endpoint.
"""

import asyncio
import configparser
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.expanduser("~/.databrickscfg")


@dataclass
class WorkspaceProfile:
    name: str
    host: Optional[str] = None
    auth_type: Optional[str] = None
    is_account_profile: bool = False
    auth_valid: bool = False
    auth_error: Optional[str] = None
    username: Optional[str] = None


def parse_databricks_config(
    config_path: str = DEFAULT_CONFIG_PATH,
) -> List[dict]:
    """Parse ~/.databrickscfg and return raw profile dicts."""
    path = Path(config_path)
    if not path.exists():
        logger.warning("Databricks config not found at %s", config_path)
        return []

    parser = configparser.ConfigParser()
    parser.read(str(path))

    profiles = []
    for section in parser.sections():
        profile = {"name": section}
        profile.update(dict(parser[section]))
        profiles.append(profile)

    return profiles


def _detect_auth_type(profile: dict) -> str:
    """Infer auth type from profile fields."""
    if profile.get("token"):
        return "pat"
    if profile.get("client_id") and profile.get("client_secret"):
        return "oauth-m2m"
    if profile.get("azure_client_id"):
        return "azure-service-principal"
    if profile.get("google_service_account"):
        return "google-service-account"
    return "default"


def _validate_profile_sync(profile_name: str, host: Optional[str]) -> WorkspaceProfile:
    """Synchronously validate a single profile's auth (runs in thread pool)."""
    try:
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient(profile=profile_name)
        me = w.current_user.me()
        return WorkspaceProfile(
            name=profile_name,
            host=host,
            auth_valid=True,
            username=me.user_name or me.display_name,
        )
    except Exception as e:
        return WorkspaceProfile(
            name=profile_name,
            host=host,
            auth_valid=False,
            auth_error=str(e),
        )


async def validate_profile_auth(profile_name: str, host: Optional[str]) -> WorkspaceProfile:
    """Validate a profile's auth by calling current_user.me() in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _validate_profile_sync, profile_name, host)


async def discover_workspace_profiles(
    config_path: str = DEFAULT_CONFIG_PATH,
) -> List[WorkspaceProfile]:
    """Parse config and validate all workspace profiles concurrently."""
    raw_profiles = parse_databricks_config(config_path)

    if not raw_profiles:
        return []

    results: List[WorkspaceProfile] = []
    validation_tasks = []

    for raw in raw_profiles:
        name = raw["name"]
        host = raw.get("host")
        is_account = bool(raw.get("account_id"))
        auth_type = _detect_auth_type(raw)

        if is_account:
            # Flag account-level profiles but skip workspace auth validation
            results.append(
                WorkspaceProfile(
                    name=name,
                    host=host,
                    auth_type=auth_type,
                    is_account_profile=True,
                    auth_valid=False,
                    auth_error="Account-level profile (not a workspace)",
                )
            )
        else:
            validation_tasks.append((name, host, auth_type))

    # Validate workspace profiles concurrently
    if validation_tasks:
        validated = await asyncio.gather(
            *[validate_profile_auth(name, host) for name, host, _ in validation_tasks]
        )
        # Patch in auth_type from parsed config
        for profile, (_, _, auth_type) in zip(validated, validation_tasks):
            profile.auth_type = auth_type
        results.extend(validated)

    # Sort: valid profiles first, then by name
    results.sort(key=lambda p: (not p.auth_valid, p.is_account_profile, p.name))

    return results
