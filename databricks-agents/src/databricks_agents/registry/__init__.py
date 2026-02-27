"""
Unity Catalog integration for agent registration.

This module provides utilities for registering agents in Unity Catalog
as AGENT objects, enabling catalog-based discovery and permission management.
"""

from .uc_registry import UCAgentRegistry, UCRegistrationError

__all__ = ["UCAgentRegistry", "UCRegistrationError"]
