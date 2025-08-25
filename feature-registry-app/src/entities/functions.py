from typing import Any, Dict, Tuple

from databricks import sdk
from pydantic import BaseModel


class FeatureFunction(BaseModel):
    function: sdk.service.catalog.FunctionInfo

    def full_name(self) -> str:
        return self.function.full_name

    def components(self) -> Tuple[str, str, Any, Any]:
        return self.full_name(), "feature spec", None, None

    def metadata(self) -> Dict[str, Any] | None:
        return None

    def inputs(self) -> Dict[str, str] | None:
        if self.function.input_params and self.function.input_params.parameters:
            return {p.name: p.type_text for p in self.function.input_params.parameters}
        return None

    def outputs(self) -> Dict[str, str] | None:
        if self.function.return_params and self.function.return_params.parameters:
            return {p.name: p.type_text for p in self.function.return_params.parameters}
        return None

    def code(self) -> str:
        return self.function.routine_definition
