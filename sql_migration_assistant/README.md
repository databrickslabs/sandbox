# Databricks Infrastructure Requirements

- A no-isolation shared cluster running the ML runtime (tested on DBR 15.0 ML) to run the notebook 2. Gradio app runner
- A vector search endpoint and an embedding model: see docs https://docs.databricks.com/en/generative-ai/vector-search.html#how-to-set-up-vector-search
- Access to a chat LLM (typically one with the name ending **-instruct**). DBRX is recommended based on it's speed of token generation. Use either the foundation model APIs or Provisioned Throughput to serve an LLM.
- A PAT stored in a secret scope
