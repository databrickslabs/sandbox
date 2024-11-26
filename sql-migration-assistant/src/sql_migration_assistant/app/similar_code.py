from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk import WorkspaceClient


class SimilarCode:

    def __init__(
        self,
        workspace_client: WorkspaceClient,
        see: StatementExecutionExt,
        catalog,
        schema,
        code_intent_table_name,
        VS_index_name,
        VS_endpoint_name,
    ):
        self.w = workspace_client
        self.see = see
        self.catalog = catalog
        self.schema = schema
        self.code_intent_table_name = code_intent_table_name
        self.vs_index_name = VS_index_name
        self.vs_endpoint_name = VS_endpoint_name

    def save_intent(self, code, intent):
        code_hash = hash(code)
        _ = self.see.execute(
            f'INSERT INTO {self.catalog}.{self.schema}.{self.code_intent_table_name} VALUES ({code_hash}, "{code}", "{intent}")',
        )

    def get_similar_code(self, chat_history):
        intent = chat_history[-1][1]
        results = self.w.vector_search_indexes.query_index(
            index_name=f"{self.catalog}.{self.schema}.{self.vs_index_name}",
            columns=["code", "intent"],
            query_text=intent,
            num_results=1,
        )
        docs = results.result.data_array
        return (docs[0][0], docs[0][1])
