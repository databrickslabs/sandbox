import json
import os
from databricks.labs.lsql.core import StatementExecutionExt
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import InvalidParameterValue
from pathlib import Path
import gradio as gr

from app.llm import LLMCalls
from app.similar_code import SimilarCode
import logging  # For printing translation attempts in console (debugging)

# Setting up logger
logging.basicConfig
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# # personal access token necessary for authenticating API requests. Stored using a secret

FOUNDATION_MODEL_NAME = os.environ.get("SERVED_FOUNDATION_MODEL_NAME")
MAX_TOKENS = os.environ.get("MAX_TOKENS")
SQL_WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID")
VECTOR_SEARCH_ENDPOINT_NAME = os.environ.get("VECTOR_SEARCH_ENDPOINT_NAME")
VS_INDEX_NAME = os.environ.get("VS_INDEX_NAME")
CODE_INTENT_TABLE_NAME = os.environ.get("CODE_INTENT_TABLE_NAME")
CATALOG = os.environ.get("CATALOG")
SCHEMA = os.environ.get("SCHEMA")
VOLUME_NAME_INPUT_PATH = os.environ.get("VOLUME_NAME_INPUT_PATH")
VOLUME_NAME = os.environ.get("VOLUME_NAME")
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST")
TRANSFORMATION_JOB_ID = os.environ.get("TRANSFORMATION_JOB_ID")
WORKSPACE_LOCATION = os.environ.get("WORKSPACE_LOCATION")
w = WorkspaceClient(product="sql_migration_assistant", product_version="0.0.1")

see = StatementExecutionExt(w, warehouse_id=SQL_WAREHOUSE_ID)
translation_llm = LLMCalls(foundation_llm_name=FOUNDATION_MODEL_NAME)
intent_llm = LLMCalls(foundation_llm_name=FOUNDATION_MODEL_NAME)
similar_code_helper = SimilarCode(
    workspace_client=w,
    see=see,
    catalog=CATALOG,
    schema=SCHEMA,
    code_intent_table_name=CODE_INTENT_TABLE_NAME,
    VS_index_name=VS_INDEX_NAME,
    VS_endpoint_name=VECTOR_SEARCH_ENDPOINT_NAME,
)

################################################################################
################################################################################

# this is the app UI. it uses gradio blocks https://www.gradio.app/docs/gradio/blocks
# each gr.{} call adds a new element to UI, top to bottom.
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    # title with Databricks image
    gr.Markdown(
        """<img align="right" src="https://asset.brandfetch.io/idSUrLOWbH/idm22kWNaH.png" alt="logo" width="120">

# Databricks Legion Migration Accelerator

Legion is an AI powered tool that aims to accelerate the migration of code to Databricks for low cost and effort. It 
does this by using AI to translate, explain, and make discoverable your code. 

This interface is the Legion Control Panel. Here you are able to configure the AI agents for translation and explanation
to fit your needs, incorporating your expertise and knowledge of the codebase by adjusting the AI agents' instructions.

Please select a tab to get started.   

"""
    )
    ################################################################################
    #### STORAGE SETTINGS TAB
    ################################################################################
    with gr.Tab(label="Test file"):

        gr.Markdown(
            f"""## Select a file to test your agents on.   
           
           Legion can batch process a volume of files to generate Databricks notebooks. The files to translate must be 
           added to the *Input Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}). 
           
           Here you can select a file to fine tune your agent prompts against. 
            """
        )
        volume_path = gr.Textbox(value=VOLUME_NAME_INPUT_PATH, visible=False)

        load_files = gr.Button("Load Files from Volume")
        select_code_file = gr.Radio(label="Select Code File")
        selected_file = gr.Code(label="Selected Code File", language="sql-msSQL")

        def list_files(path_to_volume):
            file_infos = w.dbutils.fs.ls(path_to_volume)
            file_names = [x.name for x in file_infos]
            file_name_radio = gr.Radio(label="Select Code File", choices=file_names)
            return file_name_radio

        load_files.click(list_files, volume_path, select_code_file)

        def read_code_file(volume_path, file_name):
            file_name = os.path.join(volume_path, file_name)
            file = w.files.download(file_name)
            code = file.contents.read().decode("utf-8")
            return code

    ################################################################################
    #### EXPLANATION TAB
    ################################################################################
    with gr.Tab(label="Code Explanation"):
        gr.Markdown(
            """
        ## An AI tool to generate the intent of your code.

        In this panel you need to iterate on the system prompt to refine the intent the AI generates for your code.
        This intent will be stored in Unity Catalog, and can be used for finding similar code, for documentation, 
         and to help with writing new code in Databricks to achieve the same goal.
        """
        )
        with gr.Accordion(label="Advanced Intent Settings", open=True):
            gr.Markdown(
                """ ### Advanced settings for the generating the intent of the input code.
                
                The *Temperature* paramater controls the randomness of the AI's response. Higher values will result in 
                more creative responses, while lower values will result in more predictable responses.
                """
            )

            with gr.Row():
                intent_temperature = gr.Number(
                    label="Temperature. Float between 0.0 and 1.0", value=0.0
                )
                intent_max_tokens = gr.Number(
                    label="Max tokens. Check your LLM docs for limit.", value=3500
                )
            with gr.Row():
                intent_system_prompt = gr.Textbox(
                    label="System prompt of the LLM to generate the intent.",
                    value="""Your job is to explain intent of the provided SQL code.
                            """.strip(),
                )
        with gr.Accordion(label="Intent Pane", open=True):
            gr.Markdown(
                """ ## AI generated intent of what your code aims to do. 
                        """
            )
            explain_button = gr.Button("Explain")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Code loaded from Unity Catalog.""")

                    # input box for SQL code with nice formatting
                    intent_input_code = gr.Code(
                        label="Input SQL",
                        language="sql-msSQL",
                    )
                    # a button labelled translate

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Code intent""")
                    # output box of the T-SQL translated to Spark SQL
                    explained = gr.Textbox(label="AI generated intent of your code.")

            def llm_intent_wrapper(system_prompt, input_code, max_tokens, temperature):
                # call the LLM to translate the code
                intent = intent_llm.llm_intent(
                    system_prompt, input_code, max_tokens, temperature
                )
                return intent

            # reset hidden chat history and prompt
            # do translation
            explain_button.click(
                fn=llm_intent_wrapper,
                inputs=[
                    intent_system_prompt,
                    intent_input_code,
                    intent_max_tokens,
                    intent_temperature,
                ],
                outputs=explained,
            )
    ################################################################################
    #### TRANSLATION TAB
    ################################################################################
    with gr.Tab(label="Translation"):
        gr.Markdown(
            """
        ## An AI tool to translate your code.

        In this panel you need to iterate on the system prompt to refine the translation the AI generates for your code.
      
        """
        )
        with gr.Accordion(label="Translation Advanced Settings", open=True):
            gr.Markdown(
                """ ### Advanced settings for the translating the input code.

                The *Temperature* paramater controls the randomness of the AI's response. Higher values will result in 
                more creative responses, while lower values will result in more predictable responses.
                """
            )
            with gr.Row():
                translation_temperature = gr.Number(
                    label="Temperature. Float between 0.0 and 1.0", value=0.0
                )
                translation_max_tokens = gr.Number(
                    label="Max tokens. Check your LLM docs for limit.", value=3500
                )
            with gr.Row():
                translation_system_prompt = gr.Textbox(
                    label="Instructions for the LLM translation tool.",
                    value="""
                              You are an expert in multiple SQL dialects. You only reply with SQL code and with no other text. 
                              Your purpose is to translate the given SQL query to Databricks Spark SQL. 
                              You must follow these rules:
                              - You must keep all original catalog, schema, table, and field names.
                              - Convert all dates to dd-MMM-yyyy format using the date_format() function.
                              - Subqueries must end with a semicolon.
                              - Ensure queries do not have # or @ symbols.
                              - ONLY if the original query uses temporary tables (e.g. "INTO #temptable"), re-write these as either CREATE OR REPLACE TEMPORARY VIEW or CTEs. .
                              - Square brackets must be replaced with backticks.
                              - Custom field names should be surrounded by backticks. 
                              - Ensure queries do not have # or @ symbols.
                              - Only if the original query contains DECLARE and SET statements, re-write them according to the following format:
                                    DECLARE VARIABLE variable TYPE DEFAULT value; For example: DECLARE VARIABLE number INT DEFAULT 9;
                                    SET VAR variable = value; For example: SET VAR number = 9;
                              
                            Write an initial draft of the translated query. Then double check the output for common mistakes, including:
                            - Using NOT IN with NULL values
                            - Using UNION when UNION ALL should have been used
                            - Using BETWEEN for exclusive ranges
                            - Data type mismatch in predicates
                            - Properly quoting identifiers
                            - Using the correct number of arguments for functions
                            - Casting to the correct data type
                            - Using the proper columns for joins
                            
                            Return the final translated query only. Include comments. Include only SQL.
                            """.strip(),
                    lines=20,
                )

        with gr.Accordion(label="Translation Pane", open=True):
            gr.Markdown(""" ### Input your code here for translation to Spark-SQL.""")
            # a button labelled translate
            translate_button = gr.Button("Translate")
            with gr.Row():
                with gr.Column():
                    gr.Markdown(""" ## Code loaded from Unity Catalog.""")

                    # input box for SQL code with nice formatting
                    translation_input_code = gr.Code(
                        label="Input SQL",
                        language="sql-msSQL",
                    )

                with gr.Column():
                    # divider subheader
                    gr.Markdown(""" ## Translated Code""")
                    # output box of the T-SQL translated to Spark SQL
                    translated = gr.Code(
                        label="Your code translated to Spark SQL",
                        language="sql-sparkSQL",
                    )

            # helper function to take the output from llm_translate and return outputs for chatbox and textbox
            # chatbox input is a list of lists, each list is a message from the user and the response from the LLM
            # textbox input is a string
            def llm_translate_wrapper(
                system_prompt, input_code, max_tokens, temperature
            ):
                # call the LLM to translate the code
                translated_code = translation_llm.llm_translate(
                    system_prompt, input_code, max_tokens, temperature
                )
                return translated_code

            # reset hidden chat history and prompt
            # do translation
            translate_button.click(
                fn=llm_translate_wrapper,
                inputs=[
                    translation_system_prompt,
                    translation_input_code,
                    translation_max_tokens,
                    translation_temperature,
                ],
                outputs=translated,
            )

    ################################################################################
    #### SIMILAR CODE TAB
    ################################################################################
    with gr.Tab(label="Find Similar Code"):
        gr.Markdown(
            """
        # ** Work in Progress **
        ## An AI tool to find similar code.
        """
        )
        with gr.Accordion(label="Similar Code Pane", open=True):
            gr.Markdown(
                """ ## Similar code 
                        
                        This code is thought to be similar to what you are doing, based on comparing the intent of your code with the intent of this code.
                        """
            )
            # a button
            find_similar_code = gr.Button("Find similar code")
            # a row with an code and text box to show the similar code
            with gr.Row():
                similar_code_input = gr.Code(
                    label="Input Code.", language="sql-sparkSQL"
                )
                similar_code_output = gr.Code(
                    label="Similar code to yours.", language="sql-sparkSQL"
                )
                similar_intent = gr.Textbox(label="The similar codes intent.")

            # a button
            submit = gr.Button("Save code and intent")

            # assign actions to buttons when clicked.
        find_similar_code.click(
            fn=similar_code_helper.get_similar_code,
            inputs=similar_code_input,
            outputs=[similar_code_output, similar_intent],
        )

        def save_intent_wrapper(input_code, explained):
            gr.Info("Saving intent")
            similar_code_helper.save_intent(input_code, explained)
            gr.Info("Intent saved")

        submit.click(save_intent_wrapper, inputs=[translation_input_code, explained])

    ################################################################################
    #### EXECUTE JOB TAB
    ################################################################################
    with gr.Tab(label="Execute Job"):
        gr.Markdown(
            """ ## Execute Job

            This tab is for executing the job to covert the code files in the Unity Catalog Volume to Databricks 
            Notebooks. Once you are happy with your system prompts and and the explanation and translation outputs, 
            click the execute button below. 
            
            This will kick off a Workflow which will ingest the code files, write them to a Delta Table, apply the AI
            agents, and output a Databricks Notebook per input code file. This notebook will have the intent at the top 
            of the notebook in a markdown cell, and the translated code in the cell below.
            
            The intent will also be stored in a Unity Catalog table and vector search index for finding similar code. 
            """
        )
        execute = gr.Button(
            value="EXECUTE CODE TRANSFORMATION",
            size="lg",
        )
        run_status = gr.Markdown(label="Job Status Page", visible=False)

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
                "VOLUME_NAME_CHECKPOINT_PATH": os.environ.get(
                    "VOLUME_NAME_CHECKPOINT_PATH"
                ),
                "CATALOG": os.environ.get("CATALOG"),
                "SCHEMA": os.environ.get("SCHEMA"),
                "DATABRICKS_HOST": DATABRICKS_HOST,
                "DATABRICKS_TOKEN_SECRET_SCOPE": os.environ.get(
                    "DATABRICKS_TOKEN_SECRET_SCOPE"
                ),
                "DATABRICKS_TOKEN_SECRET_KEY": os.environ.get(
                    "DATABRICKS_TOKEN_SECRET_KEY"
                ),
                "CODE_INTENT_TABLE_NAME": os.environ.get("CODE_INTENT_TABLE_NAME"),
                "WORKSPACE_LOCATION":WORKSPACE_LOCATION,
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
            textbox_message = (f"Job run initiated. Click [here]({job_url}) to view the job status. "
                               f"You just executed the run with run_id: {run_id}\n"
                               f"Output notebooks will be written to the Workspace for immediate use at {WORKSPACE_LOCATION}/outputNotebooks"
                               f", and also in the *Output Code* folder in the UC Volume [here]({DATABRICKS_HOST}/explore/data/volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME})"
                               )
            return textbox_message

        def make_status_box_visible():
            return gr.Markdown(label="Job Run Status Page", visible=True)

        execute.click(fn=make_status_box_visible, outputs=run_status)
        execute.click(
            exectute_workflow,
            inputs=[
                intent_system_prompt,
                intent_temperature,
                intent_max_tokens,
                translation_system_prompt,
                translation_temperature,
                translation_max_tokens,
            ],
            outputs=run_status,
        )

    # read the selected code file and put it into the other panes
    for output in [
        selected_file,
        translation_input_code,
        intent_input_code,
        similar_code_input,
    ]:
        select_code_file.select(
            fn=read_code_file, inputs=[volume_path, select_code_file], outputs=output
        )

# for local dev
try:
    if os.environ["LOCALE"] == "local_dev":
        demo.queue().launch()
except KeyError:
    pass

# this is necessary to get the app to run on databricks
if __name__ == "__main__":
    demo.queue().launch(
        server_name=os.getenv("GRADIO_SERVER_NAME"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT")),
    )
