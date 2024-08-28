import mlflow
from mlflow.tracking import MlflowClient
def get_latest_model_version(model_name):
    # need this to get the model version from UC as it's not available directly
    mlflow.set_registry_uri("databricks-uc")
    client = MlflowClient()
    model_version_infos = client.search_model_versions("name = '%s'" % model_name)
    return max([int(model_version_info.version) for model_version_info in model_version_infos]) or 1