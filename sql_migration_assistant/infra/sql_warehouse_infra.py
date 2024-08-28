from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import CreateWarehouseRequestWarehouseType

from databricks.labs.blueprint.tui import Prompts

import logging

class SqlWarehouseInfra():

    def __init__(self, config, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.config = config
        self.prompts = Prompts()
        self.default_sql_warehouse_name = "sql_migration_assistant_warehouse"


    def choose_compute(self):
        """
        User choose a warehouse which will be used for all migration assistant operations
        """
        warehouses = [f"CREATE A NEW SERVERLESS WAREHOUSE: {self.default_sql_warehouse_name}"]
        _ = list(self.w.warehouses.list())
        warehouse_dict = {warehouse.name: warehouse.id for warehouse in _}

        warehouses.extend([f"Name: {warehouse.name},\tType: {warehouse.warehouse_type.name},\tState: "
                           f"{warehouse.state.name},\tServerless: {warehouse.enable_serverless_compute}"
                           for warehouse in _])

        question=("Choose a warehouse: please enter the number of the warehouse you would like to use.\n"
              "This warehouse will be used for all migration assistant operations, setup and ongoing.")
        choice = self.prompts.choice(question, warehouses)

        if "CREATE A NEW SERVERLESS WAREHOUSE" in choice:
            logging.info(f"Creating a new serverless warehouse {self.default_sql_warehouse_name}.")
            _ =self.w.warehouses.create_and_wait(
                name=self.default_sql_warehouse_name,
                cluster_size="2X-Small",
                max_num_clusters=1,
                enable_serverless_compute=True,
                enable_photon=True,
                warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
                auto_stop_mins=10
            )
            warehouseID = _.id
            logging.info(f"Warehouse status visible at {self.w.config.host}/sql/warehouses/{warehouseID}")
        else:
            warehouse_name = choice.split(",\t")[0].replace("Name: ", "")
            warehouseID = warehouse_dict[warehouse_name]
        # update config with user choice
        self.config['SQL_WAREHOUSE_ID'] = warehouseID
        self.config['SQL_WAREHOUSE_NAME'] = self.default_sql_warehouse_name


