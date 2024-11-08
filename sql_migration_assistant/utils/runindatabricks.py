# this is only run from within databricks, hence the import doesn't work in IDE
from utils.configloader import ConfigLoader
from utils.run_review_app import RunReviewApp
from dbtunnel import dbtunnel
from databricks.sdk import WorkspaceClient
from databricks.sdk.runtime import *
import threading
import yaml


def run_app():
    cl = ConfigLoader()
    cl.read_yaml_to_env("config.yml")
    dbtunnel.kill_port(8080)
    app = "gradio_app.py"
    dbtunnel.gradio(path=app).run()


