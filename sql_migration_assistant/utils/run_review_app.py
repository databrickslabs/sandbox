import logging

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute
from databricks.sdk.mixins.compute import ClustersExt
from databricks.labs.blueprint.commands import CommandExecutor
from urllib.parse import urlparse


class RunReviewApp:
    def __init__(self, w: WorkspaceClient, config: dict):
        self.w = w
        self.config = config
        self.cep = compute.CommandExecutionAPI(w.api_client)
        self.cet = ClustersExt(w.api_client)
        self.executor = CommandExecutor(
            clusters=self.cet,
            command_execution=self.cep,
            cluster_id_provider=self.cluster_id_getter,
            language=compute.Language.PYTHON,
        )
        self.libraries = [
            "gradio==4.27.0",
            "pyyaml",
            "databricks-sdk==0.30.0",
            "aiohttp",
            "databricks-labs-blueprint==0.8.2",
            "fastapi==0.112.2",
            "pydantic==2.8.2",
            "dbtunnel==0.14.6",
            "databricks-labs-lsql==0.9.0",
        ]

    def cluster_id_getter(self):
        return self.config.get("SERVING_CLUSTER_ID")

    def _library_install(self):

        for l in self.libraries:
            self.executor.install_notebook_library(l)
        self.executor.run("dbutils.library.restartPython()")

    def _path_updates(self):
        self.executor.run(
            code=f"""
import sys
sys.path.insert(0, '/Workspace/Users/{self.w.current_user.me().user_name}/.sql_migration_assistant/sql_migration_assistant/utils')
sys.path.insert(0, '/Workspace/Users/{self.w.current_user.me().user_name}/.sql_migration_assistant/sql_migration_assistant/app')
import os
path = '/Workspace/Users/{self.w.current_user.me().user_name}/.sql_migration_assistant/sql_migration_assistant'
os.chdir(path)
"""
        )

    def _get_org_id(self):
        return self.w.get_workspace_id()

    def _launch_app(self):
        self.executor.run(
            code="""
            from utils.runindatabricks import run_app
            run_app()
            """
        )

    def _get_proxy_url(self, organisation_id):

        def get_cloud_proxy_settings(
            cloud: str, host: str, org_id: str, cluster_id: str, port: int
        ):
            cloud_norm = cloud.lower()
            if cloud_norm not in ["aws", "azure"]:
                raise Exception("only supported in aws or azure")
            prefix_url_settings = {
                "aws": "https://dbc-dp-",
                "azure": "https://adb-dp-",
            }
            suffix_url_settings = {
                "azure": "azuredatabricks.net",
            }
            if cloud_norm == "aws":
                suffix = remove_lowest_subdomain_from_host(host)
                suffix_url_settings["aws"] = suffix

            org_shard = ""
            # org_shard doesnt need a suffix of "." for dnsname its handled in building the url
            # only azure right now does dns sharding
            # gcp will need this
            if cloud_norm == "azure":
                org_shard_id = int(org_id) % 20
                org_shard = f".{org_shard_id}"

            url_base_path_no_port = f"/driver-proxy/o/{org_id}/{cluster_id}"
            url_base_path = f"{url_base_path_no_port}/{port}/"
            proxy_url = f"{prefix_url_settings[cloud_norm]}{org_id}{org_shard}.{suffix_url_settings[cloud_norm]}{url_base_path}"
            return proxy_url

        def remove_lowest_subdomain_from_host(url):
            parsed_url = urlparse(url)
            host = parsed_url.netloc if parsed_url.netloc else parsed_url.path
            parts = host.split(".")
            # Check if there are subdomains to remove
            if len(parts) > 2:
                # Remove the lowest subdomain
                parts.pop(0)

            # Reconstruct the modified host
            modified_host = ".".join(parts)

            return modified_host

        proxy_url = get_cloud_proxy_settings(
            cloud="azure" if "https://adb" in self.w.config.host else "aws",
            host=self.w.config.host,
            org_id=organisation_id,
            cluster_id=self.cluster_id_getter(),
            port=8080,
        )
        return proxy_url

    def launch_review_app(self):
        self._library_install()
        self._path_updates()
        org_id = self._get_org_id()
        proxy_url = self._get_proxy_url(org_id)
        logging.info(
            f"Launching review app, it may take a few minutes to come up. Visit below link to access the app.\n{proxy_url}"
        )
        print(
            f"Launching review app, it may take a few minutes to come up. Visit below link to access the app.\n{proxy_url}"
        )
        self._launch_app()

        return
