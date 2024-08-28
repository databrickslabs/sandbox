from databricks.sdk import WorkspaceClient

class SQLInterface():

    def __init__(self, warehouseID, catalog, schema):
        self.w = WorkspaceClient()
        self.warehouseID = warehouseID
        self.catalog = catalog
        self.schema = schema

    def execute_sql(self, sql):
        return self.w.statement_execution.execute_statement(
            warehouse_id=self.warehouseID,
            catalog=self.catalog,
            schema=self.schema,
            statement=sql
        )
