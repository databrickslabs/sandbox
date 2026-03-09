"""
Databricks workspace object crawler service.

Indexes notebooks, jobs, dashboards, pipelines, clusters, and experiments
using the Databricks SDK into the registry database.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

ALL_ASSET_TYPES = ["notebook", "job", "dashboard", "pipeline", "cluster", "experiment"]


@dataclass
class WorkspaceCrawlStats:
    """Tracks workspace crawl progress and results."""

    assets_discovered: int = 0
    new_assets: int = 0
    updated_assets: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class WorkspaceCrawlerService:
    """
    Crawls a Databricks workspace to index notebooks, jobs, dashboards,
    pipelines, clusters, and experiments.

    Uses the Databricks SDK WorkspaceClient for each asset type.
    """

    def __init__(self, profile: Optional[str] = None):
        self._profile = profile
        self._workspace_host: Optional[str] = None

    def _get_client(self):
        """Get a Databricks WorkspaceClient."""
        from databricks.sdk import WorkspaceClient

        if self._profile:
            client = WorkspaceClient(profile=self._profile)
        else:
            client = WorkspaceClient()
        self._workspace_host = str(client.config.host).rstrip("/")
        return client

    def crawl(
        self,
        asset_types: Optional[List[str]] = None,
        root_path: str = "/",
    ) -> WorkspaceCrawlStats:
        """
        Crawl workspace and upsert assets into the database.

        Args:
            asset_types: Specific types to crawl. If None, crawls all.
            root_path: Root path for notebook crawl.

        Returns:
            WorkspaceCrawlStats with crawl results.
        """
        stats = WorkspaceCrawlStats()
        client = self._get_client()
        now = datetime.now(timezone.utc)
        types_to_crawl = asset_types or ALL_ASSET_TYPES

        for asset_type in types_to_crawl:
            try:
                crawler = getattr(self, f"_crawl_{asset_type}s", None)
                if crawler:
                    crawler(client, now, stats, root_path=root_path)
                else:
                    stats.errors.append(f"Unknown asset type: {asset_type}")
            except Exception as e:
                stats.errors.append(f"Failed to crawl {asset_type}s: {e}")
                logger.error("Workspace crawl error for %ss: %s", asset_type, e)

        return stats

    def _crawl_notebooks(self, client, now: datetime, stats: WorkspaceCrawlStats, root_path: str = "/"):
        """Crawl workspace notebooks recursively."""
        from databricks.sdk.service.workspace import ObjectType

        count = 0
        try:
            objects = client.workspace.list(root_path, recursive=True)
            for obj in objects:
                if obj.object_type != ObjectType.NOTEBOOK:
                    continue

                name = obj.path.rsplit("/", 1)[-1] if obj.path else "unknown"
                language = str(obj.language).lower() if obj.language else None

                self._upsert_workspace_asset(
                    asset_type="notebook",
                    path=obj.path,
                    name=name,
                    language=language,
                    resource_id=str(obj.object_id) if obj.object_id else None,
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Notebook listing error at '{root_path}': {e}")

        stats.by_type["notebook"] = count

    def _crawl_jobs(self, client, now: datetime, stats: WorkspaceCrawlStats, **kwargs):
        """Crawl Databricks jobs."""
        count = 0
        try:
            jobs = client.jobs.list()
            for job in jobs:
                job_settings = job.settings if hasattr(job, "settings") else None
                name = job_settings.name if job_settings and hasattr(job_settings, "name") else f"job-{job.job_id}"

                metadata = {
                    "job_id": job.job_id,
                }
                if job_settings:
                    if hasattr(job_settings, "schedule") and job_settings.schedule:
                        metadata["schedule"] = str(job_settings.schedule.quartz_cron_expression) if hasattr(job_settings.schedule, "quartz_cron_expression") else None
                    if hasattr(job_settings, "tasks") and job_settings.tasks:
                        metadata["task_count"] = len(job_settings.tasks)
                        metadata["task_types"] = list(set(
                            t.task_key for t in job_settings.tasks if hasattr(t, "task_key")
                        ))

                owner = None
                if hasattr(job, "creator_user_name"):
                    owner = job.creator_user_name

                self._upsert_workspace_asset(
                    asset_type="job",
                    path=f"/jobs/{job.job_id}",
                    name=name,
                    owner=owner,
                    metadata_json=json.dumps(metadata),
                    resource_id=str(job.job_id),
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Jobs listing error: {e}")

        stats.by_type["job"] = count

    def _crawl_dashboards(self, client, now: datetime, stats: WorkspaceCrawlStats, **kwargs):
        """Crawl Lakeview dashboards."""
        count = 0
        try:
            dashboards = client.lakeview.list()
            for dashboard in dashboards:
                name = dashboard.display_name if hasattr(dashboard, "display_name") else "untitled"
                path = dashboard.path if hasattr(dashboard, "path") else f"/dashboards/{dashboard.dashboard_id}"

                metadata = {
                    "dashboard_id": dashboard.dashboard_id,
                }
                if hasattr(dashboard, "warehouse_id") and dashboard.warehouse_id:
                    metadata["warehouse_id"] = dashboard.warehouse_id

                owner = None
                if hasattr(dashboard, "creator_user_name"):
                    owner = dashboard.creator_user_name

                self._upsert_workspace_asset(
                    asset_type="dashboard",
                    path=path,
                    name=name,
                    owner=owner,
                    metadata_json=json.dumps(metadata),
                    resource_id=dashboard.dashboard_id if hasattr(dashboard, "dashboard_id") else None,
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Dashboard listing error: {e}")

        stats.by_type["dashboard"] = count

    def _crawl_pipelines(self, client, now: datetime, stats: WorkspaceCrawlStats, **kwargs):
        """Crawl DLT/SDP pipelines."""
        count = 0
        try:
            pipelines = client.pipelines.list_pipelines()
            for pipeline in pipelines:
                name = pipeline.name if hasattr(pipeline, "name") else f"pipeline-{pipeline.pipeline_id}"

                metadata = {
                    "pipeline_id": pipeline.pipeline_id,
                    "state": str(pipeline.state) if hasattr(pipeline, "state") and pipeline.state else None,
                }

                owner = None
                if hasattr(pipeline, "creator_user_name"):
                    owner = pipeline.creator_user_name

                self._upsert_workspace_asset(
                    asset_type="pipeline",
                    path=f"/pipelines/{pipeline.pipeline_id}",
                    name=name,
                    owner=owner,
                    metadata_json=json.dumps(metadata),
                    resource_id=pipeline.pipeline_id,
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Pipeline listing error: {e}")

        stats.by_type["pipeline"] = count

    def _crawl_clusters(self, client, now: datetime, stats: WorkspaceCrawlStats, **kwargs):
        """Crawl compute clusters."""
        count = 0
        try:
            clusters = client.clusters.list()
            for cluster in clusters:
                name = cluster.cluster_name if hasattr(cluster, "cluster_name") else f"cluster-{cluster.cluster_id}"

                metadata = {
                    "cluster_id": cluster.cluster_id,
                    "state": str(cluster.state) if hasattr(cluster, "state") and cluster.state else None,
                    "spark_version": cluster.spark_version if hasattr(cluster, "spark_version") else None,
                    "node_type_id": cluster.node_type_id if hasattr(cluster, "node_type_id") else None,
                }

                owner = None
                if hasattr(cluster, "creator_user_name"):
                    owner = cluster.creator_user_name

                self._upsert_workspace_asset(
                    asset_type="cluster",
                    path=f"/clusters/{cluster.cluster_id}",
                    name=name,
                    owner=owner,
                    metadata_json=json.dumps(metadata),
                    resource_id=cluster.cluster_id,
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Cluster listing error: {e}")

        stats.by_type["cluster"] = count

    def _crawl_experiments(self, client, now: datetime, stats: WorkspaceCrawlStats, **kwargs):
        """Crawl MLflow experiments."""
        count = 0
        try:
            experiments = client.experiments.list_experiments()
            for exp in experiments:
                name = exp.name if hasattr(exp, "name") else f"experiment-{exp.experiment_id}"

                metadata = {
                    "experiment_id": exp.experiment_id,
                    "lifecycle_stage": str(exp.lifecycle_stage) if hasattr(exp, "lifecycle_stage") and exp.lifecycle_stage else None,
                }

                self._upsert_workspace_asset(
                    asset_type="experiment",
                    path=exp.name if exp.name and exp.name.startswith("/") else f"/experiments/{exp.experiment_id}",
                    name=name.rsplit("/", 1)[-1] if "/" in name else name,
                    metadata_json=json.dumps(metadata),
                    resource_id=exp.experiment_id,
                    now=now,
                    stats=stats,
                )
                count += 1
        except Exception as e:
            stats.errors.append(f"Experiment listing error: {e}")

        stats.by_type["experiment"] = count

    def _upsert_workspace_asset(
        self,
        asset_type: str,
        path: str,
        name: str,
        now: datetime,
        stats: WorkspaceCrawlStats,
        owner: Optional[str] = None,
        description: Optional[str] = None,
        language: Optional[str] = None,
        tags_json: Optional[str] = None,
        metadata_json: Optional[str] = None,
        content_preview: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """Upsert a single workspace asset into the database."""
        from app.db_adapter import WarehouseDB

        existing = WarehouseDB.get_workspace_asset_by_path(self._workspace_host, path)

        if existing:
            WarehouseDB.update_workspace_asset(
                existing["id"],
                name=name,
                owner=owner,
                description=description,
                language=language,
                tags_json=tags_json,
                metadata_json=metadata_json,
                content_preview=content_preview,
                resource_id=resource_id,
                last_indexed_at=now.isoformat(),
            )
            stats.updated_assets += 1
        else:
            WarehouseDB.create_workspace_asset(
                asset_type=asset_type,
                workspace_host=self._workspace_host,
                path=path,
                name=name,
                owner=owner,
                description=description,
                language=language,
                tags_json=tags_json,
                metadata_json=metadata_json,
                content_preview=content_preview,
                resource_id=resource_id,
                last_indexed_at=now.isoformat(),
            )
            stats.new_assets += 1

        stats.assets_discovered += 1
