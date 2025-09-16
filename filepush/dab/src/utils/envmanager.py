import os
import json

def get_env_config() -> dict:
  environment_path =  os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "environment.json")
  assert os.path.exists(environment_path), f"Missing environment file: {environment_path}. Have you run `databricks bundle run configuration_job`?"
  with open(environment_path, "r") as f:
    configs = json.load(f)
  return configs
