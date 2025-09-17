import os
import json

def get_config() -> dict:
  json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "environment.json")
  assert os.path.exists(json_path), f"Missing environment file: {json_path}. Have you run `databricks bundle run configuration_job`?"
  with open(json_path, "r") as f:
    configs = json.load(f)
  return configs
