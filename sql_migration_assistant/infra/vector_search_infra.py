from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import EndpointCoreConfigInput, ServedEntityInput
from databricks.sdk.service.vectorsearch import (
    EndpointType,
    DeltaSyncVectorIndexSpecRequest,
    PipelineType,
    EmbeddingSourceColumn,
    VectorIndexType,
)
from databricks.sdk.errors.platform import ResourceAlreadyExists, NotFound

from databricks.labs.blueprint.tui import Prompts

import logging
from sql_migration_assistant.utils.uc_model_version import get_latest_model_version
import time


class VectorSearchInfra:
    def __init__(self, config, workspace_client: WorkspaceClient, p: Prompts):
        self.w = workspace_client
        self.config = config
        self.prompts = p

        # set defaults for user to override if they choose
        self.default_VS_endpoint_name = "sql_migration_assistant_vs_endpoint"
        self.default_embedding_endpoint_name = (
            "sql_migration_assistant_bge_large_en_v1_5"
        )
        self.default_embedding_model_UC_path = "system.ai.bge_large_en_v1_5"

        # these are updated as the user makes a choice about which VS endpoint and embedding model to use.
        # the chosen values are then written back into the config file.
        self.migration_assistant_VS_endpoint = None
        self.migration_assistant_embedding_model_name = None

        # these are not configurable by the end user
        self.catalog = self.config.get("CATALOG")
        self.schema = self.config.get("SCHEMA")
        self.code_intent_table_name = self.config.get("CODE_INTENT_TABLE_NAME")
        self.vs_index_name = self.code_intent_table_name + "_vs_index"
        self.migration_assistant_VS_index = (
            f"{self.catalog}.{self.schema}.{self.vs_index_name}"
        )
        self.migration_assistant_VS_table = (
            f"{self.catalog}.{self.schema}.{self.code_intent_table_name}"
        )

        # update config with vs index name
        self.config["VS_INDEX_NAME"] = self.vs_index_name

    def choose_VS_endpoint(self):
        """Ask the user to choose an existing vector search endpoint or create a new one."""
        endpoints = [
            f"CREATE NEW VECTOR SEARCH ENDPOINT: {self.default_VS_endpoint_name}"
        ]
        # Create a list of all endpoints in the workspace. Returns a generator
        _ = list(self.w.vector_search_endpoints.list_endpoints())

        endpoints.extend(
            [f"{endpoint.name} ({endpoint.num_indexes} indices)" for endpoint in _]
        )

        question = "Choose a Vector Search endpoint. Endpoints cannot have more than 50 indices."
        choice = self.prompts.choice(question, endpoints)
        # need only the endpoint name
        if "CREATE NEW VECTOR SEARCH ENDPOINT" in choice:
            self.migration_assistant_VS_endpoint = self.default_VS_endpoint_name
            logging.info(
                f"Creating new VS endpoint {self.migration_assistant_VS_endpoint}."
                f"This will take a few minutes."
                f"Check status here: {self.w.config.host}/compute/vector-search/{self.migration_assistant_VS_endpoint}"
            )
            print(
                f"Creating new VS endpoint {self.migration_assistant_VS_endpoint}."
                f"This will take a few minutes."
                f"Check status here: {self.w.config.host}/compute/vector-search/{self.migration_assistant_VS_endpoint}"
            )
            self._create_VS_endpoint()
        else:
            choice = choice.split(" ")[
                0
            ]  # need to remove the (num indices) part of the string
            self.migration_assistant_VS_endpoint = choice
            # update config with user choice
            self.config["VECTOR_SEARCH_ENDPOINT_NAME"] = (
                self.migration_assistant_VS_endpoint
            )

    def choose_embedding_model(self):
        # list all serving endpoints with a task of embedding
        endpoints = [
            f"CREATE NEW EMBEDDING MODEL ENDPOINT {self.default_embedding_endpoint_name} USING"
            f" {self.default_embedding_model_UC_path}"
        ]
        _ = list(self.w.serving_endpoints.list())
        _ = filter(lambda x: "embedding" in x.task if x.task else False, _)
        endpoints.extend([x.name for x in _])
        question = "Choose an embedding model endpoint:"
        choice = self.prompts.choice(question, endpoints)
        if "CREATE NEW EMBEDDING MODEL ENDPOINT" in choice:
            self.migration_assistant_embedding_model_name = (
                self.default_embedding_endpoint_name
            )
            logging.info(
                f"Creating new model serving endpoint {self.migration_assistant_embedding_model_name}. "
                f"This will take a few minutes."
                f"Check status here: {self.w.config.host}/ml/endpoints/{self.migration_assistant_embedding_model_name}"
            )
            print(
                f"Creating new model serving endpoint {self.migration_assistant_embedding_model_name}. "
                f"This will take a few minutes."
                f"Check status here: {self.w.config.host}/ml/endpoints/{self.migration_assistant_embedding_model_name}"
            )
            self._create_embedding_model_endpoint()
        else:
            self.migration_assistant_embedding_model_name = choice
            # update config with user choice
            self.config["EMBEDDING_MODEL_ENDPOINT_NAME"] = (
                self.migration_assistant_embedding_model_name
            )

    def _create_embedding_model_endpoint(self):

        latest_version = get_latest_model_version(
            model_name=self.default_embedding_model_UC_path
        )
        latest_version = str(latest_version)

        self.w.serving_endpoints.create(
            name=self.migration_assistant_embedding_model_name,
            config=EndpointCoreConfigInput(
                name=self.migration_assistant_embedding_model_name,
                served_entities=[
                    ServedEntityInput(
                        entity_name=self.default_embedding_model_UC_path,
                        entity_version=latest_version,
                        name=self.migration_assistant_embedding_model_name,
                        scale_to_zero_enabled=True,
                        workload_type="GPU_SMALL",
                        workload_size="Small",
                    )
                ],
            ),
        )

    def _create_VS_endpoint(self):
        self.w.vector_search_endpoints.create_endpoint(
            name=self.migration_assistant_VS_endpoint,
            endpoint_type=EndpointType.STANDARD,
        )

    def create_VS_index(self):
        try:
            self.w.vector_search_indexes.create_index(
                name=self.migration_assistant_VS_index,
                endpoint_name=self.migration_assistant_VS_endpoint,
                primary_key="id",
                index_type=VectorIndexType.DELTA_SYNC,
                delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
                    source_table=self.migration_assistant_VS_table,
                    pipeline_type=PipelineType.TRIGGERED,
                    embedding_source_columns=[
                        EmbeddingSourceColumn(
                            embedding_model_endpoint_name=self.migration_assistant_embedding_model_name,
                            name="intent",
                        )
                    ],
                ),
            )
        except ResourceAlreadyExists as e:
            logging.info(
                f"Index {self.migration_assistant_VS_index} already exists. Using existing index."
            )
            print(
                f"Index {self.migration_assistant_VS_index} already exists. Using existing index."
            )
        except NotFound as e:
            if (
                f"Vector search endpoint {self.migration_assistant_VS_endpoint} not found"
                in str(e)
            ):
                logging.info(
                    f"Waiting for Vector Search endpoint to provision. Retrying in 30 seconds."
                )
                print(
                    f"Waiting for Vector Search endpoint to provision. Retrying in 30 seconds."
                )
                time.sleep(30)
                self.create_VS_index()
            else:
                raise e
