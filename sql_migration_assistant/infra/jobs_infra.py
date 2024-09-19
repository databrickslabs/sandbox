from databricks.sdk import WorkspaceClient
from databricks.sdk.errors.platform import BadRequest
from databricks.labs.blueprint.tui import Prompts
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk.service.jobs import Task, NotebookTask
import os
"""
Approach

User first sets all configuration options
validate options
validate user permissions
then create infra
upload app file to databricks

"""


class JobsInfra:
    def __init__(
        self,
        config,
        workspace_client: WorkspaceClient,
        p: Prompts,
        see: StatementExecutionExt,
    ):
        self.w = workspace_client
        self.config = config
        self.prompts = p
        self.see = see

        self.job_name ="sql_migration_transformation"
        self.job_notebook_name="job"
        self.job_tasks = [
            Task(
                task_key="transform_code",
                notebook_task=NotebookTask(
                    notebook_path=f"/Workspace/Users/{self.w.current_user.me().user_name}/.sql_migration_assistant/sql_migration_assistant/{self.job_notebook_name}"
                ),
            )
        ]

    def create_transformation_job(self):
        job_id = self.w.jobs.create(
            name=self.job_name,
            tasks=self.job_tasks,
        )
        self.config["TRANSFORMATION_JOB_ID"] = job_id
