from sql_migration_assistant.utils.initialsetup import SetUpMigrationAssistant
from databricks.sdk import WorkspaceClient
from databricks.labs.blueprint.tui import Prompts
import yaml
from pathlib import Path


def hello(**kwargs):
    w = WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1", profile=kwargs.get("profile"))
    p = Prompts()
    setter_upper = SetUpMigrationAssistant()
    setter_upper.check_cloud(w)
    final_config = setter_upper.setup_migration_assistant(w, p)
    current_path = Path(__file__).parent.resolve()

    local_config = str(current_path) + "/config.yml"
    with open(local_config, "w") as f:
        yaml.dump(final_config, f)
    setter_upper.upload_files(w, current_path)
    setter_upper.launch_review_app(w, final_config)