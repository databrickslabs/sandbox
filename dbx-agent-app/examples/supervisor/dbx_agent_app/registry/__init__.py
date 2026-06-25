"""
Unity Catalog integration for agent registration.

This module provides utilities for registering agents in Unity Catalog
as AGENT objects, enabling catalog-based discovery and permission management.
"""

from .uc_registry import UCAgentRegistry, UCAgentSpec, UCRegistrationError

__all__ = ["UCAgentRegistry", "UCAgentSpec", "UCRegistrationError"]
