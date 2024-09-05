from databricks.sdk import WorkspaceClient

from databricks.labs.blueprint.tui import Prompts

import logging
from sql_migration_assistant.utils.uc_model_version import get_latest_model_version


class ChatInfra:

    def __init__(self, config, workspace_client: WorkspaceClient, p: Prompts):
        self.w = workspace_client
        self.config = config
        self.prompts = p

        # get values from config file
        self.migration_assistant_UC_catalog = self.config.get("CATALOG")
        self.migration_assistant_UC_schema = self.config.get("SCHEMA")

        # these are updated as the user makes a choice about which UC catalog and schema to use.
        # the chosen values are then written back into the config file.
        self.foundation_llm_name = None

        # user cannot change these values
        self.code_intent_table_name = self.config.get("CODE_INTENT_TABLE_NAME")
        self.provisioned_throughput_endpoint_name = "migration_assistant_endpoint"

        # set of pay per token models that can be used
        self.pay_per_token_models = [
            "databricks-meta-llama-3-1-405b-instruct",
            "databricks-meta-llama-3-1-70b-instruct",
            "databricks-dbrx-instruct",
            "databricks-mixtral-8x7b-instruct",
        ]

        # set config with max tokens
        self.config["MAX_TOKENS"] = 4000

    def setup_foundation_model_infra(self):
        """
        This function sets up the foundation model infrastructure. If using pay per token, all that is necessary is to
        choose the model. If using provisioned throughput, the user must choose a model from the system.ai catalog
        and then a scale to zero enabled endpoint is created.

        """
        # check if PPT exists
        if self._pay_per_token_exists():
            question = (
                "Would you like to use an existing pay per token endpoint? This is recommended for quick testing. "
                "The alternative is to create a Provisioned Throughput endpoint, which enables monitoring of "
                "the requests and responses made to the LLM via inference tables. (y/n)"
            )
            choice = self.prompts.question(
                question, validate=lambda x: x.lower() in ["y", "n"]
            )
            if choice.lower() == "y":
                question = "Choose a pay per token model:"
                choice = self.prompts.choice(question, self.pay_per_token_models)
                self.foundation_llm_name = choice
                self.config["SERVED_FOUNDATION_MODEL_NAME"] = self.foundation_llm_name
                return
        # create a provisioned throughput endpoint
        question = "Choose a foundation model from the system.ai schema to deploy:"
        system_models = self._list_models_from_system_ai()
        choice = self.prompts.choice(question, system_models)
        self.foundation_llm_name = choice
        logging.info(
            f"Deploying provisioned throughput endpoint {self.provisioned_throughput_endpoint_name} serving"
            f" {self.foundation_llm_name}. This may take a few minutes."
        )
        self._create_provisioned_throughput_endpoint(self.foundation_llm_name)
        # update config with user choice
        self.config["SERVED_FOUNDATION_MODEL_NAME"] = self.foundation_llm_name
        self.config["PROVISIONED_THROUGHPUT_ENDPOINT_NAME"] = (
            self.provisioned_throughput_endpoint_name
        )

    def _pay_per_token_exists(self):
        """
        Check if the pay per token models exist in the workspace
        """
        endpoints = self.w.serving_endpoints.list()
        endpoint_names = set([ep.name for ep in endpoints])
        pay_per_token_exists = max([x in endpoint_names for x in self.pay_per_token_models])
        return pay_per_token_exists

    def _create_provisioned_throughput_endpoint(self, model_name):
        # SDK does not support creating PT endpoints yet. Use  APIs for now
        # soure: https://databricks.slack.com/archives/C01KSAWFXG8/p1722990775775939
        # this below is pinched from https://docs.databricks.com/en/machine-learning/foundation-models/deploy-prov-throughput-foundation-model-apis.html#create-your-provisioned-throughput-endpoint-using-the-rest-api
        model_name = f"system.ai.{model_name}"
        model_version = get_latest_model_version(model_name)
        endpoint_name = self.provisioned_throughput_endpoint_name
        optimizable_info = self.w.api_client.do(
            method="get",
            path=f"/api/2.0/serving-endpoints/get-model-optimization-info/{model_name}/{model_version}",
        )
        # this check should be unnecessary - but worth putting in just in case
        if "optimizable" not in optimizable_info or not optimizable_info["optimizable"]:
            raise ValueError("Model is not eligible for provisioned throughput")

        chunk_size = optimizable_info["throughput_chunk_size"]
        # Maximum desired provisioned throughput
        max_provisioned_throughput = 2 * chunk_size
        self.w.api_client.do(
            method="post",
            path=f"/api/2.0/serving-endpoints",
            body={
                "name": endpoint_name,
                "config": {
                    "served_entities": [
                        {
                            "entity_name": model_name,
                            "entity_version": model_version,
                            "scale_to_zero_enabled": True,
                            "min_provisioned_throughput": 0,
                            "max_provisioned_throughput": max_provisioned_throughput,
                            # "envrionment_vars": {"ENABLE_MLFLOW_TRACING": True}
                        }
                    ],
                    "auto_capture_config": {
                        "catalog_name": self.migration_assistant_UC_catalog,
                        "schema_name": self.migration_assistant_UC_schema,
                        "table_name_prefix": endpoint_name,
                        "enabled": True,
                    },
                },
            },
        )

    def _list_models_from_system_ai(self):
        system_models = self.w.registered_models.list(
            catalog_name="system", schema_name="ai"
        )
        instruct_system_models = [
            model.name for model in system_models if "instruct" in model.name
        ]
        return instruct_system_models
