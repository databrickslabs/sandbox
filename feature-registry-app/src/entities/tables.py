from typing import Tuple

from databricks import sdk


class Table:
    def __init__(self, uc_table: sdk.service.catalog.TableInfo):
        self.uc_table = uc_table

    def full_name(self) -> str:
        return self.uc_table.full_name

    def name(self) -> str:
        return self.uc_table.name

    def schema(self) -> str:
        return self.uc_table.schema_name

    def components(self) -> Tuple[str, str, str]:
        return self.uc_table.catalog_name, self.uc_table.schema_name, self.uc_table.name
