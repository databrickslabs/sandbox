# this is only run from within databricks, hence the import doesn't work in IDE
from pathlib import Path

from dbtunnel import dbtunnel

from sql_migration_assistant.utils.configloader import ConfigLoader

current_folder = Path(__file__).parent.resolve()


def run_app():
    cl = ConfigLoader()
    cl.read_yaml_to_env()
    dbtunnel.kill_port(8080)
    app = str(Path(current_folder, "..", "main.py").absolute())
    dbtunnel.gradio(path=app).run()
