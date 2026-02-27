"""
Unity Catalog agent registry.

Registers and manages agents as Unity Catalog AGENT objects for
catalog-based discovery and permission management.
"""

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
            
            try:
                # Try to get existing model
                model = client.registered_models.get(full_name)
                logger.info(f"Agent '{full_name}' already exists, updating metadata")
                
                # Update properties
                client.registered_models.update(
                    name=full_name,
                    comment=spec.description,
                )
                
            except Exception:
                # Create new model
                logger.info(f"Creating new agent '{full_name}'")
                client.registered_models.create(
                    name=full_name,
                    catalog_name=spec.catalog,
                    schema_name=spec.schema,
                    comment=spec.description,
                )
            
            # Set properties as tags (workaround until UC has native AGENT type)
            for key, value in properties.items():
                try:
                    client.registered_models.set_tag(
                        full_name=full_name,
                        key=key,
                        value=str(value),
                    )
                except Exception as e:
                    logger.warning(f"Failed to set tag {key}: {e}")
            
            # Mark as agent type
            try:
                client.registered_models.set_tag(
                    full_name=full_name,
                    key="databricks_agent",
                    value="true",
                )
            except Exception as e:
                logger.warning(f"Failed to set agent tag: {e}")
            
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
            
            # Get tags
            tags = {}
            try:
                tag_list = client.registered_models.list_tags(full_name)
                for tag in tag_list:
                    tags[tag.key] = tag.value
            except Exception:
                pass
            
            # Check if it's marked as an agent
            if tags.get("databricks_agent") != "true":
                return None
            
            return {
                "full_name": full_name,
                "catalog": catalog,
                "schema": schema,
                "name": name,
                "description": model.comment,
                "endpoint_url": tags.get("endpoint_url"),
                "agent_card_url": tags.get("agent_card_url"),
                "capabilities": tags.get("capabilities", "").split(",") if tags.get("capabilities") else None,
                "properties": tags,
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
        
        try:
            # List all registered models in catalog/schema
            if schema:
                pattern = f"{catalog}.{schema}.*"
            else:
                pattern = f"{catalog}.*"
            
            models = client.registered_models.list(catalog_name=catalog)
            
            for model in models:
                model_name = model.name
                
                # Check if it's an agent
                try:
                    tags = {}
                    tag_list = client.registered_models.list_tags(model_name)
                    for tag in tag_list:
                        tags[tag.key] = tag.value
                    
                    if tags.get("databricks_agent") == "true":
                        parts = model_name.split(".")
                        agents.append({
                            "full_name": model_name,
                            "catalog": parts[0] if len(parts) > 0 else catalog,
                            "schema": parts[1] if len(parts) > 1 else "",
                            "name": parts[2] if len(parts) > 2 else model_name,
                            "description": model.comment,
                            "endpoint_url": tags.get("endpoint_url"),
                            "capabilities": tags.get("capabilities", "").split(",") if tags.get("capabilities") else None,
                        })
                except Exception as e:
                    logger.debug(f"Failed to check model {model_name}: {e}")
                    continue
            
            return agents
            
        except Exception as e:
            logger.error(f"Failed to list agents in {catalog}: {e}")
            return []
    
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
