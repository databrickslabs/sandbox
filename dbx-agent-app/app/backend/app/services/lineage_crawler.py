"""
Lineage Crawler Service — discovers relationships between assets.

Data sources:
  1. UC system tables: system.access.table_lineage (table→table)
  2. Job definitions: jobs API → task SQL/notebook → table refs
  3. Notebook SQL cells: regex-based table reference extraction
  4. Dashboard queries: dashboard→query→table dependencies

Produces AssetRelationship rows that form the knowledge graph.
"""

import json
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from app.config import settings
from app.db_adapter import DatabaseAdapter

logger = logging.getLogger(__name__)

# Regex for extracting table references from SQL
# Matches: catalog.schema.table or schema.table patterns
TABLE_REF_PATTERN = re.compile(
    r'(?:FROM|JOIN|INTO|UPDATE|TABLE|MERGE\s+INTO)\s+'
    r'(?:`?(\w+)`?\.)?(?:`?(\w+)`?\.)`?(\w+)`?',
    re.IGNORECASE,
)


@dataclass
class LineageCrawlStats:
    relationships_discovered: int = 0
    new_relationships: int = 0
    errors: List[str] = field(default_factory=list)


class LineageCrawlerService:
    """Discovers and indexes relationships between assets."""

    def __init__(self, databricks_profile: Optional[str] = None):
        self._profile = databricks_profile

    def _get_client(self):
        from databricks.sdk import WorkspaceClient
        kwargs = {}
        if self._profile:
            kwargs["profile"] = self._profile
        elif settings.databricks_host:
            kwargs["host"] = settings.databricks_host
            if settings.databricks_token:
                kwargs["token"] = settings.databricks_token
        return WorkspaceClient(**kwargs)

    async def crawl(self, include_column_lineage: bool = False) -> LineageCrawlStats:
        """Run all lineage discovery sources."""
        stats = LineageCrawlStats()

        # 1. UC table lineage from system tables
        await self._crawl_table_lineage(stats)

        # 2. Job → table relationships
        await self._crawl_job_dependencies(stats)

        # 3. Notebook → table references (from indexed content)
        self._crawl_notebook_references(stats)

        logger.info(
            "Lineage crawl complete: %d discovered, %d new, %d errors",
            stats.relationships_discovered, stats.new_relationships, len(stats.errors),
        )
        return stats

    async def _crawl_table_lineage(self, stats: LineageCrawlStats) -> None:
        """Query UC system.access.table_lineage for table-to-table data flow."""
        try:
            w = self._get_client()

            # Build the lookup of catalog assets by full_name for ID resolution
            asset_lookup = self._build_catalog_asset_lookup()
            if not asset_lookup:
                logger.info("No catalog assets indexed — skipping UC lineage crawl")
                return

            # Query system table via SQL statement execution
            warehouse_id = settings.databricks_warehouse_id
            if not warehouse_id:
                logger.warning("No warehouse_id configured — cannot query system tables for lineage")
                stats.errors.append("No warehouse_id configured for system table queries")
                return

            sql = """
                SELECT
                    source_table_full_name,
                    target_table_full_name,
                    source_type,
                    target_type
                FROM system.access.table_lineage
                WHERE source_table_full_name IS NOT NULL
                  AND target_table_full_name IS NOT NULL
                GROUP BY 1, 2, 3, 4
            """

            rows = self._execute_sql(w, warehouse_id, sql)

            for row in rows:
                source_full = row.get("source_table_full_name", "")
                target_full = row.get("target_table_full_name", "")

                source_asset = asset_lookup.get(source_full)
                target_asset = asset_lookup.get(target_full)

                if not source_asset or not target_asset:
                    continue

                rel_type = "reads_from"
                source_uc_type = row.get("source_type", "")
                if source_uc_type and "WRITE" in source_uc_type.upper():
                    rel_type = "writes_to"

                self._upsert_relationship(
                    source_type=source_asset["asset_type"],
                    source_id=source_asset["id"],
                    source_name=source_full,
                    target_type=target_asset["asset_type"],
                    target_id=target_asset["id"],
                    target_name=target_full,
                    relationship_type=rel_type,
                    stats=stats,
                )

        except Exception as e:
            msg = f"UC lineage crawl error: {e}"
            logger.error(msg)
            stats.errors.append(msg)

    async def _crawl_job_dependencies(self, stats: LineageCrawlStats) -> None:
        """Parse job task configs to find job→table scheduling relationships."""
        try:
            # Get all indexed jobs
            jobs, _ = DatabaseAdapter.list_workspace_assets(
                page=1, page_size=1000, asset_type="job"
            )
            if not jobs:
                return

            asset_lookup = self._build_catalog_asset_lookup()

            for job_asset in jobs:
                metadata = {}
                if job_asset.get("metadata_json"):
                    try:
                        metadata = json.loads(job_asset["metadata_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                # Extract table refs from task types
                task_types = metadata.get("task_types", "")
                if not task_types:
                    continue

                # If we have content_preview with SQL, extract table refs
                content = job_asset.get("content_preview", "") or ""
                if not content:
                    continue

                table_refs = self._extract_table_refs(content)
                for ref in table_refs:
                    target = asset_lookup.get(ref)
                    if target:
                        self._upsert_relationship(
                            source_type="job",
                            source_id=job_asset["id"],
                            source_name=job_asset["name"],
                            target_type=target["asset_type"],
                            target_id=target["id"],
                            target_name=ref,
                            relationship_type="scheduled_by",
                            stats=stats,
                        )

        except Exception as e:
            msg = f"Job dependency crawl error: {e}"
            logger.error(msg)
            stats.errors.append(msg)

    def _crawl_notebook_references(self, stats: LineageCrawlStats) -> None:
        """Parse notebook content previews for SQL table references."""
        try:
            notebooks, _ = DatabaseAdapter.list_workspace_assets(
                page=1, page_size=2000, asset_type="notebook"
            )
            if not notebooks:
                return

            asset_lookup = self._build_catalog_asset_lookup()
            if not asset_lookup:
                return

            for nb in notebooks:
                content = nb.get("content_preview", "") or ""
                if not content:
                    continue

                table_refs = self._extract_table_refs(content)
                for ref in table_refs:
                    target = asset_lookup.get(ref)
                    if target:
                        self._upsert_relationship(
                            source_type="notebook",
                            source_id=nb["id"],
                            source_name=nb["name"],
                            target_type=target["asset_type"],
                            target_id=target["id"],
                            target_name=ref,
                            relationship_type="reads_from",
                            stats=stats,
                        )

        except Exception as e:
            msg = f"Notebook reference crawl error: {e}"
            logger.error(msg)
            stats.errors.append(msg)

    # --- Helpers ---

    def _build_catalog_asset_lookup(self) -> Dict[str, Dict]:
        """Build {full_name: asset_dict} lookup for all catalog assets."""
        assets, _ = DatabaseAdapter.list_catalog_assets(page=1, page_size=5000)
        return {a["full_name"]: a for a in assets if a.get("full_name")}

    def _extract_table_refs(self, sql_text: str) -> List[str]:
        """Extract three-part table references from SQL text."""
        refs = set()
        for match in TABLE_REF_PATTERN.finditer(sql_text):
            catalog, schema, table = match.group(1), match.group(2), match.group(3)
            if catalog and schema and table:
                refs.add(f"{catalog}.{schema}.{table}")
            elif schema and table:
                refs.add(f"{schema}.{table}")
        return list(refs)

    def _execute_sql(self, client, warehouse_id: str, sql: str) -> List[Dict]:
        """Execute SQL via Databricks Statement Execution API."""
        try:
            result = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=sql,
                wait_timeout="120s",
            )

            if not result.result or not result.result.data_array:
                return []

            columns = [col.name for col in result.manifest.schema.columns]
            rows = []
            for row_data in result.result.data_array:
                row = dict(zip(columns, row_data))
                rows.append(row)
            return rows

        except Exception as e:
            logger.error("SQL execution error: %s", e)
            return []

    def _upsert_relationship(
        self,
        source_type: str,
        source_id: int,
        source_name: str,
        target_type: str,
        target_id: int,
        target_name: str,
        relationship_type: str,
        stats: LineageCrawlStats,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Create or update a relationship edge."""
        stats.relationships_discovered += 1

        existing = DatabaseAdapter.get_asset_relationship(
            source_type, source_id, target_type, target_id, relationship_type
        )

        if existing:
            # Already exists — update if metadata changed
            if metadata:
                DatabaseAdapter.update_asset_relationship(
                    existing["id"],
                    metadata_json=json.dumps(metadata),
                )
        else:
            DatabaseAdapter.create_asset_relationship(
                source_type=source_type,
                source_id=source_id,
                source_name=source_name,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                relationship_type=relationship_type,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            stats.new_relationships += 1
