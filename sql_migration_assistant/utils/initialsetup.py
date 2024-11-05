import logging
import os

from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk.errors import ResourceAlreadyExists, BadRequest
from databricks.sdk.errors.platform import PermissionDenied

from sql_migration_assistant.infra.app_serving_cluster_infra import (
    AppServingClusterInfra,
)
from sql_migration_assistant.infra.chat_infra import ChatInfra
from sql_migration_assistant.infra.jobs_infra import JobsInfra
from sql_migration_assistant.infra.secrets_infra import SecretsInfra
from sql_migration_assistant.infra.sql_warehouse_infra import SqlWarehouseInfra
from sql_migration_assistant.infra.unity_catalog_infra import UnityCatalogInfra
from sql_migration_assistant.infra.vector_search_infra import VectorSearchInfra
from sql_migration_assistant.utils.run_review_app import RunReviewApp
from sql_migration_assistant.utils.upload_files_to_workspace import FileUploader


class SetUpMigrationAssistant:

    # this is a decorator to handle errors and do a retry where user is asked to choose an existing resource
    def _handle_errors(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PermissionDenied:
                logging.error(
                    "You do not have permission to create the requested resource. Please ask your admin to grant"
                    " you permission or choose an existing resource."
                )
                return func(*args, **kwargs)
            except ResourceAlreadyExists:
                logging.error(
                    "Resource already exists. Please choose an alternative resource."
                )
                return func(*args, **kwargs)
            except BadRequest as e:
                if "Cannot write secrets" in str(e):
                    logging.error(
                        "Cannot write secrets to Azure KeyVault-backed scope. Please choose an alternative "
                        "secret scope."
                    )
                    return func(*args, **kwargs)
                else:
                    raise e

        return wrapper

    @_handle_errors
    def set_up_cluster(self, config, w, p):
        app_cluster_infra = AppServingClusterInfra(config, w, p)
        logging.info("Choose or create app serving cluster")
        app_cluster_infra.choose_serving_cluster()
        return app_cluster_infra.config

    @_handle_errors
    def create_sql_warehouse(self, config, w, p):
        sql_infra = SqlWarehouseInfra(config, w, p)
        logging.info("Choose or create warehouse")
        sql_infra.choose_compute()
        return sql_infra.config

    @_handle_errors
    def setup_uc_infra(self, config, w, p, see):
        uc_infra = UnityCatalogInfra(config, w, p, see)
        logging.info("Choose or create catalog")
        uc_infra.choose_UC_catalog()
        logging.info("Choose or create schema")
        uc_infra.create_schema()
        logging.info("Create code intent table")
        uc_infra.create_tables()
        return uc_infra.config

    @_handle_errors
    def setup_vs_infra(self, config, w, p):
        vs_infra = VectorSearchInfra(config, w, p)
        logging.info("Choose or create VS endpoint")
        vs_infra.choose_VS_endpoint()
        logging.info("Choose or create embedding model")
        vs_infra.choose_embedding_model()
        logging.info("Create VS index")
        vs_infra.create_VS_index()
        return vs_infra.config

    # no need to handle errors, no user input
    def setup_job(self, config, w):
        job_infra = JobsInfra(config, w)
        logging.info("Create transformation job")
        job_infra.create_transformation_job()
        return job_infra.config

    @_handle_errors
    def setup_chat_infra(self, config, w, p):
        chat_infra = ChatInfra(config, w, p)
        logging.info("Choose or create foundation model infra")
        chat_infra.setup_foundation_model_infra()
        return chat_infra.config

    @_handle_errors
    def setup_secrets_infra(self, config, w, p):
        secrets_infra = SecretsInfra(config, w, p)
        logging.info("Set up secret")
        secrets_infra.create_secret_PAT()
        return secrets_infra.config

    def update_config(self, w, config):
        uploader = FileUploader(w)
        config = uploader.update_config(config)
        return config

    def setup_migration_assistant(self, w, p):
        logging.info("Setting up infrastructure")
        print("\nSetting up infrastructure")
        # create empty config dict to fill in
        config = {}
        ############################################################
        logging.info("Choose or create cluster to host review app")
        print("\nChoose or create cluster to host review app")
        config = self.set_up_cluster(config, w, p)

        ############################################################
        logging.info("***Choose a Databricks SQL Warehouse***")
        print("\n***Choose a Databricks SQL Warehouse***")
        config = self.create_sql_warehouse(config, w, p)
        # create a StatementExecutionExt object to execute SQL commands with the warehouse just created / assigned
        see = StatementExecutionExt(w, warehouse_id=config["DATABRICKS_WAREHOUSE_ID"])

        ############################################################
        logging.info("Setting up Unity Catalog infrastructure")
        print("\nSetting up Unity Catalog infrastructure")
        config = self.setup_uc_infra(config, w, p, see)

        ############################################################
        logging.info("Setting up Vector Search infrastructure")
        print("\nSetting up Vector Search infrastructure")
        config = self.setup_vs_infra(config, w, p)

        ############################################################
        logging.info("Setting up Chat infrastructure")
        print("\nSetting up Chat infrastructure")
        config = self.setup_chat_infra(config, w, p)

        ############################################################
        logging.info("Setting up secrets")
        print("\nSetting up secrets")
        config = self.setup_secrets_infra(config, w, p)

        ############################################################
        logging.info("Setting up job")
        print("\nSetting up job")
        config = self.setup_job(config, w)

        ############################################################
        logging.info("Infrastructure setup complete")
        print("\nInfrastructure setup complete")

        config = self.update_config(w, config)
        return config

    def upload_files(self, w, path):
        # all this nastiness becomes unnecessary with lakehouse apps, or if we upload a whl it simplifies things.
        # But for now, this is the way.
        # TODO - MAKE THIS NICE!!
        logging.info("Uploading files to workspace")
        print("\nUploading files to workspace")
        uploader = FileUploader(w)
        files_to_upload = [
            "utils/runindatabricks.py",
            "utils/configloader.py",
            "utils/run_review_app.py",
            "jobs/bronze_to_silver.py",
            "jobs/call_agents.py",
            "jobs/silver_to_gold.py",
            "app/llm.py",
            "app/similar_code.py",
            "main.py",
            "run_app_from_databricks_notebook.py",
            "config.yml",
        ]

        def inner(f):
            full_file_path = os.path.join(path, f)
            logging.info(
                f"Uploading {full_file_path} to {uploader.installer.install_folder()}/{f}"
            )
            uploader.upload(full_file_path, f)

        for f in files_to_upload:
            inner(f)

    def launch_review_app(self, w, config):
        logging.info(
            "Launching review app, please wait. A URL will be provided when the app is ready..."
        )
        print(
            "\nLaunching review app, please wait. A URL will be provided when the app is ready..."
        )
        app_runner = RunReviewApp(w, config)
        app_runner.launch_review_app()

    def check_cloud(self, w):
        host = w.config.host
        if "https://adb" in host:
            pass
        elif ".gcp.databricks" in host:
            raise Exception("GCP is not supported")
        else:
            pass
