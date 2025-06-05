import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Constants
SERVING_ENDPOINT_NAME = os.getenv("SERVING_ENDPOINT_NAME")
assert SERVING_ENDPOINT_NAME, "SERVING_ENDPOINT_NAME is not set"

DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")

# API Configuration
API_TIMEOUT = 30.0
MAX_CONCURRENT_STREAMS = 10
MAX_QUEUE_SIZE = 100