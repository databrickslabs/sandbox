from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Database Configuration (Lakebase via Unity Catalog)
    database_url: str
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # Databricks Configuration
    databricks_host: Optional[str] = None
    databricks_token: Optional[str] = None
    databricks_config_profile: Optional[str] = None
    databricks_warehouse_id: Optional[str] = None
    db_catalog: str = "serverless_dxukih_catalog"
    db_schema: str = "registry"

    # LLM Configuration
    llm_endpoint: str = "databricks-claude-sonnet-4-5"

    # Embedding Configuration
    embedding_model: str = "databricks-bge-large-en"
    embedding_dimension: int = 1024
    search_results_limit: int = 20

    # API Configuration
    api_title: str = "Multi-Agent Registry API"
    api_version: str = "0.1.0"
    api_prefix: str = "/api"

    # Server Configuration
    port: int = 8000
    host: str = "0.0.0.0"

    # MCP Catalog Configuration
    mcp_catalog_url: Optional[str] = None

    # MLflow Tracing
    mlflow_tracking_uri: str = "databricks"
    mlflow_experiment_name: str = "/Shared/registry-api-chat-traces"

    # A2A Protocol
    a2a_protocol_version: str = "0.3.0"
    a2a_base_url: Optional[str] = None

    # Authentication
    # Set to False to disable auth middleware (not recommended for production)
    auth_enabled: bool = True

    # Environment
    environment: str = "development"
    debug: bool = False

    # CORS Settings
    # Default to localhost for development. In production, set explicit origins.
    cors_origins: str = "http://localhost:3000,http://localhost:5500,http://localhost:5501"
    cors_credentials: bool = True
    cors_methods: str = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
    cors_headers: str = "Content-Type,Authorization,X-Requested-With,Accept,Origin"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
