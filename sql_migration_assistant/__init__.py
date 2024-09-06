from sql_migration_assistant.utils.initialsetup import SetUpMigrationAssistant
from databricks.sdk import WorkspaceClient
from databricks.labs.blueprint.tui import Prompts
import yaml


def hello():
    w = WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1")
    p = Prompts()
    setter_upper = SetUpMigrationAssistant()
    final_config = setter_upper.setup_migration_assistant(w, p)
    with open("sql_migration_assistant/config.yml", "w") as f:
        yaml.dump(final_config, f)
    setter_upper.upload_files(w)
    setter_upper.launch_review_app(w, final_config)
