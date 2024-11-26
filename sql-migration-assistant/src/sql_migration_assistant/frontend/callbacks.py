import base64
import datetime
import json
import os

import gradio as gr
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from openai import OpenAI

from sql_migration_assistant.app.llm import LLMCalls
from sql_migration_assistant.app.prompt_helper import PromptHelper
from sql_migration_assistant.app.similar_code import SimilarCode
from sql_migration_assistant.config import (
    FOUNDATION_MODEL_NAME,
    SQL_WAREHOUSE_ID,
    CATALOG,
    SCHEMA,
    CODE_INTENT_TABLE_NAME,
    VECTOR_SEARCH_ENDPOINT_NAME,
    VS_INDEX_NAME,
    DATABRICKS_HOST,
    TRANSFORMATION_JOB_ID,
    WORKSPACE_LOCATION,
    VOLUME_NAME,
    DATABRICKS_TOKEN,
    PROMPT_HISTORY_TABLE_NAME,
)

openai_client = OpenAI(
    api_key=DATABRICKS_TOKEN, base_url=f"{DATABRICKS_HOST}/serving-endpoints"
)

w = WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1")
see = StatementExecutionExt(w, warehouse_id=SQL_WAREHOUSE_ID)
translation_llm = LLMCalls(openai_client, foundation_llm_name=FOUNDATION_MODEL_NAME)
intent_llm = LLMCalls(openai_client, foundation_llm_name=FOUNDATION_MODEL_NAME)

prompt_helper = PromptHelper(
    see=see, catalog=CATALOG, schema=SCHEMA, prompt_table=PROMPT_HISTORY_TABLE_NAME
)
similar_code_helper = SimilarCode(
    workspace_client=w,
    see=see,
    catalog=CATALOG,
    schema=SCHEMA,
    code_intent_table_name=CODE_INTENT_TABLE_NAME,
    VS_index_name=VS_INDEX_NAME,
    VS_endpoint_name=VECTOR_SEARCH_ENDPOINT_NAME,
)


def list_files(path_to_volume):
    file_infos = w.dbutils.fs.ls(path_to_volume)
    file_names = [x.name for x in file_infos]
    return file_names


def make_status_box_visible():
    return gr.Markdown(label="Job Run Status Page", visible=True)


def read_code_file(volume_path, file_name):
    file_name = os.path.join(volume_path, file_name)
    file = w.files.download(file_name)
    code = file.contents.read().decode("utf-8")
    return code


def llm_intent_wrapper(system_prompt, input_code, max_tokens, temperature):
    intent = intent_llm.llm_intent(system_prompt, input_code, max_tokens, temperature)
    return intent


def llm_translate_wrapper(system_prompt, input_code, max_tokens, temperature):
    translated_code = translation_llm.llm_translate(
        system_prompt, input_code, max_tokens, temperature
    )
    return translated_code


def produce_preview(explanation, translated_code):
    template = """
    -- Databricks notebook source
    -- MAGIC %md
    -- MAGIC # This notebook was AI generated. AI can make mistakes. This is provided as a tool to accelerate your migration. 
    -- MAGIC
    -- MAGIC ### AI Generated Intent
    -- MAGIC
    -- MAGIC INTENT_GOES_HERE

    -- COMMAND ----------

    TRANSLATED_CODE_GOES_HERE
    """
    preview_code = template.replace("INTENT_GOES_HERE", explanation).replace(
        "TRANSLATED_CODE_GOES_HERE", translated_code
    )
    return preview_code


def write_adhoc_to_workspace(file_name, preview):
    if len(file_name) == 0:
        raise gr.Error("Please provide a filename")

    notebook_path_root = f"{WORKSPACE_LOCATION}/outputNotebooks/{str(datetime.datetime.now()).replace(':', '_')}"
    notebook_path = f"{notebook_path_root}/{file_name}"
    content = preview
    w.workspace.mkdirs(notebook_path_root)
    w.workspace.import_(
        content=base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        path=notebook_path,
        format=ImportFormat.SOURCE,
        language=Language.SQL,
        overwrite=True,
    )
    _ = w.workspace.get_status(notebook_path)
    id = _.object_id
    url = f"{w.config.host}/#notebook/{id}"
    output_message = f"Notebook {file_name} written to Databricks [here]({url})"
    return output_message


def exectute_workflow(
    intent_prompt,
    intent_temperature,
    intent_max_tokens,
    translation_prompt,
    translation_temperature,
    translation_max_tokens,
):
    gr.Info("Beginning code transformation workflow")
    agent_config_payload = [
        [
            {
                "translation_agent": {
                    "system_prompt": translation_prompt,
                    "endpoint": FOUNDATION_MODEL_NAME,
                    "max_tokens": translation_max_tokens,
                    "temperature": translation_temperature,
                }
            }
        ],
        [
            {
                "explanation_agent": {
                    "system_prompt": intent_prompt,
                    "endpoint": FOUNDATION_MODEL_NAME,
                    "max_tokens": intent_max_tokens,
                    "temperature": intent_temperature,
                }
            }
        ],
    ]

    app_config_payload = {
        "VOLUME_NAME_OUTPUT_PATH": os.environ.get("VOLUME_NAME_OUTPUT_PATH"),
        "VOLUME_NAME_INPUT_PATH": os.environ.get("VOLUME_NAME_INPUT_PATH"),
        "VOLUME_NAME_CHECKPOINT_PATH": os.environ.get("VOLUME_NAME_CHECKPOINT_PATH"),
        "CATALOG": os.environ.get("CATALOG"),
        "SCHEMA": os.environ.get("SCHEMA"),
        "DATABRICKS_HOST": DATABRICKS_HOST,
        "DATABRICKS_TOKEN_SECRET_SCOPE": os.environ.get(
            "DATABRICKS_TOKEN_SECRET_SCOPE"
        ),
        "DATABRICKS_TOKEN_SECRET_KEY": os.environ.get("DATABRICKS_TOKEN_SECRET_KEY"),
        "CODE_INTENT_TABLE_NAME": os.environ.get("CODE_INTENT_TABLE_NAME"),
        "WORKSPACE_LOCATION": WORKSPACE_LOCATION,
    }

    app_configs = json.dumps(app_config_payload)
    agent_configs = json.dumps(agent_config_payload)

    response = w.jobs.run_now(
        job_id=int(TRANSFORMATION_JOB_ID),
        job_parameters={
            "agent_configs": agent_configs,
            "app_configs": app_configs,
        },
    )
    run_id = response.run_id

    job_url = f"{DATABRICKS_HOST}/jobs/{TRANSFORMATION_JOB_ID}"
    textbox_message = (
        f"Job run initiated. Click [here]({job_url}) to view the job status. "
        f"You just executed the run with run_id: {run_id}\n"
        f"Output notebooks will be written to the Workspace for immediate use at *{WORKSPACE_LOCATION}/outputNotebooks*"
        f", and also in the *Output Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME})"
    )
    return textbox_message


def save_intent_wrapper(input_code, explained):
    gr.Info("Saving intent")
    similar_code_helper.save_intent(input_code, explained)
    gr.Info("Intent saved")


# retreive the row from the table and populate the system prompt, temperature, and max tokens
def get_prompt_details(prompt_id, prompts):
    prompt = prompts[prompts["id"] == prompt_id]
    return [
        prompt["Prompt"].values[0],
        prompt["Temperature"].values[0],
        prompt["Max Tokens"].values[0],
    ]
