from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from .tables import Table


class MaterializedInfo(BaseModel):
    schema_name: str
    table_name: str
    primary_keys: List[str]
    timeseries_columns: List[str]


class Feature:
    def __init__(
        self, name: str, table: Table, pks: List[str], ts: Optional[List[str]] = None
    ):
        self.name = name
        self.table = table
        self.pks = pks
        self.ts = ts or []

    def get_materialized_info(self) -> MaterializedInfo:
        return MaterializedInfo(
            schema_name=self.table.schema(),
            table_name=self.table.name(),
            primary_keys=self.pks or [],
            timeseries_columns=self.ts or [],
        )

    def description(self) -> str:
        for column in self.table.uc_table.columns:
            if column.name == self.name:
                return column.comment
        return ""

    def components(self) -> Tuple[str, str, str]:
        return self.name, self.table.full_name(), ", ".join(self.pks)

    def metadata(self) -> Dict[str, Any]:
        return {
            "Table Name": self.table.full_name(),
            "Primary Keys": self.pks,
            "Timeseries Columns": self.ts,
            "# of Features": len(self.table.uc_table.columns) - len(self.pks),
            "Table Type": self.table.uc_table.table_type.name,
        }

    def inputs(self) -> Dict[str, str] | None:
        return None

    def outputs(self) -> Dict[str, str] | None:
        return None

    def code(self) -> str:
        return self.table.uc_table.view_definition

    def table_name(self) -> str:
        return self.table.full_name()

    def full_name(self) -> str:
        return f"{self.table.full_name()}.{self.name}"


class SelectableFeature:
    def __init__(self, feature: Feature, selected: bool = False):
        self.feature = feature
        self.selected = selected

    def components(self) -> Tuple[bool, str, str, str]:
        return (self.selected,) + self.feature.components()
