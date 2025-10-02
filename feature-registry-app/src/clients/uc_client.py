from databricks.sdk import WorkspaceClient


class UcClient:
    def __init__(self, user_access_token: str):
        self.w = WorkspaceClient(token=user_access_token, auth_type="pat")

    def get_catalogs(self):
        return self.w.catalogs.list(include_browse=False)

    def get_schemas(self, catalog_name: str):
        return self.w.schemas.list(catalog_name=catalog_name)

    def get_tables(self, catalog_name: str, schema_name: str):
        return self.w.tables.list(catalog_name=catalog_name, schema_name=schema_name)

    def get_table(self, full_name: str):
        return self.w.tables.get(full_name=full_name)

    def get_functions(self, catalog_name: str, schema_name: str):
        return self.w.functions.list(catalog_name=catalog_name, schema_name=schema_name)

    def get_function(self, full_name: str):
        return self.w.functions.get(name=full_name)
