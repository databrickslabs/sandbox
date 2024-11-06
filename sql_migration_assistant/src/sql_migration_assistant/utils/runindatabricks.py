# this is only run from within databricks, hence the import doesn't work in IDE
import threading
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.runtime import *
from dbtunnel import dbtunnel

from sql_migration_assistant.utils.configloader import ConfigLoader
from sql_migration_assistant.utils.run_review_app import RunReviewApp

current_folder = Path(__file__).parent.resolve()


def thread_func(config_path: str):
    cl = ConfigLoader()
    cl.read_yaml_to_env(config_path)
    dbtunnel.kill_port(8080)
    app = "main.py"
    dbtunnel.gradio(path=app).run()


def run_app(config_path: str, debug=False):
    # load config file into environment variables. This is necesarry to create the workspace client
    if debug:
        # this will get the app logs to print in the notebook cell output
        thread_func(config_path)
    else:
        cl = ConfigLoader()
        cl.read_yaml_to_env(config_path)
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        w = WorkspaceClient()

        app_runner = RunReviewApp(w, config)
        proxy_url = app_runner._get_proxy_url(app_runner._get_org_id())
        cluster_id = spark.conf.get("spark.databricks.clusterUsageTags.clusterId")
        proxy_url_split = proxy_url.split("/")
        # replace the cluster id from config which may not be the same as the current cluster id
        proxy_url_split[-3] = cluster_id
        proxy_url = "/".join(proxy_url_split)

        x = threading.Thread(target=lambda: thread_func(config_path))
        x.start()
        print(
            f"Launching review app, it may take a few minutes to come up. Visit below link to access the app.\n{proxy_url}"
        )
