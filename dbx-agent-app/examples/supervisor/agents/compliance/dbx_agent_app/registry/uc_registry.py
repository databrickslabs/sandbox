"""
Unity Catalog agent registry.

Registers and manages agents as Unity Catalog AGENT objects for
catalog-based discovery and permission management.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class UCRegistrationError(Exception):
    """Raised when agent registration in Unity Catalog fails."""
    pass


@dataclass
class UCAgentSpec:
    """
    Specification for registering an agent in Unity Catalog.
    
    Attributes:
        name: Agent name (will be catalog object name)
        catalog: UC catalog name
        schema: UC schema name
        endpoint_url: Agent's base URL
        description: Agent description
        capabilities: List of agent capabilities
        properties: Additional metadata key-value pairs
    """
    name: str
    catalog: str
    schema: str
    endpoint_url: str
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    properties: Optional[Dict[str, str]] = None


class UCAgentRegistry:
    """
    Unity Catalog agent registry.
    
    Registers agents as UC AGENT objects for catalog-based discovery
    and permission management.
    
    Usage:
        registry = UCAgentRegistry(profile="my-profile")
        
        spec = UCAgentSpec(
            name="customer_research",
            catalog="main",
            schema="agents",
            endpoint_url="https://app.databricksapps.com",
            description="Customer research agent",
            capabilities=["search", "analysis"],
        )
        
        registry.register_agent(spec)
    """
    
    def __init__(self, profile: Optional[str] = None):
        """
        Initialize UC agent registry.
        
        Args:
            profile: Databricks CLI profile name (uses default if not specified)
        """
        self.profile = profile
        self._client: Optional[WorkspaceClient] = None
    
    def _get_client(self) -> WorkspaceClient:
        """Get or create workspace client."""
        if self._client is None:
            self._client = (
                WorkspaceClient(profile=self.profile)
                if self.profile
                else WorkspaceClient()
            )
        return self._client
    
    def register_agent(self, spec: UCAgentSpec) -> Dict[str, Any]:
        """
        Register an agent in Unity Catalog.
        
        Creates a AGENT object in the specified catalog and schema with
        metadata about the agent's endpoint, capabilities, and properties.
        
        Args:
            spec: Agent specification
            
        Returns:
            Dictionary with registration details
            
        Raises:
            UCRegistrationError: If registration fails
            
        Example:
            >>> registry = UCAgentRegistry(profile="my-profile")
            >>> spec = UCAgentSpec(
            ...     name="my_agent",
            ...     catalog="main",
            ...     schema="agents",
            ...     endpoint_url="https://app.databricksapps.com",
            ... )
            >>> result = registry.register_agent(spec)
        """
        client = self._get_client()
        full_name = f"{spec.catalog}.{spec.schema}.{spec.name}"
        
        try:
            # Build agent properties for UC metadata
            properties = spec.properties or {}
            properties["endpoint_url"] = spec.endpoint_url
            properties["agent_card_url"] = f"{spec.endpoint_url}/.well-known/agent.json"
            
            if spec.capabilities:
                properties["capabilities"] = ",".join(spec.capabilities)
            
            # Register as a UC registered model with AGENT type
            # (UC doesn't have a native AGENT type yet, so we use registered models
            # with special tags/properties to mark them as agents)
            
            logger.info(f"Registering agent '{full_name}' in Unity Catalog")
            
            # Check if catalog and schema exist
            try:
                client.catalogs.get(spec.catalog)
            except Exception as e:
                raise UCRegistrationError(
                    f"Catalog '{spec.catalog}' does not exist or is not accessible: {e}"
                )
            
            try:
                client.schemas.get(f"{spec.catalog}.{spec.schema}")
            except Exception as e:
                raise UCRegistrationError(
                    f"Schema '{spec.catalog}.{spec.schema}' does not exist or is not accessible: {e}"
                )
            
            # Create or update registered model as agent placeholder
            # In a future UC version with native AGENT support, this would use:
            # client.agents.create(name=full_name, properties=properties)
            
            # Encode properties as JSON suffix in comment for discovery
            # Format: "description\n---AGENT_META---\n{json}"
            meta = {"databricks_agent": True, **properties}
            comment = spec.description or ""
            comment_with_meta = f"{comment}\n---AGENT_META---\n{json.dumps(meta)}"

            # Try update first (model may already exist from prior deploy),
            # fall back to create if it doesn't exist
            try:
                client.registered_models.update(
                    full_name,
                    comment=comment_with_meta,
                )
                logger.info(f"Updated existing agent '{full_name}'")
            except Exception as update_err:
                # Model doesn't exist or SP can't access it — try create
                logger.debug(f"Update failed ({update_err}), trying create")
                try:
                    client.registered_models.create(
                        name=spec.name,
                        catalog_name=spec.catalog,
                        schema_name=spec.schema,
                        comment=comment_with_meta,
                    )
                    logger.info(f"Created new agent '{full_name}'")
                except Exception as create_err:
                    # If create fails with "already exists", the SP just
                    # can't see the model — log warning but don't fail
                    err_str = str(create_err).lower()
                    if "already exists" in err_str or "not a valid name" in err_str:
                        logger.warning(
                            "Agent '%s' exists but SP cannot update it. "
                            "Grant the app's SP ownership or MANAGE on the model.",
                            full_name,
                        )
                    else:
                        raise
            
            logger.info(f"Successfully registered agent '{full_name}'")
            
            return {
                "full_name": full_name,
                "catalog": spec.catalog,
                "schema": spec.schema,
                "name": spec.name,
                "endpoint_url": spec.endpoint_url,
                "properties": properties,
            }
            
        except UCRegistrationError:
            raise
        except Exception as e:
            raise UCRegistrationError(
                f"Failed to register agent '{full_name}': {e}"
            ) from e
    
    @staticmethod
    def _parse_agent_meta(comment: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse agent metadata from comment field (JSON after ---AGENT_META--- marker)."""
        if not comment or "---AGENT_META---" not in comment:
            return None
        try:
            _, meta_json = comment.split("---AGENT_META---", 1)
            return json.loads(meta_json.strip())
        except (ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _clean_description(comment: Optional[str]) -> str:
        """Extract human-readable description from comment (before the meta marker)."""
        if not comment:
            return ""
        if "---AGENT_META---" in comment:
            return comment.split("---AGENT_META---")[0].strip()
        return comment

    def get_agent(self, catalog: str, schema: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent metadata from Unity Catalog.

        Args:
            catalog: UC catalog name
            schema: UC schema name
            name: Agent name

        Returns:
            Agent metadata dictionary or None if not found
        """
        client = self._get_client()
        full_name = f"{catalog}.{schema}.{name}"

        try:
            model = client.registered_models.get(full_name)
            meta = self._parse_agent_meta(model.comment)
            if not meta or not meta.get("databricks_agent"):
                return None

            return {
                "full_name": full_name,
                "catalog": catalog,
                "schema": schema,
                "name": name,
                "description": self._clean_description(model.comment),
                "endpoint_url": meta.get("endpoint_url"),
                "agent_card_url": meta.get("agent_card_url"),
                "capabilities": meta.get("capabilities", "").split(",") if meta.get("capabilities") else None,
                "properties": meta,
            }

        except Exception as e:
            logger.debug(f"Agent '{full_name}' not found: {e}")
            return None

    def list_agents(
        self,
        catalog: str,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List all agents in a catalog or schema.

        Args:
            catalog: UC catalog name
            schema: Optional UC schema name (lists all schemas if not specified)

        Returns:
            List of agent metadata dictionaries
        """
        client = self._get_client()
        agents = []

        # Determine which schemas to scan
        schemas_to_scan = [schema] if schema else []
        if not schema:
            try:
                for s in client.schemas.list(catalog_name=catalog):
                    if s.name != "information_schema":
                        schemas_to_scan.append(s.name)
            except Exception as e:
                logger.error(f"Failed to list schemas in {catalog}: {e}")
                return []

        for schema_name in schemas_to_scan:
            try:
                models = client.registered_models.list(
                    catalog_name=catalog, schema_name=schema_name
                )
                for model in models:
                    meta = self._parse_agent_meta(model.comment)
                    if not meta or not meta.get("databricks_agent"):
                        continue

                    agents.append({
                        "full_name": model.full_name,
                        "catalog": catalog,
                        "schema": schema_name,
                        "name": model.name,
                        "description": self._clean_description(model.comment),
                        "endpoint_url": meta.get("endpoint_url"),
                        "capabilities": meta.get("capabilities", "").split(",") if meta.get("capabilities") else None,
                    })
            except Exception as e:
                logger.debug(f"Failed to list models in {catalog}.{schema_name}: {e}")
                continue

        return agents
    
    def delete_agent(self, catalog: str, schema: str, name: str) -> bool:
        """
        Delete an agent from Unity Catalog.
        
        Args:
            catalog: UC catalog name
            schema: UC schema name
            name: Agent name
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            UCRegistrationError: If deletion fails
        """
        client = self._get_client()
        full_name = f"{catalog}.{schema}.{name}"
        
        try:
            client.registered_models.delete(full_name)
            logger.info(f"Deleted agent '{full_name}'")
            return True
        except Exception as e:
            if "does not exist" in str(e).lower():
                return False
            raise UCRegistrationError(
                f"Failed to delete agent '{full_name}': {e}"
            ) from e
