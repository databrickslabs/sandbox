from databricks.sdk import WorkspaceClient
from databricks.sdk.service import compute
from .helpers import Language, parse_command_output


class ContextHandler:
    def __init__(self, client: WorkspaceClient, cluster_id: str, language: Language):
        self._client = client
        self._cluster_id = cluster_id
        self._language = language
        self._context_id = client.command_execution.create_and_wait(
            cluster_id=self._cluster_id, language=self._language
        ).id

    def close(self):
        self._client.command_execution.destroy(self._cluster_id, self._context_id)
        pass

    def execute(self, cmd):
        result_raw = self._client.command_execution.execute_and_wait(
            cluster_id=self._cluster_id,
            command=cmd,
            context_id=self._context_id,
            language=self._language,
        )
        result_parsed = parse_command_output(result_raw, self._language)
        if result_parsed is not None:
            print(result_parsed)
        return result_parsed
