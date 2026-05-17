"""
Unity Catalog asset crawler service.

Walks the UC hierarchy (catalogs → schemas → tables/views/functions/models/volumes)
using the Databricks SDK and indexes metadata into the registry database.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    """Tracks crawl progress and results."""

    catalogs_crawled: int = 0
    schemas_crawled: int = 0
    assets_discovered: int = 0
    new_assets: int = 0
    updated_assets: int = 0
    errors: List[str] = field(default_factory=list)


class CatalogCrawlerService:
    """
    Crawls Unity Catalog to index tables, views, functions, models, and volumes.

    Uses the Databricks SDK WorkspaceClient to walk the UC namespace hierarchy
    and upserts discovered metadata into the CatalogAsset table.
    """

    def __init__(self, profile: Optional[str] = None):
        self._profile = profile

    def _get_client(self):
        """Get a Databricks WorkspaceClient."""
        from databricks.sdk import WorkspaceClient

        if self._profile:
            return WorkspaceClient(profile=self._profile)
        return WorkspaceClient()

    def crawl(
        self,
        catalogs: Optional[List[str]] = None,
        include_columns: bool = True,
    ) -> CrawlStats:
        """
        Crawl Unity Catalog and upsert assets into the database.

        Args:
            catalogs: Specific catalogs to crawl. If None, crawls all accessible.
            include_columns: Whether to fetch column details for tables/views.

        Returns:
            CrawlStats with crawl results.
        """
        stats = CrawlStats()
        client = self._get_client()
        now = datetime.now(timezone.utc)

        # Get catalogs to crawl
        try:
            if catalogs:
                catalog_list = catalogs
            else:
                catalog_list = [c.name for c in client.catalogs.list()]
        except Exception as e:
            stats.errors.append(f"Failed to list catalogs: {e}")
            return stats

        for catalog_name in catalog_list:
            try:
                self._crawl_catalog(client, catalog_name, include_columns, now, stats)
                stats.catalogs_crawled += 1
            except Exception as e:
                stats.errors.append(f"Failed to crawl catalog '{catalog_name}': {e}")
                logger.error("Catalog crawl error for '%s': %s", catalog_name, e)

        return stats

    def _crawl_catalog(
        self,
        client,
        catalog_name: str,
        include_columns: bool,
        now: datetime,
        stats: CrawlStats,
    ):
        """Crawl all schemas in a catalog."""
        try:
            schemas = list(client.schemas.list(catalog_name=catalog_name))
        except Exception as e:
            stats.errors.append(f"Failed to list schemas in '{catalog_name}': {e}")
            return

        for schema in schemas:
            schema_name = schema.name
            if schema_name in ("information_schema",):
                continue

            try:
                self._crawl_schema(client, catalog_name, schema_name, include_columns, now, stats)
                stats.schemas_crawled += 1
            except Exception as e:
                stats.errors.append(f"Failed to crawl schema '{catalog_name}.{schema_name}': {e}")
                logger.error("Schema crawl error for '%s.%s': %s", catalog_name, schema_name, e)

    def _crawl_schema(
        self,
        client,
        catalog_name: str,
        schema_name: str,
        include_columns: bool,
        now: datetime,
        stats: CrawlStats,
    ):
        """Crawl all assets in a schema."""
        # Tables and views
        try:
            tables = list(client.tables.list(
                catalog_name=catalog_name,
                schema_name=schema_name,
            ))
            for table in tables:
                asset_type = "view" if table.table_type and str(table.table_type) == "VIEW" else "table"
                columns = None
                if include_columns and hasattr(table, "columns") and table.columns:
                    columns = [
                        {
                            "name": col.name,
                            "type": str(col.type_text) if col.type_text else str(col.type_name),
                            "comment": col.comment,
                            "nullable": col.nullable if hasattr(col, "nullable") else True,
                            "position": col.position if hasattr(col, "position") else None,
                        }
                        for col in table.columns
                    ]

                properties = None
                if hasattr(table, "properties") and table.properties:
                    properties = dict(table.properties)

                self._upsert_asset(
                    asset_type=asset_type,
                    catalog=catalog_name,
                    schema_name=schema_name,
                    name=table.name,
                    full_name=f"{catalog_name}.{schema_name}.{table.name}",
                    owner=table.owner if hasattr(table, "owner") else None,
                    comment=table.comment if hasattr(table, "comment") else None,
                    columns_json=json.dumps(columns) if columns else None,
                    properties_json=json.dumps(properties) if properties else None,
                    data_source_format=str(table.data_source_format) if hasattr(table, "data_source_format") and table.data_source_format else None,
                    table_type=str(table.table_type) if hasattr(table, "table_type") and table.table_type else None,
                    now=now,
                    stats=stats,
                )
        except Exception as e:
            stats.errors.append(f"Failed to list tables in '{catalog_name}.{schema_name}': {e}")

        # Functions
        try:
            functions = list(client.functions.list(
                catalog_name=catalog_name,
                schema_name=schema_name,
            ))
            for func in functions:
                params = None
                if hasattr(func, "input_params") and func.input_params:
                    params_list = func.input_params.parameters if hasattr(func.input_params, "parameters") else []
                    params = [
                        {
                            "name": p.name,
                            "type": str(p.type_text) if hasattr(p, "type_text") else str(p.type_name),
                            "comment": p.comment if hasattr(p, "comment") else None,
                        }
                        for p in params_list
                    ]

                self._upsert_asset(
                    asset_type="function",
                    catalog=catalog_name,
                    schema_name=schema_name,
                    name=func.name,
                    full_name=f"{catalog_name}.{schema_name}.{func.name}",
                    owner=func.owner if hasattr(func, "owner") else None,
                    comment=func.comment if hasattr(func, "comment") else None,
                    columns_json=json.dumps(params) if params else None,
                    now=now,
                    stats=stats,
                )
        except Exception as e:
            # Functions API may not be available in all workspaces
            logger.debug("Functions listing skipped for '%s.%s': %s", catalog_name, schema_name, e)

        # Volumes
        try:
            volumes = list(client.volumes.list(
                catalog_name=catalog_name,
                schema_name=schema_name,
            ))
            for vol in volumes:
                self._upsert_asset(
                    asset_type="volume",
                    catalog=catalog_name,
                    schema_name=schema_name,
                    name=vol.name,
                    full_name=f"{catalog_name}.{schema_name}.{vol.name}",
                    owner=vol.owner if hasattr(vol, "owner") else None,
                    comment=vol.comment if hasattr(vol, "comment") else None,
                    now=now,
                    stats=stats,
                )
        except Exception as e:
            logger.debug("Volumes listing skipped for '%s.%s': %s", catalog_name, schema_name, e)

    def _upsert_asset(
        self,
        asset_type: str,
        catalog: str,
        schema_name: str,
        name: str,
        full_name: str,
        now: datetime,
        stats: CrawlStats,
        owner: Optional[str] = None,
        comment: Optional[str] = None,
        columns_json: Optional[str] = None,
        tags_json: Optional[str] = None,
        properties_json: Optional[str] = None,
        data_source_format: Optional[str] = None,
        table_type: Optional[str] = None,
    ):
        """Upsert a single catalog asset into the database."""
        from app.db_adapter import WarehouseDB

        existing = WarehouseDB.get_catalog_asset_by_full_name(full_name)

        if existing:
            WarehouseDB.update_catalog_asset(
                existing["id"],
                owner=owner,
                comment=comment,
                columns_json=columns_json,
                tags_json=tags_json,
                properties_json=properties_json,
                data_source_format=data_source_format,
                table_type=table_type,
                last_indexed_at=now.isoformat(),
            )
            stats.updated_assets += 1
        else:
            WarehouseDB.create_catalog_asset(
                asset_type=asset_type,
                catalog=catalog,
                schema_name=schema_name,
                name=name,
                full_name=full_name,
                owner=owner,
                comment=comment,
                columns_json=columns_json,
                tags_json=tags_json,
                properties_json=properties_json,
                data_source_format=data_source_format,
                table_type=table_type,
                last_indexed_at=now.isoformat(),
            )
            stats.new_assets += 1

        stats.assets_discovered += 1
