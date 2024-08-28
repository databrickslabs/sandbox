from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import ListClustersFilterBy, State, DataSecurityMode
from databricks.labs.blueprint.tui import Prompts

import logging
class AppServingClusterInfra():
    def __init__(self, config, workspace_client: WorkspaceClient):
        self.w = workspace_client
        self.config = config
        self.prompts = Prompts()
        self.node_types = {"azure": "Standard_DS3_v2", "aws": "m5d.xlarge", "gcp": "n1-standard-4"}
        self.cloud = self._get_cloud()
        self.cluster_name = "sql_migration_assistant_review_app_cluster"
        self.spark_version = "15.4.x-scala2.12"

    def choose_serving_cluster(self):
        question = ("The review application needs a cluster to run on. It is recommended to create a new, single node cluster "
              "for this. Would you like to create a new cluster? (y/n)"
              )
        choice = self.prompts.question(question, validate = lambda x: x.lower() in ['y', 'n'])
        if choice.lower() == "y":
            response = self._create_cluster()
            cluster_name = self.cluster_name
            cluster_id = response.response.cluster_id
        else:
            clusters = self.w.clusters.list(
                filter_by=ListClustersFilterBy(cluster_states=[State.RUNNING])
            )

            # get cluster name and id
            clusters = {cluster.cluster_name:cluster.cluster_id for cluster in clusters}
            if clusters == {}:
                logging.info("No running clusters found. Creating a new cluster.")
                response = self._create_cluster()
                cluster_name = self.cluster_name
                cluster_id = response.response.cluster_id
            else:
                question = "Choose a cluster:"
                cluster_name = self.prompts.choice(question, clusters.keys())
                cluster_id = clusters[cluster_name]

        self.config['SERVING_CLUSTER_NAME'] = cluster_name
        self.config['SERVING_CLUSTER_ID'] = cluster_id

    def _create_cluster(self):
        logging.info("Creating a new single node cluster for the review application.")
        response = self.w.clusters.create(
            spark_version=self.spark_version
            ,autotermination_minutes=120
            ,cluster_name=self.cluster_name
            ,data_security_mode=DataSecurityMode.NONE
            ,spark_conf={
                "spark.databricks.cluster.profile": "singleNode",
                "spark.master": "local[*]",
            }
            ,num_workers=0
            ,node_type_id=self.node_types[self.cloud]
            ,custom_tags={"ResourceClass": "SingleNode"}
        )
        logging.info(f"See cluster state at {self.w.config.host}/compute/clusters/{response.response.cluster_id}")
        return response
    def _get_cloud(self):
        host = self.w.config.host
        if 'https://adb' in host:
            return 'azure'
        elif '.gcp.databricks' in host:
            return 'gcp'
        else:
            return 'aws'


